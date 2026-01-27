from datetime import date, datetime
from uuid import UUID

from ninja import Schema


class SprintCreateSchema(Schema):
    name: str
    goal: str = ""
    start_date: date
    end_date: date


class SprintUpdateSchema(Schema):
    name: str | None = None
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class SprintSchema(Schema):
    id: UUID
    project_id: UUID
    name: str
    goal: str
    start_date: date
    end_date: date
    status: str
    initial_story_points: int | None
    completed_story_points: int | None
    created_at: datetime
    updated_at: datetime


class SprintWithStatsSchema(SprintSchema):
    total_story_points: int
    remaining_story_points: int
    total_issues: int
    completed_issues: int
    remaining_issues: int


class SprintCompleteSchema(Schema):
    move_incomplete_to: str | UUID | None = None


class SprintVelocityItemSchema(Schema):
    id: str
    name: str
    start_date: str
    end_date: str
    committed_story_points: int
    completed_story_points: int


class VelocitySchema(Schema):
    sprints: list[SprintVelocityItemSchema]
    average_velocity: float
    total_sprints: int


class BurndownPointSchema(Schema):
    date: str
    value: float


class BurndownSchema(Schema):
    sprint_id: str
    sprint_name: str
    start_date: str
    end_date: str
    initial_story_points: int
    ideal: list[BurndownPointSchema]
    actual: list[BurndownPointSchema]
