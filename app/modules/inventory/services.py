from app import db
from app.shared.models import Insumo, EntradaInsumo, Proveedor, SalidaInsumo
from app.shared.errors import DomainError, InvalidProductError, InsufficientStockError
from sqlalchemy.exc import SQLAlchemyError
import sqlalchemy as sa
import csv
import io
import logging

#Obtenemos un logger específico para este módulo.
logger = logging.getLogger(__name__)

class InventoryService:

    @staticmethod
    def _get_or_create_proveedor(nombre_proveedor):
        """Helper privado para gestionar proveedores."""
        
        try:
            proveedor = db.session.query(Proveedor).filter_by(nombre=nombre_proveedor).first()
            if not proveedor:
                proveedor = Proveedor(nombre=nombre_proveedor)
                db.session.add(proveedor)
                #Obtenemos el ID del proveedor antes del commit.
                db.session.flush()
            return proveedor
        except Exception as e:
            logger.error(f"Error interno gestionando proveedor '{nombre_proveedor}': {e}")
            raise

    @staticmethod
    def cargar_insumos(codigo_insumo, cantidad, nombre_proveedor, descripcion=None):
        """Registra una entrada de insumos. Crea el insumo si no existe.
           Maneja la transaccion de forma atomica.
        """
        #1. Logging de inicio de operación (Auditoría).
        logger.info(f"Iniciando carga: {cantidad} unidades de '{codigo_insumo}' (Prov: {nombre_proveedor})")

        #2. Validaciones de Dominio (Reglas de Negocio).
        if cantidad <= 0:
            logger.warning(f"Intento de carga inválido: Cantidad {cantidad} para {codigo_insumo}")
            raise InvalidProductError("La cantidad debe ser un número positivo.")
        
        try: 
            #3 Lógica Transaccional.
            proveedor = InventoryService._get_or_create_proveedor(nombre_proveedor)
            # Buscamos el insumo.
            insumo = db.session.scalar(sa.select(Insumo).where(Insumo.codigo_insumo == codigo_insumo))

            nuevo = False
            if insumo:
                #Actualizar existente.
                insumo.stock_actual += cantidad
                insumo.cantidad_entradas =(insumo.cantidad_entradas or 0) + cantidad
            else:
                #Crear nuevo insumo.
                if not descripcion:
                    logger.warning(f"Fallo carga: Falta descripción para insumo nuevo {codigo_insumo}")
                    raise InvalidProductError("La descripción es obligatoria para insumos nuevos.")
            
                insumo = Insumo(
                    codigo_insumo=codigo_insumo,
                    descripcion=descripcion,
                    stock_actual=cantidad,
                    cantidad_entradas=cantidad
                )   

                db.session.add(insumo)
                db.session.flush()
                nuevo = True

            #Registrar histórico.
            nueva_entrada = EntradaInsumo(
                id_proveedor=proveedor.id_proveedor,
                cantidad=cantidad,
                id_insumo=insumo.id
            )
            db.session.add(nueva_entrada)

            db.session.commit()
            #4 Logging de éxito.
            accion = "creado" if nuevo else "actualizado"
            logger.info(f"Carga exitosa: Insumo {accion} (ID: {insumo.id}). Nuevo Stock: {insumo.stock_actual}")

            return insumo, f"Insumo {accion} correctamente."
        
        except DomainError as e:
            # Si es un error de regla de negocio, hacemos rollback y lo dejamos subir al controller
            db.session.rollback()
            raise
        except Exception as e:
            # Si es un error inesperado (BBDD, bug), lo mostramos como CRÍTICO
            db.session.rollback()
            logger.error(f"Error CRÍTICO cargando insumos: {str(e)}", exc_info=True)
            raise Exception("Ocurrió un error interno al procesar la carga.")


    @staticmethod
    def registrar_salidas(id_insumo, cantidad, id_usuario, observaciones=None, id_detalle_solicitud=None):
        """ Registra una salida de stock (Descargo)
        Utiliza bloqueo pesimista en la BD para evitar errores de concurrencia.
        """
        #1. Logging de Auditoría.
        logger.info(f"Solicitud de salida: Insumo ID {id_insumo}, Cantidad {cantidad}, Usuario ID {id_usuario}")

        #2. Validación básica.
        if cantidad <=0:
            raise InvalidProductError("La cantidad debe ser un número positivo.")
        
        try:
            #3. Transacción con Bloqueo (Concurrency Control).
            #'with_for_update()' bloquea la fila en la BD hasta el commit/rollback.
            #Esto evita que dos usuarios saquen el último producto al mismo tiempo.
            insumo = db.session.query(Insumo).filter_by(id=id_insumo).with_for_update().first()

            if not insumo:
                logger.warning(f"Intento de salida para insumo inexistente ID {id_insumo}")
                raise InvalidProductError("El insumo especificado no existe.")
            
            #4. Verificación de stock.
            if insumo.stock_actual < cantidad:
                logger.warning(f"Stock insuficiente: Insumo {insumo.codigo_insumo}, Solicitado {cantidad}, Disponible {insumo.stock_actual}")
                raise InsufficientStockError(insumo.codigo_insumo, cantidad,insumo.stock_actual)
            
            #5. Actualización de stock.
            insumo.stock_actual -= cantidad
            insumo.cantidad_salidas = (insumo.cantidad_salidas or 0) + cantidad

            #6.Crear registro de salida.
            salida = SalidaInsumo(
                id_insumo=id_insumo,
                id_usuario=id_usuario,
                cantidad_entregada=cantidad,
                observaciones=observaciones,
                id_solicitudes_insumos=id_detalle_solicitud
            )
            db.session.add(salida)

            #7. Commit final.
            db.session.commit()

            logger.info(f"Salida exitosa: Insumo {insumo.codigo_insumo}, Cantidad {cantidad}, Nuevo Stock {insumo.stock_actual}")
            return salida, "Salida registrada correctamente."
       
        except DomainError:
           #Errores esperados (Stock bajo, datos mal) --> Rollback y avisar al controller.
            db.session.rollback()
            raise
        except Exception as e:
            #Errores inesperados (Bug, BD caída) --> Rollback y log crítico.
            db.session.rollback()
            logger.error(f"Error CRÍTICO en salida de insumos: {str(e)}", exc_info=True)
            raise Exception("Ocurrió un error interno al procesar la salida.")
       
    
    @staticmethod
    def verificar_disponibilidad(insumo_id, cantidad_solicitada):
        """Verifica si hay stock suficiente para un insumo dado."""
        if not cantidad_solicitada or cantidad_solicitada <=0:
            raise DomainError(f"Cantidad inváldia para el insumo ID {insumo_id}.")

        insumo = db.session.get(Insumo, insumo_id)
        if not insumo:
            raise InvalidProductError("El insumo especificado no existe.")
        
        if insumo.stock_actual < cantidad_solicitada:
            raise InsufficientStockError(insumo.codigo_insumo, cantidad_solicitada, insumo.stock_actual)
        
        return True

    @staticmethod
    def generar_csv_inventario(filtro=''):
        """Genera el contenido CSV del inventario"""
        try:
            query = Insumo.filtro_insumos(filtro) 
            insumos = query.all() #Para produccion, cambiar a streaming.


            buffer = io.StringIO()
            writer = csv.writer(buffer)
            #Headers
            writer.writerow(['ID', 'Codigo Insumo', 'Descripcion', 'Existencias Iniciales Anio', 'Stock Actual', 'Cantidad Entradas', 'Cantidad Salidas', 'Porcentaje Utilizado'])

            #Data
            for insumo in insumos:
                #CSV Injection Protection: Si empieza con caracteres de formula, agregamos comillas.
                desc = str(insumo.descripcion)
                if desc.startswith(('=', '+', '-', '@')):
                    desc = f"'{desc}"
                writer.writerow([
                    insumo.id,
                    insumo.codigo_insumo,
                    desc,
                    insumo.existencias_iniciales_anio or 0,
                    insumo.stock_actual or 0,
                    insumo.cantidad_entradas or 0,
                    insumo.cantidad_salidas or 0,
                    f"{insumo.porcentaje_utilizado:.2f}%" if insumo.porcentaje_utilizado is not None else "N/A"
                ])

            buffer.seek(0)
            
            return buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error generando CSV de inventario: {e}", exc_info=True)
            return buffer.getvalue()  # Retornamos lo que se haya generado hasta el momento.
        

    @staticmethod
    def generar_csv_entradas(filtro=''):
        """Genera el contenido CSV de las entradas de insumos"""
        try:
            query = EntradaInsumo.filtro_entradas_insumos(filtro) 
            entradas = query.all() #Para produccion, cambiar a streaming.


            buffer = io.StringIO()
            writer = csv.writer(buffer)
            #Headers
            writer.writerow(['ID Entrada', 'Proveedor', 'Codigo Insumo', 'Descripcion Insumo', 'Cantidad', 'Fecha Entrada'])

            #Data
            for entrada in entradas:
                desc = str(entrada.insumo.descripcion)
                if desc.startswith(('=', '+', '-', '@')):
                    desc = f"'{desc}"

                writer.writerow([
                    entrada.id_entrada,
                    entrada.proveedor.nombre,
                    entrada.insumo.codigo_insumo,
                    desc,
                    entrada.cantidad,
                    entrada.fecha_entrada.strftime('%d/%m/%Y')
                ])

            buffer.seek(0)
            
            return buffer.getvalue()
    
        except Exception as e:
            logger.error(f"Error generando CSV de entradas: {e}", exc_info=True)
            return buffer.getvalue()  # Retornamos lo que se haya generado hasta el momento.


    @staticmethod
    def generar_csv_salidas(filtro=''):
        """Genera el contenido CSV de las salidas de insumos"""
        try:
            query = SalidaInsumo.filtro_salidas_insumos(filtro) #Usamos .all() para el reporte.
            salidas = query.all() #Para produccion, cambiar a streaming.

            buffer = io.StringIO()
            writer = csv.writer(buffer)
            #Headers
            writer.writerow(['ID Salida', 'Dependencia', 'Usuario', 'Codigo Insumo', 'Descripcion Insumo', 'Cantidad Entregada', 'Fecha Salida', 'Observaciones'])

            #Data
            for salida in salidas:
                desc = str(salida.insumo.descripcion)
                if desc.startswith(('=', '+', '-', '@')):
                    desc = f"'{desc}"

                writer.writerow([
                    salida.id_salida,
                    salida.usuario.dependencia.nombre_dependencia,
                    salida.usuario.nombre,
                    salida.insumo.codigo_insumo,
                    desc,
                    salida.cantidad_entregada,
                    salida.fecha_salida.strftime('%d/%m/%Y'),
                    salida.observaciones or ''
                ])

            buffer.seek(0)
            
            return buffer.getvalue()
        
        except Exception as e:
            logger.error(f"Error generando CSV de salidas: {e}", exc_info=True)
            return buffer.getvalue()  # Retornamos lo que se haya generado hasta el momento.