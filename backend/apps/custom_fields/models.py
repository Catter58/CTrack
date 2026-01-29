import uuid

from django.db import models


class FieldType(models.TextChoices):
    TEXT = "text", "Текст"
    TEXTAREA = "textarea", "Многострочный текст"
    NUMBER = "number", "Число"
    DATE = "date", "Дата"
    DATETIME = "datetime", "Дата и время"
    CHECKBOX = "checkbox", "Флажок"
    SELECT = "select", "Выбор"
    MULTISELECT = "multiselect", "Множественный выбор"
    USER = "user", "Пользователь"


class CustomFieldDefinition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="custom_field_definitions",
        verbose_name="Проект",
        null=True,
        blank=True,
        help_text="Пусто = глобальное поле",
    )
    name = models.CharField("Название", max_length=100)
    field_key = models.CharField(
        "Ключ поля",
        max_length=50,
        help_text="Ключ для JSONB (например, cf_priority)",
    )
    field_type = models.CharField(
        "Тип поля",
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.TEXT,
    )
    options = models.JSONField(
        "Варианты выбора",
        default=list,
        blank=True,
        help_text="Для типов select/multiselect",
    )
    is_required = models.BooleanField("Обязательное", default=False)
    default_value = models.JSONField(
        "Значение по умолчанию",
        null=True,
        blank=True,
    )
    description = models.TextField("Описание", blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    applicable_types = models.JSONField(
        "Применимые типы задач",
        default=list,
        blank=True,
        help_text="UUID типов задач, к которым применяется поле",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Определение кастомного поля"
        verbose_name_plural = "Определения кастомных полей"
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "field_key"],
                name="unique_field_key_per_project",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "field_key"]),
        ]

    def __str__(self):
        prefix = f"[{self.project.key}] " if self.project else "[Global] "
        return f"{prefix}{self.name}"
