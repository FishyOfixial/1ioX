from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.environ.get("SECRET_KEY", "clave-falsa-en-desarrollo")
CRON_TOKEN = os.environ.get("CRON_TOKEN")
ONE_NCE_BASE_URL = os.environ.get("ONE_NCE_BASE_URL", os.environ.get("API_URL", ""))
ONE_NCE_AUTH_URL = os.environ.get("ONE_NCE_AUTH_URL", os.environ.get("AUTH_URL", ""))
ONE_NCE_AUTH_HEADER = os.environ.get("ONE_NCE_AUTH_HEADER", os.environ.get("API_AUTH_HEADER", ""))
ONE_NCE_TIMEOUT = int(os.environ.get("ONE_NCE_TIMEOUT", os.environ.get("API_TIMEOUT", "30")))

MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "")
MERCADOPAGO_BASE_URL = os.environ.get("MERCADOPAGO_BASE_URL", "https://api.mercadopago.com")
MERCADOPAGO_TIMEOUT = int(os.environ.get("MERCADOPAGO_TIMEOUT", "30"))
MERCADOPAGO_WEBHOOK_URL = os.environ.get("MERCADOPAGO_WEBHOOK_URL", "")
MERCADOPAGO_WEBHOOK_TOKEN = os.environ.get("MERCADOPAGO_WEBHOOK_TOKEN", "")
MERCADOPAGO_SUBSCRIPTIONS_ENABLED = os.environ.get("MERCADOPAGO_SUBSCRIPTIONS_ENABLED", "1") == "1"
MERCADOPAGO_SUBSCRIPTION_REASON_PREFIX = os.environ.get("MERCADOPAGO_SUBSCRIPTION_REASON_PREFIX", "Auto renew")

ALLOWED_HOSTS = [
    '*',
    'web-production-3894a.up.railway.app',
    'panel.1iox.com',
    ]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'SIM_Control',
    'billing',
    'customer_portal',
    'auditlogs',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = 'TrakSolutions.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'TrakSolutions.wsgi.application'


import dj_database_url
ENV = os.environ.get('ENV', 'development')

if ENV == 'production':
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL')
        )
    }
    DEBUG = False
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    DEBUG = True

IS_DEVELOPMENT = DEBUG



CSRF_TRUSTED_ORIGINS = [
    "https://web-production-3894a.up.railway.app",
    'https://panel.1iox.com',
]

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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'

LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/login/'

AUTH_USER_MODEL = 'SIM_Control.User'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO" if not DEBUG else "DEBUG",
    },
}

