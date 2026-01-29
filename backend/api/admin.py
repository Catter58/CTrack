"""
Admin API endpoints for CTrack.

Provides system administration functionality:
- System settings management
- User administration
- System statistics
"""

import secrets
from datetime import datetime, timedelta
from functools import wraps

from django.db.models import Q
from django.utils import timezone
from ninja import Router, Schema

from apps.core.models import SystemSettings
from apps.issues.models import Issue
from apps.projects.models import Project
from apps.users.auth import AuthBearer
from apps.users.models import User
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer(), tags=["Admin"])


def admin_required(func):
    """Decorator to require admin (is_staff) access."""

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.auth.is_staff:
            return 403, {"detail": "Доступ запрещён"}
        return func(request, *args, **kwargs)

    return wrapper


# ============================================================================
# Schemas
# ============================================================================


class SystemSettingsSchema(Schema):
    """System settings response schema."""

    organization_name: str
    default_language: str
    allow_registration: bool
    smtp_settings: dict
    storage_settings: dict
    updated_at: datetime


class SystemSettingsUpdateSchema(Schema):
    """System settings update schema."""

    organization_name: str | None = None
    default_language: str | None = None
    allow_registration: bool | None = None
    smtp_settings: dict | None = None
    storage_settings: dict | None = None


class AdminUserSchema(Schema):
    """Admin user response schema."""

    id: int
    username: str
    email: str
    first_name: str | None
    last_name: str | None
    full_name: str
    is_active: bool
    is_staff: bool
    date_joined: datetime
    last_login: datetime | None

    @staticmethod
    def resolve_first_name(obj: User) -> str | None:
        return obj.first_name or None

    @staticmethod
    def resolve_last_name(obj: User) -> str | None:
        return obj.last_name or None

    @staticmethod
    def resolve_full_name(obj: User) -> str:
        full = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        return full if full else obj.username


class AdminUserUpdateSchema(Schema):
    """Admin user update schema."""

    is_active: bool | None = None
    is_staff: bool | None = None


class AdminUserListResponse(Schema):
    """Paginated user list response."""

    items: list[AdminUserSchema]
    total: int
    limit: int
    offset: int


class PasswordResetTokenSchema(Schema):
    """Password reset token response."""

    reset_token: str
    expires_at: datetime


class SystemStatsSchema(Schema):
    """System statistics schema."""

    total_users: int
    active_users: int
    total_projects: int
    total_issues: int
    issues_this_month: int


# ============================================================================
# System Settings Endpoints
# ============================================================================


@router.get(
    "/admin/settings",
    response={200: SystemSettingsSchema, 403: ErrorSchema},
)
@admin_required
def get_system_settings(request):
    """Get system settings."""
    settings = SystemSettings.get_settings()
    return 200, settings


@router.patch(
    "/admin/settings",
    response={200: SystemSettingsSchema, 403: ErrorSchema},
)
@admin_required
def update_system_settings(request, data: SystemSettingsUpdateSchema):
    """Update system settings."""
    settings = SystemSettings.get_settings()

    if data.organization_name is not None:
        settings.organization_name = data.organization_name
    if data.default_language is not None:
        settings.default_language = data.default_language
    if data.allow_registration is not None:
        settings.allow_registration = data.allow_registration
    if data.smtp_settings is not None:
        settings.smtp_settings = data.smtp_settings
    if data.storage_settings is not None:
        settings.storage_settings = data.storage_settings

    settings.save()
    return 200, settings


# ============================================================================
# User Administration Endpoints
# ============================================================================


@router.get(
    "/admin/users",
    response={200: AdminUserListResponse, 403: ErrorSchema},
)
@admin_required
def list_admin_users(
    request,
    search: str = None,
    is_active: bool = None,
    is_staff: bool = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all users with pagination and filters."""
    queryset = User.objects.all()

    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    if is_staff is not None:
        queryset = queryset.filter(is_staff=is_staff)

    total = queryset.count()
    users = list(queryset.order_by("-date_joined")[offset : offset + limit])

    return 200, {
        "items": users,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/admin/users/{user_id}",
    response={200: AdminUserSchema, 403: ErrorSchema, 404: ErrorSchema},
)
@admin_required
def get_admin_user(request, user_id: int):
    """Get user details by ID."""
    user = User.objects.filter(id=user_id).first()

    if not user:
        return 404, {"detail": "Пользователь не найден"}

    return 200, user


@router.patch(
    "/admin/users/{user_id}",
    response={200: AdminUserSchema, 403: ErrorSchema, 404: ErrorSchema},
)
@admin_required
def update_admin_user(request, user_id: int, data: AdminUserUpdateSchema):
    """Update user status (is_active, is_staff)."""
    user = User.objects.filter(id=user_id).first()

    if not user:
        return 404, {"detail": "Пользователь не найден"}

    # Prevent self-deactivation or removing own admin status
    if user.id == request.auth.id:
        if data.is_active is False:
            return 403, {"detail": "Нельзя деактивировать свой аккаунт"}
        if data.is_staff is False:
            return 403, {"detail": "Нельзя снять с себя права администратора"}

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_staff is not None:
        user.is_staff = data.is_staff

    user.save()
    return 200, user


@router.post(
    "/admin/users/{user_id}/reset-password",
    response={200: PasswordResetTokenSchema, 403: ErrorSchema, 404: ErrorSchema},
)
@admin_required
def reset_user_password(request, user_id: int):
    """Generate a password reset token for user."""
    user = User.objects.filter(id=user_id).first()

    if not user:
        return 404, {"detail": "Пользователь не найден"}

    # Generate secure reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)

    # In a real implementation, you would:
    # 1. Store this token in a PasswordResetToken model
    # 2. Send email to user with reset link
    # For now, we return the token to admin

    return 200, {
        "reset_token": reset_token,
        "expires_at": expires_at,
    }


# ============================================================================
# Statistics Endpoints
# ============================================================================


@router.get(
    "/admin/stats",
    response={200: SystemStatsSchema, 403: ErrorSchema},
)
@admin_required
def get_system_stats(request):
    """Get system statistics."""
    # Calculate first day of current month
    now = timezone.now()
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_projects = Project.objects.filter(is_archived=False).count()
    total_issues = Issue.objects.count()
    issues_this_month = Issue.objects.filter(created_at__gte=first_day_of_month).count()

    return 200, {
        "total_users": total_users,
        "active_users": active_users,
        "total_projects": total_projects,
        "total_issues": total_issues,
        "issues_this_month": issues_this_month,
    }
