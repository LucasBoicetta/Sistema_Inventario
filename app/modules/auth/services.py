from app.shared.models import User, AuditAccion, AuditEstado
from app.shared.audit import AuditService
from flask_jwt_extended import create_access_token, create_refresh_token
from app import db

class AuthenticationError(Exception):
    """Excepción personalizada para errores de login."""
    pass


class AuthService:

    @staticmethod
    def authenticate_user(cedula, password):
        """
        Valida credenciales y retorna tokens o lanza error.
        Retorna: dict con access_token y refresh_token

        Auditoría:
            -LOGIN_EXITOSO: con id_usuario del usuario autenticado.
            -LOGIN_FALLIDO: con motivo (usuario no existe / contraseña incorrecta)
            No revelamos cuál de los dos en el mensaje al usuario (seguridad),
            pero sí lo guardamos en el detalle de auditoría para análisis interno.
        """
        user = db.session.query(User).filter_by(cedula=cedula).first() #Buscar usuario por cédula.

        #Validaciones.
        if not user:
            #Auditamos el intento - no hay id_usuario porque no existe.
            AuditService.log_fallido(
                accion=AuditAccion.LOGIN_FALLIDO,
                detalle={
                    "cedula_intentada": str(cedula),
                    "motivo": "usuario_no_encontrado"
                }
            )
            db.session.commit()
            raise AuthenticationError("Usuario no encontrado")
        
        if not user.check_password(password):
            #Sí tenemos el id_usuario aunque la contraseña sea incorrecta.
            AuditService.log_fallido(
                accion=AuditAccion.LOGIN_FALLIDO,
                entidad_tipo="User",
                entidad_id=user.id_usuario,
                id_usuario_override=user.id_usuario, #Aunque falle el login, sabemos quién intentó loguearse.
                detalle={
                    "cedula": str(cedula),
                    "motivo": "contraseña_incorrecta"
                }
            )
            db.session.commit()
            raise AuthenticationError("Contraseña incorrecta")
        
        #Generamos tokens basados en el ID del usuario.
        access_token = create_access_token(identity=str(user.id_usuario))
        refresh_token = create_refresh_token(identity=str(user.id_usuario))

        AuditService.log(
            accion=AuditAccion.LOGIN_EXITOSO,
            entidad_tipo="User",
            entidad_id=user.id_usuario,
            id_usuario_override=user.id_usuario, #current_user aun no esta cargado en login
            detalle={
                "cedula": str(cedula),
                "nombre":user.nombre,
                "rol": user.rol.nombre_rol,
            }
        )
        db.session.commit()

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user
            }
    
    
    @staticmethod
    def refresh_access(identity):    
        """Genera un nuevo access token usando el refresh token"""
        return create_access_token(identity=identity)
    
    @staticmethod
    def change_password(user, current_password, new_password, confirm_password):
        """Gestiona el cambio de contraseña.
        Lanza AuthenticationError si falla alguna validación.
        Auditoría:
        -CAMBIO_CONTRASEÑA exitoso.
        -CAMBIO_CONTRASEÑA fallido con motivo.
        """
        if not user.check_password(current_password):
            AuditService.log_fallido(
                accion=AuditAccion.CAMBIO_CONTRASEÑA,
                entidad_tipo="User",
                entidad_id=user.id_usuario,
                detalle={
                    "motivo": "contraseña_actual_incorrecta"
                }
            )
            db.session.commit()
            raise AuthenticationError("La contraseña actual es incorrecta.")
        
        if new_password != confirm_password:
            AuditService.log_fallido(
                accion=AuditAccion.CAMBIO_CONTRASEÑA,
                entidad_tipo="User",
                entidad_id=user.id_usuario,
                detalle={
                    "motivo": "confirmacion_no_coincide"
                }
            )
            db.session.commit()
            raise AuthenticationError("La nueva contraseña y su confirmación no coinciden.")
        
        user.set_password(new_password)
        AuditService.log(
            accion=AuditAccion.CAMBIO_CONTRASEÑA,
            entidad_tipo="User",
            entidad_id=user.id_usuario,
            detalle={
                "resultado": "contraseña_actualizada_correctamente"
            }
        )
        db.session.commit()
        return True