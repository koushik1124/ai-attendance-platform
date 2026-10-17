from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.reports import (
    AbsenteeismRead,
    AttendanceSummaryRead,
    MonthlyTrendRead,
    ReportBasis,
    ReportQuery,
)
from app.services import reports as reports_service


router = APIRouter(prefix="/reports", tags=["reports"])


def _report_query(
    month: str = Query(...),
    employee_id: int | None = Query(default=None),
    basis: ReportBasis = Query(default=ReportBasis.SCHEDULED_DAYS),
) -> ReportQuery:
    try:
        return ReportQuery(month=month, employee_id=employee_id, basis=basis)
    except ValidationError as exc:
        details = [
            {
                "location": ["query", *error["loc"]],
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        raise AppError(
            422,
            "validation_error",
            "Request validation failed.",
            details=details,
        ) from exc


@router.get("/monthly-trends", response_model=MonthlyTrendRead)
def monthly_trends(
    query: ReportQuery = Depends(_report_query),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyTrendRead:
    return reports_service.monthly_trends(db, current_user, query)


@router.get("/attendance-summary", response_model=AttendanceSummaryRead)
def attendance_summary(
    query: ReportQuery = Depends(_report_query),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttendanceSummaryRead:
    return reports_service.attendance_summary(db, current_user, query)


@router.get("/absenteeism", response_model=AbsenteeismRead)
def absenteeism(
    query: ReportQuery = Depends(_report_query),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AbsenteeismRead:
    return reports_service.absenteeism(db, current_user, query)
