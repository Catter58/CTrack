"""
Server-Sent Events (SSE) API endpoint for real-time updates.
"""

import json
import time
from uuid import UUID

import redis
from django.conf import settings
from django.http import StreamingHttpResponse
from ninja import Router

from apps.projects.models import ProjectMembership
from apps.users.auth import AuthQueryToken

router = Router(auth=AuthQueryToken(), tags=["Events"])


def get_user_project_ids(user) -> list[str]:
    """Get list of project IDs where user is a member."""
    return list(
        ProjectMembership.objects.filter(user=user).values_list("project_id", flat=True)
    )


def format_sse(data: dict) -> str:
    """Format data as SSE message."""
    return f"data: {json.dumps(data)}\n\n"


@router.get("/events")
def event_stream(request, project_id: UUID = None):
    """
    SSE endpoint for real-time updates.

    Streams events for all projects the user is a member of,
    or optionally filter by a specific project_id.

    Events:
    - issue.created - new issue created
    - issue.updated - issue fields changed
    - issue.moved - issue status changed (board move)
    - issue.deleted - issue deleted
    - sprint.updated - sprint changed
    - comment.added - new comment
    - member.joined - new project member
    - connected - initial connection confirmation
    - heartbeat - keep-alive signal (every 30 seconds)
    """

    def event_generator():
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        r = redis.Redis.from_url(redis_url)
        pubsub = r.pubsub()

        # Get user's projects
        user = request.auth
        project_ids = get_user_project_ids(user)

        # Build channel list
        if project_id:
            # Verify user has access to this project
            if str(project_id) in [str(pid) for pid in project_ids]:
                channels = [f"project:{project_id}"]
            else:
                # User doesn't have access to this project
                yield format_sse(
                    {"type": "error", "message": "Access denied to project"}
                )
                return
        else:
            channels = [f"project:{pid}" for pid in project_ids]

        if not channels:
            yield format_sse({"type": "error", "message": "No projects available"})
            return

        # Subscribe to channels
        pubsub.subscribe(*channels)

        # Send initial connection event
        yield format_sse(
            {
                "type": "connected",
                "timestamp": time.time(),
                "channels": len(channels),
            }
        )

        last_heartbeat = time.time()
        timeout = 1.0  # Check for messages every second

        try:
            while True:
                # Check for messages with timeout
                message = pubsub.get_message(timeout=timeout)

                # Send heartbeat every 30 seconds
                current_time = time.time()
                if current_time - last_heartbeat > 30:
                    yield format_sse({"type": "heartbeat", "timestamp": current_time})
                    last_heartbeat = current_time

                if message is None:
                    continue

                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield format_sse(data)
                    except (json.JSONDecodeError, TypeError):
                        # Skip invalid messages
                        continue

        except GeneratorExit:
            # Client disconnected
            pass
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    response = StreamingHttpResponse(
        event_generator(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
