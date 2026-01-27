"""
Boards API endpoints.
"""

from uuid import UUID

from ninja import Router

from apps.boards.schemas import (
    BoardCreateSchema,
    BoardDataSchema,
    BoardSchema,
    BoardUpdateSchema,
)
from apps.boards.services import BoardService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema, MessageSchema

router = Router(auth=AuthBearer())


# Project Boards endpoints


@router.get(
    "/projects/{key}/boards",
    response={200: list[BoardSchema], 403: ErrorSchema, 404: ErrorSchema},
)
def list_boards(request, key: str):
    """Get boards for project."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    if not ProjectService.is_member(project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    boards = BoardService.get_project_boards(project)
    return 200, list(boards)


@router.post(
    "/projects/{key}/boards",
    response={201: BoardSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def create_board(request, key: str, data: BoardCreateSchema):
    """Create a new board."""
    project = ProjectService.get_project_by_key(key)

    if not project:
        return 404, {"detail": "Проект не найден"}

    membership = ProjectService.get_user_membership(project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для создания досок"}

    board = BoardService.create_board(
        project=project,
        name=data.name,
        board_type=data.board_type,
        columns=data.columns,
        filters=data.filters,
        settings=data.settings,
        sprint_id=data.sprint_id,
    )

    return 201, board


# Board CRUD endpoints


@router.get(
    "/boards/{board_id}",
    response={200: BoardSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_board(request, board_id: UUID):
    """Get board by ID."""
    board = BoardService.get_board(board_id)

    if not board:
        return 404, {"detail": "Доска не найдена"}

    if not ProjectService.is_member(board.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    return 200, board


@router.patch(
    "/boards/{board_id}",
    response={200: BoardSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def update_board(request, board_id: UUID, data: BoardUpdateSchema):
    """Update board."""
    board = BoardService.get_board(board_id)

    if not board:
        return 404, {"detail": "Доска не найдена"}

    membership = ProjectService.get_user_membership(board.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.can_manage:
        return 403, {"detail": "Недостаточно прав для редактирования досок"}

    update_data = data.dict(exclude_unset=True)
    board = BoardService.update_board(board, **update_data)

    return 200, board


@router.delete(
    "/boards/{board_id}",
    response={200: MessageSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_board(request, board_id: UUID):
    """Delete board."""
    board = BoardService.get_board(board_id)

    if not board:
        return 404, {"detail": "Доска не найдена"}

    membership = ProjectService.get_user_membership(board.project, request.auth)
    if not membership:
        return 403, {"detail": "Нет доступа к проекту"}

    if not membership.is_admin:
        return 403, {"detail": "Только администратор может удалять доски"}

    # Check if this is the last board
    if board.project.boards.count() <= 1:
        return 400, {"detail": "Нельзя удалить единственную доску проекта"}

    BoardService.delete_board(board)

    return 200, {"message": "Доска удалена"}


# Board Issues endpoint


@router.get(
    "/boards/{board_id}/issues",
    response={200: BoardDataSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_board_issues(
    request,
    board_id: UUID,
    assignee_id: int | None = None,
    type_id: UUID | None = None,
    priority: str | None = None,
    search: str | None = None,
    sprint_id: str | None = None,
):
    """Get board data with issues grouped by columns.

    Optional filters:
    - assignee_id: Filter by assignee (use 0 for unassigned)
    - type_id: Filter by issue type
    - priority: Filter by priority (highest, high, medium, low, lowest)
    - search: Search in title (case-insensitive)
    - sprint_id: Filter by sprint ID (use "backlog" for issues without sprint)
    """
    board = BoardService.get_board(board_id)

    if not board:
        return 404, {"detail": "Доска не найдена"}

    if not ProjectService.is_member(board.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    # Build filters dict
    filters = {}
    if assignee_id is not None:
        filters["assignee_id"] = assignee_id if assignee_id != 0 else None
    if type_id:
        filters["type_id"] = type_id
    if priority:
        filters["priority"] = priority
    if search:
        filters["search"] = search
    if sprint_id:
        filters["sprint_id"] = sprint_id

    board_data = BoardService.get_board_data(board, filters=filters)

    return 200, board_data
