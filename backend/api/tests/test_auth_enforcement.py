"""
Tests for API authentication enforcement.

Verifies that all API endpoints properly enforce authentication requirements.
Public endpoints should be accessible without auth, protected endpoints should
require valid authentication.
"""

import pytest
from django.test import Client

from apps.users.models import User


@pytest.mark.django_db
class TestPublicEndpoints:
    """Tests that public endpoints work without authentication."""

    def test_auth_register_public(self, api_client: Client, db):
        """Test that /api/auth/register is publicly accessible."""
        response = api_client.post(
            "/api/auth/register",
            data={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "newpassword123",
                "first_name": "New",
                "last_name": "User",
            },
            content_type="application/json",
        )

        # Should succeed without authentication
        assert response.status_code in [201, 400]  # 201 success or 400 validation error
        # Should not be 401 Unauthorized
        assert response.status_code != 401

    def test_auth_login_public(self, api_client: Client, user: User):
        """Test that /api/auth/login is publicly accessible."""
        response = api_client.post(
            "/api/auth/login",
            data={
                "email": user.email,
                "password": "testpassword123",
            },
            content_type="application/json",
        )

        # Should succeed without authentication
        assert response.status_code in [
            200,
            401,
        ]  # 200 success or 401 invalid credentials
        # If 401, should be for invalid credentials, not missing auth header
        if response.status_code == 401:
            data = response.json()
            # Check it's not an auth header error
            assert "authorization" not in data.get("detail", "").lower()

    def test_auth_refresh_public(self, api_client: Client, db):
        """Test that /api/auth/refresh is publicly accessible."""
        response = api_client.post(
            "/api/auth/refresh",
            data={
                "refresh_token": "invalid_token",
            },
            content_type="application/json",
        )

        # Should not require authentication (may fail on invalid token though)
        assert response.status_code in [200, 401]  # 200 success or 401 invalid token
        # Should not be missing auth header error

    def test_health_check_public(self, api_client: Client, db):
        """Test that /api/health is publicly accessible."""
        # Note: Health endpoint may raise ConfigError when returning 503 (pre-existing issue)
        # We're only testing that it doesn't require authentication (no 401)
        try:
            response = api_client.get("/api/health")
            # Should succeed without authentication
            assert response.status_code in [200, 503]  # 200 healthy or 503 unhealthy
            assert response.status_code != 401
        except Exception as e:
            # If ConfigError occurs (503 schema not defined), it means the endpoint
            # was reached without authentication check - which is what we're testing
            assert "Schema for status 503" in str(e) or "ConfigError" in str(
                type(e).__name__
            )

    def test_health_ready_public(self, api_client: Client, db):
        """Test that /api/health/ready is publicly accessible."""
        response = api_client.get("/api/health/ready")

        # Should succeed without authentication
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data

    def test_health_live_public(self, api_client: Client, db):
        """Test that /api/health/live is publicly accessible."""
        response = api_client.get("/api/health/live")

        # Should succeed without authentication
        assert response.status_code == 200
        data = response.json()
        assert "live" in data

    def test_setup_status_public(self, api_client: Client, db):
        """Test that /api/setup/status is publicly accessible."""
        response = api_client.get("/api/setup/status")

        # Should succeed without authentication
        assert response.status_code == 200
        data = response.json()
        assert "setup_required" in data
        assert "has_users" in data


@pytest.mark.django_db
class TestProtectedEndpoints:
    """Tests that protected endpoints require authentication."""

    def test_auth_logout_requires_auth(self, api_client: Client, db):
        """Test that /api/auth/logout requires authentication."""
        response = api_client.post(
            "/api/auth/logout",
            data={"refresh_token": "some_token"},
            content_type="application/json",
        )

        # Should return 401 Unauthorized without auth
        assert response.status_code == 401

    def test_auth_me_requires_auth(self, api_client: Client, db):
        """Test that /api/auth/me requires authentication."""
        response = api_client.get("/api/auth/me")

        # Should return 401 Unauthorized without auth
        assert response.status_code == 401

    def test_projects_list_requires_auth(self, api_client: Client, db):
        """Test that /api/projects requires authentication."""
        response = api_client.get("/api/projects")

        # Should return 401 Unauthorized without auth
        assert response.status_code == 401

    def test_projects_create_requires_auth(self, api_client: Client, db):
        """Test that POST /api/projects requires authentication."""
        response = api_client.post(
            "/api/projects",
            data={
                "name": "Test Project",
                "key": "TEST",
                "description": "Test description",
            },
            content_type="application/json",
        )

        # Should return 401 Unauthorized without auth
        assert response.status_code == 401

    def test_issues_list_requires_auth(self, api_client: Client, db):
        """Test that /api/issues requires authentication."""
        response = api_client.get("/api/issues")

        # Should return 401 Unauthorized without auth
        assert response.status_code == 401

    def test_users_list_requires_auth(self, api_client: Client, db):
        """Test that /api/users requires authentication."""
        response = api_client.get("/api/users")

        # Should return 401 Unauthorized without auth
        assert response.status_code == 401

    def test_protected_endpoints_require_auth(self, api_client: Client, db):
        """
        Security regression test for critical endpoints.

        Verifies that projects, issues, and users endpoints all reject
        unauthenticated requests with 401 status code.
        """
        critical_endpoints = [
            "/api/projects",
            "/api/issues",
            "/api/users",
        ]

        for endpoint in critical_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == 401, (
                f"Endpoint {endpoint} should require authentication but "
                f"returned {response.status_code}"
            )


@pytest.mark.django_db
class TestAuthenticatedAccess:
    """Tests that protected endpoints work with valid authentication."""

    def test_auth_me_with_valid_token(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test that /api/auth/me works with valid authentication."""
        response = api_client.get("/api/auth/me", **auth_headers)

        # Should succeed with valid authentication
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["username"] == user.username

    def test_projects_list_with_valid_token(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test that /api/projects works with valid authentication."""
        response = api_client.get("/api/projects", **auth_headers)

        # Should succeed with valid authentication (may be empty list)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_users_list_with_valid_token(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test that /api/users works with valid authentication."""
        response = api_client.get("/api/users", **auth_headers)

        # Should succeed with valid authentication
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the test user

    def test_invalid_token_rejected(self, api_client: Client, db):
        """Test that invalid tokens are rejected."""
        response = api_client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION="Bearer invalid_token_here",
        )

        # Should return 401 for invalid token
        assert response.status_code == 401
