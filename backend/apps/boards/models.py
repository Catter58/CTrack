"""
Board models for CTrack.
"""

import uuid

from django.db import models


class BoardType(models.TextChoices):
    """Board type choices."""

    KANBAN = "kanban", "Kanban"
    SCRUM = "scrum", "Scrum"


class Board(models.Model):
    """Board model for Kanban/Scrum views."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="boards",
        verbose_name="Проект",
    )
    name = models.CharField("Название", max_length=200)
    board_type = models.CharField(
        "Тип",
        max_length=20,
        choices=BoardType.choices,
        default=BoardType.KANBAN,
    )
    columns = models.JSONField(
        "Колонки",
        default=list,
        blank=True,
        help_text="Упорядоченный список UUID статусов",
    )
    filters = models.JSONField(
        "Фильтры",
        default=dict,
        blank=True,
        help_text="Фильтры по типам задач, исполнителям и т.д.",
    )
    settings = models.JSONField(
        "Настройки",
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Доска"
        verbose_name_plural = "Доски"
        ordering = ["name"]

    def __str__(self):
        return f"{self.project.key}: {self.name}"

    @classmethod
    def create_default_board(cls, project) -> "Board":
        """Create default Kanban board for project."""
        from apps.issues.models import Status

        # Get all global statuses
        statuses = Status.objects.filter(project__isnull=True).order_by("order")
        columns = [str(s.id) for s in statuses]

        return cls.objects.create(
            project=project,
            name="Kanban",
            board_type=BoardType.KANBAN,
            columns=columns,
        )
