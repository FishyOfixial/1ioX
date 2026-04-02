import os
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_list(name, default=None):
    if default is None:
        default = []
    raw_value = os.environ.get(name)
    if raw_value is None:
        return list(default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _require_env(name):
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be configured.")
    return value


def _is_insecure_secret_key(secret_key):
    normalized = (secret_key or "").strip()
    if not normalized:
        return True
    if normalized == "clave-falsa-en-desarrollo":
        return True
    if normalized.startswith("django-insecure-"):
        return True
    return len(normalized) < 50 or len(set(normalized)) < 5


def _normalize_public_base_url(url):
    normalized = (url or "").strip().rstrip("/")
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ImproperlyConfigured("PUBLIC_BASE_URL must be a valid absolute URL.")
    return normalized


ENV = (os.environ.get("ENV") or "development").strip().lower()
IS_PRODUCTION = ENV == "production"
DEBUG = not IS_PRODUCTION

SECRET_KEY = os.environ.get("SECRET_KEY", "clave-falsa-en-desarrollo")
if IS_PRODUCTION and _is_insecure_secret_key(SECRET_KEY):
    raise ImproperlyConfigured("SECRET_KEY must be configured with a strong random value in production.")

_default_dev_hosts = [
    "127.0.0.1",
    "localhost",
    "testserver",
    "web-production-3894a.up.railway.app",
    "panel.1iox.com",
]
ALLOWED_HOSTS = _get_env_list("ALLOWED_HOSTS", default=[] if IS_PRODUCTION else _default_dev_hosts)
if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured in production.")

PUBLIC_BASE_URL = _normalize_public_base_url(os.environ.get("PUBLIC_BASE_URL", ""))
if IS_PRODUCTION and not PUBLIC_BASE_URL:
    raise ImproperlyConfigured("PUBLIC_BASE_URL must be configured in production.")

CRON_TOKEN = (os.environ.get("CRON_TOKEN") or "").strip()
ONE_NCE_BASE_URL = (os.environ.get("ONE_NCE_BASE_URL", os.environ.get("API_URL", "")) or "").strip()
ONE_NCE_AUTH_URL = (os.environ.get("ONE_NCE_AUTH_URL", os.environ.get("AUTH_URL", "")) or "").strip()
ONE_NCE_AUTH_HEADER = (os.environ.get("ONE_NCE_AUTH_HEADER", os.environ.get("API_AUTH_HEADER", "")) or "").strip()
ONE_NCE_TIMEOUT = int(os.environ.get("ONE_NCE_TIMEOUT", os.environ.get("API_TIMEOUT", "30")))
ONE_NCE_POOL_CONNECTIONS = int(os.environ.get("ONE_NCE_POOL_CONNECTIONS", "10"))
ONE_NCE_POOL_MAXSIZE = int(os.environ.get("ONE_NCE_POOL_MAXSIZE", "10"))
ONE_NCE_POOL_BLOCK = _get_env_bool("ONE_NCE_POOL_BLOCK", True)
REDIS_URL = (os.environ.get("REDIS_URL") or "").strip()

MERCADOPAGO_ACCESS_TOKEN = (os.environ.get("MERCADOPAGO_ACCESS_TOKEN") or "").strip()
MERCADOPAGO_BASE_URL = (os.environ.get("MERCADOPAGO_BASE_URL") or "https://api.mercadopago.com").strip()
MERCADOPAGO_TIMEOUT = int(os.environ.get("MERCADOPAGO_TIMEOUT", "30"))
MERCADOPAGO_WEBHOOK_URL = (os.environ.get("MERCADOPAGO_WEBHOOK_URL") or "").strip()
MERCADOPAGO_WEBHOOK_TOKEN = (os.environ.get("MERCADOPAGO_WEBHOOK_TOKEN") or "").strip()
MERCADOPAGO_SUBSCRIPTIONS_ENABLED = _get_env_bool("MERCADOPAGO_SUBSCRIPTIONS_ENABLED", True)
MERCADOPAGO_SUBSCRIPTION_REASON_PREFIX = (os.environ.get("MERCADOPAGO_SUBSCRIPTION_REASON_PREFIX") or "Auto renew").strip()

LOGIN_RATE_LIMIT_FAILURES = int(os.environ.get("LOGIN_RATE_LIMIT_FAILURES", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
LOGIN_RATE_LIMIT_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_LOCKOUT_SECONDS", "900"))

if IS_PRODUCTION:
    for required_name, required_value in (
        ("CRON_TOKEN", CRON_TOKEN),
        ("ONE_NCE_BASE_URL", ONE_NCE_BASE_URL),
        ("ONE_NCE_AUTH_HEADER", ONE_NCE_AUTH_HEADER),
        ("MERCADOPAGO_ACCESS_TOKEN", MERCADOPAGO_ACCESS_TOKEN),
        ("MERCADOPAGO_WEBHOOK_TOKEN", MERCADOPAGO_WEBHOOK_TOKEN),
    ):
        if not required_value:
            raise ImproperlyConfigured(f"{required_name} must be configured in production.")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "SIM_Control",
    "billing",
    "customer_portal",
    "auditlogs",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

ROOT_URLCONF = "TrakSolutions.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "TrakSolutions.wsgi.application"

if IS_PRODUCTION:
    DATABASES = {
        "default": dj_database_url.config(default=_require_env("DATABASE_URL"))
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if IS_PRODUCTION and REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
            "KEY_PREFIX": "traksolutions",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "traksolutions-local-cache",
            "TIMEOUT": 300,
        }
    }

CSRF_TRUSTED_ORIGINS = _get_env_list("CSRF_TRUSTED_ORIGINS")
if not CSRF_TRUSTED_ORIGINS and PUBLIC_BASE_URL:
    parsed_public_base_url = urlparse(PUBLIC_BASE_URL)
    CSRF_TRUSTED_ORIGINS = [f"{parsed_public_base_url.scheme}://{parsed_public_base_url.netloc}"]
elif not CSRF_TRUSTED_ORIGINS and not IS_PRODUCTION:
    CSRF_TRUSTED_ORIGINS = [
        "https://web-production-3894a.up.railway.app",
        "https://panel.1iox.com",
    ]

if IS_PRODUCTION:
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _get_env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = _get_env_bool("SECURE_HSTS_PRELOAD", True)
    SECURE_SSL_REDIRECT = _get_env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

IS_DEVELOPMENT = DEBUG

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
AUTH_USER_MODEL = "SIM_Control.User"

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
