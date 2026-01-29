"""
Issues API endpoints.
"""

from datetime import date
from uuid import UUID

from django.http import FileResponse
from ninja import Router
from ninja.files import UploadedFile

from apps.issues.models import Issue, IssueType, Status
from apps.issues.schemas import (
    ActivitySchema,
    AttachmentSchema,
    BulkUpdateResultSchema,
    BulkUpdateSchema,
    CommentCreateSchema,
    CommentSchema,
    CommentUpdateSchema,
    EpicSchema,
    GlobalIssuePaginatedResponseSchema,
    IssueCreateSchema,
    IssueDetailSchema,
    IssueListSchema,
    IssuePaginatedResponseSchema,
    IssueTypeCreateSchema,
    IssueTypeSchema,
    IssueTypeUpdateSchema,
    IssueUpdateSchema,
    StatusCreateSchema,
    StatusSchema,
    StatusUpdateSchema,
    WorkflowTransitionSchema,
    WorkflowTransitionUpdateSchema,
)
from apps.issues.services import ActivityService, IssueService
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


@router.get(
    "/issues",
    response={200: GlobalIssuePaginatedResponseSchema},
)
def list_global_issues(
    request,
    project_id: UUID = None,
    status_id: UUID = None,
    assignee_id: int = None,
    reporter_id: int = None,
    priority: str = None,
    issue_type_id: UUID = None,
    sprint_id: UUID = None,
    due_date_from: date = None,
    due_date_to: date = None,
    created_from: date = None,
    created_to: date = None,
    search: str = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
):
    """
    Get all issues from projects where the current user is a member.

    Supports filtering, sorting and pagination.

    Query parameters:
    - project_id: Filter by specific project UUID
    - status_id: Filter by status UUID
    - assignee_id: Filter by assignee user ID (use 0 for unassigned)
    - reporter_id: Filter by reporter user ID
    - priority: Filter by priority (highest, high, medium, low, lowest)
    - issue_type_id: Filter by issue type UUID
    - sprint_id: Filter by sprint UUID
    - due_date_from, due_date_to: Filter by due date range
    - created_from, created_to: Filter by creation date range
    - search: Search in title and key
    - sort_by: Sort field (created_at, updated_at, due_date, priority)
    - sort_order: Sort order (asc, desc)
    - page: Page number (default 1)
    - page_size: Items per page (default 20, max 100)
    """
    # Validate and cap page_size
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    if page < 1:
        page = 1

    # Validate sort_order
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    issues = IssueService.get_global_issues(
        user=request.auth,
        project_id=project_id,
        status_id=status_id,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        priority=priority,
        issue_type_id=issue_type_id,
        sprint_id=sprint_id,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        created_from=created_from,
        created_to=created_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get total count before pagination
    total = issues.count()

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_issues = list(issues[offset : offset + page_size])

    return 200, {
        "items": paginated_issues,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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
    issue_type = IssueType.objects.filter(id=data.issue_type_id).first()
    if not issue_type:
        return 400, {"detail": "Тип задачи не найден"}

    # Validate status if provided
    if data.status_id and not Status.objects.filter(id=data.status_id).exists():
        return 400, {"detail": "Статус не найден"}

    # Validate parent_id if provided
    if data.parent_id:
        # Create a simple object for validation
        from types import SimpleNamespace

        temp_issue = SimpleNamespace(id=None, issue_type=issue_type)
        is_valid, error = IssueService.validate_parent(
            temp_issue, data.parent_id, project
        )
        if not is_valid:
            return 400, {"detail": error}

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
        epic_id=data.epic_id,
        story_points=data.story_points,
        due_date=data.due_date,
        custom_fields=data.custom_fields,
    )

    return 201, issue


@router.get(
    "/projects/{key}/issues",
    response={200: IssuePaginatedResponseSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def list_issues(
    request,
    key: str,
    status_id: UUID = None,
    issue_type_id: UUID = None,
    type_id: UUID = None,
    assignee_id: int = None,
    priority: str = None,
    epic_id: UUID = None,
    search: str = None,
    page: int = 1,
    page_size: int = 20,
):
    """Get issues for project with optional filters and pagination."""
    # Validate and cap page_size
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    if page < 1:
        page = 1

    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    # Support both issue_type_id and type_id for backwards compatibility
    effective_type_id = issue_type_id or type_id

    issues = IssueService.get_issues(
        project,
        status_id=status_id,
        issue_type_id=effective_type_id,
        assignee_id=assignee_id,
        priority=priority,
        epic_id=epic_id,
        search=search,
    )

    # Get total count before pagination
    total = issues.count()

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_issues = list(issues[offset : offset + page_size])

    return 200, {
        "items": paginated_issues,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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

    # Add children stats
    stats = IssueService.get_children_stats(issue)
    issue.children_count = stats["children_count"]
    issue.completed_children_count = stats["completed_children_count"]

    return 200, issue


@router.get(
    "/issues/{issue_key}/children",
    response={200: list[IssueListSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def get_issue_children(request, issue_key: str):
    """Get children (subtasks) of an issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    children = IssueService.get_children(issue)
    return 200, children


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

    # Validate parent_id if being changed
    if data.parent_id is not None and data.parent_id != issue.parent_id:
        is_valid, error = IssueService.validate_parent(
            issue, data.parent_id, issue.project
        )
        if not is_valid:
            return 400, {"detail": error}

    update_data = data.dict(exclude_unset=True)
    updated_issue = IssueService.update_issue(issue, user=request.auth, **update_data)

    # Add children stats for response
    stats = IssueService.get_children_stats(updated_issue)
    updated_issue.children_count = stats["children_count"]
    updated_issue.completed_children_count = stats["completed_children_count"]

    return 200, updated_issue


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


@router.patch(
    "/comments/{comment_id}",
    response={200: CommentSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def update_comment(request, comment_id: UUID, data: CommentUpdateSchema):
    comment = IssueService.get_comment_by_id(comment_id)

    if not comment:
        return 404, {"detail": "Комментарий не найден"}

    if comment.author != request.auth:
        return 403, {"detail": "Только автор может редактировать комментарий"}

    updated = IssueService.update_comment(comment, data.content)
    return 200, updated


@router.delete(
    "/comments/{comment_id}",
    response={204: None, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_comment(request, comment_id: UUID):
    comment = IssueService.get_comment_by_id(comment_id)

    if not comment:
        return 404, {"detail": "Комментарий не найден"}

    is_author = comment.author == request.auth
    is_admin = ProjectService.is_admin(comment.issue.project, request.auth)

    if not is_author and not is_admin:
        return 403, {"detail": "Только автор или админ может удалить комментарий"}

    IssueService.delete_comment(comment)
    return 204, None


# Activity endpoints


@router.get(
    "/issues/{issue_key}/activity",
    response={200: list[ActivitySchema], 403: ErrorSchema, 404: ErrorSchema},
)
def get_issue_activity(request, issue_key: str):
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    activities = ActivityService.get_issue_activities(issue)
    return 200, list(activities)


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


@router.post(
    "/issues/{issue_key}/transitions/{transition_id}",
    response={
        200: IssueDetailSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def execute_transition(request, issue_key: str, transition_id: UUID):
    """Execute a workflow transition on an issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    membership = ProjectService.get_user_membership(issue.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_edit:
        return 403, {"detail": "Недостаточно прав для редактирования задач"}

    transition = IssueService.get_workflow_transition_by_id(transition_id)
    if not transition:
        return 404, {"detail": "Переход не найден"}

    try:
        updated_issue = IssueService.execute_transition(issue, transition, request.auth)
        stats = IssueService.get_children_stats(updated_issue)
        updated_issue.children_count = stats["children_count"]
        updated_issue.completed_children_count = stats["completed_children_count"]
        return 200, updated_issue
    except ValueError as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/workflow/{transition_id}",
    response={
        200: WorkflowTransitionSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_workflow_transition(
    request, transition_id: UUID, data: WorkflowTransitionUpdateSchema
):
    """Update a workflow transition."""
    transition = IssueService.get_workflow_transition_by_id(transition_id)

    if not transition:
        return 404, {"detail": "Переход не найден"}

    membership = ProjectService.get_user_membership(transition.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для управления workflow"}

    update_data = data.dict(exclude_unset=True)
    transition = IssueService.update_workflow_transition(transition, **update_data)

    return 200, transition


@router.delete(
    "/workflow/{transition_id}",
    response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_workflow_transition(request, transition_id: UUID):
    """Delete a workflow transition."""
    transition = IssueService.get_workflow_transition_by_id(transition_id)

    if not transition:
        return 404, {"detail": "Переход не найден"}

    membership = ProjectService.get_user_membership(transition.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для управления workflow"}

    IssueService.delete_workflow_transition(transition)

    return 200, {"message": "Переход удалён"}


# Backlog endpoints


@router.get(
    "/projects/{key}/backlog",
    response={200: list[IssueListSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def get_backlog(
    request,
    key: str,
    limit: int = None,
    offset: int = 0,
):
    """Get backlog issues (not in active/planned sprints)."""
    # Validate and cap limit
    if limit is not None:
        if limit < 1:
            limit = 50
        if limit > 100:
            limit = 100
    if offset < 0:
        offset = 0

    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    issues = IssueService.get_backlog(project, limit=limit, offset=offset)
    return 200, list(issues)


@router.patch(
    "/issues/{issue_key}/sprint",
    response={
        200: IssueDetailSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_issue_sprint(request, issue_key: str, sprint_id: UUID = None):
    """Update issue sprint assignment."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    membership = ProjectService.get_user_membership(issue.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_edit:
        return 403, {"detail": "Недостаточно прав для редактирования задач"}

    try:
        issue = IssueService.update_issue_sprint(issue, sprint_id)
        return 200, issue
    except ValueError as e:
        return 400, {"detail": str(e)}


@router.patch(
    "/projects/{key}/issues/bulk-update",
    response={200: BulkUpdateResultSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def bulk_update_issues(request, key: str, data: BulkUpdateSchema):
    """Bulk update story points for multiple issues."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    membership = ProjectService.get_user_membership(project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_edit:
        return 403, {"detail": "Недостаточно прав для редактирования задач"}

    updates = [
        {"key": item.key, "story_points": item.story_points} for item in data.issues
    ]
    updated, failed = IssueService.bulk_update_story_points(project, updates)

    return 200, {"updated": updated, "failed": failed}


# Epics endpoints


@router.get(
    "/projects/{key}/epics",
    response={200: list[EpicSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_epics(request, key: str):
    """Get all epics for a project with progress statistics."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    epics = IssueService.get_epics(project)
    return 200, epics


# Attachments endpoints

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
    "application/xml",
    "application/zip",
    "application/x-rar-compressed",
    "application/x-7z-compressed",
    "application/gzip",
}


@router.post(
    "/issues/{issue_key}/attachments",
    response={
        201: AttachmentSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def upload_attachment(request, issue_key: str, file: UploadedFile):
    """Upload a file attachment to an issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    if file.size > MAX_FILE_SIZE:
        return 400, {"detail": "Размер файла превышает 10 МБ"}

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        return 400, {"detail": f"Недопустимый тип файла: {content_type}"}

    attachment = IssueService.create_attachment(
        issue=issue,
        user=request.auth,
        file=file,
        filename=file.name,
        content_type=content_type,
    )

    return 201, attachment


@router.get(
    "/issues/{issue_key}/attachments",
    response={200: list[AttachmentSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_attachments(request, issue_key: str):
    """Get all attachments for an issue."""
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    attachments = IssueService.get_attachments(issue)
    return 200, list(attachments)


@router.get(
    "/attachments/{attachment_id}/download",
    response={403: ErrorSchema, 404: ErrorSchema},
)
def download_attachment(request, attachment_id: UUID):
    """Download an attachment file."""
    attachment = IssueService.get_attachment_by_id(attachment_id)

    if not attachment:
        return 404, {"detail": "Вложение не найдено"}

    if not ProjectService.is_member(attachment.issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    return FileResponse(
        attachment.file.open("rb"),
        as_attachment=True,
        filename=attachment.filename,
        content_type=attachment.content_type,
    )


@router.delete(
    "/attachments/{attachment_id}",
    response={204: None, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_attachment(request, attachment_id: UUID):
    """Delete an attachment. Only the author or project admin can delete."""
    attachment = IssueService.get_attachment_by_id(attachment_id)

    if not attachment:
        return 404, {"detail": "Вложение не найдено"}

    is_author = attachment.uploaded_by == request.auth
    is_admin = ProjectService.is_admin(attachment.issue.project, request.auth)

    if not is_author and not is_admin:
        return 403, {"detail": "Только автор или админ может удалить вложение"}

    IssueService.delete_attachment(attachment, user=request.auth)
    return 204, None
