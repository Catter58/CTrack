"""
Pydantic schemas for users app.
"""

from ninja import Schema


class UserSchema(Schema):
    """User response schema."""

    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    full_name: str = ""
    avatar: str | None = None
    bio: str = ""
    timezone: str = "Europe/Moscow"
    is_active: bool = True
    is_staff: bool = False

    @staticmethod
    def resolve_full_name(obj) -> str:
        """Combine first and last name into full name."""
        parts = [obj.first_name, obj.last_name]
        return " ".join(p for p in parts if p).strip() or obj.username

    @staticmethod
    def resolve_avatar(obj) -> str | None:
        if obj.avatar:
            return obj.avatar.url
        return None


class UserCreateSchema(Schema):
    """User registration request schema."""

    email: str
    username: str
    password: str
    first_name: str = ""
    last_name: str = ""


class LoginSchema(Schema):
    """Login request schema."""

    email: str
    password: str


class TokenSchema(Schema):
    """Token pair response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(Schema):
    """Refresh token request schema."""

    refresh_token: str


class PasswordChangeSchema(Schema):
    """Password change request schema."""

    current_password: str
    new_password: str


class UserUpdateSchema(Schema):
    """User profile update schema."""

    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    timezone: str | None = None


class MessageSchema(Schema):
    """Generic message response."""

    message: str


class ErrorSchema(Schema):
    """Error response schema."""

    detail: str
