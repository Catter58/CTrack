"""
Admin configuration for issues app.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Issue, IssueComment, IssueType, Status, WorkflowTransition


@admin.register(IssueType)
class IssueTypeAdmin(admin.ModelAdmin):
    """Admin for IssueType model."""

    list_display = ["name", "project", "icon", "color", "is_subtask", "order"]
    list_filter = ["is_subtask", "project"]
    search_fields = ["name"]
    ordering = ["order", "name"]


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    """Admin for Status model."""

    list_display = ["name", "project", "category", "color", "order"]
    list_filter = ["category", "project"]
    search_fields = ["name"]
    ordering = ["order", "name"]


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    """Admin for WorkflowTransition model."""

    list_display = ["project", "from_status", "to_status", "name"]
    list_filter = ["project"]
    search_fields = ["name", "project__key"]
    autocomplete_fields = ["project", "from_status", "to_status"]


class IssueCommentInline(admin.TabularInline):
    """Inline for issue comments."""

    model = IssueComment
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Issue)
class IssueAdmin(SimpleHistoryAdmin):
    """Admin for Issue model."""

    list_display = [
        "key",
        "title",
        "project",
        "issue_type",
        "status",
        "priority",
        "assignee",
        "created_at",
    ]
    list_filter = ["project", "status", "priority", "issue_type", "created_at"]
    search_fields = ["key", "title", "description"]
    readonly_fields = ["id", "key", "issue_number", "created_at", "updated_at"]
    autocomplete_fields = [
        "project",
        "issue_type",
        "status",
        "assignee",
        "reporter",
        "parent",
    ]
    inlines = [IssueCommentInline]

    fieldsets = (
        (None, {"fields": ("id", "key", "issue_number", "project")}),
        (
            "Основное",
            {"fields": ("title", "description", "issue_type", "status", "priority")},
        ),
        ("Участники", {"fields": ("assignee", "reporter")}),
        ("Связи", {"fields": ("parent",)}),
        ("Планирование", {"fields": ("story_points", "due_date")}),
        ("Дополнительно", {"fields": ("custom_fields",), "classes": ("collapse",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(IssueComment)
class IssueCommentAdmin(admin.ModelAdmin):
    """Admin for IssueComment model."""

    list_display = ["issue", "author", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["content", "issue__key"]
    autocomplete_fields = ["issue", "author"]
    readonly_fields = ["created_at", "updated_at"]
