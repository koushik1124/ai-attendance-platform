import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ReportScopeKind(StrEnum):
    ALL_EMPLOYEES = "all_employees"
    EMPLOYEE = "employee"


class ReportBasis(StrEnum):
    SCHEDULED_DAYS = "scheduled_days"
    CALENDAR_DAYS = "calendar_days"


class ReportQuery(BaseModel):
    month: str
    employee_id: int | None = Field(default=None, ge=1)
    basis: ReportBasis = ReportBasis.SCHEDULED_DAYS

    @field_validator("month")
    @classmethod
    def validate_month(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
            raise ValueError("month must use YYYY-MM format")
        return value


class ReportScopeRead(BaseModel):
    kind: ReportScopeKind
    employee_id: int | None


class MonthlyTrendPoint(BaseModel):
    work_date: date
    present_count: int
    completed_count: int
    incomplete_count: int
    absent_count: int


class MonthlyTrendRead(BaseModel):
    month: str
    period_start: date
    period_end: date
    scope: ReportScopeRead
    basis: ReportBasis = ReportBasis.SCHEDULED_DAYS
    employee_count: int
    points: list[MonthlyTrendPoint]


class AttendanceSummaryRead(BaseModel):
    month: str
    period_start: date
    period_end: date
    scope: ReportScopeRead
    basis: ReportBasis = ReportBasis.SCHEDULED_DAYS
    employee_count: int
    expected_employee_days: int
    present_employee_days: int
    completed_employee_days: int
    incomplete_employee_days: int
    absent_employee_days: int
    attendance_rate: float | None
    total_working_hours: float | None = None


class AbsenteeismRead(BaseModel):
    month: str
    period_start: date
    period_end: date
    scope: ReportScopeRead
    basis: ReportBasis = ReportBasis.SCHEDULED_DAYS
    employee_count: int
    expected_employee_days: int
    absent_employee_days: int
    absenteeism_rate: float | None
