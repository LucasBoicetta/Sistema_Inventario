from flask import request
from flask_jwt_extended import current_user

def is_ajax_request():
    """Detecta si la petición actual es AJAX (JSON)."""
    return (request.accept_mimetypes.accept_json and
            not request.accept_mimetypes.accept_html
    ) or request.headers.get('Accept') == 'application/json'


def get_cart_key():
        """Genera una clave única para el carrito de compras del usuario actual."""
        if current_user and current_user.is_authenticated:
            return f'lista_solicitudes_{current_user.id_usuario}'
        return 'lista_solicitudes' #Fallback (aunque no debería usarse)

def get_quantities_key():
        """Genera una clave única para las cantidades del carrito de compras del usuario actual."""
        if current_user and current_user.is_authenticated:
            return f'cantidades_solicitudes_{current_user.id_usuario}'
        return 'cantidades_solicitudes' #Fallback (aunque no debería usarse)