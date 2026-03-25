from flask import Blueprint

#Definimos el Blueprint 'auth'.

auth_bp = Blueprint('auth', __name__, template_folder='templates')

#Importamos las rutas al final para evitar dependencias circulares.
from . import routes

