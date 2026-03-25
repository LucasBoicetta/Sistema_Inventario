import logging
from flask import render_template, request, jsonify

logger = logging.getLogger(__name__)

class DomainError(Exception):
    """Clase base para errores de lógica de negocio."""
    status_code = 400

    def __init__(self, message="Error de regla de negocio.", status_code=None, payload=None):
        super().__init__(self.message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class InsufficientStockError(DomainError):
    """Error lanzado cuando no hay stock suficiente para una operación."""
    def __init__(self, insumo_id, requested, available):
        self.message = f"Stock insuficiente para el insumo {insumo_id}: solicitado {requested}, disponible {available}."
        super().__init__(self.message, status_code=409, payload={'insumo_id': insumo_id, 'solicitado': requested, 'disponible': available})

class InvalidProductError(DomainError):
    """Error cuando los datos del producto/insumo no son válidos."""
    def __init__(self, message="Datos del producto inválidos."):
        super().__init__(message, status_code=422)

class OrderNotReadyError(DomainError):
    """Se lanza cuando se intenta realizar una acción sobre una orden que no cumple los requisitos de estado."""
    def __init__(self, message="La orden no está lista para esta acción."):
        super().__init__(message, status_code=409)


def wants_json_response():
    """Detecta si el cliente espera una respuesta JSON (ej. para APIs) o HTML (para navegadores)."""
    return request.accept_mimetypes.accept_json and \
           not request.accept_mimetypes.accept_html or \
           request.headers.get("Accept") == "application/json"

def register_error_handlers(app):
    """Registra los manejadores de errores globales en la aplicación Flask."""

    @app.errorhandler(DomainError)
    def handle_domain_error(error):
        logger.warning(f"Domain error: {error.message} (Ruta: {request.path})")
        if wants_json_response():
            return jsonify(error.to_dict()), error.status_code
        return render_template('errors/domain_error.html', error=error), error.status_code
    
    @app.errorhandler(404)
    def handle_404_error(error):
        logger.info(f"404 Not Found: {request.path}")
        if wants_json_response():
            return jsonify({'message': 'Recurso no encontrado.'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def handle_500_error(error):
        logger.error(f"500 Internal Server Error: {str(error)} (Ruta: {request.path})", exc_info=True)
        if wants_json_response():
            return jsonify({'message': 'Error interno del servidor.'}), 500
        return render_template('errors/500.html'), 500