"""
Tests for authentication API endpoints.
"""

import json

import pytest
from django.test import Client

from apps.users.models import User


@pytest.mark.django_db
class TestAuthLogin:
    """Tests for login endpoint."""

    def test_login_success(self, api_client: Client, user: User):
        """Test successful login with valid credentials."""
        response = api_client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": "test@example.com", "password": "testpassword123"}
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, api_client: Client, user: User):
        """Test login with invalid password."""
        response = api_client.post(
            "/api/auth/login",
            data=json.dumps({"email": "test@example.com", "password": "wrongpassword"}),
            content_type="application/json",
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_login_invalid_email(self, api_client: Client):
        """Test login with non-existent email."""
        response = api_client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": "nonexistent@example.com", "password": "password"}
            ),
            content_type="application/json",
        )

        assert response.status_code == 401


@pytest.mark.django_db
class TestAuthRegister:
    """Tests for registration endpoint."""

    def test_register_success(self, api_client: Client, db):
        """Test successful user registration."""
        response = api_client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "newuser@example.com",
                    "username": "newuser",
                    "password": "newpassword123",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify user was created
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_duplicate_email(self, api_client: Client, user: User):
        """Test registration with existing email."""
        response = api_client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "test@example.com",  # Same as existing user
                    "username": "anotheruser",
                    "password": "password123",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_register_short_password(self, api_client: Client, db):
        """Test registration with too short password."""
        response = api_client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "short@example.com",
                    "username": "shortpwd",
                    "password": "short",  # Less than 8 characters
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestAuthMe:
    """Tests for current user endpoint."""

    def test_me_authenticated(self, api_client: Client, user: User, auth_headers: dict):
        """Test getting current user when authenticated."""
        response = api_client.get("/api/auth/me", **auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"

    def test_me_unauthenticated(self, api_client: Client):
        """Test getting current user without authentication."""
        response = api_client.get("/api/auth/me")

        assert response.status_code == 401


@pytest.mark.django_db
class TestAuthRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(
        self, api_client: Client, user: User, auth_headers: dict
    ):
        """Test successful token refresh."""
        # First, login to get tokens
        login_response = api_client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": "test@example.com", "password": "testpassword123"}
            ),
            content_type="application/json",
        )
        tokens = login_response.json()

        # Then, refresh the token
        response = api_client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": tokens["refresh_token"]}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_invalid(self, api_client: Client):
        """Test refresh with invalid token."""
        response = api_client.post(
            "/api/auth/refresh",
            data=json.dumps({"refresh_token": "invalid_token"}),
            content_type="application/json",
        )

        assert response.status_code == 401
