"""
CTrack Django project.

This module ensures the Celery app is loaded when Django starts.
"""

from ctrack.celery import app as celery_app

__all__ = ("celery_app",)
