"""Tests for issue hierarchy functionality."""

import pytest
from django.test import Client

from apps.issues.models import Issue, IssueType, Status, StatusCategory
from apps.issues.services import IssueService
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
def story_type(db, project: Project):
    """Create a Story issue type."""
    return IssueType.objects.create(
        project=project,
        name="Story",
        icon="story",
        color="#0066cc",
    )


@pytest.fixture
def subtask_type(db, project: Project, story_type: IssueType):
    """Create a Subtask issue type that can have Story as parent."""
    return IssueType.objects.create(
        project=project,
        name="Subtask",
        icon="subtask",
        color="#808080",
        is_subtask=True,
        parent_types=[str(story_type.id)],
    )


@pytest.fixture
def task_type(db, project: Project):
    """Create a Task issue type."""
    return IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#00AA00",
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
def parent_issue(project, story_type, todo_status, user):
    """Create a parent (story) issue."""
    return Issue.objects.create(
        project=project,
        issue_number=1,
        key=f"{project.key}-1",
        title="Parent Story",
        issue_type=story_type,
        status=todo_status,
        reporter=user,
    )


@pytest.fixture
def child_issues(project, subtask_type, todo_status, done_status, user, parent_issue):
    """Create child issues (subtasks) for parent."""
    children = []
    # 2 TODO subtasks
    for i in range(2):
        children.append(
            Issue.objects.create(
                project=project,
                issue_number=10 + i,
                key=f"{project.key}-{10 + i}",
                title=f"TODO Subtask {i + 1}",
                issue_type=subtask_type,
                status=todo_status,
                reporter=user,
                parent=parent_issue,
            )
        )
    # 1 DONE subtask
    children.append(
        Issue.objects.create(
            project=project,
            issue_number=12,
            key=f"{project.key}-12",
            title="Done Subtask",
            issue_type=subtask_type,
            status=done_status,
            reporter=user,
            parent=parent_issue,
        )
    )
    return children


