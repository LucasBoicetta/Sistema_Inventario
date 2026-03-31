from flask import Blueprint

#Definimos el Blueprint 'audit'.
audit_bp = Blueprint('audit', __name__, template_folder='templates')

#Importamos las rutas al final para evitar dependencias circulares.
from . import routes