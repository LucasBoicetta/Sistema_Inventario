from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, IntegerField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, NumberRange, Optional



class CargarInsumoForm(FlaskForm):
    codigo_producto = StringField('Código de Producto', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[Optional()])
    cantidad_entradas = IntegerField('Cantidad de Entradas', validators=[DataRequired(), NumberRange(min=1)])
    proveedor = StringField('Proveedor', validators=[DataRequired()])
    submit = SubmitField('Cargar')


class InsumoLineForm(FlaskForm):
    """Subformulario para una línea de insumo en carga múltiple"""
    codigo_producto = StringField('Código de Producto', validators=[DataRequired()])
    descripcion = StringField('Descripción', validators=[Optional()])
    cantidad_entradas = IntegerField('Cantidad de Entradas', validators=[DataRequired(), NumberRange(min=1)])
    proveedor = StringField('Proveedor', validators=[DataRequired()])


class CargarInsumosMultipleForm(FlaskForm):
    """Formulario para carga múltiple dinámica"""
    insumos = FieldList(FormField(InsumoLineForm), min_entries=1, max_entries=20)
    submit = SubmitField('Cargar Todos')


class ImportarInsumoForm(FlaskForm):
    """Formulario para importación desde CSV/Excel"""
    archivo = FileField('Archivo CSV o Excel', validators=[
        FileRequired(message='Debe seleccionar un archivo para importar.'),
        FileAllowed(['csv', 'xlsx', 'xls'], 'Solo se permiten archivos CSV o Excel')
    ])
    submit = SubmitField('Importar')