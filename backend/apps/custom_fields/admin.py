from django.contrib import admin

from .models import CustomFieldDefinition


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "project",
        "field_key",
        "field_type",
        "is_required",
        "order",
    ]
    list_filter = ["field_type", "is_required", "project"]
    search_fields = ["name", "field_key", "description"]
    ordering = ["order", "name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = ["project"]

    fieldsets = (
        (None, {"fields": ("id", "project", "name", "field_key")}),
        ("Настройки типа", {"fields": ("field_type", "options", "default_value")}),
        ("Применимость", {"fields": ("is_required", "applicable_types")}),
        ("Прочее", {"fields": ("description", "order")}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
