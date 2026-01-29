"""
Project models for CTrack.
"""

import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class ProjectRole(models.TextChoices):
    """Project membership roles."""

    ADMIN = "admin", "Администратор"
    MANAGER = "manager", "Менеджер"
    DEVELOPER = "developer", "Разработчик"
    VIEWER = "viewer", "Наблюдатель"


class Project(models.Model):
    """Project model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(
        "Ключ проекта",
        max_length=10,
        unique=True,
        help_text="Уникальный ключ проекта (например, PROJ)",
    )
    name = models.CharField("Название", max_length=200)
    description = models.TextField("Описание", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
        verbose_name="Владелец",
    )
    is_archived = models.BooleanField("Архивирован", default=False)
    settings = models.JSONField("Настройки", default=dict, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    # История изменений
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Проект"
        verbose_name_plural = "Проекты"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.key} - {self.name}"

    def save(self, *args, **kwargs):
        # Uppercase key
        self.key = self.key.upper()
        super().save(*args, **kwargs)


class ProjectMembership(models.Model):
    """Project membership model - links users to projects with roles."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Проект",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
        verbose_name="Пользователь",
    )
    role = models.CharField(
        "Роль",
        max_length=20,
        choices=ProjectRole.choices,
        default=ProjectRole.DEVELOPER,
    )
    joined_at = models.DateTimeField("Присоединился", auto_now_add=True)

    class Meta:
        verbose_name = "Участник проекта"
        verbose_name_plural = "Участники проекта"
        unique_together = ["project", "user"]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user} - {self.project.key} ({self.get_role_display()})"

    @property
    def is_admin(self) -> bool:
        """Check if user is project admin."""
        return self.role == ProjectRole.ADMIN

    @property
    def can_manage(self) -> bool:
        """Check if user can manage project (admin or manager)."""
        return self.role in [ProjectRole.ADMIN, ProjectRole.MANAGER]

    @property
    def can_edit(self) -> bool:
        """Check if user can edit issues (not viewer)."""
        return self.role != ProjectRole.VIEWER


class SortOrder(models.TextChoices):
    ASC = "asc", "По возрастанию"
    DESC = "desc", "По убыванию"


class SavedFilter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="saved_filters",
        verbose_name="Проект",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filters",
        verbose_name="Автор",
    )
    name = models.CharField("Название", max_length=100)
    filters = models.JSONField("Критерии фильтрации", default=dict)
    columns = models.JSONField("Видимые колонки", default=list)
    sort_by = models.CharField("Сортировка по", max_length=50, blank=True)
    sort_order = models.CharField(
        "Порядок сортировки",
        max_length=4,
        choices=SortOrder.choices,
        default=SortOrder.ASC,
    )
    is_shared = models.BooleanField("Доступен команде", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Сохранённый фильтр"
        verbose_name_plural = "Сохранённые фильтры"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.project.key})"
