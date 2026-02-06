from app.shared.models import User
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
        """
        user = db.session.query(User).filter_by(cedula=cedula).first() #Buscar usuario por cédula.

        #Validaciones.
        if not user:
            raise AuthenticationError("Usuario no encontrado")
        
        if not user.check_password(password):
            raise AuthenticationError("Contraseña incorrecta")
        
        #Generamos tokens basados en el ID del usuario.
        access_token = create_access_token(identity=str(user.id_usuario))
        refresh_token = create_refresh_token(identity=str(user.id_usuario))

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
        """
        if not user.check_password(current_password):
            raise AuthenticationError("La contraseña actual es incorrecta.")
        
        if new_password != confirm_password:
            raise AuthenticationError("La nueva contraseña y su confirmación no coinciden.")
        
        user.set_password(new_password)
        db.session.commit()
        return True