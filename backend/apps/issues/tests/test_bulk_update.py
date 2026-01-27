"""Tests for bulk update story points."""

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
def issue_type(db, project: Project):
    """Create a test issue type."""
    return IssueType.objects.create(
        project=project,
        name="Task",
        icon="task",
        color="#0066cc",
    )


@pytest.fixture
def status(db, project: Project):
    """Create a test status."""
    return Status.objects.create(
        project=project,
        name="To Do",
        category=StatusCategory.TODO,
        color="#808080",
    )


@pytest.fixture
def issues_with_sp(project, issue_type, status, user):
    """Create multiple issues with story points."""
    issues = []
    for i in range(5):
        issue = Issue.objects.create(
            project=project,
            issue_number=i + 10,
            key=f"{project.key}-{i + 10}",
            title=f"Test Issue {i + 1}",
            issue_type=issue_type,
            status=status,
            reporter=user,
            story_points=i + 1,
        )
        issues.append(issue)
    return issues


@pytest.mark.django_db
class TestBulkUpdateStoryPoints:
    """Tests for PATCH /api/projects/{key}/issues/bulk-update."""

    def test_bulk_update_success(
        self, client: Client, auth_headers, project, issues_with_sp
    ):
        """Test successful bulk update of story points."""
        data = {
            "issues": [
                {"key": issues_with_sp[0].key, "story_points": 10},
                {"key": issues_with_sp[1].key, "story_points": 20},
                {"key": issues_with_sp[2].key, "story_points": None},
            ]
        }

        response = client.patch(
            f"/api/projects/{project.key}/issues/bulk-update",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["updated"] == 3
        assert result["failed"] == []

        # Verify changes
        issues_with_sp[0].refresh_from_db()
        issues_with_sp[1].refresh_from_db()
        issues_with_sp[2].refresh_from_db()

        assert issues_with_sp[0].story_points == 10
        assert issues_with_sp[1].story_points == 20
        assert issues_with_sp[2].story_points is None

    def test_bulk_update_partial_failure(
        self, client: Client, auth_headers, project, issues_with_sp
    ):
        """Test bulk update with some invalid keys."""
        data = {
            "issues": [
                {"key": issues_with_sp[0].key, "story_points": 5},
                {"key": "INVALID-999", "story_points": 10},
                {"key": issues_with_sp[1].key, "story_points": 15},
            ]
        }

        response = client.patch(
            f"/api/projects/{project.key}/issues/bulk-update",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["updated"] == 2
        assert "INVALID-999" in result["failed"]

    def test_bulk_update_negative_story_points_rejected(
        self, client: Client, auth_headers, project, issues_with_sp
    ):
        """Test that negative story points are rejected."""
        data = {
            "issues": [
                {"key": issues_with_sp[0].key, "story_points": -5},
            ]
        }

        response = client.patch(
            f"/api/projects/{project.key}/issues/bulk-update",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["updated"] == 0
        assert issues_with_sp[0].key in result["failed"]

        # Verify original value unchanged
        issues_with_sp[0].refresh_from_db()
        assert issues_with_sp[0].story_points == 1  # Original value

    def test_bulk_update_empty_list(self, client: Client, auth_headers, project):
        """Test bulk update with empty list."""
        data = {"issues": []}

        response = client.patch(
            f"/api/projects/{project.key}/issues/bulk-update",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["updated"] == 0
        assert result["failed"] == []

    def test_bulk_update_unauthorized(self, client: Client, project, issues_with_sp):
        """Test bulk update without authentication."""
        data = {
            "issues": [
                {"key": issues_with_sp[0].key, "story_points": 10},
            ]
        }

        response = client.patch(
            f"/api/projects/{project.key}/issues/bulk-update",
            data,
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_bulk_update_project_not_found(self, client: Client, auth_headers):
        """Test bulk update for non-existent project."""
        data = {"issues": [{"key": "FAKE-1", "story_points": 10}]}

        response = client.patch(
            "/api/projects/NONEXISTENT/issues/bulk-update",
            data,
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 404
