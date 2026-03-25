from app import db
from flask import render_template, url_for, redirect, request, flash, Response, current_app, jsonify
from flask_jwt_extended import current_user
from app.shared.filters import FilterParams
from app.shared.decorators import admin_required
from app.shared.models import Insumo, EntradaInsumo, SalidaInsumo, Proveedor, Dependencia
from app.shared.errors import DomainError, InvalidProductError
from .forms import CargarInsumoForm, CargarInsumosMultipleForm, ImportarInsumoForm
from .services import InventoryService
from .validators import InsumoInput
from . import inventory_bp
import logging


logger = logging.getLogger(__name__)

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
        
        except (InvalidProductError,DomainError) as e:
            #Errores de negocio --> Amarillo.
            flash(str(e), 'warning')
        except Exception as e:
            #Errores inesperados --> Rojo.
            logger.error(f"Error crítico al cargar el insumo: {str(e)}", exc_info=True)
            flash('Error interno del servidor. Consulte al administrador.', 'danger')
    
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo {getattr(form, field).label.text}: {error}", 'warning')

    return render_template('inventory/cargar_insumos.html', form=form)


@inventory_bp.route('/cargar_insumos_multiple', methods=['GET', 'POST'])
@admin_required
def cargar_insumos_multiple():
    """Carga múltiple con formulario dinámico."""
    form = CargarInsumosMultipleForm()

    if form.validate_on_submit():
        try:
            #1.Convertir datos del formulario a InsumoInput.
            insumos_input = []
            for idx, subform in enumerate(form.insumos.data, start=1):
                insumo = InsumoInput(
                    codigo=subform['codigo_producto'],
                    descripcion=subform.get('descripcion'),
                    cantidad=subform['cantidad_entradas'],
                    proveedor=subform['proveedor'],
                    fila=idx
                )
                insumos_input.append(insumo)
            
            #2.Procesar carga múltiple.
            resultado = InventoryService.cargar_insumos_multiple(insumos_input)

            #3.Mostrar resultados.
            if resultado['exitosos'] > 0:
                flash(
                    f"✅ Carga exitosa: {resultado['exitosos']} insumos procesados "
                    f"({len(resultado['insumos_creados'])} nuevos, "
                    f"{len(resultado['insumos_actualizados'])} actualizados)",
                    'success'
                )
            
            if resultado['fallidos'] > 0:
                errores_texto = "<br>".join([
                    f"Fila {err['fila']}: {err['mensaje']}" 
                    for err in resultado['errores'] 
                    if err['tipo'] == 'error'
                ])
                flash(f"⚠️ {resultado['fallidos']} insumos con errores:<br>{errores_texto}", 'warning')

            #Mostrar advertencias.
            warnings = [err for err in resultado['errores'] if err['tipo'] == 'warning']
            if warnings:
                warnings_texto = "<br>".join([f"Fila {w['fila']}: {w['mensaje']}" for w in warnings])
                flash(f"ℹ️ Advertencias:<br>{warnings_texto}", 'info')
            
            if resultado['exitosos'] > 0:
                return redirect(url_for('inventory.entrada_insumos'))
            
        except Exception as e:
            logger.error(f"Error crítico al cargar insumos múltiples: {str(e)}", exc_info=True)
            flash('Error interno del servidor. Consulte al administrador.', 'danger')

    return render_template('inventory/cargar_insumos_multiple.html', form=form)

@inventory_bp.route('/importar_insumos', methods=['GET', 'POST'])
@admin_required
def importar_insumos():
    """Importación masiva desde CSV o Excel"""
    form = ImportarInsumoForm()

    if form.validate_on_submit():
        try:
            archivo = form.archivo.data
            filename = archivo.filename

            #Procesar importación.
            resultado = InventoryService.importar_desde_csv(archivo.stream, filename)
            
            #Mostrar resultados.
            flash(
                f"📊 Archivo procesado: {resultado['total_filas']} filas detectadas",
                'info'
            )

            if resultado['exitosos'] > 0:
                flash(
                    f"✅ Importación exitosa: {resultado['exitosos']} insumos cargados "
                    f"({len(resultado['insumos_creados'])} nuevos, "
                    f"{len(resultado['insumos_actualizados'])} actualizados)",
                    'success'
                )
            
            if resultado['fallidos'] > 0:
                errores_por_tipo = {}
                for err in resultado['errores']:
                    tipo = err['tipo']
                    if tipo not in errores_por_tipo:
                        errores_por_tipo[tipo] = []
                    errores_por_tipo[tipo].append(f"Fila {err['fila']} ({err['codigo']}): {err['mensaje']}")
                
                if 'error' in errores_por_tipo:
                    flash(
                        f"⚠️ {len(errores_por_tipo['error'])} filas con errores:<br>" +
                        "<br>".join(errores_por_tipo['error'][:10]) +
                        (f"<br>... y {len(errores_por_tipo['error']) - 10} más" 
                         if len(errores_por_tipo['error']) > 10 else ""),
                        'warning'
                    )

            if resultado['exitosos'] > 0:
                return redirect(url_for('inventory.entrada_insumos'))
            
        except InvalidProductError as e:
            flash(f"Error de validación: {str(e)}", 'warning')
        except Exception as e:
            logger.error(f"Error en importación: {e}", exc_info=True)
            flash('Error interno del servidor. Consulte al administrador.', 'danger')

    return render_template('inventory/importar_insumos.html', form=form)


