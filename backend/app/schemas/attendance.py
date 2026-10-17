from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AttendanceStatus(StrEnum):
    NOT_STARTED = "not_started"
    PUNCHED_IN = "punched_in"
    PUNCHED_OUT = "punched_out"


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_date: date
    punch_in_at: datetime | None
    punch_out_at: datetime | None
    working_seconds: int | None = None
    working_hours: float | None = None

    @field_validator("punch_in_at", "punch_out_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AttendanceStateRead(BaseModel):
    work_date: date
    status: AttendanceStatus
    attendance: AttendanceRead | None


class AttendanceHistoryQuery(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
