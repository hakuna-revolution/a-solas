# settings.py

from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Cargar las variables de entorno desde el archivo .env
load_dotenv()


# URL a la que Django redirigirá a los usuarios no autenticados
LOGIN_URL = '/login/'  # Puede ser una ruta absoluta

# URL a la que Django redirigirá después de iniciar sesión exitosamente
LOGIN_REDIRECT_URL = 'turnos:calendario'  # Usa el nombre de la URL definida en tu app

# URL a la que Django redirigirá después de cerrar sesión
LOGOUT_REDIRECT_URL = 'turnos:calendario'  # Puedes cambiarlo según tu preferencia


# Función para obtener variables de entorno y manejar su ausencia
def get_env_variable(var_name):
    """Obtiene el valor de una variable de entorno o lanza una excepción."""
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = f"La variable de entorno {var_name} no está definida."
        raise ImproperlyConfigured(error_msg)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Directorio donde Django recopilará todos los archivos estáticos (usado en producción)
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# Seguridad
SECRET_KEY = get_env_variable('SECRET_KEY')
DEBUG = os.getenv('DEBUG') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS').split(',')

# Application definition
INSTALLED_APPS = [
    'turnos',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'organizador_turnos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Asegúrate de que esta línea esté correcta
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'organizador_turnos.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de correo electrónico
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Usando Gmail
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = get_env_variable('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = get_env_variable('EMAIL_HOST_PASSWORD')

# Dirección de correo predeterminada
DEFAULT_FROM_EMAIL = get_env_variable('DEFAULT_FROM_EMAIL')

#LOGS - registro de errores
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/asolas/django/debug.log',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'my_logger': {  # Logger personalizado
             'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
         'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}