@inventory_bp.route('/salida_insumos')
@admin_required
def salida_insumos():
    """
    Consulta de salidas de insumos con filtros avanzados.

    Query Params:
        -filtro: Búsqueda por código/descripción/proveedor
        -fecha_desde: Fecha inicial (YYYY-MM-DD)
        -fecha_hasta: Fecha final (YYYY-MM-DD)
        -entidad_id: ID del proveedor o dependencia
        -page: Número de página
    """
    #1.Parsear y validar parámetros.
    params = FilterParams(request.args)

    #2.Obtener query filtrada del servicio.
    query = InventoryService.filtrar_salidas(params)
    
    #3.Paginar resultados.
    per_page = current_app.config['ITEMS_PER_PAGE']
    pagination = db.paginate(query, page=params.page, per_page=per_page, error_out=False)

    #4.Obtener dependencias para el filtro dropdown.
    dependencias = Dependencia.query.order_by(Dependencia.nombre_dependencia).all()

    return render_template('inventory/salida_insumos.html', salidas=pagination.items, filtros=params.to_dict(), pagination=pagination, dependencias=dependencias)


@inventory_bp.route('/entrada_insumos')
@admin_required
def entrada_insumos():
    """
    Consulta de entradas de insumos con filtros avanzados
    
    Query Params:
        -filtro: Búsqueda por código/descripción/proveedor
        -fecha_desde: Fecha inicial (YYYY-MM-DD)
        -fecha_hasta: Fecha final (YYYY-MM-DD)
        -entidad_id: ID del proveedor
        -page: Número de página
    """
    #1.Parsear y validar parámetros.
    params = FilterParams(request.args)

    #2.Obtener query filtrada del servicio.
    query = InventoryService.filtrar_entradas(params)

    #3.Paginar resultados.
    per_page = current_app.config['ITEMS_PER_PAGE']
    pagination = db.paginate(query, page=params.page, per_page=per_page, error_out=False)

    #4.Obtener proveedores para el filtro dropdown.
    proveedores = Proveedor.query.order_by(Proveedor.nombre).all()

    return render_template('inventory/entrada_insumos.html', entradas=pagination.items, filtros=params.to_dict(), pagination=pagination, proveedores=proveedores)


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


@inventory_bp.route('/descargar_plantilla_csv')
@admin_required
def descargar_plantilla_csv():
    """Descarga plantilla de ejemplo para importación"""
    contenido_csv = """codigo,descripcion,cantidad,proveedor
INS001,Resma de Papel A4 (500 hojas),10,Librería Central S.A.
INS002,Lápices HB (Caja x12),5,Papelería Express
INS003,Marcadores Permanentes (Set x4),8,Comercial ABC
INS004,Grapadora Metálica,3,OfficeMax
INS005,Clips Metálicos (Caja x100),20,Distribuidora XYZ"""
    
    response = Response(contenido_csv, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=plantilla_insumos.csv'
    return response


@inventory_bp.route('/api/agregar_fila_insumo', methods=['POST'])
@admin_required
def api_agregar_fila_insumo():
    """Endpoint AJAX para agregar filas dinámicamente en carga múltiple"""
    try:
        form = CargarInsumosMultipleForm()
        form.insumos.append_entry()
        
        # Renderizar solo la nueva fila
        nueva_fila_html = render_template(
            'inventory/_insumo_line_form.html',
            form=form,
            index=len(form.insumos) - 1
        )
        
        return jsonify({
            'success': True,
            'html': nueva_fila_html,
            'total_filas': len(form.insumos)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400