"""
Attachments API endpoints.
"""

from uuid import UUID

from django.http import FileResponse
from ninja import Router
from ninja.files import UploadedFile

from apps.issues.schemas import AttachmentSchema
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())

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
