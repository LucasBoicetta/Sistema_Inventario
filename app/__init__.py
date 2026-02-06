from flask import Flask, flash, make_response, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager, get_current_user, verify_jwt_in_request, unset_jwt_cookies
from config import Config
import os
import logging
from logging.handlers import RotatingFileHandler

#1. Inicialización de la app.
app = Flask(__name__)
app.config.from_object(Config)

#2. Configuracion de Logging (Sistema de Auditoría).
#Solo activamos logs en archivo si no estamos en modo debug (o puedes quitar el if para tenerlos siempre)
if not app.debug or True: #True fuerza la creación de logs incluso en desarrollo para probar.
    if not os.path.exists('logs'):
        os.mkdir('logs')

    #Rotación: Crea archivos de 1MB máx, guarda los últimos 10 archivos antiguos.
    file_handler = RotatingFileHandler('logs/sistema_sgq.log', maxBytes=1024 * 1024, backupCount=10)

    #Formato profesional: FECHA - NIVEL - [ARCHIVO:LINEA] - MENSAJE
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))

    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Sistema de Inventario SGQ startup')
    app.logger.info(f'Conectado a BD: {app.config.get('SQLALCHEMY_DATABASE_URI')}')

#3. Inicialización de extensiones.
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login=LoginManager(app)
login.login_view='auth.login'
jwt = JWTManager(app)

#4. Registro de Blueprints.
from app.modules.auth import auth_bp
app.register_blueprint(auth_bp)

from app.modules.inventory import inventory_bp
app.register_blueprint(inventory_bp)

from app.modules.orders import orders_bp
app.register_blueprint(orders_bp)

from app.modules.main import main_bp
app.register_blueprint(main_bp)


#5. Context Processors (Inyección global de variables en templates).
@app.context_processor
def inject_user():
    """Permite usar {{ current_user }} en los templates Jinja2."""
    try:
        #Intenta verificar el token silenciosamente.
        verify_jwt_in_request(optional=True)
        user = get_current_user()
    except Exception:
        user = None
        # Si no hay usuario, retornamos None (o un objeto anónimo si prefieres)
    return dict(current_user=user)

#6. Imports de Modelos y admin.
from app import admin
from app.shared import models   

#7. Callbacks de JWT.
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return db.session.get(models.User, int(identity))

#Cuando el token expiró, redirige al login con mensaje.
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    flash('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.', 'warning')
    #Importante: Redirigir al login y limpiar la cookie vieja.
    response = make_response(redirect(url_for('auth.login')))
    unset_jwt_cookies(response)
    return response

#Cuando el token es inválido, redirige al login con mensaje.
@jwt.invalid_token_loader
def invalid_token_callback(error):
    flash('Token inválido. Por favor, inicia sesión nuevamente.', 'warning')
    response = make_response(redirect(url_for('auth.login')))
    unset_jwt_cookies(response)
    return response

#Cuando no hay token, redirige al login con mensaje.
@jwt.unauthorized_loader
def missing_token_callback(error):
    flash('No has iniciado sesión. Por favor, inicia sesión para continuar.', 'info')
    return redirect(url_for('auth.login'))