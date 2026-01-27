"""
Tests for issues API endpoints.
"""

import json

import pytest
from django.test import Client

from apps.issues.models import Issue, IssueType, Status
from apps.projects.models import Project, ProjectMembership, ProjectRole
from apps.users.models import User


@pytest.fixture
def project(db, user: User):
    """Create and return a test project with the user as owner."""
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
def issue_type(db, project: Project):
    """Create and return a test issue type."""
    return IssueType.objects.create(
        project=None,  # Global issue type
        name="Task",
        icon="checkmark",
        color="#1192e8",
        is_subtask=False,
        parent_types=[],
        order=1,
    )


@pytest.fixture
def status_todo(db, project: Project):
    """Create and return a TODO status."""
    return Status.objects.create(
        project=None,  # Global status
        name="To Do",
        category="todo",
        color="#6f6f6f",
        order=1,
    )


@pytest.fixture
def status_done(db, project: Project):
    """Create and return a DONE status."""
    return Status.objects.create(
        project=None,
        name="Done",
        category="done",
        color="#198038",
        order=2,
    )


@pytest.fixture
def issue(db, project: Project, issue_type: IssueType, status_todo: Status, user: User):
    """Create and return a test issue."""
    return Issue.objects.create(
        project=project,
        issue_type=issue_type,
        title="Test Issue",
        description="A test issue description",
        status=status_todo,
        priority="medium",
        reporter=user,
    )


@pytest.mark.django_db
class TestIssueCreate:
    """Tests for creating issues."""

    def test_create_issue_success(
        self,
        api_client: Client,
        user: User,
        project: Project,
        issue_type: IssueType,
        status_todo: Status,
        auth_headers: dict,
    ):
        """Test successful issue creation."""
        response = api_client.post(
            f"/api/projects/{project.key}/issues",
            data=json.dumps(
                {
                    "title": "New Issue",
                    "description": "Issue description",
                    "issue_type_id": str(issue_type.id),
                    "priority": "high",
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Issue"
        assert data["key"] == "TEST-1"
        assert data["priority"] == "high"
        assert data["issue_type"]["id"] == str(issue_type.id)

        # Verify issue was created
        assert Issue.objects.filter(key="TEST-1").exists()

    def test_create_issue_auto_increment(
        self,
        api_client: Client,
        user: User,
        project: Project,
        issue_type: IssueType,
        status_todo: Status,
        issue: Issue,
        auth_headers: dict,
    ):
        """Test issue number auto-increment."""
        # First issue already exists as TEST-1
        response = api_client.post(
            f"/api/projects/{project.key}/issues",
            data=json.dumps(
                {
                    "title": "Second Issue",
                    "issue_type_id": str(issue_type.id),
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "TEST-2"

    def test_create_issue_invalid_type(
        self,
        api_client: Client,
        user: User,
        project: Project,
        status_todo: Status,
        auth_headers: dict,
    ):
        """Test creating issue with invalid type."""
        response = api_client.post(
            f"/api/projects/{project.key}/issues",
            data=json.dumps(
                {
                    "title": "Issue with bad type",
                    "issue_type_id": "00000000-0000-0000-0000-000000000000",
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestIssueList:
    """Tests for listing issues."""

    def test_list_issues(
        self,
        api_client: Client,
        user: User,
        project: Project,
        issue: Issue,
        auth_headers: dict,
    ):
        """Test listing issues."""
        response = api_client.get(
            f"/api/projects/{project.key}/issues",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key"] == issue.key


@pytest.mark.django_db
class TestIssueDetail:
    """Tests for issue detail."""

    def test_get_issue(
        self,
        api_client: Client,
        user: User,
        issue: Issue,
        auth_headers: dict,
    ):
        """Test getting issue by key."""
        response = api_client.get(f"/api/issues/{issue.key}", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == issue.key
        assert data["title"] == "Test Issue"

    def test_get_issue_not_found(
        self,
        api_client: Client,
        user: User,
        auth_headers: dict,
    ):
        """Test getting non-existent issue."""
        response = api_client.get("/api/issues/NOTEXIST-999", **auth_headers)

        assert response.status_code == 404


@pytest.mark.django_db
class TestIssueUpdate:
    """Tests for updating issues."""

    def test_update_issue_title(
        self,
        api_client: Client,
        user: User,
        issue: Issue,
        auth_headers: dict,
    ):
        """Test updating issue title."""
        response = api_client.patch(
            f"/api/issues/{issue.key}",
            data=json.dumps({"title": "Updated Title"}),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

        # Verify database update
        issue.refresh_from_db()
        assert issue.title == "Updated Title"

    def test_update_issue_status(
        self,
        api_client: Client,
        user: User,
        issue: Issue,
        status_done: Status,
        auth_headers: dict,
    ):
        """Test updating issue status."""
        response = api_client.patch(
            f"/api/issues/{issue.key}",
            data=json.dumps({"status_id": str(status_done.id)}),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"]["id"] == str(status_done.id)

        # Verify database update
        issue.refresh_from_db()
        assert issue.status_id == status_done.id

    def test_update_issue_priority(
        self,
        api_client: Client,
        user: User,
        issue: Issue,
        auth_headers: dict,
    ):
        """Test updating issue priority."""
        response = api_client.patch(
            f"/api/issues/{issue.key}",
            data=json.dumps({"priority": "highest"}),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "highest"


@pytest.mark.django_db
class TestIssueDelete:
    """Tests for deleting issues."""

    def test_delete_issue(
        self,
        api_client: Client,
        user: User,
        issue: Issue,
        auth_headers: dict,
    ):
        """Test deleting issue."""
        issue_key = issue.key
        response = api_client.delete(f"/api/issues/{issue_key}", **auth_headers)

        assert response.status_code == 200

        # Verify issue was deleted
        assert not Issue.objects.filter(key=issue_key).exists()

    def test_delete_issue_non_member(
        self,
        api_client: Client,
        issue: Issue,
    ):
        """Test deleting issue as non-member."""
        # Create another user who is not a member
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password123",
        )
        from apps.users.jwt import create_token_pair

        tokens = create_token_pair(other_user.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}

        response = api_client.delete(f"/api/issues/{issue.key}", **headers)

        assert response.status_code == 403
