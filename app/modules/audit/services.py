"""
app/modules/audit/services.py
 
Servicio de consulta de auditoría (solo lectura).
 
Responsabilidades:
    - Construir queries filtradas sobre AuditLog
    - Generar CSV de logs filtrados
    - NO escribe ni modifica registros de auditoría
 
Patrón seguido: idéntico a InventoryService.filtrar_entradas/filtrar_salidas
usando FilterBuilder de app/shared/filters.py.
"""

import csv
import io
import logging
from typing import Optional, Any

from sqlalchemy.orm import joinedload

from app import db
from app.shared.models import AuditLog, AuditAccion, AuditEstado, User
from app.shared.filters import FilterBuilder

logger = logging.getLogger(__name__)


class AuditQueryService:

    @staticmethod
    def filtrar_logs(params) -> Any:
        """
        Construye query filtrada para logs de auditoría.

        Args: 
            params: AuditFilterParams con los parámetros de búsqueda.
        
        Returns:
            Query de SQLAlchemy con los filtros aplicados lista para paginar.
        """
        #Eager load del usuario para evitar n+1 en el template.
        query = AuditLog.query.options(joinedload(AuditLog.usuario))

        filters = FilterBuilder(query)


        #Filtro por rango de fechas (usa el campo timestamp).
        filters.add_date_range(
            AuditLog.timestamp,
            params.date_from,
            params.date_to
        )

        #Filtro exacto por acción (valor del enum como string).
        if params.accion:
            filters.add_custom_condition(AuditLog.accion == params.accion)
        
        #Filtro exacto por estado.
        if params.estado:
            filters.add_custom_condition(AuditLog.estado == params.estado)

        #Búsqueda por usuario: join con User y filtro por nombre.
        if params.search:
            query = filters.build().join(
                User, AuditLog.id_usuario == User.id_usuario, isouter=True
            )
            from sqlalchemy import or_
            search_str = f"%{params.search}%"
            query = query.filter(
                or_(
                    User.nombre.ilike(search_str),
                    User.cedula.cast(db.String).ilike(search_str),
                )
            )
            return query.order_by(AuditLog.timestamp.desc())

        return filters.build().order_by(AuditLog.timestamp.desc())
    

    @staticmethod
    def generar_csv(params) -> str:
        """
        Genera contenido CSV de los logs filtrados.
        Aplica los mismos filtros que filtar_logs() pero sin paginación.

        Returns:
            String con el contenido CSV completo.
        """
        buffer = io.StringIO()

        try:
            query = AuditQueryService.filtrar_logs(params)
            logs = query.all()

            writer = csv.writer(buffer)
            writer.writerow([
                'ID', 'Timestamp', 'Usuario', 'Cedula',
                'Accion', 'Entidad Tipo', 'Entidad ID',
                'Estado', 'IP Address', 'Detalle'
            ])

            for log in logs:
                nombre_usuario = log.usuario.nombre if log.usuario else "Sistema"
                cedula_usuario = log.usuario.cedula if log.usuario else "-"

                #CSV Injection Protection.
                nombre_usuario = AuditQueryService._sanitizar_csv(nombre_usuario)

                writer.writerow([
                    log.id,
                    log.timestamp.strftime('%d/%m/%Y %H:%M:%S') if log.timestamp else '',
                    nombre_usuario,
                    cedula_usuario,
                    log.accion.value if log.accion else '',
                    log.entidad_tipo or '',
                    log.entidad_id or '',
                    log.estado.value if log.estado else '',
                    log.ip_address or '',
                    log.detalle_json or ''
                ])
            
            buffer.seek(0)
            return buffer.getvalue()
    
    
        except Exception as e:
            logger.error(f"Error al generar CSV de auditoría: {e}", exc_info=True)
            buffer.seek(0)
            return buffer.getvalue()  # Devuelve lo que se haya podido generar, aunque sea solo el header.
    

    @staticmethod
    def _sanitizar_csv(valor: str) -> str:        
        """Previene CSV Injection prefincando con comilla si empieza con carácter de fórmula."""
        if valor and valor.startswith(('=', '+', '-', '@')):
            return f"'{valor}"
        return valor


class AuditFilterParams:
    """
    DTO para parámetros de filtro de auditoría.
    Extiende el concepto de FilterParams de app/shared/filters.py
    con campos específicos para auditoría.
    """

    def __init__(self, request_args):
        #Heredados del patrón existente.
        self.search = request_args.get('filtro', '').strip()
        self.date_from = request_args.get('fecha_desde', '').strip()
        self.date_to = request_args.get('fecha_hasta', '').strip()
        self.page = request_args.get('page', 1, type=int)

        #Específicos de auditoría.
        accion_raw = request_args.get('accion', '').strip()
        estado_raw = request_args.get('estado', '').strip()

        #Convertir strings a enums (None si no viene o es inválido).
        self.accion = AuditFilterParams._parse_enum(AuditAccion, accion_raw)
        self.estado = AuditFilterParams._parse_enum(AuditEstado, estado_raw)

    def to_dict(self) -> dict:
        """Para pasar a url_for() y preservar filtros en la paginación."""
        return {
            'filtro': self.search,
            'fecha_desde': self.date_from,
            'fecha_hasta': self.date_to,
            'accion': self.accion.value if self.accion else '',
            'estado': self.estado.value if self.estado else ''
        }
    
    def has_filters(self) -> bool:
        """Indica si se ha aplicado algún filtro (para mostrar botón de limpiar)."""
        return bool([
            self.search or self.date_from or self.date_to or self.accion or self.estado
        ])

    @staticmethod
    def _parse_enum(enum_cls, value: str):
        """Convierte string a enum de forma segura, devuelve None si no es válido."""
        if not value:
            return None
        try:
            return enum_cls(value)
        except ValueError:
            return None
