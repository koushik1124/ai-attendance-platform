from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.attendance import AttendanceRecord
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceHistoryQuery,
    AttendanceRead,
    AttendanceStateRead,
    AttendanceStatus,
)
from app.services import attendance as attendance_service


router = APIRouter(prefix="/attendance", tags=["attendance"])


def _state_response(
    work_date: date,
    record: AttendanceRecord | None,
    status: AttendanceStatus,
) -> AttendanceStateRead:
    return AttendanceStateRead(
        work_date=work_date,
        status=status,
        attendance=AttendanceRead.model_validate(record) if record is not None else None,
    )


@router.post("/punch-in", response_model=AttendanceStateRead, status_code=201)
def punch_in(
    employee: User = Depends(require_roles(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> AttendanceStateRead:
    record = attendance_service.punch_in(db, employee)
    return _state_response(record.work_date, record, AttendanceStatus.PUNCHED_IN)


@router.post("/punch-out", response_model=AttendanceStateRead)
def punch_out(
    employee: User = Depends(require_roles(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> AttendanceStateRead:
    record = attendance_service.punch_out(db, employee)
    return _state_response(record.work_date, record, AttendanceStatus.PUNCHED_OUT)


@router.get("/current", response_model=AttendanceStateRead)
def current_attendance(
    employee: User = Depends(require_roles(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> AttendanceStateRead:
    work_date, record, status = attendance_service.current_state(db, employee)
    return _state_response(work_date, record, status)


@router.get("/history", response_model=list[AttendanceRead])
def attendance_history(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    employee: User = Depends(require_roles(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> list[AttendanceRead]:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise AppError(
            422,
            "validation_error",
            "Request validation failed.",
            details=[
                {
                    "location": ["query", "from_date"],
                    "message": "from_date must be on or before to_date",
                    "type": "value_error",
                }
            ],
        )
    query_params = AttendanceHistoryQuery(
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    records = attendance_service.list_history(db, employee, query_params)
    return [AttendanceRead.model_validate(record) for record in records]
