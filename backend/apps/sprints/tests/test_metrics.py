"""Tests for sprint metrics endpoints."""

from datetime import date, timedelta

import pytest

from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
from apps.sprints.services import SprintService
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
def issue_type(db, project) -> IssueType:
    return IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#0000FF",
    )


@pytest.fixture
def todo_status(db, project) -> Status:
    return Status.objects.create(
        project=project,
        name="To Do",
        category=StatusCategory.TODO,
        color="#808080",
        order=0,
    )


@pytest.fixture
def done_status(db, project) -> Status:
    return Status.objects.create(
        project=project,
        name="Done",
        category=StatusCategory.DONE,
        color="#00FF00",
        order=2,
    )


@pytest.mark.django_db
class TestVelocityEndpoint:
    def test_get_velocity_empty(self, api_client, auth_headers, project):
        """Test velocity with no completed sprints."""
        response = api_client.get(
            f"/api/projects/{project.key}/metrics/velocity", **auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sprints"] == []
        assert data["average_velocity"] == 0
        assert data["total_sprints"] == 0

    def test_get_velocity_with_completed_sprints(
        self, api_client, auth_headers, project, user
    ):
        """Test velocity with completed sprints."""
        # Create completed sprints
        today = date.today()
        sprints_data = [
            {"name": "Sprint 1", "initial_sp": 20, "completed_sp": 15, "offset": 21},
            {"name": "Sprint 2", "initial_sp": 25, "completed_sp": 20, "offset": 14},
            {"name": "Sprint 3", "initial_sp": 30, "completed_sp": 28, "offset": 7},
        ]

        for sp_data in sprints_data:
            Sprint.objects.create(
                project=project,
                name=sp_data["name"],
                start_date=today - timedelta(days=sp_data["offset"]),
                end_date=today - timedelta(days=sp_data["offset"] - 7),
                status=SprintStatus.COMPLETED,
                initial_story_points=sp_data["initial_sp"],
                completed_story_points=sp_data["completed_sp"],
            )

        response = api_client.get(
            f"/api/projects/{project.key}/metrics/velocity", **auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_sprints"] == 3
        # Average: (15 + 20 + 28) / 3 = 21.0
        assert data["average_velocity"] == 21.0
        assert len(data["sprints"]) == 3

        # Check sprints are ordered oldest first
        assert data["sprints"][0]["name"] == "Sprint 1"
        assert data["sprints"][2]["name"] == "Sprint 3"

    def test_get_velocity_respects_limit(self, api_client, auth_headers, project):
        """Test velocity respects limit parameter."""
        today = date.today()

        # Create 10 completed sprints
        for i in range(10):
            Sprint.objects.create(
                project=project,
                name=f"Sprint {i + 1}",
                start_date=today - timedelta(days=(i + 1) * 14),
                end_date=today - timedelta(days=i * 14 + 7),
                status=SprintStatus.COMPLETED,
                initial_story_points=20,
                completed_story_points=15 + i,
            )

        # Default limit is 6
        response = api_client.get(
            f"/api/projects/{project.key}/metrics/velocity", **auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sprints"]) == 6

        # Custom limit
        response = api_client.get(
            f"/api/projects/{project.key}/metrics/velocity?limit=3", **auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sprints"]) == 3

    def test_get_velocity_ignores_non_completed_sprints(
        self, api_client, auth_headers, project
    ):
        """Test velocity only counts completed sprints."""
        today = date.today()

        # Create sprints with different statuses
        Sprint.objects.create(
            project=project,
            name="Completed Sprint",
            start_date=today - timedelta(days=14),
            end_date=today - timedelta(days=7),
            status=SprintStatus.COMPLETED,
            initial_story_points=20,
            completed_story_points=18,
        )
        Sprint.objects.create(
            project=project,
            name="Active Sprint",
            start_date=today - timedelta(days=7),
            end_date=today,
            status=SprintStatus.ACTIVE,
            initial_story_points=25,
        )
        Sprint.objects.create(
            project=project,
            name="Planned Sprint",
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=14),
            status=SprintStatus.PLANNED,
        )

        response = api_client.get(
            f"/api/projects/{project.key}/metrics/velocity", **auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_sprints"] == 1
        assert data["sprints"][0]["name"] == "Completed Sprint"

    def test_get_velocity_project_not_found(self, api_client, auth_headers):
        """Test velocity with non-existent project."""
        response = api_client.get(
            "/api/projects/INVALID/metrics/velocity", **auth_headers
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestBurndownEndpoint:
    def test_get_burndown_planned_sprint(
        self, api_client, auth_headers, project, issue_type, todo_status, user
    ):
        """Test burndown for planned sprint."""
        today = date.today()
        sprint = Sprint.objects.create(
            project=project,
            name="Test Sprint",
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=14),
            status=SprintStatus.PLANNED,
        )

        # Add issues to sprint
        for i in range(3):
            Issue.objects.create(
                project=project,
                issue_type=issue_type,
                title=f"Issue {i + 1}",
                status=todo_status,
                reporter=user,
                sprint=sprint,
                story_points=5,
            )

        response = api_client.get(f"/api/sprints/{sprint.id}/burndown", **auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["sprint_id"] == str(sprint.id)
        assert data["sprint_name"] == "Test Sprint"
        assert data["initial_story_points"] == 15
        assert len(data["ideal"]) == 15  # 14 days + 1

        # Ideal line should start at 15 and end at 0
        assert data["ideal"][0]["value"] == 15.0
        assert data["ideal"][-1]["value"] == 0.0

    def test_get_burndown_active_sprint(
        self,
        api_client,
        auth_headers,
        project,
        issue_type,
        todo_status,
        done_status,
        user,
    ):
        """Test burndown for active sprint."""
        today = date.today()
        sprint = Sprint.objects.create(
            project=project,
            name="Active Sprint",
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=7),
            status=SprintStatus.ACTIVE,
            initial_story_points=20,
        )

        # Add issues
        Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Todo Issue",
            status=todo_status,
            reporter=user,
            sprint=sprint,
            story_points=10,
        )
        Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Done Issue",
            status=done_status,
            reporter=user,
            sprint=sprint,
            story_points=10,
        )

        response = api_client.get(f"/api/sprints/{sprint.id}/burndown", **auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["initial_story_points"] == 20
        # Should have actual data up to today
        assert len(data["actual"]) > 0

    def test_get_burndown_completed_sprint(
        self, api_client, auth_headers, project, issue_type, done_status, user
    ):
        """Test burndown for completed sprint."""
        today = date.today()
        sprint = Sprint.objects.create(
            project=project,
            name="Completed Sprint",
            start_date=today - timedelta(days=14),
            end_date=today - timedelta(days=7),
            status=SprintStatus.COMPLETED,
            initial_story_points=15,
            completed_story_points=15,
        )

        response = api_client.get(f"/api/sprints/{sprint.id}/burndown", **auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["sprint_name"] == "Completed Sprint"
        assert data["initial_story_points"] == 15

    def test_get_burndown_sprint_not_found(self, api_client, auth_headers):
        """Test burndown with non-existent sprint."""
        import uuid

        response = api_client.get(
            f"/api/sprints/{uuid.uuid4()}/burndown", **auth_headers
        )
        assert response.status_code == 404

    def test_get_burndown_unauthorized_user(self, api_client, auth_headers, db):
        """Test burndown for sprint user doesn't have access to."""
        # Create another user and project
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="testpass123",
        )
        other_project = Project.objects.create(
            name="Other Project",
            key="OTHER",
            owner=other_user,
        )
        sprint = Sprint.objects.create(
            project=other_project,
            name="Other Sprint",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
            status=SprintStatus.PLANNED,
        )

        response = api_client.get(f"/api/sprints/{sprint.id}/burndown", **auth_headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestVelocityService:
    def test_get_velocity_returns_correct_structure(self, project):
        """Test velocity service returns correct data structure."""
        today = date.today()
        Sprint.objects.create(
            project=project,
            name="Sprint 1",
            start_date=today - timedelta(days=14),
            end_date=today - timedelta(days=7),
            status=SprintStatus.COMPLETED,
            initial_story_points=20,
            completed_story_points=18,
        )

        result = SprintService.get_velocity(project)

        assert "sprints" in result
        assert "average_velocity" in result
        assert "total_sprints" in result

        sprint = result["sprints"][0]
        assert "id" in sprint
        assert "name" in sprint
        assert "start_date" in sprint
        assert "end_date" in sprint
        assert "committed_story_points" in sprint
        assert "completed_story_points" in sprint


@pytest.mark.django_db
class TestBurndownService:
    def test_get_burndown_returns_correct_structure(
        self, project, issue_type, todo_status, user
    ):
        """Test burndown service returns correct data structure."""
        today = date.today()
        sprint = Sprint.objects.create(
            project=project,
            name="Test Sprint",
            start_date=today,
            end_date=today + timedelta(days=7),
            status=SprintStatus.ACTIVE,
            initial_story_points=10,
        )

        Issue.objects.create(
            project=project,
            issue_type=issue_type,
            title="Test Issue",
            status=todo_status,
            reporter=user,
            sprint=sprint,
            story_points=10,
        )

        result = SprintService.get_burndown(sprint)

        assert "sprint_id" in result
        assert "sprint_name" in result
        assert "start_date" in result
        assert "end_date" in result
        assert "initial_story_points" in result
        assert "ideal" in result
        assert "actual" in result

        # Check ideal data points structure
        assert len(result["ideal"]) > 0
        assert "date" in result["ideal"][0]
        assert "value" in result["ideal"][0]
