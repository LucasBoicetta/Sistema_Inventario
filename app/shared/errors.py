class DomainError(Exception):
    """Clase base para errores de lógica de negocio."""
    def __init__(self, message="Error de regla de negocio."):
        self.message = message
        super().__init__(self.message)

class InsufficientStockError(DomainError):
    """Error lanzado cuando no hay stock suficiente para una operación."""
    def __init__(self, insumo_id, requested, available):
        self.message = f"Stock insuficiente para el insumo {insumo_id}: solicitado {requested}, disponible {available}."
        super().__init__(self.message)

class InvalidProductError(DomainError):
    """Error cuando los datos del producto/insumo no son válidos."""
    pass

class OrderNotReadyError(DomainError):
    """Se lanza cuando se intenta realizar una acción sobre una orden que no cumple los requisitos de estado."""
    pass