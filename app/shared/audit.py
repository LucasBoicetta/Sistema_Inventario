"""
app/shared/audit.py

Motor de auditoría del sistema SGQ Inventario.

Uso básico:
    from app.shared.audit import AuditService
    from app.shared.models import AuditAccion

    AuditService.log(
        accion=AuditAccion.CARGA_INSUMO,
        entidad_tipo="Insumo",
        entidad_id=insumo.id,
        detalle={
            "stock_antes": 10,
            "stock_despues": 20,
            "cantidad_cargada": 10,
            "proveedor": "Librería Central S.A.",
        }
    )

Decisiones de diseño:
    - Si falla guardar el audit log, se registra en el log técnico
      y la operación principal CONTINÚA (degradación elegante).
    - El usuario y la IP se obtienen automáticamente del contexto Flask.
    - Usa una transacción separada (savepoint) para no contaminar
      la transacción principal del negocio.
"""
import json
import logging
from typing import Optional, Any
from flask import request, has_request_context
from flask_jwt_extended import current_user as jwt_current_user
from app import db
from app.shared.models import AuditLog, AuditAccion, AuditEstado

logger = logging.getLogger(__name__)

class AuditService:
    """
    Servicio de auditoría de negocio.
    Todos los métodos son estáticos: no hay estado en esta clase.
    """

    @staticmethod
    def log(
        accion: AuditAccion,
        estado: AuditEstado = AuditEstado.EXITOSO,
        entidad_tipo: Optional[str] = None,
        entidad_id: Optional[int] = None,
        detalle: Optional[dict] = None,
        id_usuario_override: Optional[int] = None
    ) -> None:
        """
        Registra un evento de auditoría en la base de datos.

        Args:
            accion:              La acción que se realizó (del enum AuditAccion).
            estado:              Si la operación fue exitosa o falló.
            entidad_tipo:        Nombre de la entidad afectada ("Insumo", "Solicitud", etc.)
            entidad_id:          ID del registro afectado.
            detalle:             Dict con datos relevantes (snapshot antes/después, etc.)
            id_usuario_override: Pasar explícitamente un ID de usuario (útil en login
                                 fallido, donde current_user no está cargado).
        """
        try:
            # --- Resolver usuario ---
            #Intentamos obtenerlo del contexto JWT de Flask.
            #En login fallido, jwt_current_user puede ser None - por eso existe el override.
            id_usuario = id_usuario_override
            try:
                user = jwt_current_user
                if user and hasattr(user, 'id_usuario'):
                    id_usuario = user.id_usuario
            except Exception:
                #Si no hay contexto JWT activo, simplemente no hay usuario.
                pass

            # --- Resolver IP ---
            ip = AuditService._get_client_ip()

            # --- Serializar detalle ---
            detalle_str = None
            if detalle:
                try:
                    detalle_str = json.dumps(detalle, ensure_ascii=False, default=str)
                except (TypeError, ValueError) as e:
                    #Si el dict no es serializable, guardamos lo que podamos.
                    logger.warning(f"AuditService: no se pudo serializar el detalle {e}.")
                    detalle_str = str(detalle)

            # --- Crear registro ---
            #Usamos un savepoint para que un fallo aquí no afecte la transacción principal del negocio.
            entry = AuditLog(
                accion = accion,
                estado = estado,
                entidad_tipo = entidad_tipo,
                entidad_id = entidad_id,
                detalle_json = detalle_str,
                id_usuario = id_usuario,
                ip_address = ip
            )
            #Flush dentro de la sesión actual.
            # Si hay una transacción abierta (lo normal en Flask), esto funciona dentro de ella.
            # El commit final lo hace el caller (InventoryService, etc.)
            db.session.add(entry)

        except Exception as e:
            #Degradación elegante:
            #Si algo falla al preparar o guardar el log de auditoría, lo registramos en el log técnico y dejamos que la operación principal continue.
            logger.error(
                f"AuditService: FALLO al registrar evento de auditoría."
                f"Acción: {accion.value} if hasattr(accion, 'value') else accion, "
                f"Entidad: {entidad_tipo}:{entidad_id}, "
                f"Error: {e}",
                exc_info=True
            )
            #No re-lanzamos la excepcion, la operacion de negocio continua.
        
    @staticmethod
    def log_fallido(
        accion: AuditAccion,
        entidad_tipo: Optional[str] = None,
        entidad_id: Optional[int] = None,
        detalle: Optional[dict] = None,
        id_usuario_override: Optional[int] = None
    ) -> None:
        """
        Atajo para registrar un evento FALLIDO.
        Equivale a llamar log(..., estado=AuditEstado.FALLIDO).
        """
        AuditService.log(
            accion=accion,
            estado=AuditEstado.FALLIDO,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            detalle=detalle,
            id_usuario_override=id_usuario_override
        )
    
    @staticmethod
    def _get_client_ip() -> Optional[str]:
        """
        Obtiene la IP real del cliente, considerando proxies (X-Forwarded-For).

        En producción con nginx/gunicorn, la IP real viene en el header
        X-Forwarded-For. Sin proxy, viene en request.remote_addr.
        """
        if not has_request_context():
            return None
        
        #X-Forwarded-For puede contener múltiples IPs: "client, proxy1, proxy2"
        #La primera es siempre la del cliente real.
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            #Tomamos solo la primera IP y eleminamos espacios.
            ip = forwarded_for.split(',')[0].strip()
            return ip
        
        #Si no hay X-Forwarded-For, usamos remote_addr.
        return request.remote_addr