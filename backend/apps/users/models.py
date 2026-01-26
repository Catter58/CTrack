from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


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
