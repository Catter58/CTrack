from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import NotificationPreference, User


@admin.register(User)
class UserAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    """Админка для модели User."""

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    ]
    list_filter = ["is_staff", "is_superuser", "is_active", "groups"]
    search_fields = ["username", "first_name", "last_name", "email"]
    ordering = ["username"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Дополнительно",
            {
                "fields": ("avatar", "bio", "timezone"),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Дополнительно",
            {
                "fields": ("email", "avatar", "bio", "timezone"),
            },
        ),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin for NotificationPreference model."""

    list_display = [
        "user",
        "notify_on_assign",
        "notify_on_mention",
        "notify_on_comment",
        "notify_on_status_change",
        "email_frequency",
    ]
    list_filter = [
        "notify_on_assign",
        "notify_on_mention",
        "notify_on_comment",
        "notify_on_status_change",
        "email_frequency",
    ]
    search_fields = ["user__username", "user__email"]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "user")}),
        (
            "Уведомления",
            {
                "fields": (
                    "notify_on_assign",
                    "notify_on_mention",
                    "notify_on_comment",
                    "notify_on_status_change",
                )
            },
        ),
        ("Email", {"fields": ("email_frequency",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
