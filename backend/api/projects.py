"""
Projects API endpoints.
"""

from uuid import UUID

from django.db.models import Count, Q
from ninja import Router

from apps.issues.models import Issue, Status, WorkflowTransition
from apps.issues.schemas import (
    IssueListSchema,
    WorkflowTransitionCreateSchema,
    WorkflowTransitionSchema,
)
from apps.issues.services import IssueService
from apps.projects.models import Project, ProjectMembership, ProjectRole, SortOrder
from apps.projects.schemas import (
    MemberAddSchema,
    MembershipSchema,
    MemberUpdateSchema,
    PaginatedIssueListSchema,
    ProjectCreateSchema,
    ProjectListSchema,
    ProjectSchema,
    ProjectUpdateSchema,
    ProjectWithOwnerSchema,
    SavedFilterCreateSchema,
    SavedFilterSchema,
    SavedFilterUpdateSchema,
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


@router.post(
    "/{key}/workflow",
    response={
        201: WorkflowTransitionSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def create_workflow_transition(request, key: str, data: WorkflowTransitionCreateSchema):
    """Create a new workflow transition for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    membership = ProjectService.get_user_membership(project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для управления workflow"}

    if not Status.objects.filter(id=data.from_status_id).exists():
        return 400, {"detail": "Исходный статус не найден"}

    if not Status.objects.filter(id=data.to_status_id).exists():
        return 400, {"detail": "Целевой статус не найден"}

    if WorkflowTransition.objects.filter(
        project=project,
        from_status_id=data.from_status_id,
        to_status_id=data.to_status_id,
    ).exists():
        return 400, {"detail": "Такой переход уже существует"}

    transition = IssueService.create_workflow_transition(
        project=project,
        from_status_id=data.from_status_id,
        to_status_id=data.to_status_id,
        name=data.name,
        allowed_roles=data.allowed_roles,
    )

    return 201, transition


# Saved Filters endpoints


@router.get(
    "/{key}/filters",
    response={200: list[SavedFilterSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_saved_filters(request, key: str):
    """Get saved filters for project (own + shared)."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    filters = ProjectService.get_saved_filters(project, request.auth)
    return 200, list(filters)


@router.post(
    "/{key}/filters",
    response={
        201: SavedFilterSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def create_saved_filter(request, key: str, data: SavedFilterCreateSchema):
    """Create a new saved filter."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    if data.sort_order and data.sort_order not in [c.value for c in SortOrder]:
        return 400, {"detail": "Недопустимый порядок сортировки"}

    saved_filter = ProjectService.create_saved_filter(
        project=project,
        user=request.auth,
        name=data.name,
        filters=data.filters,
        columns=data.columns,
        sort_by=data.sort_by,
        sort_order=data.sort_order,
        is_shared=data.is_shared,
    )

    return 201, saved_filter


@router.get(
    "/filters/{filter_id}",
    response={200: SavedFilterSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_saved_filter(request, filter_id: UUID):
    """Get saved filter by ID."""
    saved_filter = ProjectService.get_saved_filter_by_id(filter_id)

    if not saved_filter:
        return 404, {"detail": "Фильтр не найден"}

    if not ProjectService.is_member(saved_filter.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    if saved_filter.user != request.auth and not saved_filter.is_shared:
        return 403, {"detail": "Нет доступа к фильтру"}

    return 200, saved_filter


@router.patch(
    "/filters/{filter_id}",
    response={
        200: SavedFilterSchema,
        400: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_saved_filter(request, filter_id: UUID, data: SavedFilterUpdateSchema):
    """Update saved filter (owner only)."""
    saved_filter = ProjectService.get_saved_filter_by_id(filter_id)

    if not saved_filter:
        return 404, {"detail": "Фильтр не найден"}

    if saved_filter.user != request.auth:
        return 403, {"detail": "Только автор может редактировать фильтр"}

    if data.sort_order and data.sort_order not in [c.value for c in SortOrder]:
        return 400, {"detail": "Недопустимый порядок сортировки"}

    update_data = data.dict(exclude_unset=True)
    saved_filter = ProjectService.update_saved_filter(saved_filter, **update_data)

    return 200, saved_filter


@router.delete(
    "/filters/{filter_id}",
    response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_saved_filter(request, filter_id: UUID):
    """Delete saved filter (owner only)."""
    saved_filter = ProjectService.get_saved_filter_by_id(filter_id)

    if not saved_filter:
        return 404, {"detail": "Фильтр не найден"}

    if saved_filter.user != request.auth:
        return 403, {"detail": "Только автор может удалить фильтр"}

    ProjectService.delete_saved_filter(saved_filter)

    return 200, {"message": "Фильтр удалён"}


@router.get(
    "/filters/{filter_id}/issues",
    response={200: PaginatedIssueListSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_filter_issues(
    request,
    filter_id: UUID,
    limit: int = 50,
    offset: int = 0,
):
    """Get issues matching saved filter criteria."""
    # Validate and cap limit
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    saved_filter = ProjectService.get_saved_filter_by_id(filter_id)

    if not saved_filter:
        return 404, {"detail": "Фильтр не найден"}

    if not ProjectService.is_member(saved_filter.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    if saved_filter.user != request.auth and not saved_filter.is_shared:
        return 403, {"detail": "Нет доступа к фильтру"}

    queryset = Issue.objects.filter(project=saved_filter.project).select_related(
        "issue_type", "status", "assignee", "reporter"
    )

    filters = saved_filter.filters or {}
    if filters.get("status_id"):
        queryset = queryset.filter(status_id=filters["status_id"])
    if filters.get("issue_type_id"):
        queryset = queryset.filter(issue_type_id=filters["issue_type_id"])
    if filters.get("assignee_id"):
        queryset = queryset.filter(assignee_id=filters["assignee_id"])
    if filters.get("priority"):
        queryset = queryset.filter(priority=filters["priority"])
    if filters.get("epic_id"):
        queryset = queryset.filter(epic_id=filters["epic_id"])
    if filters.get("search"):
        search = filters["search"]
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(key__icontains=search)
        )

    total = queryset.count()

    if saved_filter.sort_by:
        order_prefix = "-" if saved_filter.sort_order == SortOrder.DESC else ""
        queryset = queryset.order_by(f"{order_prefix}{saved_filter.sort_by}")
    else:
        queryset = queryset.order_by("-created_at")

    issues = list(queryset[offset : offset + limit])

    return 200, {
        "items": [IssueListSchema.from_orm(issue) for issue in issues],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
