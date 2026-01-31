"""
Epics API endpoints.
"""

from ninja import Router

from apps.issues.schemas import EpicSchema
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


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
