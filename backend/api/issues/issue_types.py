"""
Issue Types API endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.issues.models import Issue
from apps.issues.schemas import (
    IssueTypeCreateSchema,
    IssueTypeSchema,
    IssueTypeUpdateSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


@router.get(
    "/projects/{key}/issue-types",
    response={200: list[IssueTypeSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_issue_types(request, key: str):
    """Get issue types for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    types = IssueService.get_issue_types(project)
    return 200, list(types)


@router.post(
    "/projects/{key}/issue-types",
    response={
        201: IssueTypeSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def create_issue_type(request, key: str, data: IssueTypeCreateSchema):
    """Create a new issue type for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    membership = ProjectService.get_user_membership(project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для создания типов задач"}

    issue_type = IssueService.create_issue_type(
        project=project,
        name=data.name,
        icon=data.icon,
        color=data.color,
        is_subtask=data.is_subtask,
        parent_types=data.parent_types,
        order=data.order,
    )

    return 201, issue_type


@router.get(
    "/issue-types/{issue_type_id}",
    response={200: IssueTypeSchema, 404: ErrorSchema},
)
def get_issue_type(request, issue_type_id: UUID):
    """Get issue type by ID."""
    issue_type = IssueService.get_issue_type(issue_type_id)

    if not issue_type:
        return 404, {"detail": "Тип задачи не найден"}

    return 200, issue_type


@router.patch(
    "/issue-types/{issue_type_id}",
    response={200: IssueTypeSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def update_issue_type(request, issue_type_id: UUID, data: IssueTypeUpdateSchema):
    """Update issue type."""
    issue_type = IssueService.get_issue_type(issue_type_id)

    if not issue_type:
        return 404, {"detail": "Тип задачи не найден"}

    # Check permissions if project-specific type
    if issue_type.project:
        membership = ProjectService.get_user_membership(
            issue_type.project, request.auth
        )
        if not membership or not membership.can_manage:
            return 403, {"detail": "Недостаточно прав для редактирования типов задач"}

    update_data = data.dict(exclude_unset=True)
    issue_type = IssueService.update_issue_type(issue_type, **update_data)

    return 200, issue_type


@router.delete(
    "/issue-types/{issue_type_id}",
    response={200: MessageSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_issue_type(request, issue_type_id: UUID):
    """Delete issue type."""
    issue_type = IssueService.get_issue_type(issue_type_id)

    if not issue_type:
        return 404, {"detail": "Тип задачи не найден"}

    # Check permissions if project-specific type
    if issue_type.project:
        membership = ProjectService.get_user_membership(
            issue_type.project, request.auth
        )
        if not membership or not membership.can_manage:
            return 403, {"detail": "Недостаточно прав для удаления типов задач"}

    # Check if type is in use
    if Issue.objects.filter(issue_type=issue_type).exists():
        return 400, {
            "detail": "Тип задачи используется в задачах и не может быть удалён"
        }

    IssueService.delete_issue_type(issue_type)

    return 200, {"message": "Тип задачи удалён"}
