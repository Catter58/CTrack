"""Schemas for project reports API."""

from datetime import date
from enum import Enum
from uuid import UUID

from ninja import Schema


class PeriodType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class StatusStatsSchema(Schema):
    status_id: UUID
    status_name: str
    category: str
    status_color: str
    count: int


class TypeStatsSchema(Schema):
    type_id: UUID
    type_name: str
    count: int


class AssigneeStatsSchema(Schema):
    assignee_id: int | None
    assignee_name: str
    count: int


class PriorityStatsSchema(Schema):
    priority: str
    count: int


class ReportSummarySchema(Schema):
    total_issues: int
    by_status: list[StatusStatsSchema]
    by_type: list[TypeStatsSchema]
    by_assignee: list[AssigneeStatsSchema]
    by_priority: list[PriorityStatsSchema]


class CreatedVsResolvedItemSchema(Schema):
    date: date
    created: int
    resolved: int


class CreatedVsResolvedSchema(Schema):
    period: str
    date_from: date
    date_to: date
    data: list[CreatedVsResolvedItemSchema]


class CycleTimeGroupSchema(Schema):
    group_name: str
    group_id: UUID | None
    avg_hours: float | None
    median_hours: float | None
    count: int


class CycleTimeSchema(Schema):
    overall_avg_hours: float | None
    overall_median_hours: float | None
    total_completed: int
    by_type: list[CycleTimeGroupSchema]
    by_priority: list[CycleTimeGroupSchema]
