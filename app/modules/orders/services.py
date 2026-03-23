from app import db
from app.shared.models import Insumo, SolicitudInsumo, SolicitudDetalle, SalidaInsumo
from app.shared.errors import DomainError, InvalidProductError, InsufficientStockError, OrderNotReadyError
from app.modules.inventory.services import InventoryService
from typing import List, Dict, Tuple
import logging

#Configuracion de Logging.
logger = logging.getLogger(__name__)

class OrderProductService:

    @staticmethod
    def agregar_insumos_solicitud(carrito: List[int], insumo_id: int,) -> Tuple[bool, str, str]:
        """Agrega un insumo al carrito de solicitudes.
           Retorna el estado de la operación, un mensaje y la categoría del flash."""
        
        try:
            insumo = db.session.get(Insumo, insumo_id)
            if not insumo:
                return False, 'El insumo no existe', 'danger'
            
            if insumo_id in carrito:
                return False, f'El insumo {insumo.descripcion} ya está en la lista de la solicitud', 'info'
            
            carrito.append(insumo_id)
            return True, f'Insumo {insumo.descripcion} agregado a la solicitud', 'success'
        
        except Exception as e:
            logger.error(f"Error al agregar insumo a la solicitud: {e}")
            return False, f'Error al agregar el insumo: {str(e)}', 'danger'
        
    @staticmethod
    def eliminar_insumos_solicitud(carrito: List[int], cantidades: Dict[str, int], insumo_id: int) -> Tuple[bool, str, str]:
        """Elimina un insumo de la lista de solicitudes.
           Retorna el estado de la operación, un mensaje y la categoría del flash."""
        try:
            if insumo_id not in carrito:
                return False, 'El insumo no está en la lista de la solicitud', 'info'
            
            carrito.remove(insumo_id)
            cantidades.pop(str(insumo_id), None)
            
            return True, 'Insumo eliminado de la solicitud', 'success'
                
        except Exception as e:
            return False, f'Error al eliminar el insumo: {str(e)}', 'danger'
    
    
    @staticmethod
    def crear_solicitud_insumos(id_usuario: int, lista_insumos_ids: List[int], cantidades:Dict[str, int]) -> Tuple[bool, str, str]:
        """Crea una nueva solicitud de insumos.
           Retorna el estado de la operación, un mensaje y la categoría del flash."""
        logger.info(f"Uusario {id_usuario} está creando una solicitud con {len(lista_insumos_ids)} insumos.")

        #1. Validar que hay insumos.
        if not lista_insumos_ids:
            raise DomainError('La lista de insumos está vacía.')
        
        try:

            #2. Crear la Solicitud.
            nueva_solicitud = SolicitudInsumo(id_usuario=id_usuario, estado=False)
            db.session.add(nueva_solicitud)
            db.session.flush()  # Para obtener el ID de la solicitud.

            
            #3. Crear los detalles de la solicitud.
            for insumo_id in lista_insumos_ids:
                cantidad_solicitada = cantidades.get(str(insumo_id)) or 0
                #4. Verificamos disponibilidad al servicio de inventario.
                InventoryService.verificar_disponibilidad(insumo_id, cantidad_solicitada)
                #Si pasa la linea de arriba es que hay stock suficiente.
                detalle = SolicitudDetalle(
                    cantidad_solicitada=cantidad_solicitada,
                    id_solicitud=nueva_solicitud.id_solicitud,
                    id_insumo=insumo_id
                )
                db.session.add(detalle)

            #5. Confirmar transacción.
            db.session.commit()
            logger.info(f"Solicitud {nueva_solicitud.id_solicitud} creada exitosamente para el usuario {id_usuario}.")
            return nueva_solicitud

        except DomainError:
            db.session.rollback()
            raise #Sube al controller para Flash Warning.
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creando solicitud BD: {e},", exc_info=True)
            raise DomainError(f'Error interno al guardar la solicitud')
        
    
    @staticmethod
    def procesar_entrega_item(detalle_id: int, cantidad_entregada: int, observaciones: str, id_admin: int):
        """El Admin entrega UN item específico de una solicitud.
           Acá es donde interactuemos con el Inventario real."""
        logger.info(f"Procesando entrega Detalle #{detalle_id} - Cant: {cantidad_entregada}.")

        try:
            #1. Obtener Detalle con bloqueo (evitar doble entrega simultánea).
            detalle = db.session.query(SolicitudDetalle).filter_by(id_solicitudes_insumos=detalle_id).with_for_update().first()
            if not detalle:
                raise DomainError('El detalle de la solicitud no existe.')
            
            #2. Obtener los objetos relacionados al detalle.
            insumo = detalle.insumo
            solicitud = detalle.solicitud

            #3. Validaciones lógicas.
            if cantidad_entregada > detalle.cantidad_solicitada:
                raise DomainError(f"No puedes entregar más de lo solicitado ({detalle.cantidad_solicitada}.")
                                     
            #4. Utilizamos el servicio de inventario para registrar la salida.
            salida, msg = InventoryService.registrar_salidas(
                id_insumo = insumo.id,
                cantidad = cantidad_entregada,
                id_usuario = solicitud.id_usuario,
                observaciones = observaciones,
                id_detalle_solicitud = detalle.id_solicitudes_insumos
            )

            #5. Actualizar estado global de la solicitud.
            db.session.flush() #BD ve la nueva salida.

            #Verificamos si TODOS los detalles tienen al menos UNA salida asociada.
            todos_tienen_salida = all(len(d.salidas) > 0 for d in solicitud.detalles)

            if todos_tienen_salida:
                solicitud.estado = True  # Marcamos como completada.
                logger.info(f"Solicitud #{solicitud.id_solicitud} marcada como completada.")

            db.session.commit()
            return True, f'{msg}', 'success'
        
        except InsufficientStockError as e:
            db.session.rollback()
            logger.warning(f"Insuficiente stock al procesar entrega: {e.message}")
            raise
        except DomainError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error critico en entrega: {e}", exc_info=True)
            raise Exception('Error interno al procesar la entrega.')


    @staticmethod
    def generar_pdf_solicitud(solicitud):
        """Genera un PDF con los detalles de la solicitud entregada."""
        
        #Validacion de Integridad.
        if not solicitud:
            raise ValueError("Se intentó generar PDF de una solicitud inexistente.")
        
        #Validación de regla de negocio.
        todos_entregados = all(len(detalle.salidas) > 0 for detalle in solicitud.detalles)
        
        if not todos_entregados:
            logger.warning(f"Intento de generar PDF para solicitud #{solicitud.id_solicitud} que no está completa.")
            raise OrderNotReadyError("No se puede generar el PDF hasta que todos los insumos de la solicitud hayan sido entregados.")

        try:

            import io
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors
            from reportlab.platypus import Table, TableStyle, Paragraph
            from reportlab.lib.styles import ParagraphStyle


            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

            # --- LOGO GRANDE CENTRADO ---
            # Ajusta el tamaño y posición del logo para que ocupe el espacio del título
            logo_path = "app/static/logoSindicaturaNew-removebg-preview.png"
            logo_width = 300  # más grande
            logo_height = 90
            logo_x = (width - logo_width) / 2
            logo_y = height - 100
            p.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

            # --- TÍTULOS PEQUEÑOS ---
            p.setFont("Helvetica", 10)
            p.drawCentredString(width / 2.0, height - 95, "DIRECCIÓN GENERAL DE ADMINISTRACIÓN Y FINANZAS")
            p.setFont("Helvetica-Bold", 11)
            p.drawCentredString(width / 2.0, height - 110, "Solicitud de Materiales e Insumos para Oficina")
            

            # --- CAMPOS SUPERIORES ---
            p.setFont("Helvetica", 10)
            # Fecha y Nº
            p.drawString(45, height - 140, "FECHA:")
            p.drawString(100, height - 140, solicitud.fecha_solicitud.strftime('%d/%m/%Y'))
            p.drawString(width - 220, height - 140, "Nº:")
            p.drawString(width - 190, height - 140, str(solicitud.id_solicitud))

            # Dependencia y Firma Solicitante
            p.drawString(45, height - 160, "DEPENDENCIA SOLICITANTE:")
            p.drawString(190, height - 160, solicitud.usuario.dependencia.nombre_dependencia)
            p.drawString(width - 220, height - 160, "FIRMA SOLICITANTE:")
            p.line(width - 110, height - 163, width - 45, height - 163)  # Línea para firma

            # Solicitado por y V°B° DIGEAF
            p.drawString(45, height - 180, "SOLICITADO POR:")
            p.drawString(145, height - 180, solicitud.usuario.nombre)
            p.drawString(width - 220, height - 180, "V°B° DIGEAF:")
            p.line(width - 110, height - 183, width - 45, height - 183)  # Línea para V°B°

            # --- TABLA DE DETALLES ---
            # Preparamos los datos para la tabla (15 filas)
            table_data = [['Nº', 'CÓDIGO', 'DESCRIPCIÓN', 'CANTIDAD\nSOLICITADA', 'CANTIDAD\nENTREGADA', 'OBSERVACIONES']]
            fecha_entrega_final = None

            # Estilo para observaciones largas
            obs_style = ParagraphStyle(
                name='obs',
                fontName='Helvetica',
                fontSize=9,
                leading=11,
                alignment=0,  # left
                wordWrap='CJK',
            )

            detalles = solicitud.detalles
            for i in range(15):  # 15 filas como en el formulario físico
                if i < len(detalles):
                    detalle = detalles[i]
                    salida = detalle.salidas[0] if detalle.salidas else None
                    nro = i + 1
                    codigo = detalle.insumo.codigo_insumo
                    descripcion = detalle.insumo.descripcion
                    cant_solicitada = detalle.cantidad_solicitada
                    cant_entregada = salida.cantidad_entregada if salida else ''
                    observaciones = salida.observaciones if salida and salida.observaciones else ''
                    if salida and (fecha_entrega_final is None or salida.fecha_salida > fecha_entrega_final):
                        fecha_entrega_final = salida.fecha_salida
                    # Usar Paragraph para observaciones largas
                    obs_paragraph = Paragraph(observaciones, obs_style)
                    table_data.append([nro, codigo, descripcion, cant_solicitada, cant_entregada, obs_paragraph])
                else:
                    table_data.append(['', '', '', '', '', ''])  # Fila vacía

            # Crear la tabla con los datos
            table = Table(table_data, colWidths=[35, 65, 180, 70, 70, 120])
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTSIZE', (0,1), (-1,-1), 9),
                ('ALIGN', (2,1), (2,-1), 'LEFT'),
                ('ALIGN', (5,1), (5,-1), 'LEFT'),  # Observaciones alineadas a la izquierda
            ])
            table.setStyle(style)

            # Posiciona la tabla más cerca de los campos completables
            table.wrapOn(p, width, height)
            table.drawOn(p, 45, height - 545)

            # --- CAMPOS FINALES ---
            p.setFont("Helvetica", 10)
            p.drawString(45, 120, "RETIRADO POR: _________________________")
            p.drawString(width/2 + 10, 120, f"FECHA DE ENTREGA: {fecha_entrega_final.strftime('%d/%m/%Y') if fecha_entrega_final else ''}")
            p.drawString(45, 95, "FIRMA: _________________________")
            p.drawString(width/2 + 10, 95, "ACLARACION FIRMA: _________________________")

            p.showPage()
            p.save()
            buffer.seek(0)


            logger.info(f"PDF generado exitosamente para solicitud {solicitud.id_solicitud}.")
            return buffer

        except Exception as e:
            logger.error(f"Error al generar PDF para solicitud {solicitud.id_solicitud}: {e}", exc_info=True)
            raise Exception('Error interno al generar el PDF de la solicitud.')

    @staticmethod
    def obtener_insumos_ordenado(lista):
        """Obtiene los insumos en el orden especificado por la lista de IDs."""
        insumos = []
        if lista:
            insumos = db.session.query(Insumo).filter(Insumo.id.in_(lista)).all()
            insumos.sort(key=lambda x: lista.index(x.id))

        return insumos