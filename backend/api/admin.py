"""
Admin API endpoints for CTrack.

Provides system administration functionality:
- System settings management
- User administration
- System statistics
- Time-series usage analytics
"""

import secrets
from datetime import datetime, timedelta
from functools import wraps

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from ninja import Router, Schema

from apps.core.email_backend import test_smtp_connection
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


class SMTPTestSchema(Schema):
    """SMTP test request schema."""

    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    from_email: str = ""
    test_recipient: str = ""


class SMTPTestResultSchema(Schema):
    """SMTP test result schema."""

    success: bool
    message: str


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


class AdminUserCreateSchema(Schema):
    """Admin user creation schema."""

    username: str
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    is_staff: bool = False
    send_welcome_email: bool = False


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


class TimeSeriesPointSchema(Schema):
    """Single data point in time series."""

    date: str
    value: int


class TimeSeriesDataSchema(Schema):
    """Time series data for a single metric."""

    name: str
    data: list[TimeSeriesPointSchema]


class TimeSeriesStatsSchema(Schema):
    """Time series statistics response."""

    period: str
    aggregation: str
    start_date: str
    end_date: str
    users_registered: TimeSeriesDataSchema
    issues_created: TimeSeriesDataSchema
    active_users: TimeSeriesDataSchema


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


@router.post(
    "/admin/settings/smtp/test",
    response={200: SMTPTestResultSchema, 403: ErrorSchema},
)
@admin_required
def test_smtp_settings(request, data: SMTPTestSchema):
    """Test SMTP connection with provided settings."""
    result = test_smtp_connection(
        host=data.host,
        port=data.port,
        username=data.username,
        password=data.password,
        use_tls=data.use_tls,
        use_ssl=data.use_ssl,
        from_email=data.from_email,
        test_recipient=data.test_recipient,
    )
    return 200, result


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


@router.post(
    "/admin/users",
    response={200: AdminUserSchema, 400: ErrorSchema, 403: ErrorSchema},
)
@admin_required
def create_admin_user(request, data: AdminUserCreateSchema):
    """Create a new user (admin only)."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    # Check if username already exists
    if User.objects.filter(username=data.username).exists():
        return 400, {"detail": "Пользователь с таким именем уже существует"}

    # Check if email already exists
    if User.objects.filter(email=data.email).exists():
        return 400, {"detail": "Пользователь с таким email уже существует"}

    # Validate password
    try:
        validate_password(data.password)
    except ValidationError as e:
        return 400, {"detail": "; ".join(e.messages)}

    # Create user
    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        is_staff=data.is_staff,
    )

    # Send welcome email if requested and SMTP is configured
    if data.send_welcome_email:
        from apps.core.tasks import send_welcome_email_task

        send_welcome_email_task.delay(user.id)

    return 200, user


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


@router.get(
    "/admin/stats/timeseries",
    response={200: TimeSeriesStatsSchema, 403: ErrorSchema},
)
@admin_required
def get_timeseries_stats(
    request,
    days: int = 30,
    aggregation: str = "day",
):
    """
    Get time-series statistics for usage graphs.

    Args:
        days: Number of days to look back (default 30)
        aggregation: Aggregation level - 'day', 'week', or 'month'
    """
    now = timezone.now()
    start_date = now - timedelta(days=days)

    # Select truncation function based on aggregation
    if aggregation == "week":
        trunc_func = TruncWeek
    elif aggregation == "month":
        trunc_func = TruncMonth
    else:
        trunc_func = TruncDate
        aggregation = "day"

    # Users registered over time
    users_by_date = (
        User.objects.filter(date_joined__gte=start_date)
        .annotate(period=trunc_func("date_joined"))
        .values("period")
        .annotate(count=Count("id"))
        .order_by("period")
    )

    users_data = [
        {"date": item["period"].strftime("%Y-%m-%d"), "value": item["count"]}
        for item in users_by_date
    ]

    # Issues created over time
    issues_by_date = (
        Issue.objects.filter(created_at__gte=start_date)
        .annotate(period=trunc_func("created_at"))
        .values("period")
        .annotate(count=Count("id"))
        .order_by("period")
    )

    issues_data = [
        {"date": item["period"].strftime("%Y-%m-%d"), "value": item["count"]}
        for item in issues_by_date
    ]

    # Active users per day (users who logged in)
    active_by_date = (
        User.objects.filter(last_login__gte=start_date, last_login__isnull=False)
        .annotate(period=trunc_func("last_login"))
        .values("period")
        .annotate(count=Count("id", distinct=True))
        .order_by("period")
    )

    active_data = [
        {"date": item["period"].strftime("%Y-%m-%d"), "value": item["count"]}
        for item in active_by_date
    ]

    return 200, {
        "period": f"{days} days",
        "aggregation": aggregation,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
        "users_registered": {
            "name": "Регистрации",
            "data": users_data,
        },
        "issues_created": {
            "name": "Созданные задачи",
            "data": issues_data,
        },
        "active_users": {
            "name": "Активные пользователи",
            "data": active_data,
        },
    }
