"""
Tests for projects API endpoints.
"""

import json

import pytest
from django.test import Client

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


@pytest.mark.django_db
class TestProjectList:
    """Tests for listing projects."""

    def test_list_projects_authenticated(
        self, api_client: Client, user: User, project: Project, auth_headers: dict
    ):
        """Test listing projects when authenticated."""
        response = api_client.get("/api/projects", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["key"] == "TEST"
        assert data[0]["name"] == "Test Project"

    def test_list_projects_unauthenticated(self, api_client: Client):
        """Test listing projects without authentication."""
        response = api_client.get("/api/projects")

        assert response.status_code == 401


@pytest.mark.django_db
class TestProjectCreate:
    """Tests for creating projects."""

    def test_create_project_success(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test successful project creation."""
        response = api_client.post(
            "/api/projects",
            data=json.dumps(
                {
                    "name": "New Project",
                    "key": "NEW",
                    "description": "A new project",
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["key"] == "NEW"

        # Verify project was created
        assert Project.objects.filter(key="NEW").exists()

        # Verify user is a member
        project = Project.objects.get(key="NEW")
        assert ProjectMembership.objects.filter(project=project, user=user).exists()

    def test_create_project_duplicate_key(
        self, api_client: Client, user: User, project: Project, auth_headers: dict
    ):
        """Test creating project with duplicate key."""
        response = api_client.post(
            "/api/projects",
            data=json.dumps(
                {
                    "name": "Another Project",
                    "key": "TEST",  # Same key as existing project
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 400

    def test_create_project_invalid_key(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test creating project with invalid key format."""
        response = api_client.post(
            "/api/projects",
            data=json.dumps(
                {
                    "name": "Invalid Key Project",
                    "key": "in valid",  # Space not allowed
                }
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestProjectDetail:
    """Tests for project detail endpoint."""

    def test_get_project_member(
        self, api_client: Client, user: User, project: Project, auth_headers: dict
    ):
        """Test getting project detail as a member."""
        response = api_client.get(f"/api/projects/{project.key}", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "TEST"
        assert data["name"] == "Test Project"
        assert "owner" in data

    def test_get_project_non_member(self, api_client: Client, project: Project):
        """Test getting project detail as non-member."""
        # Create another user who is not a member
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password123",
        )
        from apps.users.jwt import create_token_pair

        tokens = create_token_pair(other_user.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}

        response = api_client.get(f"/api/projects/{project.key}", **headers)

        assert response.status_code == 403

    def test_get_project_not_found(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test getting non-existent project."""
        response = api_client.get("/api/projects/NOTEXIST", **auth_headers)

        assert response.status_code == 404


@pytest.mark.django_db
class TestProjectUpdate:
    """Tests for updating projects."""

    def test_update_project_admin(
        self, api_client: Client, user: User, project: Project, auth_headers: dict
    ):
        """Test updating project as admin."""
        response = api_client.patch(
            f"/api/projects/{project.key}",
            data=json.dumps(
                {"name": "Updated Name", "description": "Updated description"}
            ),
            content_type="application/json",
            **auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

        # Verify database update
        project.refresh_from_db()
        assert project.name == "Updated Name"

    def test_update_project_non_admin(self, api_client: Client, project: Project):
        """Test updating project as non-admin member."""
        # Create a member with developer role
        member = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="password123",
        )
        ProjectMembership.objects.create(
            project=project,
            user=member,
            role=ProjectRole.DEVELOPER,
        )
        from apps.users.jwt import create_token_pair

        tokens = create_token_pair(member.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}

        response = api_client.patch(
            f"/api/projects/{project.key}",
            data=json.dumps({"name": "Hacked Name"}),
            content_type="application/json",
            **headers,
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestProjectArchive:
    """Tests for archiving projects (soft delete)."""

    def test_archive_project_admin(
        self, api_client: Client, user: User, project: Project, auth_headers: dict
    ):
        """Test archiving project as admin."""
        response = api_client.delete(f"/api/projects/{project.key}", **auth_headers)

        assert response.status_code == 200

        # Verify project was archived (not deleted)
        project.refresh_from_db()
        assert project.is_archived is True

    def test_archive_project_non_admin(self, api_client: Client, project: Project):
        """Test archiving project as non-admin member."""
        # Create a member with developer role
        member = User.objects.create_user(
            username="member2",
            email="member2@example.com",
            password="password123",
        )
        ProjectMembership.objects.create(
            project=project,
            user=member,
            role=ProjectRole.DEVELOPER,
        )
        from apps.users.jwt import create_token_pair

        tokens = create_token_pair(member.id)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}

        response = api_client.delete(f"/api/projects/{project.key}", **headers)

        assert response.status_code == 403
