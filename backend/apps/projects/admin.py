"""
Admin configuration for projects app.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Project, ProjectMembership, SavedFilter


class ProjectMembershipInline(admin.TabularInline):
    """Inline for project memberships."""

    model = ProjectMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Project)
class ProjectAdmin(SimpleHistoryAdmin):
    """Admin for Project model."""

    list_display = ["key", "name", "owner", "is_archived", "created_at"]
    list_filter = ["is_archived", "created_at"]
    search_fields = ["key", "name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    autocomplete_fields = ["owner"]
    inlines = [ProjectMembershipInline]

    fieldsets = (
        (None, {"fields": ("id", "key", "name", "description")}),
        ("Владелец", {"fields": ("owner",)}),
        ("Статус", {"fields": ("is_archived",)}),
        ("Настройки", {"fields": ("settings",), "classes": ("collapse",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """Admin for ProjectMembership model."""

    list_display = ["user", "project", "role", "joined_at"]
    list_filter = ["role", "joined_at"]
    search_fields = ["user__username", "user__email", "project__key", "project__name"]
    autocomplete_fields = ["user", "project"]


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    """Admin for SavedFilter model."""

    list_display = [
        "name",
        "project",
        "user",
        "is_shared",
        "created_at",
    ]
    list_filter = ["is_shared", "project", "created_at"]
    search_fields = ["name", "project__key", "user__username"]
    autocomplete_fields = ["project", "user"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("id", "project", "user", "name")}),
        (
            "Настройки фильтра",
            {"fields": ("filters", "columns", "sort_by", "sort_order")},
        ),
        ("Доступ", {"fields": ("is_shared",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
