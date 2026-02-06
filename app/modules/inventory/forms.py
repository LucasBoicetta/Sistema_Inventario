from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField,SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class CargarInsumoForm(FlaskForm):
    codigo_producto = StringField('Código de Producto', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[Optional()])
    cantidad_entradas = IntegerField('Cantidad de Entradas', validators=[DataRequired(), NumberRange(min=1)])
    proveedor = StringField('Proveedor', validators=[DataRequired()])
    submit = SubmitField('Cargar')