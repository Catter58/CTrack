"""
Pydantic schemas for boards app.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

from apps.issues.schemas import IssueListSchema, StatusSchema


class BoardCreateSchema(Schema):
    """Schema for creating a board."""

    name: str
    board_type: str = "kanban"
    columns: list[str] | None = None
    filters: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class BoardUpdateSchema(Schema):
    """Schema for updating a board."""

    name: str | None = None
    columns: list[str] | None = None
    filters: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class BoardSchema(Schema):
    """Schema for board response."""

    id: UUID
    name: str
    board_type: str
    columns: list[str]
    filters: dict[str, Any]
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BoardColumnSchema(Schema):
    """Schema for board column with issues."""

    status: StatusSchema
    issues: list[IssueListSchema]
    count: int


class BoardDataSchema(Schema):
    """Schema for board data with columns and issues."""

    board: BoardSchema
    columns: list[BoardColumnSchema]
