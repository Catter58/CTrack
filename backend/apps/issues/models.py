"""
Issue models for CTrack.
"""

import uuid

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class StatusCategory(models.TextChoices):
    """Status categories for workflow."""

    TODO = "todo", "К выполнению"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Готово"


class Priority(models.TextChoices):
    """Issue priority levels."""

    LOWEST = "lowest", "Очень низкий"
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"
    HIGHEST = "highest", "Критический"


class IssueType(models.Model):
    """Issue type model (Epic, Story, Task, Bug, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="issue_types",
        verbose_name="Проект",
        null=True,
        blank=True,
        help_text="Пусто = глобальный тип",
    )
    name = models.CharField("Название", max_length=100)
    icon = models.CharField("Иконка", max_length=50, blank=True)
    color = models.CharField("Цвет", max_length=20, blank=True, default="#1192e8")
    is_subtask = models.BooleanField("Подзадача", default=False)
    is_epic = models.BooleanField(
        "Эпик",
        default=False,
        help_text="Эпики группируют связанные задачи",
    )
    parent_types = models.JSONField(
        "Допустимые родительские типы",
        default=list,
        blank=True,
        help_text="UUID типов, которые могут быть родителями",
    )
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Тип задачи"
        verbose_name_plural = "Типы задач"
        ordering = ["order", "name"]

    def __str__(self):
        prefix = f"[{self.project.key}] " if self.project else "[Global] "
        return f"{prefix}{self.name}"


class Status(models.Model):
    """Issue status model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="statuses",
        verbose_name="Проект",
        null=True,
        blank=True,
        help_text="Пусто = глобальный статус",
    )
    name = models.CharField("Название", max_length=100)
    category = models.CharField(
        "Категория",
        max_length=20,
        choices=StatusCategory.choices,
        default=StatusCategory.TODO,
    )
    color = models.CharField("Цвет", max_length=20, blank=True, default="#8a3ffc")
    order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Статус"
        verbose_name_plural = "Статусы"
        ordering = ["order", "name"]

    def __str__(self):
        prefix = f"[{self.project.key}] " if self.project else "[Global] "
        return f"{prefix}{self.name}"


class WorkflowTransition(models.Model):
    """Allowed status transitions for a project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="workflow_transitions",
        verbose_name="Проект",
    )
    from_status = models.ForeignKey(
        Status,
        on_delete=models.CASCADE,
        related_name="transitions_from",
        verbose_name="Из статуса",
    )
    to_status = models.ForeignKey(
        Status,
        on_delete=models.CASCADE,
        related_name="transitions_to",
        verbose_name="В статус",
    )
    name = models.CharField("Название перехода", max_length=100, blank=True)
    allowed_roles = models.JSONField(
        "Разрешённые роли",
        default=list,
        blank=True,
        help_text="Пусто = все роли",
    )

    class Meta:
        verbose_name = "Переход workflow"
        verbose_name_plural = "Переходы workflow"
        unique_together = ["project", "from_status", "to_status"]

    def __str__(self):
        return f"{self.project.key}: {self.from_status.name} → {self.to_status.name}"


class Issue(models.Model):
    """Issue model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="issues",
        verbose_name="Проект",
    )
    key = models.CharField(
        "Ключ задачи",
        max_length=20,
        unique=True,
        help_text="Формат: PROJ-123",
    )
    issue_number = models.PositiveIntegerField("Номер задачи")
    issue_type = models.ForeignKey(
        IssueType,
        on_delete=models.PROTECT,
        related_name="issues",
        verbose_name="Тип",
    )
    title = models.CharField("Заголовок", max_length=500)
    description = models.TextField("Описание", blank=True)
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name="issues",
        verbose_name="Статус",
    )
    priority = models.CharField(
        "Приоритет",
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_issues",
        verbose_name="Исполнитель",
        null=True,
        blank=True,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reported_issues",
        verbose_name="Автор",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="subtasks",
        verbose_name="Родительская задача",
        null=True,
        blank=True,
    )
    epic = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="epic_issues",
        verbose_name="Эпик",
        null=True,
        blank=True,
        limit_choices_to={"issue_type__is_epic": True},
        help_text="Эпик, к которому относится задача",
    )
    sprint = models.ForeignKey(
        "sprints.Sprint",
        on_delete=models.SET_NULL,
        related_name="issues",
        verbose_name="Спринт",
        null=True,
        blank=True,
    )
    story_points = models.PositiveSmallIntegerField(
        "Story Points",
        null=True,
        blank=True,
    )
    due_date = models.DateField("Срок", null=True, blank=True)
    custom_fields = models.JSONField("Кастомные поля", default=dict, blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    # История изменений
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "assignee"]),
            models.Index(fields=["project", "issue_type"]),
            models.Index(fields=["project", "issue_number"]),
        ]

    def __str__(self):
        return f"{self.key}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate key and number for new issues
        if not self.key:
            last_issue = (
                Issue.objects.filter(project=self.project)
                .order_by("-issue_number")
                .first()
            )
            self.issue_number = (last_issue.issue_number + 1) if last_issue else 1
            self.key = f"{self.project.key}-{self.issue_number}"

        super().save(*args, **kwargs)


class IssueComment(models.Model):
    """Issue comment model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Задача",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issue_comments",
        verbose_name="Автор",
    )
    content = models.TextField("Содержание")
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.issue.key} by {self.author}"


class ActivityAction(models.TextChoices):
    CREATED = "created", "Создана"
    UPDATED = "updated", "Обновлена"
    STATUS_CHANGED = "status_changed", "Изменён статус"
    ASSIGNED = "assigned", "Назначен исполнитель"
    COMMENTED = "commented", "Добавлен комментарий"
    SPRINT_CHANGED = "sprint_changed", "Изменён спринт"
    TYPE_CHANGED = "type_changed", "Изменён тип"
    PRIORITY_CHANGED = "priority_changed", "Изменён приоритет"


class IssueActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="Задача",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="issue_activities",
        verbose_name="Пользователь",
        null=True,
    )
    action = models.CharField(
        "Действие",
        max_length=20,
        choices=ActivityAction.choices,
    )
    field_name = models.CharField("Поле", max_length=100, blank=True)
    old_value = models.JSONField("Старое значение", null=True, blank=True)
    new_value = models.JSONField("Новое значение", null=True, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Активность задачи"
        verbose_name_plural = "Активность задач"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["issue", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.issue.key}: {self.get_action_display()}"


class IssueAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Задача",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_attachments",
        verbose_name="Загрузил",
        null=True,
    )
    file = models.FileField("Файл", upload_to="attachments/%Y/%m/")
    filename = models.CharField("Имя файла", max_length=255)
    file_size = models.PositiveIntegerField("Размер (байт)")
    content_type = models.CharField("MIME-тип", max_length=100)
    created_at = models.DateTimeField("Загружен", auto_now_add=True)

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.issue.key})"
