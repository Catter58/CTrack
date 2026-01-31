"""
Activity API endpoints.
"""

from ninja import Router

from apps.issues.schemas import ActivitySchema
from apps.issues.services import ActivityService, IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

router = Router(auth=AuthBearer())


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
