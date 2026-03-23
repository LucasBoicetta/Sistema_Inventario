from app import db
from app.shared.filters import FilterBuilder
from app.shared.models import Insumo, EntradaInsumo, Proveedor, SalidaInsumo, User, Dependencia
from app.shared.errors import DomainError, InvalidProductError, InsufficientStockError
from .validators import InsumoValidator, InsumoInput
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from typing import List, Tuple, Optional
import sqlalchemy as sa
import csv
import io
import logging
import pandas as pd

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
    def _procesar_insumo_individual(insumo_input: InsumoInput, proveedor: Proveedor) -> Tuple[Insumo, bool]:
        """
        Procesa la carga de un insumo individual (lógica compartida).

        Args:
            insumo_input: Datos validados y normalizados del insumo.
            proveedor: Instancia de Proveedor ya gestionada.

        Returns:
            Tupla(insumo, es_nuevo)
        """
        #1.Buscar insumo existente.
        insumo = db.session.scalar(sa.select(Insumo).where(Insumo.codigo_insumo == insumo_input.codigo))

        es_nuevo = False

        if insumo:
            #Actualizar existente.
            insumo.stock_actual += insumo_input.cantidad
            insumo.cantidad_entradas = (insumo.cantidad_entradas or 0) + insumo_input.cantidad
        else:
            #Crear nuevo insumo.
            insumo = Insumo(
                codigo_insumo=insumo_input.codigo,
                descripcion=insumo_input.descripcion,
                stock_actual=insumo_input.cantidad,
                cantidad_entradas=insumo_input.cantidad
            )
            db.session.add(insumo)
            db.session.flush()  #Para obtener ID antes del commit.
            es_nuevo = True

        #Registrar entrada en histórico.
        entrada = EntradaInsumo(
            id_proveedor=proveedor.id_proveedor,
            cantidad=insumo_input.cantidad,
            id_insumo=insumo.id
        )
        db.session.add(entrada)

        return insumo, es_nuevo


    @staticmethod
    def cargar_insumos(codigo_insumo, cantidad, nombre_proveedor, descripcion=None):
        """
        Registra una entrada de insumos individual (método original refactorizado).
        """
        #1.Crear input y validar.
        insumo_input = InsumoInput(
            codigo=codigo_insumo,
            descripcion=descripcion,
            cantidad=cantidad,
            proveedor=nombre_proveedor
        )

        resultado = InsumoValidator.validate_single(insumo_input)

        if not resultado.is_valid:
            logger.warning(f"Validación fallida: {resultado.error_message}")
            raise InvalidProductError(resultado.error_message)
        
        #2.Logging de auditoría.
        normalized = resultado.normalized_input
        logger.info(f"Iniciando carga individual: {normalized.cantidad} unidades de "
                    f"'{normalized.codigo}' por proveedor '{normalized.proveedor}'")

        try:
            #3.Gestionar proveedor.
            proveedor = InventoryService._get_or_create_proveedor(normalized.proveedor)

            #4.Procesar insumo.
            insumo, es_nuevo = InventoryService._procesar_insumo_individual(normalized, proveedor)

            #5.Commit final.
            db.session.commit()

            #6.Logging de éxito.
            accion = "creado" if es_nuevo else "actualizado"
            logger.info(f"Insumo '{insumo.codigo_insumo}' {accion} exitosamente. "
                        f"Nuevo Stock: {insumo.stock_actual}")
            
            mensaje = f"Insumo {accion} correctamente."
            if resultado.warnings:
                mensaje += " Advertencias: " + "; ".join(resultado.warnings)

            return insumo, mensaje
        
        except DomainError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error CRÍTICO cargando insumo '{str(e)}'", exc_info=True)
            raise Exception("Ocurrió un error interno al procesar la carga del insumo.")



    @staticmethod
    def cargar_insumos_multiple(insumos_input: List[InsumoInput]) -> dict:
        """
        Carga múltiple de insumos en una sola transaccion.
        
        Args:
            insumos_input: Lista de InsumoInput a procesar.
        
        Returns:
            Dict con resultados: {
                'exitosos': int,
                'fallidos': int,
                'errores': List[dict],
                'insumos_creados': List[int],
                'insumos_actualizados': List[int]
            }
        """
        logger.info(f"Iniciando carga múltiple de {len(insumos_input)} insumos.")

        #1.Validar todos los insumos.
        insumos_validos, errores = InsumoValidator.validate_batch(insumos_input)

        if not insumos_validos:
            logger.warning("Carga múltiple cancelada: Ningún insumo pasó validación.")
            return {
                'exitosos': 0,
                'fallidos': len(errores),
                'errores': errores,
                'insumos_creados': [],
                'insumos_actualizados': []
            }

        try:
            creados = []
            actualizados = []
            proveedores_cache = {} #Cache para evitar consultas repetidas de proveedores.

            #2.Procesar en una sola transacción.
            for insumo_input in insumos_validos:
                #Reutilizar proveedor si ya se procesó.
                if insumo_input.proveedor not in proveedores_cache:
                    proveedores_cache[insumo_input.proveedor] = \
                    InventoryService._get_or_create_proveedor(insumo_input.proveedor)
                
                proveedor = proveedores_cache[insumo_input.proveedor]

                #Procesar insumo.
                insumo, es_nuevo = InventoryService._procesar_insumo_individual(insumo_input, proveedor)

                if es_nuevo:
                    creados.append(insumo.id)
                else:
                    actualizados.append(insumo.id)
                
            #3.Commit único.
            db.session.commit()

            logger.info(f"Carga múltiple completada: {len(creados)} creados, {len(actualizados)} actualizados.")

            return {
                'exitosos': len(creados) + len(actualizados),
                'fallidos': len(errores),
                'errores': errores,
                'insumos_creados': creados,
                'insumos_actualizados': actualizados
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error CRÍTICO en carga múltiple: {str(e)}", exc_info=True)
            raise Exception("Ocurrió un error interno al procesar la carga múltiple de insumos.")
    

    @staticmethod
    def importar_desde_csv(archivo_stream, filename: str) -> dict:
        """
        Importa insumos desde archivo CSV/Excel.

        Args:
            archivo_stream: FileStorage de Flask.
            filename: Nombre del archivo para detectar formato.
        
        Returns:
            Dict con resultados de la importación.
        """
        logger.info(f"Iniciando importación desde archivo: {filename}")

        try:
            #1.Detectar formato y leer archivo.
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(archivo_stream, engine='openpyxl')
            elif filename.endswith('.csv'):
                df = pd.read_csv(archivo_stream, encoding='utf-8-sig')
            else:
                raise InvalidProductError("Formato de archivo no soportado. Use CSV o Excel.")
            
            #2.Validar columnas requeridas.
            columnas_requeridas = ['codigo', 'cantidad', 'proveedor']
            columnas_opcionales = ['descripcion', 'nombre']

            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            if columnas_faltantes:
                raise InvalidProductError(
                    f"Columnas faltantes en el archivo: {', '.join(columnas_faltantes)}. "
                    f"Requeridas: {', '.join(columnas_requeridas)}"
                )

            #3.Convertir dataframe a lista de InsumoInput.
            insumos_input = []
            for idx, row in df.iterrows():
                #Usar 'descripcion' o 'nombre' para la descripción del insumo.
                descripcion = (
                    row.get('descripcion') or
                    row.get('nombre') or
                    row.get('Descripcion') or
                    row.get('Nombre')
                )

                insumo = InsumoInput(
                    codigo=str(row['codigo']).strip(),
                    descripcion=str(descripcion).strip() if pd.notna(descripcion) else None,
                    cantidad=int(row['cantidad']) if pd.notna(row['cantidad']) else 0,
                    proveedor=str(row['proveedor']).strip() if pd.notna(row['proveedor']) else '',
                    fila=idx + 2  # +2 para ajustar por header y base 0.
                )
                insumos_input.append(insumo)
            
            logger.info(f"Archivo parseado: {len(insumos_input)} insumos encontrados. Iniciando validación.")
            
            #4.Delegar a carga múltiple.
            resultado = InventoryService.cargar_insumos_multiple(insumos_input)
            resultado['total_filas'] = len(insumos_input)

            return resultado

        except pd.errors.EmptyDataError:
            raise InvalidProductError("El archivo está vacío.")
        except pd.errors.ParserError as e:
            raise InvalidProductError(f"Error al parsear el archivo: {str(e)}")
        except Exception as e:
            logger.error(f"Error CRÍTICO importando desde archivo: {str(e)}", exc_info=True)
            raise
        

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
    def filtrar_entradas(params) -> any:
        """
        Construye query filtrada para entradas de insumos.

        Args:
            params: Objeto FiterParams con parámetros de búsqueda

        Returns:
            Query de SQLAlchemy lista para paginar
        """
        #1.Query base con eager loading para evitar N+1.
        query = EntradaInsumo.query.options(
            joinedload(EntradaInsumo.proveedor),
            joinedload(EntradaInsumo.insumo)
        )

        #2.Aplicar joins necesarios.
        query = query.join(Proveedor).join(Insumo)

        #3.Construir filtros dinámicamente.
        filters = FilterBuilder(query)

        #Filtro por rango de fechas.
        filters.add_date_range(
            EntradaInsumo.fecha_entrada,
            params.date_from,
            params.date_to
        )

        #Filtro por proveedor específico.
        filters.add_exact_match(
            EntradaInsumo.id_proveedor,
            params.entity_id
        )

        #Búsqueda general (código, descripción, proveedor)
        if params.search:
            from sqlalchemy import or_
            search_str = f"%{params.search}%"
            filters.add_custom_condition(
                or_(
                    Insumo.codigo_insumo.ilike(search_str),
                    Insumo.descripcion.ilike(search_str),
                    Proveedor.nombre.ilike(search_str)
                )
            )

        #4.Construir query final y ordenar.
        return filters.build().order_by(EntradaInsumo.fecha_entrada.desc())
    

    @staticmethod
    def filtrar_salidas(params) -> any:
        """
        Construye query filtrada para salidas de insumos.

        Args:
            params: Objeto FilterParams con parámetros de búsqueda.

        Returns:
            Query de SQLAlchemy lista para paginar.
        """
        #1.Query base con eager loading.
        query = SalidaInsumo.query.options(
            joinedload(SalidaInsumo.usuario).joinedload(User.dependencia),
            joinedload(SalidaInsumo.insumo)
        )

        #2.Aplicar joins necesarios.
        query = query.join(User).join(Dependencia).join(Insumo)

        #3.Construir filtros dinámicamente.
        filters = FilterBuilder(query)

        #Filtro por rango de fechas.
        filters.add_date_range(
            SalidaInsumo.fecha_salida,
            params.date_from,
            params.date_to
        )

        #Filtro por dependencia específica.
        filters.add_exact_match(
            User.id_dependencia,
            params.entity_id
        )
        #Búsqueda general (código, descripción, usuario, dependencia)
        if params.search:
            from sqlalchemy import or_
            search_str = f"%{params.search}%"
            filters.add_custom_condition(
                or_(
                    Insumo.codigo_insumo.ilike(search_str),
                    Insumo.descripcion.ilike(search_str),
                    User.nombre.ilike(search_str),
                    Dependencia.nombre_dependencia.ilike(search_str)
                )
            )

        #4.Construir query final y ordenar.
        return filters.build().order_by(SalidaInsumo.fecha_salida.desc())
    

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