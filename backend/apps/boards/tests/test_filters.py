"""Tests for board filter functionality."""

import pytest

from apps.boards.models import Board, BoardType
from apps.boards.services import BoardService
from apps.issues.models import Issue, IssueType, Priority, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.users.models import User


@pytest.fixture
def project(db, user) -> Project:
    project = Project.objects.create(
        name="Test Project",
        key="TEST",
        owner=user,
    )
    ProjectMembership.objects.create(
        project=project,
        user=user,
        role=ProjectRole.ADMIN,
    )
    return project


@pytest.fixture
def statuses(db, project) -> dict:
    todo = Status.objects.create(
        project=project,
        name="To Do",
        category=StatusCategory.TODO,
        color="#808080",
        order=0,
    )
    in_progress = Status.objects.create(
        project=project,
        name="In Progress",
        category=StatusCategory.IN_PROGRESS,
        color="#0066cc",
        order=1,
    )
    done = Status.objects.create(
        project=project,
        name="Done",
        category=StatusCategory.DONE,
        color="#00cc00",
        order=2,
    )
    return {"todo": todo, "in_progress": in_progress, "done": done}


@pytest.fixture
def issue_types(db, project) -> dict:
    task = IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#0066cc",
    )
    bug = IssueType.objects.create(
        project=project,
        name="Bug",
        icon="bug",
        color="#ff0000",
    )
    return {"task": task, "bug": bug}


@pytest.fixture
def board(db, project, statuses) -> Board:
    return Board.objects.create(
        project=project,
        name="Test Board",
        board_type=BoardType.KANBAN,
        columns=[
            str(statuses["todo"].id),
            str(statuses["in_progress"].id),
            str(statuses["done"].id),
        ],
    )


@pytest.fixture
def assignee(db) -> User:
    return User.objects.create_user(
        username="assignee",
        email="assignee@example.com",
        password="testpass123",
    )


@pytest.fixture
def issues(db, project, statuses, issue_types, user, assignee) -> list[Issue]:
    """Create a set of issues for testing filters."""
    return [
        Issue.objects.create(
            project=project,
            title="Task 1 - High Priority",
            issue_type=issue_types["task"],
            status=statuses["todo"],
            reporter=user,
            assignee=assignee,
            priority=Priority.HIGH,
        ),
        Issue.objects.create(
            project=project,
            title="Bug 1 - Critical",
            issue_type=issue_types["bug"],
            status=statuses["todo"],
            reporter=user,
            assignee=None,
            priority=Priority.HIGHEST,
        ),
        Issue.objects.create(
            project=project,
            title="Task 2 - Medium",
            issue_type=issue_types["task"],
            status=statuses["in_progress"],
            reporter=user,
            assignee=user,
            priority=Priority.MEDIUM,
        ),
        Issue.objects.create(
            project=project,
            title="Bug 2 - Low",
            issue_type=issue_types["bug"],
            status=statuses["done"],
            reporter=user,
            assignee=assignee,
            priority=Priority.LOW,
        ),
    ]


@pytest.mark.django_db
class TestBoardFilters:
    def test_no_filters_returns_all_issues(self, board, issues):
        """Test that without filters, all issues are returned."""
        data = BoardService.get_board_data(board)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 4

    def test_filter_by_assignee(self, board, issues, assignee):
        """Test filtering by specific assignee."""
        filters = {"assignee_id": assignee.id}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 2  # Task 1 and Bug 2

    def test_filter_by_unassigned(self, board, issues):
        """Test filtering by unassigned (assignee_id=None)."""
        filters = {"assignee_id": None}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 1  # Bug 1

    def test_filter_by_issue_type(self, board, issues, issue_types):
        """Test filtering by issue type."""
        filters = {"type_id": issue_types["bug"].id}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 2  # Bug 1 and Bug 2

    def test_filter_by_priority(self, board, issues):
        """Test filtering by priority."""
        filters = {"priority": Priority.HIGH}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 1  # Task 1

    def test_filter_by_search(self, board, issues):
        """Test filtering by search term."""
        filters = {"search": "Bug"}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 2  # Bug 1 and Bug 2

    def test_filter_search_case_insensitive(self, board, issues):
        """Test that search is case-insensitive."""
        filters = {"search": "bug"}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 2

    def test_multiple_filters_combined(self, board, issues, issue_types, assignee):
        """Test that multiple filters are combined with AND logic."""
        filters = {
            "type_id": issue_types["bug"].id,
            "assignee_id": assignee.id,
        }
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 1  # Only Bug 2 (bug + assignee)

    def test_filter_no_matches(self, board, issues):
        """Test filters that match no issues."""
        filters = {"search": "nonexistent"}
        data = BoardService.get_board_data(board, filters=filters)

        total_issues = sum(col["count"] for col in data["columns"])
        assert total_issues == 0


@pytest.mark.django_db
class TestBoardFiltersAPI:
    def test_get_board_issues_with_filters(
        self, api_client, auth_headers, board, issues, issue_types, user, project
    ):
        """Test API endpoint with filters."""
        # Add user as project member
        ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={"role": ProjectRole.ADMIN}
        )

        # Filter by issue type
        response = api_client.get(
            f"/api/boards/{board.id}/issues?type_id={issue_types['bug'].id}",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        total = sum(col["count"] for col in data["columns"])
        assert total == 2

    def test_get_board_issues_with_search(
        self, api_client, auth_headers, board, issues, user, project
    ):
        """Test API search filter."""
        ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={"role": ProjectRole.ADMIN}
        )

        response = api_client.get(
            f"/api/boards/{board.id}/issues?search=Task",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        total = sum(col["count"] for col in data["columns"])
        assert total == 2  # Task 1 and Task 2

    def test_get_board_issues_with_priority(
        self, api_client, auth_headers, board, issues, user, project
    ):
        """Test API priority filter."""
        ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={"role": ProjectRole.ADMIN}
        )

        response = api_client.get(
            f"/api/boards/{board.id}/issues?priority=highest",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        total = sum(col["count"] for col in data["columns"])
        assert total == 1  # Bug 1 - Critical

    def test_get_board_issues_unassigned(
        self, api_client, auth_headers, board, issues, user, project
    ):
        """Test API filter for unassigned issues."""
        ProjectMembership.objects.get_or_create(
            project=project, user=user, defaults={"role": ProjectRole.ADMIN}
        )

        response = api_client.get(
            f"/api/boards/{board.id}/issues?assignee_id=0",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        total = sum(col["count"] for col in data["columns"])
        assert total == 1  # Bug 1 (unassigned)
