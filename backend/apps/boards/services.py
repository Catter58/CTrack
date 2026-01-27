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
        sprint_id: UUID | None = None,
    ) -> Board:
        """Create a new board."""
        from apps.boards.models import BoardType
        from apps.sprints.models import Sprint, SprintStatus

        # If no columns provided, use project's statuses
        if columns is None:
            statuses = Status.objects.filter(project__isnull=True).order_by("order")
            columns = [str(s.id) for s in statuses]

        # For scrum boards, assign active sprint if not provided
        sprint = None
        if board_type == BoardType.SCRUM:
            if sprint_id:
                sprint = Sprint.objects.filter(id=sprint_id, project=project).first()
            else:
                sprint = project.sprints.filter(status=SprintStatus.ACTIVE).first()

        return Board.objects.create(
            project=project,
            name=name,
            board_type=board_type,
            columns=columns or [],
            filters=filters or {},
            settings=settings or {},
            sprint=sprint,
        )

    @staticmethod
    def update_board(board: Board, **kwargs) -> Board:
        """Update board fields."""
        from apps.sprints.models import Sprint

        # Handle sprint_id specially
        if "sprint_id" in kwargs:
            sprint_id = kwargs.pop("sprint_id")
            if sprint_id:
                board.sprint = Sprint.objects.filter(
                    id=sprint_id, project=board.project
                ).first()
            else:
                board.sprint = None

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
    def get_board_data(board: Board, filters: dict | None = None) -> dict:
        """Get board data with issues grouped by columns.

        Args:
            board: The board to get data for
            filters: Optional dict with filters:
                - assignee_id: Filter by assignee ID (None for unassigned)
                - type_id: Filter by issue type ID
                - priority: Filter by priority string
                - search: Search in issue title
                - sprint_id: Filter by sprint ID ("backlog" for no sprint)
        """
        from apps.boards.models import BoardType
        from apps.sprints.models import SprintStatus

        columns_data = []
        filters = filters or {}

        # Get all statuses for columns
        status_ids = [UUID(sid) for sid in board.columns if sid]
        statuses = {s.id: s for s in Status.objects.filter(id__in=status_ids)}

        # Get all issues for the project
        issues = (
            Issue.objects.filter(project=board.project)
            .select_related("issue_type", "status", "assignee", "reporter")
            .order_by("-created_at")
        )

        # Check if sprint filter is explicitly specified
        sprint_filter = filters.get("sprint_id")

        if sprint_filter:
            # Explicit sprint filter overrides default behavior
            if sprint_filter == "backlog":
                issues = issues.filter(sprint__isnull=True)
            else:
                issues = issues.filter(sprint_id=sprint_filter)
        elif board.board_type == BoardType.SCRUM:
            # Default scrum board behavior - filter by active sprint
            if board.sprint:
                issues = issues.filter(sprint=board.sprint)
            else:
                # If no sprint assigned, try to get active sprint
                active_sprint = board.project.sprints.filter(
                    status=SprintStatus.ACTIVE
                ).first()
                if active_sprint:
                    issues = issues.filter(sprint=active_sprint)
                else:
                    # No active sprint - show no issues
                    issues = issues.none()

        # Apply board filters if any
        if board.filters:
            if "issue_type_ids" in board.filters:
                issues = issues.filter(
                    issue_type_id__in=board.filters["issue_type_ids"]
                )
            if "assignee_ids" in board.filters:
                issues = issues.filter(assignee_id__in=board.filters["assignee_ids"])

        # Apply request filters
        if "assignee_id" in filters:
            assignee_id = filters["assignee_id"]
            if assignee_id is None:
                issues = issues.filter(assignee__isnull=True)
            else:
                issues = issues.filter(assignee_id=assignee_id)

        if "type_id" in filters:
            issues = issues.filter(issue_type_id=filters["type_id"])

        if "priority" in filters:
            issues = issues.filter(priority=filters["priority"])

        if "search" in filters:
            search_term = filters["search"]
            issues = issues.filter(title__icontains=search_term)

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
