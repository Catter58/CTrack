"""
Event publishing module for real-time updates.

Publishes events to Redis channels for SSE consumption.
"""

import json
import time
from uuid import UUID

import redis
from django.conf import settings


class EventType:
    """Event type constants."""

    # Issue events
    ISSUE_CREATED = "issue.created"
    ISSUE_UPDATED = "issue.updated"
    ISSUE_MOVED = "issue.moved"
    ISSUE_DELETED = "issue.deleted"
    ISSUE_EDITING = "issue.editing"

    # Sprint events
    SPRINT_UPDATED = "sprint.updated"

    # Comment events
    COMMENT_ADDED = "comment.added"

    # Member events
    MEMBER_JOINED = "member.joined"

    # Activity feed events
    ACTIVITY_CREATED = "activity.created"


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Get Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.Redis.from_url(redis_url)
    return _redis_client


def publish_event(project_id: UUID | str, event_type: str, data: dict) -> None:
    """
    Publish event to project channel.

    Args:
        project_id: The project UUID
        event_type: One of EventType constants
        data: Event payload data
    """
    r = get_redis()
    message = {
        "type": event_type,
        "project_id": str(project_id),
        "data": data,
        "timestamp": time.time(),
    }
    channel = f"project:{project_id}"
    r.publish(channel, json.dumps(message))


def publish_issue_created(project_id: UUID | str, issue_data: dict) -> None:
    """Publish issue.created event."""
    publish_event(project_id, EventType.ISSUE_CREATED, issue_data)


def publish_issue_updated(project_id: UUID | str, issue_data: dict) -> None:
    """Publish issue.updated event."""
    publish_event(project_id, EventType.ISSUE_UPDATED, issue_data)


def publish_issue_moved(
    project_id: UUID | str, issue_key: str, from_status: str, to_status: str
) -> None:
    """Publish issue.moved event (status change)."""
    publish_event(
        project_id,
        EventType.ISSUE_MOVED,
        {
            "key": issue_key,
            "from_status": from_status,
            "to_status": to_status,
        },
    )


def publish_issue_deleted(project_id: UUID | str, issue_key: str) -> None:
    """Publish issue.deleted event."""
    publish_event(project_id, EventType.ISSUE_DELETED, {"key": issue_key})


def publish_sprint_updated(project_id: UUID | str, sprint_data: dict) -> None:
    """Publish sprint.updated event."""
    publish_event(project_id, EventType.SPRINT_UPDATED, sprint_data)


def publish_comment_added(
    project_id: UUID | str, issue_key: str, comment_data: dict
) -> None:
    """Publish comment.added event."""
    publish_event(
        project_id,
        EventType.COMMENT_ADDED,
        {
            "issue_key": issue_key,
            **comment_data,
        },
    )


def publish_member_joined(
    project_id: UUID | str, user_id: int, username: str, role: str
) -> None:
    """Publish member.joined event."""
    publish_event(
        project_id,
        EventType.MEMBER_JOINED,
        {
            "user_id": user_id,
            "username": username,
            "role": role,
        },
    )


def publish_issue_editing(
    project_id: UUID | str,
    issue_key: str,
    user_id: int,
    username: str,
    full_name: str,
    avatar_url: str | None,
    is_editing: bool,
) -> None:
    """Publish issue.editing event when a user starts/stops editing an issue."""
    publish_event(
        project_id,
        EventType.ISSUE_EDITING,
        {
            "issue_key": issue_key,
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "is_editing": is_editing,
        },
    )


def publish_activity(
    project_id: UUID | str,
    activity_data: dict,
) -> None:
    """
    Publish activity.created event for real-time feed updates.

    Args:
        project_id: The project UUID
        activity_data: Activity data matching FeedItemSchema structure
    """
    publish_event(project_id, EventType.ACTIVITY_CREATED, activity_data)
