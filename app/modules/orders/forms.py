from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class EntregarSolicitudForm(FlaskForm):
    cantidad_entregada = IntegerField('Cantidad Entregada', validators=[DataRequired(), NumberRange(min=1)])
    observaciones = StringField('Observaciones')
    submit = SubmitField('Entregar Solicitud')
