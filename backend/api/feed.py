"""
Activity Feed API endpoint.
"""

from datetime import datetime
from uuid import UUID

from django.db.models import Q
from ninja import Router, Schema

from apps.issues.models import ActivityAction, IssueActivity, IssueComment
from apps.projects.models import ProjectMembership
from apps.users.auth import AuthBearer


class FeedUserSchema(Schema):
    """User info for feed item."""

    id: int
    username: str
    full_name: str
    avatar: str | None = None

    @staticmethod
    def resolve_full_name(obj) -> str:
        parts = [obj.first_name, obj.last_name]
        return " ".join(p for p in parts if p).strip() or obj.username

    @staticmethod
    def resolve_avatar(obj) -> str | None:
        if obj.avatar:
            return obj.avatar.url
        return None


class FeedProjectSchema(Schema):
    """Project info for feed item."""

    key: str
    name: str


class FeedIssueSchema(Schema):
    """Issue info for feed item."""

    key: str
    title: str
    project: FeedProjectSchema


class FeedItemSchema(Schema):
    """Single activity feed item."""

    id: UUID
    action: str
    field_name: str
    old_value: dict | None
    new_value: dict | None
    created_at: datetime
    issue: FeedIssueSchema
    user: FeedUserSchema | None
    comment_preview: str | None = None


class FeedResponseSchema(Schema):
    """Paginated feed response with cursor."""

    items: list[FeedItemSchema]
    next_cursor: str | None


router = Router(auth=AuthBearer())


def encode_cursor(created_at: datetime, activity_id: UUID) -> str:
    """Encode cursor from created_at and id."""
    timestamp = created_at.isoformat()
    return f"{timestamp}|{activity_id}"


def decode_cursor(cursor: str) -> tuple[datetime, UUID] | None:
    """Decode cursor into created_at and id."""
    try:
        parts = cursor.split("|")
        if len(parts) != 2:
            return None
        created_at = datetime.fromisoformat(parts[0])
        activity_id = UUID(parts[1])
        return created_at, activity_id
    except (ValueError, TypeError):
        return None


def get_comment_preview(activity: IssueActivity) -> str | None:
    """Get comment preview for commented action."""
    if activity.action != ActivityAction.COMMENTED:
        return None

    comment = (
        IssueComment.objects.filter(
            issue=activity.issue,
            author=activity.user,
            created_at__lte=activity.created_at,
        )
        .order_by("-created_at")
        .first()
    )

    if comment:
        content = comment.content
        if len(content) > 200:
            return content[:200] + "..."
        return content
    return None


@router.get(
    "/feed",
    response={200: FeedResponseSchema},
)
def get_feed(
    request,
    user_id: int = None,
    project_id: UUID = None,
    action: str = None,
    date_from: datetime = None,
    date_to: datetime = None,
    cursor: str = None,
    limit: int = 50,
):
    """
    Get activity feed from all projects where user is a member.

    Cursor-based pagination for infinite scroll.
    Cursor format: ISO datetime|UUID (created_at|id).

    Query parameters:
    - user_id: Filter by action performer
    - project_id: Filter by project UUID
    - action: Filter by action type (status_changed, commented, etc.)
    - date_from, date_to: Filter by date range
    - cursor: Pagination cursor (created_at|id)
    - limit: Number of items (default 50, max 100)
    """
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100

    user_project_ids = ProjectMembership.objects.filter(user=request.auth).values_list(
        "project_id", flat=True
    )

    queryset = IssueActivity.objects.filter(
        issue__project_id__in=user_project_ids
    ).select_related(
        "user",
        "issue",
        "issue__project",
    )

    if user_id is not None:
        queryset = queryset.filter(user_id=user_id)

    if project_id is not None:
        queryset = queryset.filter(issue__project_id=project_id)

    if action:
        queryset = queryset.filter(action=action)

    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    if cursor:
        decoded = decode_cursor(cursor)
        if decoded:
            cursor_time, cursor_id = decoded
            queryset = queryset.filter(
                Q(created_at__lt=cursor_time)
                | Q(created_at=cursor_time, id__lt=cursor_id)
            )

    queryset = queryset.order_by("-created_at", "-id")

    activities = list(queryset[: limit + 1])

    has_more = len(activities) > limit
    if has_more:
        activities = activities[:limit]

    items = []
    for activity in activities:
        item_data = {
            "id": activity.id,
            "action": activity.action,
            "field_name": activity.field_name,
            "old_value": activity.old_value,
            "new_value": activity.new_value,
            "created_at": activity.created_at,
            "issue": {
                "key": activity.issue.key,
                "title": activity.issue.title,
                "project": {
                    "key": activity.issue.project.key,
                    "name": activity.issue.project.name,
                },
            },
            "user": activity.user,
            "comment_preview": get_comment_preview(activity),
        }
        items.append(item_data)

    next_cursor = None
    if has_more and activities:
        last = activities[-1]
        next_cursor = encode_cursor(last.created_at, last.id)

    return 200, {
        "items": items,
        "next_cursor": next_cursor,
    }
