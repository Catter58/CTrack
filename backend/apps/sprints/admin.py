from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Sprint


@admin.register(Sprint)
class SprintAdmin(SimpleHistoryAdmin):
    list_display = [
        "name",
        "project",
        "status",
        "start_date",
        "end_date",
        "initial_story_points",
    ]
    list_filter = ["status", "project", "start_date"]
    search_fields = ["name", "goal", "project__key", "project__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = ["project"]
    date_hierarchy = "start_date"

    fieldsets = (
        (None, {"fields": ("id", "project", "name", "goal")}),
        ("Даты", {"fields": ("start_date", "end_date")}),
        ("Статус", {"fields": ("status",)}),
        (
            "Story Points",
            {"fields": ("initial_story_points", "completed_story_points")},
        ),
        ("Служебные", {"fields": ("created_at", "updated_at")}),
    )
