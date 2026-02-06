from flask import Blueprint

# Definición del Blueprint para el módulo de órdenes.
orders_bp = Blueprint('orders', __name__, template_folder='templates')

from . import routes