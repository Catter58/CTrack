"""
Pydantic schemas for issues app.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from apps.users.schemas import UserSchema


class IssueTypeSchema(Schema):
    """Schema for issue type."""

    id: UUID
    name: str
    icon: str
    color: str
    is_subtask: bool
    is_epic: bool
    parent_types: list[str]
    order: int


class IssueTypeCreateSchema(Schema):
    """Schema for creating an issue type."""

    name: str
    icon: str = "checkmark"
    color: str = "#1192e8"
    is_subtask: bool = False
    parent_types: list[str] = []
    order: int = 1


class IssueTypeUpdateSchema(Schema):
    """Schema for updating an issue type."""

    name: str | None = None
    icon: str | None = None
    color: str | None = None
    is_subtask: bool | None = None
    parent_types: list[str] | None = None
    order: int | None = None


class StatusSchema(Schema):
    """Schema for status."""

    id: UUID
    name: str
    category: str
    color: str
    order: int


class StatusCreateSchema(Schema):
    """Schema for creating a status."""

    name: str
    category: str = "todo"  # todo, in_progress, done
    color: str = "#6f6f6f"
    order: int = 1


class StatusUpdateSchema(Schema):
    """Schema for updating a status."""

    name: str | None = None
    category: str | None = None
    color: str | None = None
    order: int | None = None


class IssueCreateSchema(Schema):
    """Schema for creating an issue."""

    title: str
    description: str = ""
    issue_type_id: UUID
    status_id: UUID | None = None
    priority: str = "medium"
    assignee_id: int | None = None
    parent_id: UUID | None = None
    epic_id: UUID | None = None
    story_points: int | None = None
    due_date: date | None = None


class IssueUpdateSchema(Schema):
    """Schema for updating an issue."""

    title: str | None = None
    description: str | None = None
    issue_type_id: UUID | None = None
    status_id: UUID | None = None
    priority: str | None = None
    assignee_id: int | None = None
    parent_id: UUID | None = None
    epic_id: UUID | None = None
    story_points: int | None = None
    due_date: date | None = None


class IssueSchema(Schema):
    """Schema for issue response."""

    id: UUID
    key: str
    issue_number: int
    title: str
    description: str
    priority: str
    story_points: int | None
    due_date: date | None
    custom_fields: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IssueDetailSchema(IssueSchema):
    """Schema for detailed issue response."""

    issue_type: IssueTypeSchema
    status: StatusSchema
    assignee: UserSchema | None
    reporter: UserSchema
    parent_id: UUID | None
    epic_id: UUID | None
    children_count: int = 0
    completed_children_count: int = 0


class IssueListSchema(Schema):
    """Schema for issue list item."""

    id: UUID
    key: str
    title: str
    priority: str
    story_points: int | None
    due_date: date | None
    created_at: datetime
    issue_type: IssueTypeSchema
    status: StatusSchema
    epic_id: UUID | None = None
    assignee: UserSchema | None


class CommentCreateSchema(Schema):
    """Schema for creating a comment."""

    content: str


class CommentSchema(Schema):
    """Schema for comment response."""

    id: UUID
    author: UserSchema
    content: str
    created_at: datetime
    updated_at: datetime


class WorkflowTransitionSchema(Schema):
    """Schema for workflow transition."""

    id: UUID
    from_status: StatusSchema
    to_status: StatusSchema
    name: str


class BulkUpdateItemSchema(Schema):
    """Schema for single item in bulk update."""

    key: str
    story_points: int | None = None


class BulkUpdateSchema(Schema):
    """Schema for bulk update request."""

    issues: list[BulkUpdateItemSchema]


class BulkUpdateResultSchema(Schema):
    """Schema for bulk update response."""

    updated: int
    failed: list[str]


class EpicSchema(Schema):
    """Schema for epic with progress."""

    id: UUID
    key: str
    title: str
    description: str
    priority: str
    status: StatusSchema
    # Progress statistics
    total_issues: int
    completed_issues: int
    total_story_points: int
    completed_story_points: int
