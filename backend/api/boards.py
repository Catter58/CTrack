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
def get_board_issues(request, board_id: UUID):
    """Get board data with issues grouped by columns."""
    board = BoardService.get_board(board_id)

    if not board:
        return 404, {"detail": "Доска не найдена"}

    if not ProjectService.is_member(board.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    board_data = BoardService.get_board_data(board)

    return 200, board_data
