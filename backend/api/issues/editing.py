"""
Editing session endpoints for issues.
"""

import json

import redis
from django.conf import settings
from ninja import Router

from apps.core.events import publish_issue_editing
from apps.issues.schemas import EditingStatusSchema, EditingUserSchema
from apps.issues.services import IssueService
from apps.projects.services import ProjectService
from apps.users.auth import AuthBearer
from apps.users.schemas import ErrorSchema

# Redis key prefix for editing sessions
EDITING_KEY_PREFIX = "issue_editing:"
EDITING_TTL = 60  # 60 seconds TTL

router = Router(auth=AuthBearer())


# Helper functions


def _get_redis() -> redis.Redis:
    """Get Redis client for editing sessions."""
    redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(redis_url)


def _get_editing_key(issue_key: str) -> str:
    """Get Redis key for issue editing session."""
    return f"{EDITING_KEY_PREFIX}{issue_key}"


def _get_editors(r: redis.Redis, key: str) -> list[EditingUserSchema]:
    """Get list of current editors from Redis hash."""
    editors = []
    raw_editors = r.hgetall(key)

    for editor_json in raw_editors.values():
        try:
            editor_data = json.loads(editor_json)
            editors.append(
                EditingUserSchema(
                    user_id=editor_data["user_id"],
                    username=editor_data["username"],
                    full_name=editor_data["full_name"],
                    avatar_url=editor_data.get("avatar_url") or None,
                )
            )
        except (json.JSONDecodeError, KeyError):
            continue

    return editors


# Editing session endpoints


@router.post(
    "/issues/{issue_key}/editing",
    response={200: EditingStatusSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def start_editing(request, issue_key: str):
    """
    Start an editing session for an issue.

    Sets a Redis key with TTL to track who is editing.
    Broadcasts SSE event to notify other users.
    """
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    user = request.auth
    r = _get_redis()
    key = _get_editing_key(issue_key)

    # Get user info
    full_name = user.get_full_name() or user.username
    avatar_url = user.avatar.url if user.avatar else None

    # Store editor info in Redis hash
    editor_data = {
        "user_id": user.id,
        "username": user.username,
        "full_name": full_name,
        "avatar_url": avatar_url or "",
    }

    # Use hash to allow multiple editors
    r.hset(key, str(user.id), json.dumps(editor_data))
    r.expire(key, EDITING_TTL)

    # Publish SSE event
    publish_issue_editing(
        project_id=issue.project_id,
        issue_key=issue_key,
        user_id=user.id,
        username=user.username,
        full_name=full_name,
        avatar_url=avatar_url,
        is_editing=True,
    )

    # Return current editors
    editors = _get_editors(r, key)
    return 200, {"is_editing": len(editors) > 0, "editors": editors}


@router.delete(
    "/issues/{issue_key}/editing",
    response={200: EditingStatusSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def stop_editing(request, issue_key: str):
    """
    Stop an editing session for an issue.

    Removes user from Redis and broadcasts SSE event.
    """
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    user = request.auth
    r = _get_redis()
    key = _get_editing_key(issue_key)

    # Remove this user from editors
    r.hdel(key, str(user.id))

    # Publish SSE event
    full_name = user.get_full_name() or user.username
    avatar_url = user.avatar.url if user.avatar else None

    publish_issue_editing(
        project_id=issue.project_id,
        issue_key=issue_key,
        user_id=user.id,
        username=user.username,
        full_name=full_name,
        avatar_url=avatar_url,
        is_editing=False,
    )

    # Return current editors
    editors = _get_editors(r, key)
    return 200, {"is_editing": len(editors) > 0, "editors": editors}


@router.get(
    "/issues/{issue_key}/editing",
    response={200: EditingStatusSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def get_editing_status(request, issue_key: str):
    """
    Get current editing status for an issue.

    Returns list of users currently editing.
    """
    issue = IssueService.get_issue_by_key(issue_key)

    if not issue:
        return 404, {"detail": "Задача не найдена"}

    if not ProjectService.is_member(issue.project, request.auth):
        return 403, {"detail": "Нет доступа к проекту"}

    r = _get_redis()
    key = _get_editing_key(issue_key)
    editors = _get_editors(r, key)

    return 200, {"is_editing": len(editors) > 0, "editors": editors}
