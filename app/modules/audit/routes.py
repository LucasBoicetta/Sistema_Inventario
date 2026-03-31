"""
app/modules/audit/routes.py

Rutas de la vista de auditoría (solo administradores).
"""

import logging

from flask import render_template, request, Response, current_app

from app import db
from app.shared.decorators import admin_required
from app.shared.models import AuditAccion, AuditEstado
from .services import AuditQueryService, AuditFilterParams
from . import audit_bp

logger = logging.getLogger(__name__)

@audit_bp.route('/auditoria')
@admin_required
def audit_logs():
    """
    Vista principal de auditoría.
    Muestra logs filtados con paginación.
    """
    params = AuditFilterParams(request.args)
    per_page = current_app.config['ITEMS_PER_PAGE']
    query = AuditQueryService.filtrar_logs(params)
    pagination = db.paginate(query, page=params.page, per_page=per_page, error_out=False)

    return render_template(
        'audit/audit_logs.html',
        logs=pagination.items,
        pagination=pagination,
        filtros=params.to_dict(),
        params=params,
        #Pasamos los enums completos para los dropdowns de filtro.
        acciones=AuditAccion,
        estados=AuditEstado
    )


@audit_bp.route('/auditoria/exportar')
@admin_required
def exportar_audit_csv():
    """
    Exporta los logs filtrados a CSV.
    Aplica los mismos filtros activos en la vista principal.
    """
    params = AuditFilterParams(request.args)
    csv_output = AuditQueryService.generar_csv(params)

    return Response(
        csv_output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=auditoria.csv'}
    )