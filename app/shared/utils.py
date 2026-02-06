from flask import request

def is_ajax_request():
    """Detecta si la petición actual es AJAX (JSON)."""
    return (request.accept_mimetypes.accept_json and
            not request.accept_mimetypes.accept_html
    ) or request.headers.get('Accept') == 'application/json'