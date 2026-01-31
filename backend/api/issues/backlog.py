"""
Backlog API endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.issues.schemas import (
    BulkUpdateResultSchema,
    BulkUpdateSchema,
    IssueDetailSchema,
    IssueListSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


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
