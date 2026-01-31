"""
Comments API endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.issues.schemas import (
    CommentCreateSchema,
    CommentSchema,
    CommentUpdateSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


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
