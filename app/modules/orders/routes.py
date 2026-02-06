from flask import render_template, request, redirect, url_for, flash, session, jsonify, Response, current_app
from flask_jwt_extended import current_user
from app import db
from app.shared.models import Insumo, SolicitudInsumo
from app.shared.decorators import jwt_required_html, admin_required
from app.shared.errors import DomainError, InsufficientStockError, OrderNotReadyError
from app.shared.utils import is_ajax_request
from .services import OrderProductService
from .forms import EntregarSolicitudForm
from . import orders_bp



@orders_bp.route('/solicitar_insumos', methods=['GET'])
@jwt_required_html()
def solicitar_insumos():
    """Ruta para solicitar insumos. Muestra una lista paginada de insumos con filtro de búsqueda."""
    #Obtenemos el filtro de búsqueda desde los parámetros de la URL y la primer página.
    filtro=request.args.get('filtro', '')
    #Obtenemos valores de paginación.
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    #1.Obtenemos la query del modelo.
    query = Insumo.filtro_insumos(filtro)
    #2. Paginar la query.
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    #Pasamos las Ids que ya están en el carrito.
    carrito_ids = session.get('lista_solicitudes', [])

    return render_template('orders/solicitar_insumos.html', insumos=pagination.items, filtro=filtro,
                            pagination=pagination, carrito_ids=carrito_ids)


@orders_bp.route('/agregar_insumos/<int:insumo_id>', methods=['POST'])
@jwt_required_html()
def agregar_insumos(insumo_id):
    """Agrega un insumo a la lista de solicitudes en sesión."""
    lista=session.get('lista_solicitudes', [])
    
    exito, mensaje, categoria = OrderProductService.agregar_insumos_solicitud(lista, insumo_id)

    if exito:
        session['lista_solicitudes'] = lista

    #Deteccion de petición AJAX

    if is_ajax_request():
        return jsonify({
            'success': exito,
            'message': mensaje,
            'category': categoria,
            'cart_count': len(lista),
            'insumo_id': insumo_id
        })
    
    flash(mensaje, categoria)
    return redirect(url_for('orders.solicitar_insumos'))


@orders_bp.route('/eliminar_insumo_lista/<int:insumo_id>', methods=['POST'])
@jwt_required_html()
def eliminar_insumo_lista(insumo_id):
    """Elimina un insumo de la lista de solicitudes en sesión."""
    lista=session.get('lista_solicitudes', [])
    cantidades=session.get('cantidades_solicitadas', {})

    # Guardar cantidades actuales (solo en modo HTML tradicional )
  
    if not is_ajax_request():
        for id_insumo in lista:
            cantidad=request.form.get(f'cantidad_{id_insumo}', type=int)
            if cantidad and cantidad>0:
                cantidades[str(id_insumo)]=cantidad

    exito, mensaje, categoria = OrderProductService.eliminar_insumos_solicitud(lista, cantidades, insumo_id)

    #Si fue exitoso, actualizar sesión.
    if exito:
        session['lista_solicitudes'] = lista
        session['cantidades_solicitadas'] = cantidades
    

    if is_ajax_request():
        return jsonify({
            'success': exito,
            'message': mensaje,
            'category': categoria,
            'cart_count': len(lista),
            'is_empty': len(lista) == 0,
            'insumo_id': insumo_id
        })

    flash(mensaje, categoria)
    target = 'orders.confirmar_solicitud_insumos' if lista else 'orders.solicitar_insumos'
    return redirect(url_for(target))


@orders_bp.route('/confirmar_solicitud_insumos', methods=['GET', 'POST'])
@jwt_required_html()
def confirmar_solicitud_insumos():
    """Muestra la lista de insumos seleccionados para confirmar la solicitud."""
    lista = session.get('lista_solicitudes', [])
    cantidades = session.get('cantidades_solicitadas', {})

    #Controlamos la situación de llegar a esta ruta sin insumos en la lista.
    if not lista:
        flash("No hay insumos seleccionados para solicitar.", 'warning')
        return redirect(url_for('orders.solicitar_insumos'))
    
    if request.method == 'POST':
        #Actualizar cantidades desde el formulario.
        for insumo_id in lista:
            cantidad = request.form.get(f'cantidad_{insumo_id}', type=int)
            if cantidad and cantidad>0:
                cantidades[str(insumo_id)] = cantidad
        
        session['cantidades_solicitadas'] = cantidades

        try:
            #Llamamos al servicio para crear la solicitud.
            OrderProductService.crear_solicitud_insumos(current_user.id_usuario, lista, cantidades)
            #Si no lanza excepción, es que se creó exitosamente.
            session.pop('lista_solicitudes', None)
            session.pop('cantidades_solicitadas', None)
            flash("Solicitud creada exitosamente.", 'success')
            return redirect(url_for('orders.mis_solicitudes'))

        except (DomainError, InsufficientStockError) as e:
            flash(str(e), 'warning')
        except Exception as e:
            current_app.logger.error(f"Error interno al crear solicitud: {str(e)}")
            flash(f"Ocurrió un error al procesar la solicitud", 'danger')
    

    insumos = OrderProductService.obtener_insumos_ordenado(lista)
    return render_template('orders/confirmar_solicitud_insumos.html', insumos=insumos, cantidades=cantidades)


