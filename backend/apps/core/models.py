"""
Core models for CTrack system.
"""

from django.db import models


class SystemSettings(models.Model):
    """Singleton model for system-wide settings."""

    organization_name = models.CharField(
        "Название организации",
        max_length=255,
        default="CTrack",
    )
    default_language = models.CharField(
        "Язык по умолчанию",
        max_length=10,
        default="ru",
    )
    allow_registration = models.BooleanField(
        "Разрешить регистрацию",
        default=True,
    )
    smtp_settings = models.JSONField(
        "Настройки SMTP",
        default=dict,
        blank=True,
    )
    storage_settings = models.JSONField(
        "Настройки хранилища",
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Системные настройки"
        verbose_name_plural = "Системные настройки"

    def __str__(self):
        return f"Системные настройки ({self.organization_name})"

    def save(self, *args, **kwargs):
        """Enforce singleton pattern."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of singleton."""
        pass

    @classmethod
    def get_settings(cls) -> "SystemSettings":
        """Get or create the singleton settings instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
