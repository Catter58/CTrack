"""Tests for epic functionality."""

import pytest
from django.test import Client

from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.users.models import User


@pytest.fixture
def project(db, user: User):
    """Create a test project with user as member."""
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
def epic_type(db, project: Project):
    """Create an epic issue type."""
    return IssueType.objects.create(
        project=project,
        name="Epic",
        icon="epic",
        color="#7B68EE",
        is_epic=True,
    )


@pytest.fixture
def task_type(db, project: Project):
    """Create a task issue type."""
    return IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#0066cc",
        is_epic=False,
    )


@pytest.fixture
def todo_status(db, project: Project):
    """Create a TODO status."""
    return Status.objects.create(
        project=project,
        name="To Do",
        category=StatusCategory.TODO,
        color="#808080",
    )


@pytest.fixture
def done_status(db, project: Project):
    """Create a DONE status."""
    return Status.objects.create(
        project=project,
        name="Done",
        category=StatusCategory.DONE,
        color="#00AA00",
    )


@pytest.fixture
def epic(project, epic_type, todo_status, user):
    """Create an epic issue."""
    return Issue.objects.create(
        project=project,
        issue_number=1,
        key=f"{project.key}-1",
        title="Test Epic",
        description="Epic description",
        issue_type=epic_type,
        status=todo_status,
        reporter=user,
        priority="high",
    )


@pytest.fixture
def epic_with_issues(project, epic_type, task_type, todo_status, done_status, user):
    """Create an epic with linked issues having various states."""
    epic = Issue.objects.create(
        project=project,
        issue_number=100,
        key=f"{project.key}-100",
        title="Epic with Issues",
        description="Epic with child issues",
        issue_type=epic_type,
        status=todo_status,
        reporter=user,
        priority="high",
    )

    # Create 3 TODO issues (2 with SP, 1 without)
    Issue.objects.create(
        project=project,
        issue_number=101,
        key=f"{project.key}-101",
        title="TODO Task 1",
        issue_type=task_type,
        status=todo_status,
        reporter=user,
        epic=epic,
        story_points=3,
    )
    Issue.objects.create(
        project=project,
        issue_number=102,
        key=f"{project.key}-102",
        title="TODO Task 2",
        issue_type=task_type,
        status=todo_status,
        reporter=user,
        epic=epic,
        story_points=5,
    )
    Issue.objects.create(
        project=project,
        issue_number=103,
        key=f"{project.key}-103",
        title="TODO Task 3",
        issue_type=task_type,
        status=todo_status,
        reporter=user,
        epic=epic,
        story_points=None,
    )

    # Create 2 DONE issues with SP
    Issue.objects.create(
        project=project,
        issue_number=104,
        key=f"{project.key}-104",
        title="Done Task 1",
        issue_type=task_type,
        status=done_status,
        reporter=user,
        epic=epic,
        story_points=2,
    )
    Issue.objects.create(
        project=project,
        issue_number=105,
        key=f"{project.key}-105",
        title="Done Task 2",
        issue_type=task_type,
        status=done_status,
        reporter=user,
        epic=epic,
        story_points=8,
    )

    return epic


