from app import app, db
from flask import render_template, redirect, url_for, flash, request, session, Response
from flask_login import current_user, login_user, logout_user, login_required
from app.forms import CargarInsumoForm,LoginForm
from app.models import Insumo, EntradaInsumo, SalidaInsumo, SolicitudInsumo, User, SolicitudDetalle, Proveedor, Rol, Dependencia
from app.decorators import admin_required
from sqlalchemy import or_
import sqlalchemy as sa
import csv
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

#PAGINA PRINCIPAL/RUTAS DE LA APLICACION
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# MUESTRA UNA TABLA DEL INVENTARIO COMPLETO, ADEMAS PERMITE FILTRAR POR CODIGO O DESCRIPCION
@app.route('/consultar_inventario', methods=['GET'])
@admin_required
def consultar_inventario():
    filtro=request.args.get('filtro', '')
    if filtro:
        insumos = Insumo.query.filter(
            or_(
                Insumo.codigo_insumo.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        ).all()
    else:
        insumos = Insumo.query.all()
    return render_template('consultar_inventario.html', insumos=insumos, filtro=filtro)

# RUTA PARA CARGAR INSUMOS AL INVENTARIO, SOLO ACCESIBLE PARA ADMINISTRADORES
# SI EL INSUMO YA EXISTE, ACTUALIZA EL STOCK, SI NO, CREA UN NUEVO REGISTRO
# SI EL INSUMO ES NUEVO, LA CANTIDAD DE ENTRADAS SERIA EL STOCK ACTUAL Y LA EXISTENCIA INICIAL DEL AÑO
@app.route('/cargar_insumos', methods=['GET', 'POST'])
@admin_required
def cargar_insumos():
    form = CargarInsumoForm()
    if form.validate_on_submit():
        insumo=db.session.scalar(sa.select(Insumo)
                                 .where(Insumo.codigo_insumo==form.codigo_producto.data))
        if insumo:
            insumo.stock_actual+=form.cantidad_entradas.data
            if insumo.cantidad_entradas is None:
                insumo.cantidad_entradas=0
            insumo.cantidad_entradas+=form.cantidad_entradas.data
            db.session.commit()
            flash(f'Se han actualizado las existencias del insumo {insumo.codigo_insumo}.', 'success')
        else:
            nuevo_insumo = Insumo(
                codigo_insumo=form.codigo_producto.data,
                descripcion=form.descripcion.data,
                stock_actual=form.cantidad_entradas.data,
                existencias_iniciales_anio=form.cantidad_entradas.data
            )
            db.session.add(nuevo_insumo)
            db.session.commit()
            flash(f'Se ha agregado un nuevo insumo: {nuevo_insumo.codigo_insumo}.', 'success')
        
        proveedor=db.session.scalar(sa.select(Proveedor).where(Proveedor.nombre==form.proveedor.data))
        if not proveedor:
            proveedor=Proveedor(nombre=form.proveedor.data)
            db.session.add(proveedor)
            db.session.commit()

        nueva_entrada = EntradaInsumo(
            id_proveedor=proveedor.id_proveedor,
            cantidad=form.cantidad_entradas.data,
            id_insumo=insumo.id if insumo else nuevo_insumo.id,
        )
        db.session.add(nueva_entrada)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('cargar_insumos.html', form=form)

# RUTA PARA SOLICITAR INSUMOS, MUESTRA UNA TABLA DE INSUMOS CON UN BOTON PARA SOLICITAR
# PERMITE FILTRAR POR CODIGO O DESCRIPCION
@app.route('/solicitar_insumos', methods=['GET'])
@login_required
def solicitar_insumos():
    filtro=request.args.get('filtro', '')
    if filtro:
        insumos = Insumo.query.filter(
            or_(
                Insumo.codigo_insumo.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        ).all()
    else:
        insumos = Insumo.query.all()
    return render_template('solicitar_insumos.html', insumos=insumos, filtro=filtro)

# RUTA PARA VER LAS SOLICITUDES
# PARA USUARIOS SOLO MUESTRA SI ALGUNA SOLICITUD TUYA FUE COMPLETADA Y SE PUEDE DESCARGAR EL PDF
# PARA ADMINISTRADORES MUESTRA TODAS LAS SOLICITUDES PENDIENTES Y PERMITE ENTREGAR REGISTRO POR REGISTRO
# EL ADMINISTRADOR DEBE CARGAR LA CANTIDAD ENTREGADA Y LAS OBSERVACIONES
@app.route('/ver_solicitudes', methods=['GET'])
@login_required
def ver_solicitudes():
    filtro = request.args.get('filtro', '')
    query = sa.select(SolicitudInsumo).join(User).where(SolicitudInsumo.estado == False)
    if filtro:
        try:
            numero_solicitud = int(filtro)
            query = query.where(SolicitudInsumo.id_solicitud == numero_solicitud)
        except ValueError:
            flash('Por favor ingresa un número de solicitud válido.', 'warning')

    solicitudes_pendientes = db.session.scalars(
        query.order_by(SolicitudInsumo.fecha_solicitud.desc())
    ).all()
    if not solicitudes_pendientes:
        flash('No hay solicitudes pendientes.', 'info')
    
    solicitudes_completadas_usuario = db.session.scalars( 
        sa.select(SolicitudInsumo)
        .where(SolicitudInsumo.id_usuario == current_user.id_usuario)
        .filter(sa.not_(SolicitudInsumo.detalles.any(SolicitudDetalle.salidas == None)))
        .order_by(SolicitudInsumo.fecha_solicitud.desc())
    ).all()
    print("Solicitudes completadas para PDF:", [s.id_solicitud for s in solicitudes_completadas_usuario])

    return render_template('ver_solicitudes.html', solicitudes_pendientes=solicitudes_pendientes, solicitudes_completadas_usuario=solicitudes_completadas_usuario, filtro=filtro)

# LOGICA COMPLETA DETRÁS DE LA ACCION DE ENTREGAR UNA SOLICITUD
# SE ACTUALIZA EL STOCK, SE CREA EL REGISTRO DE SALIDA, SE ACTUALIZA EL ESTADO DE LA SOLICITUD
# SI TODOS LOS DETALLES DE LA SOLICITUD FUERON ENTREGADOS, SE MARCA LA SOLICITUD COMO COMPLETADA
@app.route('/entregar_solicitud/<int:detalle_id>', methods=['POST'])
@admin_required
def entregar_solicitud(detalle_id):
    # Obtenemos el detalle específico usando el detalle_id
    detalle = db.session.get(SolicitudDetalle, detalle_id)
    if not detalle:
        flash('El ítem de la solicitud no existe.', 'danger')
        return redirect(url_for('ver_solicitudes'))

    # Obtenemos la solicitud y el insumo a partir del detalle
    solicitud = detalle.solicitud
    insumo = detalle.insumo
    
    cantidad_entregada = request.form.get('cantidad_entregada', type=int, default=detalle.cantidad_solicitada)
    observaciones = request.form.get('observaciones', type=str, default='')

    if cantidad_entregada > insumo.stock_actual:
        flash(f'No hay suficiente stock para entregar {insumo.descripcion}. Stock actual: {insumo.stock_actual}.', 'danger')
        return redirect(url_for('ver_solicitudes'))
    
    if cantidad_entregada > detalle.cantidad_solicitada:
        flash('La cantidad entregada no puede ser mayor a la cantidad solicitada.', 'danger')
        return redirect(url_for('ver_solicitudes'))

    # Crear la salida para este detalle específico
    nueva_salida = SalidaInsumo(
        cantidad_entregada=cantidad_entregada,
        id_usuario=solicitud.id_usuario,
        id_insumo=insumo.id,
        id_solicitudes_insumos=detalle.id_solicitudes_insumos,
        observaciones=observaciones
    )
    db.session.add(nueva_salida)

    # Actualizar el stock del insumo
    insumo.stock_actual -= cantidad_entregada
    if insumo.cantidad_salidas is None:
        insumo.cantidad_salidas = 0
    insumo.cantidad_salidas += cantidad_entregada
    if (insumo.existencias_iniciales_anio + insumo.cantidad_entradas) > 0:
        insumo.porcentaje_utilizado = (insumo.cantidad_salidas / (insumo.existencias_iniciales_anio + insumo.cantidad_entradas)) * 100

    # Actualizar el estado de la solicitud
    todos_entregados = all(len(d.salidas) > 0 for d in solicitud.detalles)
    if todos_entregados:
        solicitud.estado = True

    db.session.commit()
    flash(f'Insumo "{insumo.descripcion}" entregado y registrado como salida.', 'success')
    
    return redirect(url_for('ver_solicitudes'))

# RUTA QUE MUESTRA LA TABLA CON TODAS LAS SALIDAS DE INSUMOS
# SE PUEDE FILTRAR POR DEPENDENCIA, USUARIO, FECHA O DESCRIPCION DEL INSUMO
@app.route('/salida_insumos')
@admin_required
def salida_insumos():
    filtro = request.args.get('filtro', '')
    query = sa.select(SalidaInsumo).join(User).join(Insumo).join(Dependencia, User.id_dependencia==Dependencia.id_dependencia).order_by(SalidaInsumo.fecha_salida.desc(), SalidaInsumo.id_salida.desc())
    if filtro:
        query = query.where(
            sa.or_(
                Dependencia.nombre_dependencia.ilike(f'%{filtro}%'),
                User.nombre.ilike(f'%{filtro}%'),
                SalidaInsumo.fecha_salida.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        )
    salidas = db.session.scalars(query).all()
    return render_template('salida_insumos.html', salidas=salidas, filtro=filtro)

# RUTA QUE MUESTRA LA TABLA CON TODAS LAS ENTRADAS DE INSUMOS
# SE PUEDE FILTRAR POR PROVEEDOR, CANTIDAD, FECHA O DESCRIPCION DEL INSUMO
@app.route('/entrada_insumos')
@admin_required
def entrada_insumos():
    filtro = request.args.get('filtro', '')
    query = sa.select(EntradaInsumo).join(Proveedor, EntradaInsumo.id_proveedor==Proveedor.id_proveedor).join(Insumo, EntradaInsumo.id_insumo==Insumo.id).order_by(EntradaInsumo.fecha_entrada.desc(), EntradaInsumo.id_entrada.desc())
    if filtro:
        query = query.where(
            sa.or_(
                Proveedor.nombre.ilike(f'%{filtro}%'),
                EntradaInsumo.cantidad.ilike(f'%{filtro}%'),
                EntradaInsumo.fecha_entrada.ilike(f'%{filtro}%'),
                Insumo.codigo_insumo.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        )

    entradas = db.session.scalars(query).all()
    return render_template('entrada_insumos.html', entradas=entradas, filtro=filtro)

# RUTAS DE AUTENTICACION DE USUARIOS, LOGICAS DE LOGIN, LOGOUT Y CAMBIO DE CONTRASEÑA
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.cedula == form.cedula.data))
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        flash('Inicio de sesión exitoso', 'success')
        return redirect(url_for('index'))
    return render_template('login.html', form=form)


@app.route('/cambiar_contraseña', methods=['GET', 'POST'])
@login_required
def cambiar_contraseña():
    if request.method=='POST':
        contraseña_actual=request.form.get('contraseña_actual')
        nueva_contraseña=request.form.get('nueva_contraseña')
        confirmar_contraseña=request.form.get('confirmar_contraseña')
        if not current_user.check_password(contraseña_actual):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('cambiar_contraseña'))
        elif nueva_contraseña!=confirmar_contraseña:
            flash('Las contraseñas nuevas no coinciden','danger')
            return redirect(url_for('cambiar_contraseña'))
        else:
            current_user.set_password(nueva_contraseña)
            db.session.commit()
            flash('Contraseña cambiada con exito','success')
            return redirect(url_for('index'))
    return render_template('cambiar_contraseña.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada','info')
    return redirect(url_for('login'))

# LOGICA DE ALMACENAMIENTO DE LA LISTA DE SOLICITUDES EN SESION
# SE ALMACENA UNA LISTA DE IDS DE INSUMOS EN LA SESION
# MEDIANTE EL BOTON DE AGREGAR
@app.route('/agregar_insumos/<int:insumo_id>', methods=['POST'])
@login_required
def agregar_insumos(insumo_id):
    lista=session.get('lista_solicitudes', [])
    insumo=Insumo.query.get_or_404(insumo_id)
    if insumo_id not in lista:
        lista.append(insumo_id)
        session['lista_solicitudes']=lista
        flash(f'Insumo: {insumo.descripcion} agregado a la lista de solicitudes.', 'success')
    else:
        flash('El insumo ya está en la lista de solicitudes.', 'info')
    return redirect(url_for('solicitar_insumos'))    

# RUTA PARA CONFIRMAR LA SOLICITUD DE INSUMOS
# MUESTRA LA LISTA DE INSUMOS SELECCIONADOS, PERMITE INGRESAR LAS CANTIDADES SOLICITADAS
# AL DAR CONFIRMAR SE CARGA LA SOLICITUD Y EL DETALLE DE LA SOLICITUD
@app.route('/confirmar_solicitud_insumos', methods=['GET', 'POST'])
@login_required
def confirmar_solicitud_insumos():
    lista=session.get('lista_solicitudes', [])
    insumos=Insumo.query.filter(Insumo.id.in_(lista)).all() if lista else []
    insumos = sorted(insumos, key=lambda x: lista.index(x.id))
    cantidades=session.get('cantidades_solicitadas', {})
    if request.method=='POST':

        for insumo in insumos:
            cantidad=request.form.get(f'cantidad_{insumo.id}', type=int)
            if cantidad and cantidad>0:
                cantidades[str(insumo.id)]=cantidad
        session['cantidades_solicitadas']=cantidades

        for insumo in insumos:
            cantidad_solicitada = cantidades.get(str(insumo.id))
            if cantidad_solicitada and cantidad_solicitada>0:
                if cantidad_solicitada>insumo.stock_actual:
                    flash(f'La cantidad solicitada para {insumo.descripcion} no puede ser mayor al stock actual.', 'danger')
                    return redirect(url_for('confirmar_solicitud_insumos'))
        nueva_solicitud = SolicitudInsumo(
            id_usuario=current_user.id_usuario,
            estado=False,   
        )
        db.session.add(nueva_solicitud)
        db.session.flush()
        for insumo in insumos:
            cantidad_solicitada= cantidades.get(str(insumo.id))
            if cantidad_solicitada and cantidad_solicitada>0:
                nuevo_detalle = SolicitudDetalle(
                    cantidad_solicitada=cantidad_solicitada,
                    id_solicitud=nueva_solicitud.id_solicitud,
                    id_insumo=insumo.id
                )
                db.session.add(nuevo_detalle)
        db.session.commit()
        session.pop('lista_solicitudes', None)
        session.pop('cantidades_solicitadas', None)
        flash('Solicitudes de insumos creadas con éxito.', 'success')
        return redirect(url_for('index'))
    return render_template('confirmar_solicitud_insumos.html', insumos=insumos, cantidades=cantidades)

# LOGICA DETRÁS DEL BOTON DE ELIMINAR UN INSUMO DE LA LISTA DE SOLICITUDES
@app.route('/eliminar_insumo_lista/<int:insumo_id>', methods=['POST'])
@login_required
def eliminar_insumo_lista(insumo_id):
    lista=session.get('lista_solicitudes', [])
    cantidades=session.get('cantidades_solicitadas', {})

    for id in lista:
        cantidad=request.form.get(f'cantidad_{id}', type=int)
        if cantidad and cantidad>0:
            cantidades[str(id)]=cantidad

    if insumo_id in lista:
        lista.remove(insumo_id)
        session['lista_solicitudes']=lista
        cantidades.pop(str(insumo_id), None)
        session['cantidades_solicitadas']=cantidades
        flash('Insumo eliminado de la lista de solicitudes.', 'success')
    else:
        flash('El insumo no está en la lista de solicitudes.', 'info')
    return redirect(url_for('confirmar_solicitud_insumos'))


# RUTAS DE EXPORTACIÓN A CSV. CADA RUTA REUTILIZA LA MISMA LOGICA DE CONSULTA QUE LA VISTA NORMAL
# PARA GENERAR EL ARCHIVO CSV DESCARGABLE
@app.route('/exportar/inventario')
@admin_required
def exportar_inventario():
    filtro = request.args.get('filtro', '')
    # Reutilizamos la misma lógica de consulta que la vista normal
    if filtro:
        insumos = Insumo.query.filter(
            or_(
                Insumo.codigo_insumo.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        ).all()
    else:
        insumos = Insumo.query.all()

    output = io.StringIO()
    writer = csv.writer(output)    
    
    #Fila de encabezado
    writer.writerow(['ID', 'Codigo Insumo', 'Descripcion', 'Existencias Iniciales Anho', 'Stock Actual', 'Cantidad Entradas', 'Cantidad Salidas', 'Porcentaje Utilizado'])

    for insumo in insumos:
        writer.writerow([
            insumo.id,
            insumo.codigo_insumo,
            insumo.descripcion,
            insumo.existencias_iniciales_anio,
            insumo.stock_actual,
            insumo.cantidad_entradas,
            insumo.cantidad_salidas,
            f"{insumo.porcentaje_utilizado:.2f}%" if insumo.porcentaje_utilizado is not None else "0.00%"
        ])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=inventario.csv"})

@app.route('/exportar/entradas')
@admin_required
def exportar_entradas():
    filtro = request.args.get('filtro', '')
    # Reutilizamos la misma lógica de consulta
    query = sa.select(EntradaInsumo).join(Proveedor).join(Insumo).order_by(EntradaInsumo.fecha_entrada.desc())
    if filtro:
        query = query.where(
            sa.or_(
                Proveedor.nombre.ilike(f'%{filtro}%'),
                Insumo.codigo_insumo.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        )
    entradas = db.session.scalars(query).all()

    output = io.StringIO()
    writer = csv.writer(output)
    #Fila de encabezado
    writer.writerow(['ID Entrada', 'Proveedor', 'Codigo Insumo', 'Descripcion Insumo', 'Cantidad', 'Fecha Entrada'])

    for entrada in entradas:
        writer.writerow([
            entrada.id_entrada,
            entrada.proveedor.nombre,
            entrada.insumo.codigo_insumo,
            entrada.insumo.descripcion,
            entrada.cantidad,
            entrada.fecha_entrada.strftime('%d/%m/%Y')
        ])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=entradas_insumos.csv"})

@app.route('/exportar/salidas')
@admin_required
def exportar_salidas():
    filtro = request.args.get('filtro', '')
    # Reutilizamos la misma lógica de consulta
    query = sa.select(SalidaInsumo).join(User).join(Insumo).join(Dependencia, User.id_dependencia==Dependencia.id_dependencia).order_by(SalidaInsumo.fecha_salida.desc())
    if filtro:
        query = query.where(
            sa.or_(
                Dependencia.nombre_dependencia.ilike(f'%{filtro}%'),
                User.nombre.ilike(f'%{filtro}%'),
                SalidaInsumo.fecha_salida.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        )
    salidas = db.session.scalars(query).all()

    output = io.StringIO()
    writer = csv.writer(output)
    #Fila de encabezado
    writer.writerow(['ID Salida', 'Dependencia', 'Usuario', 'Codigo Insumo', 'Descripcion Insumo', 'Cantidad Entregada', 'Fecha Salida', 'Observaciones'])

    for salida in salidas:
        writer.writerow([
            salida.id_salida,
            salida.usuario.dependencia.nombre_dependencia,
            salida.usuario.nombre,
            salida.insumo.codigo_insumo,
            salida.insumo.descripcion,
            salida.cantidad_entregada,
            salida.fecha_salida.strftime('%d/%m/%Y'),
            salida.observaciones or ''
        ])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=salidas_insumos.csv"})

# === RUTA PARA GENERAR PDF DE SOLICITUD ENTREGADA ===

@app.route('/generar_pdf/<int:solicitud_id>')
@login_required
def generar_pdf_solicitud(solicitud_id):
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle

    solicitud = db.session.get(SolicitudInsumo, solicitud_id)

    if not solicitud:
        flash('La solicitud no existe.', 'danger')
        return redirect(url_for('ver_solicitudes'))

    if solicitud.id_usuario != current_user.id_usuario and not current_user.id_rol == 1:
        flash('No tienes permiso para generar el PDF de esta solicitud.', 'danger')
        return redirect(url_for('ver_solicitudes') )

    todos_entregados = all(len(detalle.salidas) > 0 for detalle in solicitud.detalles)
    if not todos_entregados:
        flash('No se puede generar el PDF hasta que todos los insumos de la solicitud hayan sido entregados.', 'warning')
        return redirect(url_for('ver_solicitudes'))

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- LOGO GRANDE CENTRADO ---
    # Ajusta el tamaño y posición del logo para que ocupe el espacio del título
    logo_path = "app/static/logo.png"
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

    return Response(buffer, mimetype='application/pdf', headers={
        'Content-Disposition': f'attachment;filename=solicitud_{solicitud_id}.pdf'
    })
#Cargar las existencias iniciales del año. Habilitar.
"""
@app.route('/cargar_existencias_iniciales', methods=['GET', 'POST'])
def cargar_existencias_inciales():
    insumos = Insumo.query.all()
    if request.method == 'POST':
        for insumo in insumos:
            valor = request.form.get(f'existencias_{insumo.id}', type=int)
            if valor is not None:
                insumo.existencias_iniciales_anio = valor
                insumo.cantidad_entradas = 0
                insumo.cantidad_salidas = 0
                insumo.porcentaje_utilizado = 0.0
                insumo.stock_actual = valor
        db.session.commit()
        flash('Existencias iniciales actualizadas para el nuevo año.', 'success')
        return redirect(url_for('index'))
    return render_template('cargar_existencias_iniciales.html', insumos=insumos)
"""
