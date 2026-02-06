from app import db
from flask import render_template, url_for, redirect, request, flash, Response, current_app
from app.shared.decorators import admin_required
from app.shared.models import Insumo, EntradaInsumo, SalidaInsumo
from app.shared.errors import DomainError
from .forms import CargarInsumoForm
from .services import InventoryService
from . import inventory_bp


@inventory_bp.route('/consultar_inventario', methods=['GET'])
@admin_required
def consultar_inventario():
    """Ruta para consultar el inventario de insumos con paginación y filtro de búsqueda."""
    #Obtener el filtro de búsqueda desde los parámetros de la URL.
    filtro=request.args.get('filtro', '')
    #Obtenemos la primer página o página actual.
    page = request.args.get('page', 1, type=int)   
    per_page = current_app.config['ITEMS_PER_PAGE']
    #1. Obtenemos la query del modelo.
    query = Insumo.filtro_insumos(filtro)

    #2. Paginar la query.
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return render_template('inventory/consultar_inventario.html', insumos=pagination.items, pagination=pagination, filtro=filtro)


@inventory_bp.route('/cargar_insumos', methods=['GET', 'POST'])
@admin_required
def cargar_insumos():
    """Ruta para cargar insumos al inventario."""
    form = CargarInsumoForm()
    if form.validate_on_submit():
        try:
            #Llamamos al servicio pasando los datos del formulario.
            insumo, mensaje = InventoryService.cargar_insumos(
                codigo_insumo=form.codigo_producto.data,
                cantidad=form.cantidad_entradas.data,
                nombre_proveedor=form.proveedor.data,
                descripcion=form.descripcion.data
            )
            flash(mensaje, 'success')
            return redirect(url_for('inventory.entrada_insumos'))
        
        except DomainError as e:
            #Errores de negocio --> Amarillo.
            flash(str(e), 'warning')
        except Exception as e:
            #Errores inesperados --> Rojo.
            current_app.logger.error(f"Error interno al cargar insumos: {str(e)}")
            flash(f"Error interno: {str(e)}", 'danger')
    
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo {getattr(form, field).label.text}: {error}", 'warning')

    return render_template('inventory/cargar_insumos.html', form=form)



@inventory_bp.route('/salida_insumos')
@admin_required
def salida_insumos():
    """Ruta para consultar las salidas de insumos con paginación y filtro de búsqueda."""
    #Obtenemos el filtro de búsqueda desde los parámetros de la URL.
    filtro = request.args.get('filtro', '')
    #Obtenemos la primera página o página actual.
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    #1. Obtenemos la query del modelo.
    query = SalidaInsumo.filtro_salidas_insumos(filtro)
    #2. Paginar la query.
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return render_template('inventory/salida_insumos.html', salidas=pagination.items, filtro=filtro, pagination=pagination)


@inventory_bp.route('/entrada_insumos')
@admin_required
def entrada_insumos():
    """Ruta para consultar las entradas de insumos con paginación y filtro de búsqueda."""
    #Obtenemos el filtro de búsqueda desde los parámetros de la URL.
    filtro = request.args.get('filtro', '')
    #Obtenemos la primera página o página actual.
    page=request.args.get('page', 1, type=int)
    per_page = current_app.config['ITEMS_PER_PAGE']
    #1. Obtenemos la query del modelo.
    query = EntradaInsumo.filtro_entradas_insumos(filtro)

    #2. Paginar la query.
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    
    return render_template('inventory/entrada_insumos.html', entradas=pagination.items, filtro=filtro, pagination=pagination)


@inventory_bp.route('/exportar/inventario')
@admin_required
def exportar_inventario():
    """Lógica para exportar el inventario en formato CSV."""
    filtro = request.args.get('filtro', '')

    #Delegamos la lógica al servicio.
    csv_output = InventoryService.generar_csv_inventario(filtro)

    return Response(csv_output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=inventario.csv"})

@inventory_bp.route('/exportar/entradas')
@admin_required
def exportar_entradas():
    """Lógica para exportar el inventario en formato CSV."""
    filtro = request.args.get('filtro', '')

    #Delegamos la lógica al servicio.
    csv_output = InventoryService.generar_csv_entradas(filtro)

    return Response(csv_output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=entradas.csv"})


@inventory_bp.route('/exportar/salidas')
@admin_required
def exportar_salidas():
    """Lógica para exportar las salidas de insumos en formato CSV."""
    filtro = request.args.get('filtro', '')

    #Delegamos la lógica al servicio.
    csv_output = InventoryService.generar_csv_salidas(filtro)

    return Response(csv_output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=salidas.csv"})