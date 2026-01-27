from datetime import date, timedelta

import pytest
from django.db import IntegrityError

from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
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
        description="A test project",
        owner=user,
    )
    ProjectMembership.objects.create(
        project=project,
        user=user,
        role=ProjectRole.ADMIN,
    )
    return project


@pytest.fixture
def sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Sprint 1",
        goal="Complete MVP features",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=14),
        status=SprintStatus.PLANNED,
    )


class TestSprintModel:
    def test_create_sprint(self, project: Project):
        sprint = Sprint.objects.create(
            project=project,
            name="Sprint 1",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        assert sprint.id is not None
        assert sprint.status == SprintStatus.PLANNED
        assert sprint.name == "Sprint 1"
        assert sprint.project == project

    def test_sprint_str(self, sprint: Sprint):
        assert str(sprint) == f"{sprint.project.key} - {sprint.name}"

    def test_sprint_status_choices(self, sprint: Sprint):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.status == SprintStatus.ACTIVE

        sprint.status = SprintStatus.COMPLETED
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.status == SprintStatus.COMPLETED

    def test_sprint_goal_optional(self, project: Project):
        sprint = Sprint.objects.create(
            project=project,
            name="Sprint without goal",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        assert sprint.goal == ""

    def test_sprint_story_points(self, sprint: Sprint):
        sprint.initial_story_points = 20
        sprint.completed_story_points = 15
        sprint.save()
        sprint.refresh_from_db()
        assert sprint.initial_story_points == 20
        assert sprint.completed_story_points == 15
        assert sprint.remaining_story_points == 5

    def test_remaining_story_points_none(self, sprint: Sprint):
        assert sprint.remaining_story_points is None

    def test_remaining_story_points_with_zero_completed(self, sprint: Sprint):
        sprint.initial_story_points = 20
        sprint.completed_story_points = None
        sprint.save()
        assert sprint.remaining_story_points == 20

    def test_sprint_dates_constraint(self, project: Project):
        with pytest.raises(IntegrityError):
            Sprint.objects.create(
                project=project,
                name="Invalid Sprint",
                start_date=date.today(),
                end_date=date.today() - timedelta(days=1),
            )

    def test_sprint_ordering(self, project: Project):
        sprint1 = Sprint.objects.create(
            project=project,
            name="Sprint 1",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=16),
        )
        sprint2 = Sprint.objects.create(
            project=project,
            name="Sprint 2",
            start_date=date.today() - timedelta(days=14),
            end_date=date.today(),
        )
        sprint3 = Sprint.objects.create(
            project=project,
            name="Sprint 3",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )

        sprints = list(Sprint.objects.filter(project=project))
        assert sprints[0] == sprint3
        assert sprints[1] == sprint2
        assert sprints[2] == sprint1

    def test_sprint_project_cascade_delete(self, sprint: Sprint):
        sprint_id = sprint.id
        sprint.project.delete()
        assert not Sprint.objects.filter(id=sprint_id).exists()

    def test_sprint_history_tracking(self, sprint: Sprint):
        original_name = sprint.name
        sprint.name = "Updated Sprint"
        sprint.save()

        history = sprint.history.all()
        assert history.count() == 2
        assert history.first().name == "Updated Sprint"
        assert history.last().name == original_name