@orders_bp.route('/solicitudes_pendientes', methods = ['GET'])
@admin_required
def solicitudes_pendientes():
    """
    Vista Exclusiva para administradores.
    Muestra todas las solicitudes que tienen ítems pendientes de entrega.
    """
    #Obtenemos el filtro de búsqueda desde los parámetros de la URL y la primer página.
    filtro = request.args.get('filtro', '')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    #1.Obtenemos la query del modelo.
    query = SolicitudInsumo.obtener_solicitudes_pendientes(filtro)

    #2.Paginar la query.
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False) 


    return render_template('orders/solicitudes_pendientes.html', solicitudes=pagination.items, 
                           pagination=pagination, filtro=filtro, form=EntregarSolicitudForm())

@orders_bp.route('/mis_solicitudes', methods = ['GET'])
@jwt_required_html()
def mis_solicitudes():
    """
    Vista para el usuario.
    Muestra el historial de solicitudes completadas (listas para descargar PDF)
    """
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    #1.Obtenemos la query del modelo.
    query = SolicitudInsumo.obtener_solicitudes_completadas(current_user.id_usuario)

    #2.Paginar la query.
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return render_template('orders/mis_solicitudes.html', solicitudes=pagination.items, pagination=pagination)
    

@orders_bp.route('/entregar_solicitud/<int:detalle_id>', methods=['POST'])
@admin_required
def entregar_solicitud(detalle_id):
    """Procesa la entrega de un ítem solicitado.
       Descuenta stock y verifica si la solicitud se completa."""
    #Capturamos los datos.
    form = EntregarSolicitudForm()

    if form.validate_on_submit():
        try:
            exito, mensaje, categoria = OrderProductService.procesar_entrega_item(
                 detalle_id=detalle_id,
                 cantidad_entregada=form.cantidad_entregada.data,
                 observaciones=form.observaciones.data,
                 id_admin=current_user.id_usuario
            )
            flash(mensaje, categoria)

        except InsufficientStockError as e:
            flash(f"No se pudo entregar: {e}", 'danger')
        
        except DomainError as e:
            flash(str(e), 'warning')

        except Exception as e:
            current_app.logger.error(f"Error interno al entregar solicitud: {str(e)}")
            flash(f"Ocurrió un error al procesar la entrega", 'danger')

    else:
        #Si falla la validacion (ej:token vencido, dato invalido)
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo {getattr(form, field).label.text}: {error}", 'warning')
       
    return redirect(url_for('orders.solicitudes_pendientes'))


@orders_bp.route('/generar_pdf/<int:solicitud_id>')
@jwt_required_html()
def generar_pdf_solicitud(solicitud_id):
    """Genera un PDF con el detalle de una solicitud entregada."""
    #Validaciones (Permisos, existencia, estado)
    solicitud = db.session.get(SolicitudInsumo, solicitud_id)
    #Validación de existencia.
    if not solicitud:
        flash("La solicitud no existe.", 'danger')
        return redirect(url_for('orders.mis_solicitudes'))
    
    #Validación de Seguridad.
    es_propietario = (solicitud.id_usuario == current_user.id_usuario)
    es_admin = (current_user.rol.id_rol == 7)

    if not es_propietario and not es_admin:
        current_app.logger.warning(
            f"El usuario {current_user.id_usuario} intentó acceder al PDF de la solicitud {solicitud_id} sin permisos.")
        flash("No tienes permiso para visualizar este documento", 'danger')
        return redirect(url_for('orders.mis_solicitudes'))


    try:
        #Por buena práctica el controller debería decidir el redirect.
        buffer = OrderProductService.generar_pdf_solicitud(solicitud)

        return Response(buffer, mimetype='application/pdf', headers={
            'Content-Disposition': f'attachment;filename=solicitud_{solicitud_id}.pdf'
        })
    
    except OrderNotReadyError as e:
        #Manejo específico de reglas de negocio.
        flash(str(e), 'warning')
        return redirect(url_for('orders.mis_solicitudes'))
    
    except ValueError as e:
        #Manejo de datos corruptos.
        current_app.logger.error(f"Error de datos: {e}")
        flash(f"Error en los datos de la solicitud.", 'danger')
        return redirect(url_for('orders.mis_solicitudes'))

    except Exception as e:
        #Fallback para errores inesperados.
        current_app.logger.error(f"Error interno al generar PDF: {e}", exc_info=True)
        flash(f"Ocurrió un error al generar el PDF.", 'danger')
        return redirect(url_for('orders.mis_solicitudes'))