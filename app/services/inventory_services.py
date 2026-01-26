from app import db
from app.models import Insumo, EntradaInsumo, Proveedor, SolicitudDetalle, SalidaInsumo
import sqlalchemy as sa

class InventoryService:
    @staticmethod
    def cargar_insumos(codigo_insumo, cantidad, nombre_proveedor, descripcion=None):
        """Gestiona la lógica de carga de insumos en el inventario.
           Retorna el objeto, mensaje y la categoria del flash."""
        try: 
            #1 Gestion del proveedor.
            proveedor = db.session.scalar(db.select(Proveedor).where(Proveedor.nombre == nombre_proveedor))
            if not proveedor:
                proveedor = Proveedor(nombre=nombre_proveedor)
                db.session.add(proveedor)
                #Obtenemos el ID del proveedor antes del commit.
                db.session.flush()
            
            #2 Gestion del insumo.
            insumo = db.session.scalar(sa.select(Insumo).where(Insumo.codigo_insumo == codigo_insumo))

            if insumo:
                insumo.stock_actual += cantidad
                insumo.cantidad_entradas =(insumo.cantidad_entradas or 0) + cantidad
                mensaje = f'Se han agregado {cantidad} unidades al insumo {insumo.codigo_insumo}.'
            else:
                if not descripcion:
                    raise ValueError("La descripción es obligatoria para insumos nuevos.")
            
                insumo = Insumo(
                    codigo_insumo=codigo_insumo,
                    descripcion=descripcion,
                    stock_actual=cantidad,
                    cantidad_entradas=cantidad
                )

                db.session.add(insumo)
                db.session.flush()
                mensaje = f'Nuevo insumo {codigo_insumo} creado con éxito.'

            #3 Registro de la entrada de insumo.
            nueva_entrada = EntradaInsumo(
                id_proveedor=proveedor.id_proveedor,
                cantidad=cantidad,
                id_insumo=insumo.id
            )
            db.session.add(nueva_entrada)

            #4 Confirmacion de la transacción.
            db.session.commit()
            return insumo, mensaje, 'success'
        except Exception as e:
            db.session.rollback()
            return None, f'Error al procesar la carga: {str(e)}', 'danger'

    @staticmethod
    def entregar_item_solicitud(detalle_id, cantidad_entregada, observaciones):
        """Procesa la entrega de un item específico de una solicitud.
           Retorna el estado de la operación, un mensaje y la categoría del flash."""

        try:
            #1. Obtener y validar detalle.
            detalle = db.session.get(SolicitudDetalle, detalle_id)
            if not detalle:
                return False, 'El item de la solicitud no existe', 'danger'

            #Obtenemos los objetos relacionados al detalle.
            insumo = detalle.insumo
            solicitud = detalle.solicitud 

            #2. Validaciones del negocio.
            if cantidad_entregada > insumo.stock_actual:
                return False, f'No hay stock suficiente para el insumo {insumo.codigo_insumo}. (Actual: {insumo.stock_actual})', 'danger'
        
            if cantidad_entregada > detalle.cantidad_solicitada:
                return False, f'La cantidad entregada supera lo solicitado', 'danger'

            #3. Crear registro de salida. 
            nueva_salida = SalidaInsumo(
                cantidad_entregada=cantidad_entregada,
                id_usuario = solicitud.id_usuario,
                id_insumo = insumo.id,
                id_solicitudes_insumos = detalle.id_solicitudes_insumos,
                observaciones = observaciones
            )
            db.session.add(nueva_salida)

            #4. Actualizar insumo (stock y estadisticas).
            insumo.stock_actual -= cantidad_entregada
            insumo.cantidad_salidas = (insumo.cantidad_salidas or 0) + cantidad_entregada

            #Calculo de porcentaje utilizado.
            total_gestionado = (insumo.existencias_iniciales_anio or 0) + (insumo.cantidad_entradas or 0)
            if total_gestionado > 0:
                insumo.porcentaje_utilizado = ((insumo.cantidad_salidas or 0) / total_gestionado) * 100

            #5. Actualizar Estado de la Solicitud.
            #Verificamos si con esta entrega todos los detalles tienen al menos una salida.
            #Usamos flush para que la bd "vea" la nueva salida antes del commit.
            db.session.flush()

            todos_entregados = all(len(d.salidas)> 0 for d in solicitud.detalles)
            if todos_entregados:
                solicitud.estado = True  # Marcamos como entregado.
            

            db.session.commit()
            return True, f'Se ha confirmado la entrega.', 'success' 
    
        except Exception as e:
            db.session.rollback()
            return False, f'Error al procesar la entrega: {str(e)}', 'danger'