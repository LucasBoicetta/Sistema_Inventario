import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))

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

    # === Configuración JWT ===
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key'
    JWT_TOKEN_LOCATION = ['cookies'] #Guardar en cookies no headers.
    JWT_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS.
    JWT_COOKIE_CSRF_PROTECT = False # Protección contra ataques CSRF.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30) # Expiración del token de acceso.
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)    # Expiración del token de refresco.
    JWT_CSRF_CHECK_FORM = True  # Verificar CSRF en formularios Ajax y Html.

    # === Session de flask ===
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30) #Duración de la sesión (coincide con JWT).
    SESSION_COOKIE_HTTPSONLY = True #Protege contra XSS (JavaScript no puede acceder a la cookie).
    SESSION_COOKIE_SAMESITE = 'Lax' #Protege contra CSRF (evita envío cross-site).
    SESSION_COOKIE_SECURE = False #Cambiar a True en producción con HTTPS.
    SESSION_COOKIE_NAME = 'session' #Nombre de la cookie de sesión (puedes personalizarlo).
    