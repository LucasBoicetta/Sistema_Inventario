import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    #Obtiene la base de datos del entorno.
    DATABASE_URL = os.environ.get('DATABASE_URL')

    #Si no hay una base de datos usar sqlite por defecto.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuraciones adicionales para PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verifica conexiones antes de usarlas
        'pool_recycle': 300,     # Recicla conexiones cada 5 minutos
    }
