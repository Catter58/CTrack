"""
Issues API endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.issues.models import Issue, IssueType, Status
from apps.issues.schemas import (
    CommentCreateSchema,
    CommentSchema,
    IssueCreateSchema,
    IssueDetailSchema,
    IssueListSchema,
    IssueTypeCreateSchema,
    IssueTypeSchema,
    IssueTypeUpdateSchema,
    IssueUpdateSchema,
    StatusCreateSchema,
    StatusSchema,
    StatusUpdateSchema,
    WorkflowTransitionSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


# Issue Types endpoints


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


# Statuses endpoints


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


# Issues endpoints


@router.post(
    "/projects/{key}/issues",
    response={
        201: IssueDetailSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def create_issue(request, key: str, data: IssueCreateSchema):
    """Create a new issue."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    membership = ProjectService.get_user_membership(project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_edit:
        return 403, {"detail": "Недостаточно прав для создания задач"}

    # Validate issue type
    if not IssueType.objects.filter(id=data.issue_type_id).exists():
        return 400, {"detail": "Тип задачи не найден"}

    # Validate status if provided
    if data.status_id and not Status.objects.filter(id=data.status_id).exists():
        return 400, {"detail": "Статус не найден"}

    issue = IssueService.create_issue(
        project=project,
        user=request.auth,
        title=data.title,
        description=data.description,
        issue_type_id=data.issue_type_id,
        status_id=data.status_id,
        priority=data.priority,
        assignee_id=data.assignee_id,
        parent_id=data.parent_id,
        story_points=data.story_points,
        due_date=data.due_date,
    )

    return 201, issue


@router.get(
    "/projects/{key}/issues",
    response={200: list[IssueListSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_issues(
    request,
    key: str,
    status_id: UUID = None,
    issue_type_id: UUID = None,
    assignee_id: int = None,
    priority: str = None,
):
    """Get issues for project with optional filters."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    issues = IssueService.get_issues(
        project,
        status_id=status_id,
        issue_type_id=issue_type_id,
        assignee_id=assignee_id,
        priority=priority,
    )

    return 200, list(issues)


@router.get(
    "/issues/{issue_key}",
    response={200: IssueDetailSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_issue(request, issue_key: str):
    """Get issue by key."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    return 200, issue


@router.patch(
    "/issues/{issue_key}",
    response={
        200: IssueDetailSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_issue(request, issue_key: str, data: IssueUpdateSchema):
    """Update issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    membership = ProjectService.get_user_membership(issue.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_edit:
        return 403, {"detail": "Недостаточно прав для редактирования задач"}

    # Check workflow if status is being changed
    if data.status_id and data.status_id != issue.status_id:
        if not IssueService.can_transition(issue, data.status_id, request.auth):
            return 400, {"detail": "Недопустимый переход статуса"}

    update_data = data.dict(exclude_unset=True)
    issue = IssueService.update_issue(issue, **update_data)

    return 200, issue


@router.delete(
    "/issues/{issue_key}",
    response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_issue(request, issue_key: str):
    """Delete issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    membership = ProjectService.get_user_membership(issue.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для удаления задач"}

    IssueService.delete_issue(issue)

    return 200, {"message": "Задача удалена"}


# Comments endpoints


@router.get(
    "/issues/{issue_key}/comments",
    response={200: list[CommentSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_comments(request, issue_key: str):
    """Get comments for issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    comments = IssueService.get_comments(issue)
    return 200, list(comments)


@router.post(
    "/issues/{issue_key}/comments",
    response={201: CommentSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def add_comment(request, issue_key: str, data: CommentCreateSchema):
    """Add comment to issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    comment = IssueService.add_comment(issue, request.auth, data.content)
    return 201, comment


# Workflow endpoints


@router.get(
    "/issues/{issue_key}/transitions",
    response={200: list[WorkflowTransitionSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def get_issue_transitions(request, issue_key: str):
    """Get available status transitions for issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    transitions = IssueService.get_available_transitions(issue, request.auth)
    return 200, transitions
