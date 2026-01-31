"""
Workflow API endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.issues.schemas import (
    IssueDetailSchema,
    WorkflowTransitionSchema,
    WorkflowTransitionUpdateSchema,
)
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


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
