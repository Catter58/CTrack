"""Tests for Sprint Board functionality."""

from datetime import date, timedelta

import pytest

from apps.boards.models import Board, BoardType
from apps.boards.services import BoardService
from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
from apps.users.models import User


@pytest.fixture
def project(db, user: User):
    project = Project.objects.create(
        name="Test Project",
        key="TST",
        owner=user,
    )
    ProjectMembership.objects.create(
        project=project,
        user=user,
        role=ProjectRole.ADMIN,
    )
    return project


@pytest.fixture
def issue_type(db, project: Project):
    return IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#0066cc",
    )


@pytest.fixture
def status_todo(db, project: Project):
    return Status.objects.create(
        project=project,
        name="To Do",
        category=StatusCategory.TODO,
        color="#808080",
    )


@pytest.fixture
def status_done(db, project: Project):
    return Status.objects.create(
        project=project,
        name="Done",
        category=StatusCategory.DONE,
        color="#00cc66",
    )


@pytest.fixture
def active_sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Active Sprint",
        start_date=date.today() - timedelta(days=7),
        end_date=date.today() + timedelta(days=7),
        status=SprintStatus.ACTIVE,
    )


@pytest.fixture
def planned_sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Planned Sprint",
        start_date=date.today() + timedelta(days=14),
        end_date=date.today() + timedelta(days=28),
        status=SprintStatus.PLANNED,
    )


@pytest.mark.django_db
class TestScrumBoard:
    def test_create_scrum_board_assigns_active_sprint(
        self,
        project: Project,
        active_sprint: Sprint,
        status_todo: Status,
    ):
        """Scrum board auto-assigns active sprint if not provided."""
        board = BoardService.create_board(
            project=project,
            name="Sprint Board",
            board_type=BoardType.SCRUM,
            columns=[str(status_todo.id)],
        )

        assert board.board_type == BoardType.SCRUM
        assert board.sprint == active_sprint

    def test_create_scrum_board_with_specific_sprint(
        self,
        project: Project,
        active_sprint: Sprint,
        planned_sprint: Sprint,
        status_todo: Status,
    ):
        """Scrum board can be created with specific sprint."""
        board = BoardService.create_board(
            project=project,
            name="Sprint Board",
            board_type=BoardType.SCRUM,
            columns=[str(status_todo.id)],
            sprint_id=planned_sprint.id,
        )

        assert board.sprint == planned_sprint

    def test_scrum_board_filters_by_sprint(
        self,
        project: Project,
        active_sprint: Sprint,
        planned_sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        """Scrum board only shows issues from its sprint."""
        # Create issues in different sprints
        issue_in_active = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Active Sprint Issue",
            status=status_todo,
            reporter=user,
            sprint=active_sprint,
        )
        issue_in_planned = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Planned Sprint Issue",
            status=status_todo,
            reporter=user,
            sprint=planned_sprint,
        )
        issue_no_sprint = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Backlog Issue",
            status=status_todo,
            reporter=user,
            sprint=None,
        )

        # Create scrum board with active sprint
        board = Board.objects.create(
            project=project,
            name="Sprint Board",
            board_type=BoardType.SCRUM,
            columns=[str(status_todo.id)],
            sprint=active_sprint,
        )

        board_data = BoardService.get_board_data(board)
        all_issues = []
        for col in board_data["columns"]:
            all_issues.extend(col["issues"])

        issue_keys = [i.key for i in all_issues]
        assert issue_in_active.key in issue_keys
        assert issue_in_planned.key not in issue_keys
        assert issue_no_sprint.key not in issue_keys

    def test_scrum_board_without_sprint_uses_active(
        self,
        project: Project,
        active_sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        """Scrum board without sprint falls back to active sprint."""
        issue = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Sprint Issue",
            status=status_todo,
            reporter=user,
            sprint=active_sprint,
        )

        # Create scrum board without sprint
        board = Board.objects.create(
            project=project,
            name="Sprint Board",
            board_type=BoardType.SCRUM,
            columns=[str(status_todo.id)],
            sprint=None,
        )

        board_data = BoardService.get_board_data(board)
        all_issues = []
        for col in board_data["columns"]:
            all_issues.extend(col["issues"])

        assert len(all_issues) == 1
        assert all_issues[0].key == issue.key

    def test_scrum_board_no_active_sprint_shows_nothing(
        self,
        project: Project,
        planned_sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        """Scrum board with no active sprint shows no issues."""
        Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Planned Sprint Issue",
            status=status_todo,
            reporter=user,
            sprint=planned_sprint,
        )

        # Create scrum board without active sprint
        board = Board.objects.create(
            project=project,
            name="Sprint Board",
            board_type=BoardType.SCRUM,
            columns=[str(status_todo.id)],
            sprint=None,
        )

        board_data = BoardService.get_board_data(board)
        all_issues = []
        for col in board_data["columns"]:
            all_issues.extend(col["issues"])

        assert len(all_issues) == 0

    def test_kanban_board_shows_all_issues(
        self,
        project: Project,
        active_sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        """Kanban board shows all issues regardless of sprint."""
        issue_with_sprint = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Sprint Issue",
            status=status_todo,
            reporter=user,
            sprint=active_sprint,
        )
        issue_no_sprint = Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Backlog Issue",
            status=status_todo,
            reporter=user,
            sprint=None,
        )

        # Create kanban board
        board = Board.objects.create(
            project=project,
            name="Kanban Board",
            board_type=BoardType.KANBAN,
            columns=[str(status_todo.id)],
        )

        board_data = BoardService.get_board_data(board)
        all_issues = []
        for col in board_data["columns"]:
            all_issues.extend(col["issues"])

        issue_keys = [i.key for i in all_issues]
        assert issue_with_sprint.key in issue_keys
        assert issue_no_sprint.key in issue_keys
