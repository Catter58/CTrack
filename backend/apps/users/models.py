import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class EmailFrequency(models.TextChoices):
    INSTANT = "instant", "Мгновенно"
    DAILY = "daily", "Ежедневный дайджест"
    WEEKLY = "weekly", "Еженедельный дайджест"


class User(AbstractUser):
    """Кастомная модель пользователя CTrack."""

    email = models.EmailField("Email", unique=True)
    avatar = models.ImageField(
        "Аватар",
        upload_to="avatars/",
        blank=True,
        null=True,
    )
    bio = models.TextField("О себе", blank=True)
    timezone = models.CharField(
        "Часовой пояс",
        max_length=50,
        default="Europe/Moscow",
    )

    # История изменений
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        verbose_name="Пользователь",
    )
    notify_on_assign = models.BooleanField("При назначении", default=True)
    notify_on_mention = models.BooleanField("При упоминании", default=True)
    notify_on_comment = models.BooleanField("При комментарии", default=True)
    notify_on_status_change = models.BooleanField("При смене статуса", default=False)
    email_frequency = models.CharField(
        "Частота уведомлений",
        max_length=10,
        choices=EmailFrequency.choices,
        default=EmailFrequency.INSTANT,
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Настройки уведомлений"
        verbose_name_plural = "Настройки уведомлений"

    def __str__(self):
        return f"Уведомления для {self.user}"
