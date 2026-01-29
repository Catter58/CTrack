from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema


class CustomFieldDefinitionSchema(Schema):
    id: UUID
    project_id: UUID | None
    name: str
    field_key: str
    field_type: str
    options: list[str]
    is_required: bool
    default_value: Any | None
    description: str
    order: int
    applicable_types: list[UUID]
    created_at: datetime
    updated_at: datetime


class CustomFieldDefinitionCreateSchema(Schema):
    name: str
    field_type: str
    options: list[str] = []
    is_required: bool = False
    default_value: Any | None = None
    description: str = ""
    applicable_types: list[UUID] = []


class CustomFieldDefinitionUpdateSchema(Schema):
    name: str | None = None
    options: list[str] | None = None
    is_required: bool | None = None
    default_value: Any | None = None
    description: str | None = None
    order: int | None = None
    applicable_types: list[UUID] | None = None