@pytest.mark.django_db
class TestListEpics:
    """Tests for GET /api/projects/{key}/epics."""

    def test_list_epics_empty(self, client: Client, auth_headers, project):
        """Test listing epics when none exist."""
        response = client.get(
            f"/api/projects/{project.key}/epics",
            **auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_list_epics_single(self, client: Client, auth_headers, project, epic):
        """Test listing a single epic without linked issues."""
        response = client.get(
            f"/api/projects/{project.key}/epics",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        epic_data = data[0]
        assert epic_data["id"] == str(epic.id)
        assert epic_data["key"] == epic.key
        assert epic_data["title"] == epic.title
        assert epic_data["total_issues"] == 0
        assert epic_data["completed_issues"] == 0
        assert epic_data["total_story_points"] == 0
        assert epic_data["completed_story_points"] == 0

    def test_list_epics_with_progress(
        self, client: Client, auth_headers, project, epic_with_issues
    ):
        """Test listing epics with progress statistics."""
        response = client.get(
            f"/api/projects/{project.key}/epics",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        epic_data = data[0]
        assert epic_data["id"] == str(epic_with_issues.id)
        assert epic_data["total_issues"] == 5
        assert epic_data["completed_issues"] == 2
        # Total SP: 3 + 5 + 0 + 2 + 8 = 18
        assert epic_data["total_story_points"] == 18
        # Completed SP: 2 + 8 = 10
        assert epic_data["completed_story_points"] == 10

    def test_list_epics_unauthorized(self, client: Client, project):
        """Test listing epics without authentication."""
        response = client.get(
            f"/api/projects/{project.key}/epics",
        )

        assert response.status_code == 401

    def test_list_epics_project_not_found(self, client: Client, auth_headers):
        """Test listing epics for non-existent project."""
        response = client.get(
            "/api/projects/NONEXISTENT/epics",
            **auth_headers,
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestFilterIssuesByEpic:
    """Tests for filtering issues by epic_id."""

    def test_filter_issues_by_epic(
        self, client: Client, auth_headers, project, epic_with_issues
    ):
        """Test filtering issues by epic_id."""
        response = client.get(
            f"/api/projects/{project.key}/issues?epic_id={epic_with_issues.id}",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # 5 issues linked to the epic
        assert len(data) == 5

        # All should have the epic_id
        for issue in data:
            assert issue["epic_id"] == str(epic_with_issues.id)

    def test_issues_include_epic_id(
        self,
        client: Client,
        auth_headers,
        project,
        epic_with_issues,
        task_type,
        todo_status,
        user,
    ):
        """Test that issue response includes epic_id field."""
        # Create an issue without epic
        standalone = Issue.objects.create(
            project=project,
            issue_number=200,
            key=f"{project.key}-200",
            title="Standalone Issue",
            issue_type=task_type,
            status=todo_status,
            reporter=user,
        )

        # Get issue without epic
        response = client.get(
            f"/api/issues/{standalone.key}",
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["epic_id"] is None

        # Get issue with epic
        response = client.get(
            f"/api/issues/{project.key}-101",  # First linked issue
            **auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["epic_id"] == str(epic_with_issues.id)


@pytest.mark.django_db
class TestCreateIssueWithEpic:
    """Tests for creating issues linked to epics."""

    def test_create_issue_with_epic(
        self, client: Client, auth_headers, project, epic, task_type, todo_status
    ):
        """Test creating an issue linked to an epic."""
        data = {
            "title": "New Task in Epic",
            "issue_type_id": str(task_type.id),
            "epic_id": str(epic.id),
        }

        response = client.post(
            f"/api/projects/{project.key}/issues",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["epic_id"] == str(epic.id)

        # Verify in DB
        created_issue = Issue.objects.get(id=result["id"])
        assert created_issue.epic_id == epic.id

    def test_update_issue_epic(
        self, client: Client, auth_headers, project, epic, task_type, todo_status, user
    ):
        """Test updating an issue's epic assignment."""
        # Create issue without epic
        issue = Issue.objects.create(
            project=project,
            issue_number=300,
            key=f"{project.key}-300",
            title="Issue to link",
            issue_type=task_type,
            status=todo_status,
            reporter=user,
        )

        # Update to add epic
        response = client.patch(
            f"/api/issues/{issue.key}",
            {"epic_id": str(epic.id)},
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["epic_id"] == str(epic.id)

        # Verify in DB
        issue.refresh_from_db()
        assert issue.epic_id == epic.id


@pytest.mark.django_db
class TestIssueTypeIsEpic:
    """Tests for is_epic flag on issue types."""

    def test_issue_type_includes_is_epic(
        self, client: Client, auth_headers, project, epic_type, task_type
    ):
        """Test that issue type response includes is_epic field."""
        response = client.get(
            f"/api/projects/{project.key}/issue-types",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        epic_type_data = next(t for t in data if t["id"] == str(epic_type.id))
        task_type_data = next(t for t in data if t["id"] == str(task_type.id))

        assert epic_type_data["is_epic"] is True
        assert task_type_data["is_epic"] is False
