"""
Sistema de filtros dinámicos para consultas SQLAlchemy.
Permite construir queries complejas de forma declarativa y segura.
Uso:
    filters = FilterBuilder(EntradaInsumo.query)
    filters.add_date_range('fecha_entrada', date_from, date_to)
    filters.add_like('insumo.descripcion', search_term)
    query = filters.build()
"""

from datetime import datetime, date
from typing import Optional, Any
from sqlalchemy import and_, or_, cast, String
from sqlalchemy.orm import Query

class FilterBuilder:
    """
    Constructor dinámico de filtros para SQLAlchemy.

    Permite encadenar condiciones de forma segura y limpia.
    """
    def __init__(self, base_query: Query):
        """
        Args:
            base_query: Query inicial de SQLAlchemy (ej: Model.query)
        """
        self.query = base_query
        self.conditions = []

    def add_date_range(self, field, date_from: Optional[str] = None, date_to: Optional[str] = None) -> 'FilterBuilder':
        """
        Agrega filtro por rango de fechas.

        Args:
            field: Campo del modelo (ej: EntradaInsumo.fecha_entrada)
            date_from: Fecha inicial en formato 'YYYY-MM-DD'
            date_to: Fecha final en formato 'YYYY-MM-DD'
        
        Returns: 
            self (para encadenamiento)
        """
        if date_from:
            parsed_from = self._parse_date(date_from)
            if parsed_from:
                self.conditions.append(field >= parsed_from)
        
        if date_to:
            parsed_to = self._parse_date(date_to)
            if parsed_to:
                self.conditions.append(field <= parsed_to)
        
        return self


    def add_like(self, field, search_term: Optional[str] = None, case_sensitive: bool = False) -> 'FilterBuilder':
        """
        Agrega filtro de búsqueda parcial (LIKE).

        Args: 
            field: Campo del modelo o relación (ej: Insumo.descripcion)
            search_term: Término de búsqueda
            case_sensitive: Si True, usa LIKE en vez de ILIKE

        Returns: 
            self (para encadenamiento)
        """
        if search_term and search_term.strip():
            search_str = f"%{search_term.strip()}%"
            if case_sensitive:
                self.conditions.append(field.like(search_str))
            else:
                self.conditions.append(field.ilike(search_str))
        
        return self


    def add_exact_match(self, field, value: Optional[Any] = None) -> 'FilterBuilder':
        """
        Agrega filtro de coincidencia exacta.

        Args:
            field: Campo del modelo (ej: Proveedor.id_proveedor)
            value: Valor a comparar
        
        Returns:
            self (para encadenamiento)
        """
        if value is not None and str(value).strip():
            #Convertir a int si es ID númerico
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            self.conditions.append(field == value)
        
        return self
    

    def add_in_list(self, field, values: Optional[list] = None) -> 'FilterBuilder':
        """
        Agrega filtro IN (multiples valores).

        Args:
            field: Campo del modelo
            values: Lista de valores permitidos

        Returns:
            self (para encadenamiento)
        """
        if values and len(values) > 0:
            self.conditions.append(field.in_(values))

        return self


    def add_custom_condition(self, condition) -> 'FilterBuilder':
        """
        Agrega una condición SQLAlchemy personalizada.
        
        Args:
            condition: Expresión SQLAlchemy (ej: User.edad > 18)
        
        Returns:
            self (para encadenamiento)
        """
        if condition is not None:
            self.conditions.append(condition)

        return self
    

    def build(self) -> Query:
        """
        Construye la query final con todos los filtros aplicados.

        Returns:
            Query de SQLAlchemy lista para ejecutar o paginar
        """
        if self.conditions:
            return self.query.filter(and_(*self.conditions))
        return self.query


    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """
        Parsea una fecha en formato YYYY-MM-DD de forma segura.

        Args:
            date_str: String con fecha
        
        Returns:
            datetime.date o None si es inválida
        """
        if not date_str:
            return None

        try:
            return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except (ValueError, AttributeError):
            return None
        

class FilterParams:
    """
    DTO (Data Transfer Object) para encapusular parámetros de filtro.

    Valida y limpia los parámetros recibidos desde request.args.
    """

    def __init__(self, request_args):
        """
        Args:
            request_args: Objeto request.args de Flask
        """
        self.search = request_args.get('filtro', '').strip()
        self.date_from = request_args.get('fecha_desde', '').strip()
        self.date_to = request_args.get('fecha_hasta', '').strip()
        self.entity_id = request_args.get('entidad_id', '').strip() #Proveedor o Dependencia
        self.page = request_args.get('page', 1, type=int)

    def to_dict(self) -> dict:
        """
        Convierte los parámetros a diccionario (útil para templates).
            
        Returns:
            Dict con filtros activos
        """

        return {
            'filtro': self.search,
            'fecha_desde': self.date_from,
            'fecha_hasta': self.date_to,
            'entidad_id': self.entity_id,
            
        }
    
    def has_filters(self) -> bool:
        """
        Verifica si hay algún filtro activo.

        Returns:
            True si hay filtros aplicados
        """
        return bool(self.search or self.date_from or self.date_to or self.entity_id)
    