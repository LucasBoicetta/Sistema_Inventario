from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from app import app, db
from app.models import User, Insumo, SolicitudInsumo, SalidaInsumo, EntradaInsumo

class AdminOnlyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'rol', None) == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        flash('Acceso restringido solo para administradores.', 'danger')
        return redirect(url_for('login'))


class UserAdmin(AdminOnlyModelView):
    column_list = ['id_usuario', 'cedula', 'nombre', 'dependencia', 'rol']
    form_columns = ['cedula', 'nombre', 'dependencia', 'rol', 'password']
    column_searchable_list = ['nombre', 'cedula', 'dependencia', 'rol']
    column_filters = ['rol', 'dependencia']
    column_exclude_list = ['password']

    def on_model_change(self, form, model, is_created):
        # Solo hashea si la contraseña fue cambiada o es nuevo usuario
        if form.password.data and (is_created or form.password.data != model.password):
            model.set_password(form.password.data)

    def edit_form(self, obj=None):
        form = super(UserAdmin, self).edit_form(obj)
        form.password.data = ''
        return form


class InsumoAdmin(AdminOnlyModelView):
    column_list = ['id', 'codigo_producto', 'descripcion', 'existencias_iniciales_anio', 'stock_actual', 'porcentaje_utilizado']
    form_columns = ['codigo_producto', 'descripcion', 'existencias_iniciales_anio', 'stock_actual']
    column_searchable_list = ['codigo_producto', 'descripcion']
    column_filters = ['descripcion']

class SolicitudInsumoAdmin(AdminOnlyModelView):
    column_list = ['id_solicitud', 'fecha_solicitud', 'cantidad_solicitada', 'estado', 'usuario_id', 'insumo_id', 'observaciones']
    form_columns = ['fecha_solicitud', 'cantidad_solicitada', 'estado', 'usuario_id', 'insumo_id', 'observaciones']
    column_filters = ['estado']
    column_searchable_list = ['estado', 'observaciones']

class SalidaInsumoAdmin(AdminOnlyModelView):
    column_list = ['id_salida', 'cantidad_solicitada', 'cantidad_entregada', 'fecha_salida', 'usuario_id', 'insumo_id']
    form_columns = ['cantidad_solicitada', 'cantidad_entregada', 'fecha_salida', 'usuario_id', 'insumo_id']
    column_filters = ['fecha_salida']
    column_searchable_list = ['usuario_id']

class EntradaInsumoAdmin(AdminOnlyModelView):
    column_list = ['id_entrada', 'fecha_entrada', 'proveedor', 'cantidad', 'insumo_id']
    form_columns = ['fecha_entrada', 'proveedor', 'cantidad', 'insumo_id']
    column_searchable_list = ['proveedor']
    column_filters = ['fecha_entrada']

admin = Admin(app, name='Panel de Administración', template_mode='bootstrap4')
admin.add_view(UserAdmin(User, db.session))
admin.add_view(InsumoAdmin(Insumo, db.session))
admin.add_view(SolicitudInsumoAdmin(SolicitudInsumo, db.session))
admin.add_view(SalidaInsumoAdmin(SalidaInsumo, db.session))
admin.add_view(EntradaInsumoAdmin(EntradaInsumo, db.session))