"""
Celery configuration for CTrack project.

This module configures Celery with Redis as the message broker.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ctrack.settings.development")

app = Celery("ctrack")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
