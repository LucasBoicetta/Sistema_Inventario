"""
Módulo de validaciones de negocio para carga de insumos.
Centraliza las reglas de validación para reutilizacion entre carga individual, múltiple e importación.
"""
from dataclasses import dataclass
from typing import Optional, Tuple, List
from app.shared.models import Insumo, Proveedor
from app.shared.errors import InvalidProductError
import re


@dataclass
class InsumoInput:
    """
    DTO para datos de entrada de un insumo.
    """
    codigo: str
    descripcion: Optional[str]
    cantidad: int
    proveedor: str
    fila: Optional[int] = None  # Para trazabilidad en cargas masivas por CSV.


@dataclass
class ValidationResult:
    """
    Resultado de validación con detalles de error.
    """
    is_valid: bool
    normalized_input: Optional[InsumoInput] = None
    error_message: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    

class InsumoValidator:
    """Validador centralizado de reglas de negocio para insumos."""

    #Patrones de validación.
    CODIGO_PATTERN = re.compile(r'^[A-Z0-9]{6,10}$')  # Ejemplo: 6-10 caracteres alfanuméricos en mayúscula.
    MIN_DESCRIPCION_LENGTH = 3
    MAX_DESCRIPCION_LENGTH = 200

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normaliza texto: trim, espacios duplicados, capitalización."""
        if not text:
            return ""
        #Remover espacios multiples y trim.
        normalized = ' '.join(text.strip().split()) #Strip elimina espacios al inicio y final, split divide por espacios y join vuelve a unir con un solo espacio.
        return normalized

    @staticmethod
    def normalize_codigo(codigo: str) -> str:
        """Normaliza código: uppercase, sin espacios."""
        if not codigo:
            return "" 
        return codigo.strip().upper().replace(" ", "") #Strip elimina espacios al inicio y final, replace elimina espacios intermedios, upper convierte a mayusculas.
    
    @classmethod
    def validate_single(cls, insumo_input: InsumoInput) -> ValidationResult:
        """
        Valida un insumo individual según las reglas de negocio.
        
        Args:
            insumo_input: Datos del insumo a validar.

        Returns:
            ValidationResult con datos normalizados o errores.
        """
        warnings = []

        #1.Validar código.
        codigo_normalizado = cls.normalize_codigo(insumo_input.codigo)
        if not codigo_normalizado:
            return ValidationResult(is_valid=False, error_message="El código del insumo es obligatorio.")
        
        if not cls.CODIGO_PATTERN.match(codigo_normalizado):
            return ValidationResult(is_valid=False, 
                                    error_message=f"Código inválido {codigo_normalizado}. Ejemplo válido: INS001.")

        #2.Validar cantidad.
        if insumo_input.cantidad <= 0:
            return ValidationResult(is_valid=False, error_message="La cantidad debe ser un número positivo.")

        #3.Validar proveedor.
        proveedor_normalizado = cls.normalize_text(insumo_input.proveedor)
        if not proveedor_normalizado:
            return ValidationResult(is_valid=False, error_message="El nombre del proveedor es obligatorio.")
        
        #4.Validar descripción (solo si es insumo nuevo).
        descripcion_normalizada = None
        if insumo_input.descripcion:
            descripcion_normalizada = cls.normalize_text(insumo_input.descripcion)

            if len(descripcion_normalizada) < cls.MIN_DESCRIPCION_LENGTH:
                return ValidationResult(is_valid=False, 
                                        error_message=f"La descripción debe tener al menos {cls.MIN_DESCRIPCION_LENGTH} caracteres.")
        
            if len(descripcion_normalizada) > cls.MAX_DESCRIPCION_LENGTH:
                return ValidationResult(is_valid=False, 
                                        error_message=f"La descripción no puede exceder {cls.MAX_DESCRIPCION_LENGTH} caracteres.")

        
        #5.Verificar consistencia con BD.
        insumo_existente = Insumo.query.filter_by(codigo_insumo=codigo_normalizado).first()

        if insumo_existente:
            #Si existe, usar descripción de BD.
            descripcion_normalizada = insumo_existente.descripcion

            #Advertencia si hay inconsistencia de nombre.
            if insumo_input.descripcion:
                descripcion_input = cls.normalize_text(insumo_input.descripcion)
                if descripcion_input != insumo_existente.descripcion:
                    warnings.append(
                        f"Nombre ignorado para código existente '{codigo_normalizado}'."
                        f"Se mantiene la descripción original: '{insumo_existente.descripcion}'."   
                    )
        else:
            #Si es nuevo, descripción es obligatoria.
            if not descripcion_normalizada:
                return ValidationResult(is_valid=False, error_message="La descripción es obligatoria para un nuevo insumo.")
        
        #6.Crear input normalizado.
        normalized = InsumoInput(
            codigo=codigo_normalizado,
            descripcion=descripcion_normalizada,
            cantidad=insumo_input.cantidad,
            proveedor=proveedor_normalizado,
            fila=insumo_input.fila
        )

        return ValidationResult(is_valid=True, normalized_input=normalized, warnings=warnings)
    

    @classmethod
    def validate_batch(cls, insumos: List[InsumoInput]) -> Tuple[List[InsumoInput], List[dict]]:
        """
        Valida un lote de insumos.

        Args:
            insumos: Lista de InsumoInput a validar.

        Returns:
            Tupla(insumos_validos, errores)
            -insumos_validos: Lista de InsumoInput normalizados y válidos.
            -errores: Lista de diccionarios con {fila, codigo, error, warnings}.
        """
        validos = []
        errores = []

        for insumo in insumos:
            resultado = cls.validate_single(insumo)

            if resultado.is_valid:
                validos.append(resultado.normalized_input)
            
                #Registrar warnings si existen.
                if resultado.warnings:
                    errores.append({
                        'fila': insumo.fila,
                        'codigo': insumo.codigo,
                        'tipo': 'error',
                        'warnings': resultado.error_message
                    })
                    
        return validos, errores
