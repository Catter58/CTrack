"""
Authentication classes for Django Ninja.
"""

from django.http import HttpRequest
from ninja.security import HttpBearer

from apps.users.jwt import verify_access_token
from apps.users.models import User


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
