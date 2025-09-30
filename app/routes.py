from app import app, db
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import current_user, login_user, logout_user, login_required
from app.forms import CargarInsumoForm,LoginForm
from app.models import Insumo, EntradaInsumo, SalidaInsumo, SolicitudInsumo, User
from app.decorators import admin_required
from sqlalchemy import or_
import sqlalchemy as sa

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# Additional routes can be added here
@app.route('/consultar_inventario', methods=['GET'])
@admin_required
def consultar_inventario():
    filtro=request.args.get('filtro', '')
    if filtro:
        insumos = Insumo.query.filter(
            or_(
                Insumo.codigo_producto.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        ).all()
    else:
        insumos = Insumo.query.all()
    return render_template('consultar_inventario.html', insumos=insumos, filtro=filtro)

@app.route('/cargar_insumos', methods=['GET', 'POST'])
@admin_required
def cargar_insumos():
    form = CargarInsumoForm()
    if form.validate_on_submit():
        insumo=db.session.scalar(sa.select(Insumo)
                                 .where(Insumo.codigo_producto==form.codigo_producto.data))
        if insumo:
            insumo.stock_actual+=form.cantidad_entradas.data
            if insumo.cantidad_entradas is None:
                insumo.cantidad_entradas=0
            insumo.cantidad_entradas+=form.cantidad_entradas.data
            db.session.commit()
            flash(f'Se han actualizado las existencias del insumo {insumo.codigo_producto}.', 'success')
        else:
            nuevo_insumo = Insumo(
                codigo_producto=form.codigo_producto.data,
                descripcion=form.descripcion.data,
                stock_actual=form.cantidad_entradas.data,
                existencias_iniciales_anio=form.cantidad_entradas.data
            )
            db.session.add(nuevo_insumo)
            db.session.commit()
            flash(f'Se ha agregado un nuevo insumo: {nuevo_insumo.codigo_producto}.', 'success')    
        nueva_entrada = EntradaInsumo(
            proveedor=form.proveedor.data,
            cantidad=form.cantidad_entradas.data,
            insumo_id=insumo.id if insumo else nuevo_insumo.id,
        )
        db.session.add(nueva_entrada)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('cargar_insumos.html', form=form)


@app.route('/solicitar_insumos', methods=['GET'])
@login_required
def solicitar_insumos():
    filtro=request.args.get('filtro', '')
    if filtro:
        insumos = Insumo.query.filter(
            or_(
                Insumo.codigo_producto.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        ).all()
    else:
        insumos = Insumo.query.all()
    return render_template('solicitar_insumos.html', insumos=insumos, filtro=filtro)


@app.route('/ver_solicitudes', methods=['GET'])
@login_required
def ver_solicitudes():
    solicitudes = db.session.scalars(
        sa.select(SolicitudInsumo)
        .join(User)
        .join(Insumo)
        .where(SolicitudInsumo.estado == 'pendiente')
        .order_by(SolicitudInsumo.fecha_solicitud.desc())
    ).all()
    if not solicitudes:
        flash('No hay solicitudes pendientes.', 'info')
        return redirect(url_for('index'))
    return render_template('ver_solicitudes.html', solicitudes=solicitudes)

@app.route('/entregar_solicitud/<int:solicitud_id>', methods=['POST'])
@admin_required
def entregar_solicitud(solicitud_id):
    solicitud = SolicitudInsumo.query.get_or_404(solicitud_id)
    insumo = Insumo.query.get_or_404(solicitud.insumo_id)
    cantidad_entregada=request.form.get('cantidad_entregada', type=int, default=solicitud.cantidad_solicitada)
    if cantidad_entregada > insumo.stock_actual:
        flash('No hay suficiente stock para completar la entrega.', 'danger')
        return redirect(url_for('ver_solicitudes'))
    
    if cantidad_entregada > solicitud.cantidad_solicitada:
        flash('La cantidad entregada no puede ser mayor a la cantidad solicitada.', 'danger')
        return redirect(url_for('ver_solicitudes'))

    solicitud.estado = 'entregada'
    db.session.commit()
    flash('Solicitud entregada y registrada como salida.', 'success')
    
    nueva_salida = SalidaInsumo(
        usuario_id=solicitud.usuario_id,
        cantidad_solicitada=solicitud.cantidad_solicitada,
        cantidad_entregada=cantidad_entregada,
        insumo_id=insumo.id  
    )
    db.session.add(nueva_salida)
    db.session.commit()
    insumo.stock_actual -= cantidad_entregada
    if insumo.cantidad_salidas is None:
        insumo.cantidad_salidas = 0
    insumo.cantidad_salidas += cantidad_entregada
    insumo.porcentaje_utilizado = (insumo.cantidad_salidas / (insumo.existencias_iniciales_anio + insumo.cantidad_entradas)) * 100
    db.session.commit()
    return redirect(url_for('ver_solicitudes'))

@app.route('/salida_insumos')
@admin_required
def salida_insumos():
    filtro = request.args.get('filtro', '')
    query = sa.select(SalidaInsumo).join(User).join(Insumo).order_by(SalidaInsumo.fecha_salida.desc())
    if filtro:
        query = query.where(
            sa.or_(
                User.dependencia.ilike(f'%{filtro}%'),
                User.nombre.ilike(f'%{filtro}%'),
                SalidaInsumo.fecha_salida.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        )
    salidas = db.session.scalars(query).all()
    return render_template('salida_insumos.html', salidas=salidas, filtro=filtro)

@app.route('/entrada_insumos')
@admin_required
def entrada_insumos():
    filtro = request.args.get('filtro', '')
    query = sa.select(EntradaInsumo).order_by(EntradaInsumo.fecha_entrada.desc())
    if filtro:
        query = query.where(
            sa.or_(
                EntradaInsumo.proveedor.ilike(f'%{filtro}%'),
                EntradaInsumo.cantidad.ilike(f'%{filtro}%'),
                EntradaInsumo.fecha_entrada.ilike(f'%{filtro}%'),
                Insumo.codigo_producto.ilike(f'%{filtro}%'),
                Insumo.descripcion.ilike(f'%{filtro}%')
            )
        ).join(Insumo)

    entradas = db.session.scalars(query).all()
    return render_template('entrada_insumos.html', entradas=entradas, filtro=filtro)


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

#Nuevo sistema de solicitar insumos.

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
                    usuario_id=current_user.id_usuario,
                    cantidad_solicitada=cantidad_solicitada,
                    estado="pendiente",
                    insumo_id=insumo.id     
                )
                db.session.add(nueva_solicitud)
        db.session.commit()
        session.pop('lista_solicitudes', None)
        session.pop('cantidades_solicitadas', None)
        flash('Solicitudes de insumos creadas con éxito.', 'success')
        return redirect(url_for('index'))
    return render_template('confirmar_solicitud_insumos.html', insumos=insumos, cantidades=cantidades)


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
