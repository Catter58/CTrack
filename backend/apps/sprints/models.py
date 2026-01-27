import uuid

from django.db import models
from simple_history.models import HistoricalRecords


class SprintStatus(models.TextChoices):
    PLANNED = "planned", "Запланирован"
    ACTIVE = "active", "Активен"
    COMPLETED = "completed", "Завершён"


class Sprint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="sprints",
        verbose_name="Проект",
    )
    name = models.CharField("Название", max_length=100)
    goal = models.TextField("Цель спринта", blank=True)
    start_date = models.DateField("Дата начала")
    end_date = models.DateField("Дата окончания")
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=SprintStatus.choices,
        default=SprintStatus.PLANNED,
    )
    initial_story_points = models.PositiveIntegerField(
        "SP на старте",
        null=True,
        blank=True,
    )
    completed_story_points = models.PositiveIntegerField(
        "SP завершённых",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Спринт"
        verbose_name_plural = "Спринты"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "start_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="sprint_dates_valid",
                condition=models.Q(start_date__lt=models.F("end_date")),
            ),
        ]

    def __str__(self):
        return f"{self.project.key} - {self.name}"

    @property
    def remaining_story_points(self):
        if self.initial_story_points is None:
            return None
        completed = self.completed_story_points or 0
        return self.initial_story_points - completed
