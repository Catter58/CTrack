"""
Authentication classes for Django Ninja.
"""

from django.http import HttpRequest
from ninja.security import APIKeyQuery, HttpBearer

from apps.users.jwt import verify_access_token
from apps.users.models import User


class AuthQueryToken(APIKeyQuery):
    """
    JWT token authentication via query parameter.

    Used for endpoints that don't support headers (e.g., SSE/EventSource).

    Usage:
        @api.get("/events", auth=AuthQueryToken())
        def sse_endpoint(request):
            user = request.auth
            return StreamingResponse(...)
    """

    param_name = "token"

    def authenticate(self, request: HttpRequest, key: str | None) -> User | None:
        """
        Authenticate request using JWT token from query parameter.

        Args:
            request: The HTTP request
            key: The token from query parameter

        Returns:
            User object if valid, None otherwise
        """
        if not key:
            return None

        payload = verify_access_token(key)
        if payload is None:
            return None

        try:
            user_id = int(payload["sub"])
            user = User.objects.filter(id=user_id, is_active=True).first()
            return user
        except (KeyError, ValueError, User.DoesNotExist):
            return None


class AuthBearer(HttpBearer):
    """
    JWT Bearer token authentication for Django Ninja.

    Usage:
        @api.get("/protected", auth=AuthBearer())
        def protected_endpoint(request):
            user = request.auth  # This is the User object
            return {"user_id": user.id}
    """

    def authenticate(self, request: HttpRequest, token: str) -> User | None:
        """
        Authenticate request using JWT Bearer token.

        Args:
            request: The HTTP request
            token: The Bearer token from Authorization header

        Returns:
            User object if valid, None otherwise
        """
        payload = verify_access_token(token)
        if payload is None:
            return None

        try:
            user_id = int(payload["sub"])
            user = User.objects.filter(id=user_id, is_active=True).first()
            return user
        except (KeyError, ValueError, User.DoesNotExist):
            return None


class OptionalAuthBearer(HttpBearer):
    """
    Optional JWT Bearer token authentication.

    Same as AuthBearer but allows unauthenticated access.
    request.auth will be User or None.
    """

    def authenticate(self, request: HttpRequest, token: str) -> User | None:
        """Authenticate if token provided, otherwise return None."""
        if not token:
            return None

        payload = verify_access_token(token)
        if payload is None:
            return None

        try:
            user_id = int(payload["sub"])
            user = User.objects.filter(id=user_id, is_active=True).first()
            return user
        except (KeyError, ValueError, User.DoesNotExist):
            return None


# Global auth instance for easy import
auth_bearer = AuthBearer()
optional_auth = OptionalAuthBearer()
auth_query_token = AuthQueryToken()
