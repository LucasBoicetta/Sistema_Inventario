from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SubmitField, StringField, PasswordField
from wtforms.validators import DataRequired, NumberRange

class CargarInsumoForm(FlaskForm):
    codigo_producto = StringField('Código de Producto', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[DataRequired()])
    cantidad_entradas = IntegerField('Cantidad de Entradas', validators=[DataRequired(), NumberRange(min=1)])
    proveedor = StringField('Proveedor', validators=[DataRequired()])
    submit = SubmitField('Cargar')


class EntregarSolicitudForm(FlaskForm):
    cantidad_entregada = IntegerField('Cantidad Entregada', validators=[DataRequired(), NumberRange(min=1)])
    observaciones = StringField('Observaciones')
    submit = SubmitField('Entregar Solicitud')


class LoginForm(FlaskForm):
    cedula = StringField('Cedula', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')