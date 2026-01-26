from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import User


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
