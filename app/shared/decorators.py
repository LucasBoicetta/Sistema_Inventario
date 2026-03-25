
from functools import wraps
from flask import redirect, url_for, flash, make_response
from flask_jwt_extended import verify_jwt_in_request, get_jwt, current_user, unset_jwt_cookies
from flask_jwt_extended.exceptions import NoAuthorizationError, JWTExtendedException



def jwt_required_html(role_required=None):
    """
    Decorador híbrido: Protege la ruta verificando JWT.
    Si falla, redirige al Login.
    Si role_required se especifica, verifica permisos.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                #Intenta verificar el token en cookies.
                verify_jwt_in_request()

            except (NoAuthorizationError, JWTExtendedException):
                #Si el token no existe o expiró.
                flash('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.', 'warning')
                response = make_response(redirect(url_for('auth.login')))
                unset_jwt_cookies(response)
                return response
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator 



def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            
            #Verificacion de Rol( usando el user_lookup_loader )
            if not current_user or current_user.rol.id_rol != 7:
                flash('No tienes permisos para acceder a esta página.', 'danger')
                return redirect(url_for('main.index'))
        
        except (NoAuthorizationError, JWTExtendedException):
            #Token expirado o faltante.
            response = make_response(redirect(url_for('auth.login')))
            unset_jwt_cookies(response)
            return response
        except Exception as e:
            #Error inesperado.
            response = make_response(redirect(url_for('auth.login')))
            unset_jwt_cookies(response)
            return response
        
        return fn(*args, **kwargs)
    return wrapper