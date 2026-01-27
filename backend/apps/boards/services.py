"""
Board service layer.
"""

from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.boards.models import Board
from apps.issues.models import Issue, Status
from apps.projects.models import Project


class BoardService:
    """Service for board operations."""

    @staticmethod
    def get_project_boards(project: Project) -> QuerySet[Board]:
        """Get all boards for a project."""
        return project.boards.all()

    @staticmethod
    def get_board(board_id: UUID) -> Board | None:
        """Get board by ID."""
        try:
            return Board.objects.select_related("project").get(id=board_id)
        except Board.DoesNotExist:
            return None

    @staticmethod
    def create_board(
        project: Project,
        name: str,
        board_type: str = "kanban",
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Board:
        """Create a new board."""
        # If no columns provided, use project's statuses
        if columns is None:
            statuses = Status.objects.filter(project__isnull=True).order_by("order")
            columns = [str(s.id) for s in statuses]

        return Board.objects.create(
            project=project,
            name=name,
            board_type=board_type,
            columns=columns or [],
            filters=filters or {},
            settings=settings or {},
        )

    @staticmethod
    def update_board(board: Board, **kwargs) -> Board:
        """Update board fields."""
        for key, value in kwargs.items():
            if hasattr(board, key):
                setattr(board, key, value)
        board.save()
        return board

    @staticmethod
    def delete_board(board: Board) -> None:
        """Delete board."""
        board.delete()

    @staticmethod
    def get_board_data(board: Board) -> dict:
        """Get board data with issues grouped by columns."""

        columns_data = []

        # Get all statuses for columns
        status_ids = [UUID(sid) for sid in board.columns if sid]
        statuses = {s.id: s for s in Status.objects.filter(id__in=status_ids)}

        # Get all issues for the project
        issues = (
            Issue.objects.filter(project=board.project)
            .select_related("issue_type", "status", "assignee", "reporter")
            .order_by("-created_at")
        )

        # Apply board filters if any
        if board.filters:
            if "issue_type_ids" in board.filters:
                issues = issues.filter(
                    issue_type_id__in=board.filters["issue_type_ids"]
                )
            if "assignee_ids" in board.filters:
                issues = issues.filter(assignee_id__in=board.filters["assignee_ids"])

        # Group issues by status
        issues_by_status: dict[UUID, list] = {sid: [] for sid in status_ids}
        for issue in issues:
            if issue.status_id in issues_by_status:
                issues_by_status[issue.status_id].append(issue)

        # Build columns data
        for status_id in status_ids:
            status = statuses.get(status_id)
            if status:
                column_issues = issues_by_status.get(status_id, [])
                columns_data.append(
                    {
                        "status": status,
                        "issues": column_issues,
                        "count": len(column_issues),
                    }
                )

        return {
            "board": board,
            "columns": columns_data,
        }

    @staticmethod
    def create_default_board(project: Project) -> Board:
        """Create default board for a new project."""
        return Board.create_default_board(project)
