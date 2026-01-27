from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.projects.models import Project, ProjectMembership
from apps.sprints.models import Sprint
from apps.sprints.schemas import (
    BurndownSchema,
    SprintCompleteSchema,
    SprintCreateSchema,
    SprintSchema,
    SprintUpdateSchema,
    SprintWithStatsSchema,
    VelocitySchema,
)
from apps.sprints.services import SprintService, SprintServiceError
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


def get_project_for_user(project_key: str, user) -> Project:
    project = get_object_or_404(Project, key=project_key.upper())
    if not ProjectMembership.objects.filter(project=project, user=user).exists():
        raise Project.DoesNotExist
    return project


@router.post(
    "/projects/{project_key}/sprints",
    response={201: SprintSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def create_sprint(request, project_key: str, data: SprintCreateSchema):
    try:
        project = get_project_for_user(project_key, request.auth)
    except Project.DoesNotExist:
        return 404, {"detail": "Проект не найден"}

    try:
        sprint = SprintService.create_sprint(
            project=project,
            name=data.name,
            goal=data.goal,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        return 201, sprint
    except SprintServiceError as e:
        return 400, {"detail": str(e)}


@router.get(
    "/projects/{project_key}/sprints",
    response={200: list[SprintSchema], 404: ErrorSchema},
)
def list_sprints(request, project_key: str, status: str | None = None):
    try:
        project = get_project_for_user(project_key, request.auth)
    except Project.DoesNotExist:
        return 404, {"detail": "Проект не найден"}

    sprints = SprintService.get_sprints(project, status=status)
    return 200, sprints


@router.get(
    "/sprints/{sprint_id}",
    response={200: SprintWithStatsSchema, 404: ErrorSchema},
)
def get_sprint(request, sprint_id: UUID):
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    stats = SprintService.get_sprint_stats(sprint)
    return 200, {
        "id": sprint.id,
        "project_id": sprint.project_id,
        "name": sprint.name,
        "goal": sprint.goal,
        "start_date": sprint.start_date,
        "end_date": sprint.end_date,
        "status": sprint.status,
        "initial_story_points": sprint.initial_story_points,
        "completed_story_points": sprint.completed_story_points,
        "created_at": sprint.created_at,
        "updated_at": sprint.updated_at,
        **stats,
    }


@router.patch(
    "/sprints/{sprint_id}",
    response={200: SprintSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def update_sprint(request, sprint_id: UUID, data: SprintUpdateSchema):
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    try:
        sprint = SprintService.update_sprint(
            sprint=sprint,
            name=data.name,
            goal=data.goal,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        return 200, sprint
    except SprintServiceError as e:
        return 400, {"detail": str(e)}


@router.delete(
    "/sprints/{sprint_id}",
    response={200: MessageSchema, 404: ErrorSchema},
)
def delete_sprint(request, sprint_id: UUID):
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    SprintService.delete_sprint(sprint)
    return 200, {"message": "Спринт удалён"}


@router.post(
    "/sprints/{sprint_id}/start",
    response={200: SprintSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def start_sprint(request, sprint_id: UUID):
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    try:
        sprint = SprintService.start_sprint(sprint)
        return 200, sprint
    except SprintServiceError as e:
        return 400, {"detail": str(e)}


@router.post(
    "/sprints/{sprint_id}/complete",
    response={200: SprintSchema, 400: ErrorSchema, 404: ErrorSchema},
)
def complete_sprint(request, sprint_id: UUID, data: SprintCompleteSchema):
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    try:
        sprint = SprintService.complete_sprint(
            sprint=sprint,
            move_incomplete_to=data.move_incomplete_to,
        )
        return 200, sprint
    except SprintServiceError as e:
        return 400, {"detail": str(e)}


@router.get(
    "/sprints/{sprint_id}/issues",
    response={200: list, 404: ErrorSchema},
)
def get_sprint_issues(request, sprint_id: UUID):
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    issues = SprintService.get_sprint_issues(sprint)
    return 200, [
        {
            "id": str(issue.id),
            "key": issue.key,
            "title": issue.title,
            "status": {
                "id": str(issue.status.id),
                "name": issue.status.name,
                "category": issue.status.category,
                "color": issue.status.color,
            },
            "issue_type": {
                "id": str(issue.issue_type.id),
                "name": issue.issue_type.name,
                "icon": issue.issue_type.icon,
                "color": issue.issue_type.color,
            },
            "assignee": (
                {
                    "id": issue.assignee.id,
                    "username": issue.assignee.username,
                    "full_name": issue.assignee.get_full_name(),
                }
                if issue.assignee
                else None
            ),
            "story_points": issue.story_points,
            "priority": issue.priority,
        }
        for issue in issues
    ]


@router.get(
    "/projects/{project_key}/metrics/velocity",
    response={200: VelocitySchema, 404: ErrorSchema},
)
def get_velocity(request, project_key: str, limit: int = 6):
    """Get velocity metrics for the last N completed sprints."""
    try:
        project = get_project_for_user(project_key, request.auth)
    except Project.DoesNotExist:
        return 404, {"detail": "Проект не найден"}

    velocity_data = SprintService.get_velocity(project, limit=limit)
    return 200, velocity_data


@router.get(
    "/sprints/{sprint_id}/burndown",
    response={200: BurndownSchema, 404: ErrorSchema},
)
def get_burndown(request, sprint_id: UUID):
    """Get burndown chart data for a sprint."""
    try:
        sprint = SprintService.get_sprint(sprint_id)
    except Sprint.DoesNotExist:
        return 404, {"detail": "Спринт не найден"}

    if not ProjectMembership.objects.filter(
        project=sprint.project, user=request.auth
    ).exists():
        return 404, {"detail": "Спринт не найден"}

    burndown_data = SprintService.get_burndown(sprint)
    return 200, burndown_data
