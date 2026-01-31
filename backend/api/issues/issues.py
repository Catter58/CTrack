"""
Issues CRUD API endpoints.
"""

from datetime import date
from types import SimpleNamespace
from uuid import UUID

from ninja import Router

from apps.issues.models import IssueType, Status
from apps.issues.schemas import (
    GlobalIssuePaginatedResponseSchema,
    IssueCreateSchema,
    IssueDetailSchema,
    IssueListSchema,
    IssuePaginatedResponseSchema,
    IssueUpdateSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


# Issues CRUD endpoints


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
