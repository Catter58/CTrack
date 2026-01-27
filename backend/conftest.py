"""
Pytest configuration and fixtures for CTrack tests.
"""

import pytest
from django.test import Client

from apps.users.jwt import create_token_pair
from apps.users.models import User


@pytest.fixture
def api_client():
    """Return a Django test client."""
    return Client()


@pytest.fixture
def user(db):
    """Create and return a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpassword123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def auth_headers(user):
    """Return authorization headers for the test user."""
    tokens = create_token_pair(user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}


@pytest.fixture
def admin_auth_headers(admin_user):
    """Return authorization headers for the admin user."""
    tokens = create_token_pair(admin_user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}
