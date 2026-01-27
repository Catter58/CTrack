"""
Tests for setup wizard API endpoints.
"""

import json

import pytest
from django.test import Client

from apps.issues.models import IssueType, Status
from apps.users.models import User


@pytest.mark.django_db
class TestSetupStatus:
    """Tests for setup status endpoint."""

    def test_setup_required_no_users(self, api_client: Client, db):
        """Test setup status when no users exist."""
        response = api_client.get("/api/setup/status")

        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is True
        assert data["has_users"] is False

    def test_setup_not_required_with_users(self, api_client: Client, user: User):
        """Test setup status when users exist."""
        response = api_client.get("/api/setup/status")

        assert response.status_code == 200
        data = response.json()
        assert data["setup_required"] is False
        assert data["has_users"] is True


@pytest.mark.django_db
class TestSetupComplete:
    """Tests for setup completion endpoint."""

    def test_setup_complete_success(self, api_client: Client, db):
        """Test successful setup completion."""
        response = api_client.post(
            "/api/setup/complete",
            data=json.dumps(
                {
                    "admin_user": {
                        "email": "admin@example.com",
                        "username": "admin",
                        "password": "adminpassword123",
                        "full_name": "Admin User",
                    },
                    "org_settings": {
                        "name": "Test Organization",
                        "timezone": "Europe/Moscow",
                    },
                    "issue_type_template": "scrum",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify user was created
        admin = User.objects.get(email="admin@example.com")
        assert admin.is_staff is True
        assert admin.is_superuser is True

        # Verify default data was created
        assert IssueType.objects.filter(project__isnull=True).exists()
        assert Status.objects.filter(project__isnull=True).exists()

    def test_setup_complete_already_done(self, api_client: Client, user: User):
        """Test setup completion when setup is already done."""
        response = api_client.post(
            "/api/setup/complete",
            data=json.dumps(
                {
                    "admin_user": {
                        "email": "another@example.com",
                        "username": "another",
                        "password": "password123",
                    },
                    "org_settings": {"name": "Another Org"},
                    "issue_type_template": "scrum",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_setup_complete_short_password(self, api_client: Client, db):
        """Test setup completion with short password."""
        response = api_client.post(
            "/api/setup/complete",
            data=json.dumps(
                {
                    "admin_user": {
                        "email": "admin@example.com",
                        "username": "admin",
                        "password": "short",  # Less than 8 characters
                    },
                    "org_settings": {"name": "Org"},
                    "issue_type_template": "scrum",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_setup_complete_empty_template(self, api_client: Client, db):
        """Test setup completion with empty template."""
        response = api_client.post(
            "/api/setup/complete",
            data=json.dumps(
                {
                    "admin_user": {
                        "email": "admin@example.com",
                        "username": "admin",
                        "password": "password123",
                    },
                    "org_settings": {"name": "Org"},
                    "issue_type_template": "empty",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 201

        # Verify no issue types were created for empty template
        assert not IssueType.objects.filter(project__isnull=True).exists()