@pytest.mark.django_db
class TestGetIssueChildren:
    """Tests for GET /api/issues/{key}/children."""

    def test_get_children_success(
        self, client: Client, auth_headers, parent_issue, child_issues
    ):
        """Test getting children of an issue."""
        response = client.get(
            f"/api/issues/{parent_issue.key}/children",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # All children should have this parent
        for child in data:
            assert child["key"] in [c.key for c in child_issues]

    def test_get_children_empty(self, client: Client, auth_headers, parent_issue):
        """Test getting children when none exist."""
        response = client.get(
            f"/api/issues/{parent_issue.key}/children",
            **auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_get_children_unauthorized(self, client: Client, parent_issue):
        """Test getting children without authentication."""
        response = client.get(
            f"/api/issues/{parent_issue.key}/children",
        )

        assert response.status_code == 401

    def test_get_children_not_found(self, client: Client, auth_headers):
        """Test getting children of non-existent issue."""
        response = client.get(
            "/api/issues/FAKE-999/children",
            **auth_headers,
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestIssueChildrenStats:
    """Tests for children_count and completed_children_count."""

    def test_issue_includes_children_stats(
        self, client: Client, auth_headers, parent_issue, child_issues
    ):
        """Test that issue detail includes children stats."""
        response = client.get(
            f"/api/issues/{parent_issue.key}",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["children_count"] == 3
        assert data["completed_children_count"] == 1

    def test_issue_without_children_has_zero_stats(
        self, client: Client, auth_headers, project, task_type, todo_status, user
    ):
        """Test issue without children has zero stats."""
        issue = Issue.objects.create(
            project=project,
            issue_number=100,
            key=f"{project.key}-100",
            title="Standalone Issue",
            issue_type=task_type,
            status=todo_status,
            reporter=user,
        )

        response = client.get(
            f"/api/issues/{issue.key}",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["children_count"] == 0
        assert data["completed_children_count"] == 0


@pytest.mark.django_db
class TestValidateParent:
    """Tests for parent validation."""

    def test_validate_parent_success(
        self, project, story_type, subtask_type, todo_status, user, parent_issue
    ):
        """Test valid parent assignment."""
        child = Issue.objects.create(
            project=project,
            issue_number=20,
            key=f"{project.key}-20",
            title="New Subtask",
            issue_type=subtask_type,
            status=todo_status,
            reporter=user,
        )

        is_valid, error = IssueService.validate_parent(child, parent_issue.id, project)

        assert is_valid is True
        assert error is None

    def test_validate_parent_not_found(self, project, story_type, todo_status, user):
        """Test validation fails for non-existent parent."""
        import uuid

        issue = Issue.objects.create(
            project=project,
            issue_number=21,
            key=f"{project.key}-21",
            title="Issue",
            issue_type=story_type,
            status=todo_status,
            reporter=user,
        )

        is_valid, error = IssueService.validate_parent(issue, uuid.uuid4(), project)

        assert is_valid is False
        assert "не найдена" in error

    def test_validate_parent_self_reference(
        self, project, story_type, todo_status, user
    ):
        """Test validation fails when issue is its own parent."""
        issue = Issue.objects.create(
            project=project,
            issue_number=22,
            key=f"{project.key}-22",
            title="Self Parent",
            issue_type=story_type,
            status=todo_status,
            reporter=user,
        )

        is_valid, error = IssueService.validate_parent(issue, issue.id, project)

        assert is_valid is False
        assert "самой себя" in error

    def test_validate_parent_invalid_type(
        self, project, task_type, subtask_type, todo_status, user
    ):
        """Test validation fails for invalid parent type."""
        # task_type is NOT in subtask_type.parent_types
        task_issue = Issue.objects.create(
            project=project,
            issue_number=23,
            key=f"{project.key}-23",
            title="Task Issue",
            issue_type=task_type,
            status=todo_status,
            reporter=user,
        )
        subtask_issue = Issue.objects.create(
            project=project,
            issue_number=24,
            key=f"{project.key}-24",
            title="Subtask Issue",
            issue_type=subtask_type,
            status=todo_status,
            reporter=user,
        )

        is_valid, error = IssueService.validate_parent(
            subtask_issue, task_issue.id, project
        )

        assert is_valid is False
        assert "не может быть родителем" in error


@pytest.mark.django_db
class TestCreateIssueWithParent:
    """Tests for creating issues with parent."""

    def test_create_issue_with_valid_parent(
        self, client: Client, auth_headers, project, subtask_type, parent_issue
    ):
        """Test creating an issue with a valid parent."""
        data = {
            "title": "New Subtask",
            "issue_type_id": str(subtask_type.id),
            "parent_id": str(parent_issue.id),
        }

        response = client.post(
            f"/api/projects/{project.key}/issues",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["parent_id"] == str(parent_issue.id)

    def test_create_issue_with_invalid_parent_type(
        self,
        client: Client,
        auth_headers,
        project,
        subtask_type,
        task_type,
        todo_status,
        user,
    ):
        """Test creating an issue with invalid parent type fails."""
        # Create a task (not a story)
        task_issue = Issue.objects.create(
            project=project,
            issue_number=30,
            key=f"{project.key}-30",
            title="Task",
            issue_type=task_type,
            status=todo_status,
            reporter=user,
        )

        data = {
            "title": "Subtask with wrong parent",
            "issue_type_id": str(subtask_type.id),
            "parent_id": str(task_issue.id),
        }

        response = client.post(
            f"/api/projects/{project.key}/issues",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 400
        assert "родителем" in response.json()["detail"]


@pytest.mark.django_db
class TestUpdateIssueParent:
    """Tests for updating issue parent."""

    def test_update_issue_parent(
        self,
        client: Client,
        auth_headers,
        project,
        subtask_type,
        todo_status,
        user,
        parent_issue,
    ):
        """Test updating issue to set parent."""
        issue = Issue.objects.create(
            project=project,
            issue_number=40,
            key=f"{project.key}-40",
            title="Issue to update",
            issue_type=subtask_type,
            status=todo_status,
            reporter=user,
        )

        response = client.patch(
            f"/api/issues/{issue.key}",
            {"parent_id": str(parent_issue.id)},
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["parent_id"] == str(parent_issue.id)

        # Verify in DB
        issue.refresh_from_db()
        assert issue.parent_id == parent_issue.id
