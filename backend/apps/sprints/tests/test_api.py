import json
from datetime import date, timedelta

import pytest
from django.test import Client

from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.sprints.models import Sprint, SprintStatus
from apps.users.models import User


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
def sprint(db, project: Project):
    return Sprint.objects.create(
        project=project,
        name="Sprint 1",
        goal="Test goal",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=14),
        status=SprintStatus.PLANNED,
    )


@pytest.mark.django_db
class TestSprintCreate:
    def test_create_sprint(
        self, api_client: Client, project: Project, auth_headers: dict
    ):
        response = api_client.post(
            f"/api/projects/{project.key}/sprints",
            data=json.dumps(
                {
                    "name": "Sprint 1",
                    "goal": "Complete MVP",
                    "start_date": str(date.today()),
                    "end_date": str(date.today() + timedelta(days=14)),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sprint 1"
        assert data["goal"] == "Complete MVP"
        assert data["status"] == "planned"

    def test_create_sprint_invalid_dates(
        self, api_client: Client, project: Project, auth_headers: dict
    ):
        response = api_client.post(
            f"/api/projects/{project.key}/sprints",
            data=json.dumps(
                {
                    "name": "Sprint 1",
                    "start_date": str(date.today()),
                    "end_date": str(date.today() - timedelta(days=1)),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400

    def test_create_sprint_project_not_found(
        self, api_client: Client, auth_headers: dict
    ):
        response = api_client.post(
            "/api/projects/NONEXIST/sprints",
            data=json.dumps(
                {
                    "name": "Sprint 1",
                    "start_date": str(date.today()),
                    "end_date": str(date.today() + timedelta(days=14)),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestSprintList:
    def test_list_sprints(self, api_client: Client, sprint: Sprint, auth_headers: dict):
        response = api_client.get(
            f"/api/projects/{sprint.project.key}/sprints",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Sprint 1"

    def test_list_sprints_filter_by_status(
        self,
        api_client: Client,
        project: Project,
        sprint: Sprint,
        auth_headers: dict,
    ):
        Sprint.objects.create(
            project=project,
            name="Sprint 2",
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=28),
            status=SprintStatus.ACTIVE,
        )
        response = api_client.get(
            f"/api/projects/{project.key}/sprints?status=planned",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "planned"


@pytest.mark.django_db
class TestSprintDetail:
    def test_get_sprint(self, api_client: Client, sprint: Sprint, auth_headers: dict):
        response = api_client.get(f"/api/sprints/{sprint.id}", **auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sprint 1"
        assert "total_story_points" in data

    def test_get_sprint_not_found(self, api_client: Client, auth_headers: dict):
        import uuid

        response = api_client.get(f"/api/sprints/{uuid.uuid4()}", **auth_headers)
        assert response.status_code == 404


@pytest.mark.django_db
class TestSprintUpdate:
    def test_update_sprint(
        self, api_client: Client, sprint: Sprint, auth_headers: dict
    ):
        response = api_client.patch(
            f"/api/sprints/{sprint.id}",
            data=json.dumps({"name": "Updated Sprint", "goal": "New goal"}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Sprint"
        assert data["goal"] == "New goal"


@pytest.mark.django_db
class TestSprintDelete:
    def test_delete_sprint(
        self, api_client: Client, sprint: Sprint, auth_headers: dict
    ):
        sprint_id = sprint.id
        response = api_client.delete(f"/api/sprints/{sprint_id}", **auth_headers)
        assert response.status_code == 200
        assert not Sprint.objects.filter(id=sprint_id).exists()


@pytest.mark.django_db
class TestSprintStart:
    def test_start_sprint(self, api_client: Client, sprint: Sprint, auth_headers: dict):
        response = api_client.post(
            f"/api/sprints/{sprint.id}/start",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    def test_start_sprint_already_active(
        self, api_client: Client, sprint: Sprint, auth_headers: dict
    ):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()
        response = api_client.post(
            f"/api/sprints/{sprint.id}/start",
            **auth_headers,
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestSprintComplete:
    def test_complete_sprint(
        self, api_client: Client, sprint: Sprint, auth_headers: dict
    ):
        sprint.status = SprintStatus.ACTIVE
        sprint.save()
        response = api_client.post(
            f"/api/sprints/{sprint.id}/complete",
            data=json.dumps({"move_incomplete_to": "backlog"}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_complete_sprint_not_active(
        self, api_client: Client, sprint: Sprint, auth_headers: dict
    ):
        response = api_client.post(
            f"/api/sprints/{sprint.id}/complete",
            data=json.dumps({}),
            content_type="application/json",
            **auth_headers,
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestSprintIssues:
    def test_get_sprint_issues(
        self,
        api_client: Client,
        sprint: Sprint,
        issue_type: IssueType,
        status_todo: Status,
        user: User,
        auth_headers: dict,
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
        response = api_client.get(
            f"/api/sprints/{sprint.id}/issues",
            **auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Task 1"
        assert data[0]["story_points"] == 5
