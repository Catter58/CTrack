"""
Setup Wizard API endpoints.
"""

from django.db import transaction
from ninja import Router, Schema

from apps.issues.models import IssueType, Status
from apps.users.jwt import create_token_pair
from apps.users.models import User
from apps.users.schemas import ErrorSchema

router = Router()


class SetupStatusSchema(Schema):
    """Schema for setup status response."""

    setup_required: bool
    has_users: bool
    has_issue_types: bool
    has_statuses: bool


class AdminUserSchema(Schema):
    """Schema for admin user creation."""

    email: str
    username: str
    password: str
    full_name: str | None = None


class OrgSettingsSchema(Schema):
    """Schema for organization settings."""

    name: str
    timezone: str = "Europe/Moscow"


class SetupCompleteSchema(Schema):
    """Schema for setup completion request."""

    admin_user: AdminUserSchema
    org_settings: OrgSettingsSchema
    issue_type_template: str = "scrum"  # scrum, kanban, bug_tracking, empty


class SetupCompleteResponseSchema(Schema):
    """Schema for setup completion response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    message: str


@router.get(
    "/status",
    response={200: SetupStatusSchema},
)
def setup_status(request):
    """Check if initial setup is required."""
    has_users = User.objects.exists()
    has_issue_types = IssueType.objects.filter(project__isnull=True).exists()
    has_statuses = Status.objects.filter(project__isnull=True).exists()

    return 200, {
        "setup_required": not has_users,
        "has_users": has_users,
        "has_issue_types": has_issue_types,
        "has_statuses": has_statuses,
    }


@router.post(
    "/complete",
    response={201: SetupCompleteResponseSchema, 400: ErrorSchema},
)
@transaction.atomic
def setup_complete(request, data: SetupCompleteSchema):
    """Complete initial setup."""
    # Check if setup is still required
    if User.objects.exists():
        return 400, {"detail": "Настройка уже выполнена"}

    # Validate admin user data
    if not data.admin_user.email or not data.admin_user.password:
        return 400, {"detail": "Email и пароль обязательны"}

    if len(data.admin_user.password) < 8:
        return 400, {"detail": "Пароль должен содержать минимум 8 символов"}

    # Check email uniqueness
    if User.objects.filter(email=data.admin_user.email).exists():
        return 400, {"detail": "Email уже используется"}

    # Create admin user
    user = User.objects.create_user(
        username=data.admin_user.username or data.admin_user.email.split("@")[0],
        email=data.admin_user.email,
        password=data.admin_user.password,
        first_name=(
            data.admin_user.full_name.split()[0] if data.admin_user.full_name else ""
        ),
        last_name=(
            " ".join(data.admin_user.full_name.split()[1:])
            if data.admin_user.full_name
            else ""
        ),
        is_staff=True,
        is_superuser=True,
    )

    # Load default issue types and statuses if not exists
    _ensure_default_data(data.issue_type_template)

    # TODO: Save org settings (need OrgSettings model or site settings)

    # Generate tokens
    access_token, refresh_token = create_token_pair(user.id)

    return 201, {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "message": "Настройка завершена успешно",
    }


def _ensure_default_data(template: str) -> None:
    """Ensure default issue types and statuses exist."""
    from django.core.management import call_command

    # Load default statuses if not exist
    if not Status.objects.filter(project__isnull=True).exists():
        try:
            call_command("loaddata", "default_statuses", verbosity=0)
        except Exception:
            _create_default_statuses()

    # Load issue types based on template
    if not IssueType.objects.filter(project__isnull=True).exists():
        if template == "empty":
            return
        try:
            call_command("loaddata", "default_issue_types", verbosity=0)
        except Exception:
            _create_default_issue_types(template)


def _create_default_statuses() -> None:
    """Create default statuses manually."""
    statuses = [
        {"name": "К выполнению", "category": "todo", "color": "#6f6f6f", "order": 1},
        {"name": "В работе", "category": "in_progress", "color": "#1192e8", "order": 2},
        {
            "name": "На проверке",
            "category": "in_progress",
            "color": "#8a3ffc",
            "order": 3,
        },
        {"name": "Готово", "category": "done", "color": "#198038", "order": 4},
    ]
    for s in statuses:
        Status.objects.create(project=None, **s)


def _create_default_issue_types(template: str) -> None:
    """Create default issue types based on template."""
    if template == "scrum":
        types = [
            {
                "name": "Эпик",
                "icon": "target",
                "color": "#8a3ffc",
                "is_subtask": False,
                "is_epic": True,
                "order": 1,
            },
            {
                "name": "История",
                "icon": "book",
                "color": "#0f62fe",
                "is_subtask": False,
                "order": 2,
            },
            {
                "name": "Задача",
                "icon": "checkmark",
                "color": "#1192e8",
                "is_subtask": False,
                "order": 3,
            },
            {
                "name": "Баг",
                "icon": "debug",
                "color": "#da1e28",
                "is_subtask": False,
                "order": 4,
            },
            {
                "name": "Подзадача",
                "icon": "subtract",
                "color": "#6f6f6f",
                "is_subtask": True,
                "order": 5,
            },
        ]
    elif template == "kanban":
        types = [
            {
                "name": "Задача",
                "icon": "checkmark",
                "color": "#1192e8",
                "is_subtask": False,
                "order": 1,
            },
            {
                "name": "Баг",
                "icon": "debug",
                "color": "#da1e28",
                "is_subtask": False,
                "order": 2,
            },
            {
                "name": "Улучшение",
                "icon": "upgrade",
                "color": "#198038",
                "is_subtask": False,
                "order": 3,
            },
        ]
    elif template == "bug_tracking":
        types = [
            {
                "name": "Баг",
                "icon": "debug",
                "color": "#da1e28",
                "is_subtask": False,
                "order": 1,
            },
            {
                "name": "Улучшение",
                "icon": "upgrade",
                "color": "#198038",
                "is_subtask": False,
                "order": 2,
            },
            {
                "name": "Фича",
                "icon": "add",
                "color": "#0f62fe",
                "is_subtask": False,
                "order": 3,
            },
        ]
    else:
        return

    for t in types:
        IssueType.objects.create(project=None, parent_types=[], **t)
