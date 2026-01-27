"""
JWT token utilities for CTrack authentication.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from jose import JWTError, jwt

# Redis key prefix for token blacklist
BLACKLIST_PREFIX = "jwt_blacklist:"


def create_access_token(
    user_id: int, extra_claims: dict[str, Any] | None = None
) -> str:
    """
    Create a new access token for a user.

    Args:
        user_id: The user's database ID
        extra_claims: Optional additional claims to include

    Returns:
        Encoded JWT access token string
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "iat": now,
        "jti": str(uuid4()),
    }

    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Create a new refresh token for a user.

    Args:
        user_id: The user's database ID

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    claims = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": now,
        "jti": str(uuid4()),
    }

    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(user_id: int) -> dict[str, str]:
    """
    Create both access and refresh tokens for a user.

    Args:
        user_id: The user's database ID

    Returns:
        Dictionary with 'access_token' and 'refresh_token'
    """
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
    }


def decode_token(token: str, verify_exp: bool = True) -> dict[str, Any] | None:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token string
        verify_exp: Whether to verify expiration (default True)

    Returns:
        Decoded claims dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": verify_exp},
        )
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> dict[str, Any] | None:
    """
    Verify an access token and return its claims.

    Args:
        token: The JWT access token string

    Returns:
        Decoded claims dict or None if invalid/expired/wrong type
    """
    payload = decode_token(token)
    if payload is None:
        return None

    # Verify token type
    if payload.get("type") != "access":
        return None

    return payload


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """
    Verify a refresh token and check it's not blacklisted.

    Args:
        token: The JWT refresh token string

    Returns:
        Decoded claims dict or None if invalid/expired/blacklisted
    """
    payload = decode_token(token)
    if payload is None:
        return None

    # Verify token type
    if payload.get("type") != "refresh":
        return None

    # Check blacklist
    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        return None

    return payload


def blacklist_token(jti: str, expires_in_seconds: int | None = None) -> None:
    """
    Add a token's JTI to the blacklist.

    Args:
        jti: The token's unique identifier (jti claim)
        expires_in_seconds: How long to keep in blacklist (default: 7 days)
    """
    if expires_in_seconds is None:
        # Default to refresh token lifetime
        expires_in_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    cache.set(f"{BLACKLIST_PREFIX}{jti}", "1", expires_in_seconds)


def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        jti: The token's unique identifier (jti claim)

    Returns:
        True if blacklisted, False otherwise
    """
    return cache.get(f"{BLACKLIST_PREFIX}{jti}") is not None


def get_user_id_from_token(token: str) -> int | None:
    """
    Extract user ID from a valid access token.

    Args:
        token: The JWT access token string

    Returns:
        User ID as integer or None if invalid
    """
    payload = verify_access_token(token)
    if payload is None:
        return None

    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        return None
