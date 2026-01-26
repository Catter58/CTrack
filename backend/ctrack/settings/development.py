"""
Настройки Django для разработки.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Django Debug Toolbar
INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

INTERNAL_IPS = [
    "127.0.0.1",
]

# Email backend для разработки
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Для разработки можно использовать SQLite
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

# Логирование
LOGGING["loggers"]["django"]["level"] = "DEBUG"  # noqa: F405
