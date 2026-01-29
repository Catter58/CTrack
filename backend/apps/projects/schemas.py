"""
Pydantic schemas for projects app.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from apps.users.schemas import UserSchema


class ProjectCreateSchema(Schema):
    """Schema for creating a project."""

    key: str
    name: str
    description: str = ""
    settings: dict[str, Any] | None = None


class ProjectUpdateSchema(Schema):
    """Schema for updating a project."""

    name: str | None = None
    description: str | None = None
    settings: dict[str, Any] | None = None
    is_archived: bool | None = None


class ProjectSchema(Schema):
    """Schema for project response."""

    id: UUID
    key: str
    name: str
    description: str
    owner_id: int
    is_archived: bool
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProjectWithOwnerSchema(ProjectSchema):
    """Schema for project with owner details."""

    owner: UserSchema


class MembershipSchema(Schema):
    """Schema for project membership."""

    user: UserSchema
    role: str
    joined_at: datetime


class MemberAddSchema(Schema):
    """Schema for adding a member."""

    user_id: int
    role: str = "developer"


class MemberUpdateSchema(Schema):
    """Schema for updating member role."""

    role: str


class ProjectListSchema(Schema):
    """Schema for project list item."""

    id: UUID
    key: str
    name: str
    description: str
    is_archived: bool
    created_at: datetime
    member_count: int = 0
    my_role: str | None = None


class SavedFilterSchema(Schema):
    """Schema for saved filter response."""

    id: UUID
    project_id: UUID
    user_id: int
    name: str
    filters: dict[str, Any]
    columns: list[str]
    sort_by: str
    sort_order: str
    is_shared: bool
    created_at: datetime
    updated_at: datetime


class SavedFilterCreateSchema(Schema):
    """Schema for creating a saved filter."""

    name: str
    filters: dict[str, Any] = {}
    columns: list[str] = []
    sort_by: str = ""
    sort_order: str = "asc"
    is_shared: bool = False


class SavedFilterUpdateSchema(Schema):
    """Schema for updating a saved filter."""

    name: str | None = None
    filters: dict[str, Any] | None = None
    columns: list[str] | None = None
    sort_by: str | None = None
    sort_order: str | None = None
    is_shared: bool | None = None


class PaginatedIssueListSchema(Schema):
    """Schema for paginated issue list."""

    items: list
    total: int
    limit: int
    offset: int
