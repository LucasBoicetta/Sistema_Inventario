from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from app import app, db
from app.models import User, Insumo, SolicitudInsumo, SalidaInsumo, EntradaInsumo, SolicitudDetalle, Proveedor, Rol, Dependencia

class AdminOnlyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user.rol, 'nombre_rol', None) == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        flash('Acceso restringido solo para administradores.', 'danger')
        return redirect(url_for('login'))

class UserAdmin(AdminOnlyModelView):
    column_list = ['id_usuario', 'cedula', 'nombre', 'id_dependencia', 'id_rol']
    form_columns = ['cedula', 'nombre', 'id_dependencia', 'id_rol', 'password']
    column_searchable_list = ['nombre', 'cedula']
    column_filters = ['id_rol', 'id_dependencia']
    column_exclude_list = ['password']

    def on_model_change(self, form, model, is_created):
        if form.password.data and (is_created or form.password.data != model.password):
            model.set_password(form.password.data)

    def edit_form(self, obj=None):
        form = super(UserAdmin, self).edit_form(obj)
        form.password.data = ''
        return form

class InsumoAdmin(AdminOnlyModelView):
    column_list = ['id', 'codigo_insumo', 'descripcion', 'existencias_iniciales_anio', 'stock_actual', 'porcentaje_utilizado', 'cantidad_entradas', 'cantidad_salidas']
    form_columns = ['codigo_insumo', 'descripcion', 'existencias_iniciales_anio', 'stock_actual', 'porcentaje_utilizado', 'cantidad_entradas', 'cantidad_salidas']
    column_searchable_list = ['codigo_insumo', 'descripcion']
    column_filters = ['descripcion']

class SolicitudInsumoAdmin(AdminOnlyModelView):
    column_list = ['id_solicitud', 'fecha_solicitud', 'estado', 'id_usuario']
    form_columns = ['fecha_solicitud', 'estado', 'id_usuario']
    column_filters = ['estado', 'id_usuario']
    column_searchable_list = ['id_usuario']

class SolicitudDetalleAdmin(AdminOnlyModelView):
    column_list = ['id_solicitudes_insumos', 'cantidad_solicitada', 'id_solicitud', 'id_insumo']
    form_columns = ['cantidad_solicitada', 'id_solicitud', 'id_insumo']
    column_searchable_list = ['id_solicitud', 'id_insumo']
    column_filters = ['id_solicitud', 'id_insumo']

class SalidaInsumoAdmin(AdminOnlyModelView):
    column_list = ['id_salida', 'cantidad_entregada', 'fecha_salida', 'id_usuario', 'id_insumo', 'id_solicitudes_insumos', 'observaciones']
    form_columns = ['cantidad_entregada', 'fecha_salida', 'id_usuario', 'id_insumo', 'id_solicitudes_insumos', 'observaciones']
    column_filters = ['fecha_salida', 'id_usuario', 'id_insumo', 'id_solicitudes_insumos']
    column_searchable_list = ['id_usuario', 'id_insumo']

class EntradaInsumoAdmin(AdminOnlyModelView):
    column_list = ['id_entrada', 'fecha_entrada', 'id_proveedor', 'cantidad', 'id_insumo']
    form_columns = ['fecha_entrada', 'id_proveedor', 'cantidad', 'id_insumo']
    column_searchable_list = ['id_proveedor']
    column_filters = ['fecha_entrada', 'id_proveedor', 'id_insumo']

class ProveedorAdmin(AdminOnlyModelView):
    column_list = ['id_proveedor', 'nombre']
    form_columns = ['nombre']
    column_searchable_list = ['nombre']
    column_filters = ['nombre']

class RolAdmin(AdminOnlyModelView):
    column_list = ['id_rol', 'nombre_rol']
    form_columns = ['nombre_rol']
    column_searchable_list = ['nombre_rol']
    column_filters = ['nombre_rol']

class DependenciaAdmin(AdminOnlyModelView):
    column_list = ['id_dependencia', 'nombre_dependencia']
    form_columns = ['nombre_dependencia']
    column_searchable_list = ['nombre_dependencia']
    column_filters = ['nombre_dependencia']

admin = Admin(app, name='Panel de Administración', template_mode='bootstrap4')
admin.add_view(UserAdmin(User, db.session))
admin.add_view(InsumoAdmin(Insumo, db.session))
admin.add_view(SolicitudInsumoAdmin(SolicitudInsumo, db.session))
admin.add_view(SolicitudDetalleAdmin(SolicitudDetalle, db.session))
admin.add_view(SalidaInsumoAdmin(SalidaInsumo, db.session))
admin.add_view(EntradaInsumoAdmin(EntradaInsumo, db.session))
admin.add_view(ProveedorAdmin(Proveedor, db.session))
admin.add_view(RolAdmin(Rol, db.session))
admin.add_view(DependenciaAdmin(Dependencia, db.session))