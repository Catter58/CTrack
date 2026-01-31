"""
Authentication API endpoints.
"""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ninja import Router

from apps.users.auth import AuthBearer
from apps.users.jwt import (
    blacklist_token,
    create_token_pair,
    verify_refresh_token,
)
from apps.users.models import User
from apps.users.schemas import (
    ErrorSchema,
    LoginSchema,
    MessageSchema,
    RefreshTokenSchema,
    TokenSchema,
    UserCreateSchema,
    UserSchema,
)

router = Router(auth=AuthBearer())


@router.post("/register", response={201: TokenSchema, 400: ErrorSchema}, auth=None)
def register(request, data: UserCreateSchema):
    """
    Register a new user.

    Creates a new user account and returns access/refresh tokens.
    """
    # Check if email already exists
    if User.objects.filter(email=data.email).exists():
        return 400, {"detail": "Пользователь с таким email уже существует"}

    # Check if username already exists
    if User.objects.filter(username=data.username).exists():
        return 400, {"detail": "Пользователь с таким именем уже существует"}

    # Validate password
    try:
        validate_password(data.password)
    except ValidationError as e:
        return 400, {"detail": " ".join(e.messages)}

    # Create user
    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
    )

    # Generate tokens
    tokens = create_token_pair(user.id)

    return 201, {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.post("/login", response={200: TokenSchema, 401: ErrorSchema}, auth=None)
def login(request, data: LoginSchema):
    """
    Login user with email and password.

    Returns access and refresh tokens on success.
    """
    # Try to find user by email
    try:
        user = User.objects.get(email=data.email)
    except User.DoesNotExist:
        return 401, {"detail": "Неверный email или пароль"}

    # Authenticate with username (Django uses username for auth)
    user = authenticate(request, username=user.username, password=data.password)

    if user is None:
        return 401, {"detail": "Неверный email или пароль"}

    if not user.is_active:
        return 401, {"detail": "Учётная запись деактивирована"}

    # Generate tokens
    tokens = create_token_pair(user.id)

    return 200, {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.post("/refresh", response={200: TokenSchema, 401: ErrorSchema}, auth=None)
def refresh(request, data: RefreshTokenSchema):
    """
    Refresh access token using refresh token.

    Returns new access and refresh tokens, invalidates old refresh token.
    """
    payload = verify_refresh_token(data.refresh_token)

    if payload is None:
        return 401, {"detail": "Невалидный или истёкший refresh token"}

    # Get user
    try:
        user_id = int(payload["sub"])
        user = User.objects.get(id=user_id, is_active=True)
    except (ValueError, User.DoesNotExist):
        return 401, {"detail": "Пользователь не найден"}

    # Blacklist old refresh token
    old_jti = payload.get("jti")
    if old_jti:
        blacklist_token(old_jti)

    # Generate new tokens
    tokens = create_token_pair(user.id)

    return 200, {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer",
    }


@router.post("/logout", response={200: MessageSchema, 401: ErrorSchema})
def logout(request, data: RefreshTokenSchema):
    """
    Logout user by invalidating refresh token.

    Requires authentication. Adds refresh token to blacklist.
    """
    payload = verify_refresh_token(data.refresh_token)

    if payload is None:
        return 401, {"detail": "Невалидный refresh token"}

    # Verify token belongs to current user
    try:
        token_user_id = int(payload["sub"])
        if token_user_id != request.auth.id:
            return 401, {"detail": "Token не принадлежит текущему пользователю"}
    except (ValueError, KeyError):
        return 401, {"detail": "Невалидный refresh token"}

    # Blacklist refresh token
    jti = payload.get("jti")
    if jti:
        blacklist_token(jti)

    return 200, {"message": "Успешный выход из системы"}


@router.get("/me", response={200: UserSchema, 401: ErrorSchema})
def me(request):
    """
    Get current authenticated user's profile.

    Requires valid access token in Authorization header.
    """
    return 200, request.auth
