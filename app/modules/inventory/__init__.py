from flask import Blueprint

#Definimos el blueprint "Inventory".

inventory_bp = Blueprint('inventory', __name__, template_folder='templates')

from . import routes
