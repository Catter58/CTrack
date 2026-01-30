"""
Базовые настройки Django для CTrack.

Общие настройки для всех окружений.
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Инициализация django-environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Читаем .env файл если он существует
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])


# Application definition

INSTALLED_APPS = [
    # Django Daphne (ASGI server) - должен быть первым
    "daphne",
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third-party
    "corsheaders",
    "django_filters",
    "simple_history",
    "channels",
    "django_celery_results",
    "django_celery_beat",
    # Local apps
    "apps.core",
    "apps.users",
    "apps.projects",
    "apps.issues",
    "apps.boards",
    "apps.sprints",
    "apps.custom_fields",
]

MIDDLEWARE = [
    "apps.core.middleware.MetricsMiddleware",
    "apps.core.middleware.CacheMetricsMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.core.middleware.ETagMiddleware",
]

ROOT_URLCONF = "ctrack.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "ctrack.wsgi.application"
ASGI_APPLICATION = "ctrack.asgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://ctrack:ctrack_password@localhost:5432/ctrack",
    )
}


# Redis URL (shared by Cache, Channels, and SSE)
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")


# Cache
# https://docs.djangoproject.com/en/6.0/topics/cache/

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}


# Channels (WebSockets)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}


# Celery Configuration

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Moscow"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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


# Custom User Model
AUTH_USER_MODEL = "users.User"


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS Settings
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
CORS_ALLOW_CREDENTIALS = True


# JWT Settings
JWT_SECRET_KEY = env("JWT_SECRET_KEY", default=SECRET_KEY)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = env.int("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=15)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = env.int("JWT_REFRESH_TOKEN_EXPIRE_DAYS", default=7)
JWT_ALGORITHM = "HS256"


# Frontend URL for notifications
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# Email Settings
# Use custom backend that reads SMTP settings from database
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="apps.core.email_backend.DatabaseEmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="CTrack <noreply@ctrack.local>")


# Logging Configuration
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_FORMAT = env("LOG_FORMAT", default="json")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
                "pathname": "file",
                "lineno": "line",
            },
            "static_fields": {
                "service": "ctrack-backend",
            },
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name} | {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "console_verbose": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Django core loggers
        "django": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("DJANGO_REQUEST_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("DJANGO_DB_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("DJANGO_SECURITY_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        # Application loggers
        "apps": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("APPS_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps.core.middleware": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("REQUEST_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps.users": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("USERS_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps.projects": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("PROJECTS_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps.issues": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("ISSUES_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        # Third-party loggers
        "celery": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("CELERY_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "channels": {
            "handlers": ["console_json" if LOG_FORMAT == "json" else "console_verbose"],
            "level": env("CHANNELS_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}


# Cookie Security Settings
# HttpOnly is enabled by default in Django for session cookies
# SameSite prevents CSRF attacks by restricting cookie sending
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Secure cookies are configured in production.py (requires HTTPS)
# SESSION_COOKIE_SECURE = True  (set in production)
# CSRF_COOKIE_SECURE = True     (set in production)
