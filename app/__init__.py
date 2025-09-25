from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.config import Config


app = Flask(__name__)
app.config.from_object(Config)
print("Base de datos en uso:", app.config['SQLALCHEMY_DATABASE_URI'])
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login=LoginManager(app)
login.login_view='login'

from app import models, routes, admin