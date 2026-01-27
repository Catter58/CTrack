"""
Projects API endpoints.
"""

from django.db.models import Count
from ninja import Router

from apps.issues.models import WorkflowTransition
from apps.issues.schemas import WorkflowTransitionSchema
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.projects.schemas import (
    MemberAddSchema,
    MembershipSchema,
    MemberUpdateSchema,
    ProjectCreateSchema,
    ProjectListSchema,
    ProjectSchema,
    ProjectUpdateSchema,
    ProjectWithOwnerSchema,
)
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.models import User
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


@router.post("", response={201: ProjectSchema, 400: ErrorSchema})
def create_project(request, data: ProjectCreateSchema):
    """Create a new project."""
    # Validate key format
    if not data.key.isalnum() or len(data.key) > 10:
        return 400, {
            "detail": "Ключ должен содержать только буквы и цифры (макс. 10 символов)"
        }

    # Check key uniqueness
    if Project.objects.filter(key=data.key.upper()).exists():
        return 400, {"detail": f"Проект с ключом {data.key.upper()} уже существует"}

    project = ProjectService.create_project(
        user=request.auth,
        key=data.key,
        name=data.name,
        description=data.description,
        settings=data.settings,
    )

    return 201, project


@router.get("", response=list[ProjectListSchema])
def list_projects(request, include_archived: bool = False):
    """Get all projects for current user."""
    user = request.auth
    projects = ProjectService.get_user_projects(user, include_archived)

    # Annotate with member count
    projects = projects.annotate(member_count=Count("memberships"))

    result = []
    for project in projects:
        membership = ProjectService.get_user_membership(project, user)
        result.append(
            ProjectListSchema(
                id=project.id,
                key=project.key,
                name=project.name,
                description=project.description,
                is_archived=project.is_archived,
                created_at=project.created_at,
                member_count=project.member_count,
                my_role=membership.role if membership else None,
            )
        )

    return result


@router.get(
    "/{key}", response={200: ProjectWithOwnerSchema, 403: ErrorSchema, 404: ErrorSchema}
)
def get_project(request, key: str):
    """Get project by key."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    return 200, project


@router.patch(
    "/{key}", response={200: ProjectSchema, 403: ErrorSchema, 404: ErrorSchema}
)
def update_project(request, key: str, data: ProjectUpdateSchema):
    """Update project details."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.can_manage_project(project, request.auth):
        return 403, {"detail": "Недостаточно прав для редактирования проекта"}

    # Handle archive/unarchive
    if data.is_archived is not None:
        if not ProjectService.can_manage_members(project, request.auth):
            return 403, {"detail": "Только администратор может изменять статус архива"}
        if data.is_archived:
            ProjectService.archive_project(project)
        else:
            ProjectService.unarchive_project(project)
        # Reload project after archive status change
        project = ProjectService.get_project_by_key(key)

    project = ProjectService.update_project(
        project,
        name=data.name,
        description=data.description,
        settings=data.settings,
    )

    return 200, project


@router.delete(
    "/{key}", response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema}
)
def archive_or_delete_project(request, key: str, permanent: bool = False):
    """Archive a project (soft delete) or permanently delete it."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.can_manage_members(project, request.auth):
        return 403, {"detail": "Только администратор может архивировать/удалять проект"}

    if permanent:
        # Only allow permanent deletion of archived projects
        if not project.is_archived:
            return 403, {"detail": "Сначала нужно архивировать проект"}
        ProjectService.delete_project_permanently(project)
        return 200, {"message": "Проект удалён навсегда"}
    else:
        ProjectService.archive_project(project)
        return 200, {"message": "Проект архивирован"}


# Members endpoints


@router.get(
    "/{key}/members",
    response={200: list[MembershipSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_members(request, key: str):
    """Get project members."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    members = ProjectService.get_members(project)
    return 200, list(members)


@router.post(
    "/{key}/members",
    response={
        201: MembershipSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def add_member(request, key: str, data: MemberAddSchema):
    """Add a member to project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.can_manage_members(project, request.auth):
        return 403, {"detail": "Только администратор может добавлять участников"}

    # Validate role
    if data.role not in [r.value for r in ProjectRole]:
        return 400, {"detail": "Некорректная роль"}

    # Get user to add
    user = User.objects.filter(id=data.user_id, is_active=True).first()
    if not user:
        return 400, {"detail": "Пользователь не найден"}

    membership = ProjectService.add_member(project, user, data.role)
    return 201, membership


@router.patch(
    "/{key}/members/{user_id}",
    response={
        200: MembershipSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_member_role(request, key: str, user_id: int, data: MemberUpdateSchema):
    """Update member's role."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.can_manage_members(project, request.auth):
        return 403, {"detail": "Только администратор может изменять роли"}

    # Validate role
    if data.role not in [r.value for r in ProjectRole]:
        return 400, {"detail": "Некорректная роль"}

    # Cannot change owner's role
    if project.owner_id == user_id:
        return 400, {"detail": "Нельзя изменить роль владельца проекта"}

    user = User.objects.filter(id=user_id).first()
    if not user:
        return 404, {"detail": "Пользователь не найден"}

    membership = ProjectService.change_member_role(project, user, data.role)
    if not membership:
        return 404, {"detail": "Пользователь не является участником проекта"}

    return 200, membership


@router.delete(
    "/{key}/members/{user_id}",
    response={200: MessageSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def remove_member(request, key: str, user_id: int):
    """Remove member from project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.can_manage_members(project, request.auth):
        return 403, {"detail": "Только администратор может удалять участников"}

    # Cannot remove owner
    if project.owner_id == user_id:
        return 400, {"detail": "Нельзя удалить владельца проекта"}

    # Cannot remove yourself if you're the only admin
    if request.auth.id == user_id:
        admin_count = ProjectMembership.objects.filter(
            project=project, role=ProjectRole.ADMIN
        ).count()
        if admin_count <= 1:
            return 400, {"detail": "Нельзя удалить единственного администратора"}

    user = User.objects.filter(id=user_id).first()
    if not user:
        return 404, {"detail": "Пользователь не найден"}

    removed = ProjectService.remove_member(project, user)
    if not removed:
        return 404, {"detail": "Пользователь не является участником проекта"}

    return 200, {"message": "Участник удалён"}


# Workflow endpoints


@router.get(
    "/{key}/workflow",
    response={200: list[WorkflowTransitionSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def get_project_workflow(request, key: str):
    """Get all workflow transitions for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    transitions = (
        WorkflowTransition.objects.filter(project=project)
        .select_related("from_status", "to_status")
        .order_by("from_status__order", "to_status__order")
    )

    return 200, list(transitions)
