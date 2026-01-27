"""
Admin configuration for boards app.
"""

from django.contrib import admin

from .models import Board


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    """Admin for Board model."""

    list_display = ["name", "project", "board_type", "created_at"]
    list_filter = ["board_type", "created_at"]
    search_fields = ["name", "project__key", "project__name"]
    autocomplete_fields = ["project"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "project", "name", "board_type")}),
        ("Конфигурация", {"fields": ("columns", "filters", "settings")}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
