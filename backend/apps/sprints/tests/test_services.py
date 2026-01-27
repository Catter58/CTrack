from datetime import date, timedelta

import pytest

from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
from apps.sprints.services import SprintService, SprintServiceError
from apps.users.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def project(db, user: User):
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
        color="#00cc00",
    )


@pytest.fixture
def sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Sprint 1",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=14),
        status=SprintStatus.PLANNED,
    )


class TestSprintServiceCreate:
    def test_create_sprint(self, project: Project):
        sprint = SprintService.create_sprint(
            project=project,
            name="Sprint 1",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
            goal="Complete MVP",
        )
        assert sprint.name == "Sprint 1"
        assert sprint.goal == "Complete MVP"
        assert sprint.status == SprintStatus.PLANNED

    def test_create_sprint_invalid_dates(self, project: Project):
        with pytest.raises(SprintServiceError, match="Дата начала"):
            SprintService.create_sprint(
                project=project,
                name="Sprint 1",
                start_date=date.today(),
                end_date=date.today() - timedelta(days=1),
            )


class TestSprintServiceUpdate:
    def test_update_sprint(self, sprint: Sprint):
        updated = SprintService.update_sprint(
            sprint=sprint,
            name="Updated Sprint",
            goal="New goal",
        )
        assert updated.name == "Updated Sprint"
        assert updated.goal == "New goal"

    def test_update_sprint_invalid_dates(self, sprint: Sprint):
        with pytest.raises(SprintServiceError):
            SprintService.update_sprint(
                sprint=sprint,
                start_date=date.today() + timedelta(days=10),
                end_date=date.today(),
            )


class TestSprintServiceStart:
    def test_start_sprint(self, sprint: Sprint):
        started = SprintService.start_sprint(sprint)
        assert started.status == SprintStatus.ACTIVE
        assert started.initial_story_points == 0

    def test_start_sprint_with_issues(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Task 1",
            status=status_todo,
            reporter=user,
            sprint=sprint,
            story_points=5,
        )
        Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Task 2",
            status=status_todo,
            reporter=user,
            sprint=sprint,
            story_points=3,
        )

        started = SprintService.start_sprint(sprint)
        assert started.initial_story_points == 8

    def test_start_sprint_already_active(self, sprint: Sprint):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()
        with pytest.raises(SprintServiceError, match="запланированный"):
            SprintService.start_sprint(sprint)

    def test_start_sprint_another_active_exists(self, project: Project, sprint: Sprint):
        Sprint.objects.create(
            project=project,
            name="Active Sprint",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today() + timedelta(days=7),
            status=SprintStatus.ACTIVE,
        )
        with pytest.raises(SprintServiceError, match="уже есть активный"):
            SprintService.start_sprint(sprint)


class TestSprintServiceComplete:
    def test_complete_sprint(self, sprint: Sprint):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()
        completed = SprintService.complete_sprint(sprint)
        assert completed.status == SprintStatus.COMPLETED
        assert completed.completed_story_points == 0

    def test_complete_sprint_with_issues(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        status_done: Status,
        user: User,
    ):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()

        Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Done Task",
            status=status_done,
            reporter=user,
            sprint=sprint,
            story_points=5,
        )
        Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Incomplete Task",
            status=status_todo,
            reporter=user,
            sprint=sprint,
            story_points=3,
        )

        completed = SprintService.complete_sprint(sprint, move_incomplete_to="backlog")
        assert completed.completed_story_points == 5

        incomplete = Issue.objects.get(title="Incomplete Task")
        assert incomplete.sprint is None

    def test_complete_sprint_move_to_next(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()

        next_sprint = Sprint.objects.create(
            project=sprint.project,
            name="Sprint 2",
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=28),
            status=SprintStatus.PLANNED,
        )

        issue = Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Incomplete Task",
            status=status_todo,
            reporter=user,
            sprint=sprint,
            story_points=3,
        )

        SprintService.complete_sprint(sprint, move_incomplete_to=next_sprint.id)
        issue.refresh_from_db()
        assert issue.sprint == next_sprint

    def test_complete_sprint_not_active(self, sprint: Sprint):
        with pytest.raises(SprintServiceError, match="активный"):
            SprintService.complete_sprint(sprint)


class TestSprintServiceDelete:
    def test_delete_sprint(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        issue = Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Task",
            status=status_todo,
            reporter=user,
            sprint=sprint,
        )
        sprint_id = sprint.id

        SprintService.delete_sprint(sprint)

        assert not Sprint.objects.filter(id=sprint_id).exists()
        issue.refresh_from_db()
        assert issue.sprint is None


class TestSprintServiceStats:
    def test_get_sprint_stats(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        status_done: Status,
        user: User,
    ):
        Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Done Task",
            status=status_done,
            reporter=user,
            sprint=sprint,
            story_points=5,
        )
        Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Todo Task",
            status=status_todo,
            reporter=user,
            sprint=sprint,
            story_points=3,
        )

        stats = SprintService.get_sprint_stats(sprint)
        assert stats["total_story_points"] == 8
        assert stats["completed_story_points"] == 5
        assert stats["remaining_story_points"] == 3
        assert stats["total_issues"] == 2
        assert stats["completed_issues"] == 1
        assert stats["remaining_issues"] == 1


class TestSprintServiceIssueManagement:
    def test_add_issue_to_sprint(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        issue = Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Task",
            status=status_todo,
            reporter=user,
        )
        SprintService.add_issue_to_sprint(issue, sprint)
        issue.refresh_from_db()
        assert issue.sprint == sprint

    def test_add_issue_to_completed_sprint(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        sprint.status = SprintStatus.COMPLETED
        sprint.save()

        issue = Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Task",
            status=status_todo,
            reporter=user,
        )
        with pytest.raises(SprintServiceError, match="завершённый"):
            SprintService.add_issue_to_sprint(issue, sprint)

    def test_remove_issue_from_sprint(
        self,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
    ):
        issue = Issue.objects.create(
            project=sprint.project,
            issue_type=issue_type,
            title="Task",
            status=status_todo,
            reporter=user,
            sprint=sprint,
        )
        SprintService.remove_issue_from_sprint(issue)
        issue.refresh_from_db()
        assert issue.sprint is None
