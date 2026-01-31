"""
Status management endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.issues.models import Issue
from apps.issues.schemas import (
    StatusCreateSchema,
    StatusSchema,
    StatusUpdateSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


@router.get(
    "/projects/{key}/statuses",
    response={200: list[StatusSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_statuses(request, key: str):
    """Get statuses for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    statuses = IssueService.get_statuses(project)
    return 200, list(statuses)


@router.post(
    "/projects/{key}/statuses",
    response={201: StatusSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def create_status(request, key: str, data: StatusCreateSchema):
    """Create a new status for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    membership = ProjectService.get_user_membership(project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для создания статусов"}

    # Validate category
    valid_categories = ["todo", "in_progress", "done"]
    if data.category not in valid_categories:
        return 400, {
            "detail": f"Категория должна быть одной из: {', '.join(valid_categories)}"
        }

    status = IssueService.create_status(
        project=project,
        name=data.name,
        category=data.category,
        color=data.color,
        order=data.order,
    )

    return 201, status


@router.get(
    "/statuses/{status_id}",
    response={200: StatusSchema, 404: ErrorSchema},
)
def get_status(request, status_id: UUID):
    """Get status by ID."""
    status = IssueService.get_status(status_id)

    if not status:
        return 404, {"detail": "Статус не найден"}

    return 200, status


@router.patch(
    "/statuses/{status_id}",
    response={200: StatusSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def update_status(request, status_id: UUID, data: StatusUpdateSchema):
    """Update status."""
    status = IssueService.get_status(status_id)

    if not status:
        return 404, {"detail": "Статус не найден"}

    # Check permissions if project-specific status
    if status.project:
        membership = ProjectService.get_user_membership(status.project, request.auth)
        if not membership or not membership.can_manage:
            return 403, {"detail": "Недостаточно прав для редактирования статусов"}

    # Validate category if provided
    if data.category:
        valid_categories = ["todo", "in_progress", "done"]
        if data.category not in valid_categories:
            return 400, {
                "detail": f"Категория должна быть одной из: {', '.join(valid_categories)}"
            }

    update_data = data.dict(exclude_unset=True)
    status = IssueService.update_status(status, **update_data)

    return 200, status


@router.delete(
    "/statuses/{status_id}",
    response={200: MessageSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_status(request, status_id: UUID):
    """Delete status."""
    status = IssueService.get_status(status_id)

    if not status:
        return 404, {"detail": "Статус не найден"}

    # Check permissions if project-specific status
    if status.project:
        membership = ProjectService.get_user_membership(status.project, request.auth)
        if not membership or not membership.can_manage:
            return 403, {"detail": "Недостаточно прав для удаления статусов"}

    # Check if status is in use
    if Issue.objects.filter(status=status).exists():
        return 400, {"detail": "Статус используется в задачах и не может быть удалён"}

    IssueService.delete_status(status)

    return 200, {"message": "Статус удалён"}
