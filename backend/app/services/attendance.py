from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.exceptions import AppError
from app.core.time import utc_now
from app.models.attendance import AttendanceRecord
from app.models.shift import Shift
from app.models.user import User
from app.schemas.attendance import AttendanceHistoryQuery, AttendanceStatus
from app.services.audit import add_audit_event


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _shift_for_employee(db: Session, employee: User) -> Shift | None:
    if employee.shift_id is None:
        return None
    shift = db.get(Shift, employee.shift_id)
    if shift is None:
        raise AppError(409, "shift_not_found", "The employee's assigned shift was not found.")
    return shift


def _work_date_for_employee(
    db: Session,
    employee: User,
    at: datetime,
) -> date:
    timestamp = _as_utc(at)
    shift = _shift_for_employee(db, employee)
    if shift is None:
        return timestamp.date()

    try:
        local_now = timestamp.astimezone(ZoneInfo(shift.timezone))
    except ZoneInfoNotFoundError as exc:
        raise AppError(
            500,
            "invalid_shift_timezone",
            "The employee's assigned shift has an invalid timezone.",
        ) from exc

    local_date = local_now.date()
    local_time = local_now.time().replace(tzinfo=None)
    if shift.start_time > shift.end_time and local_time <= shift.end_time:
        return local_date - timedelta(days=1)
    return local_date


def _attendance_for_date(
    db: Session,
    employee_id: int,
    work_date: date,
    *,
    lock: bool = False,
) -> AttendanceRecord | None:
    query = select(AttendanceRecord).where(
        AttendanceRecord.user_id == employee_id,
        AttendanceRecord.work_date == work_date,
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _open_attendance_elsewhere(
    db: Session,
    employee_id: int,
    work_date: date,
) -> AttendanceRecord | None:
    return db.scalar(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.user_id == employee_id,
            AttendanceRecord.work_date != work_date,
            AttendanceRecord.punch_in_at.is_not(None),
            AttendanceRecord.punch_out_at.is_(None),
        )
        .order_by(AttendanceRecord.work_date.desc())
        .with_for_update()
    )


def _commit_attendance(
    db: Session,
    record: AttendanceRecord,
    *,
    action: str,
) -> AttendanceRecord:
    try:
        db.flush()
        add_audit_event(
            db,
            action=action,
            entity_type="attendance",
            entity_id=str(record.id),
            actor_user_id=record.user_id,
            metadata={"work_date": record.work_date.isoformat()},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            409,
            "attendance_conflict",
            "The attendance record changed while the operation was in progress.",
        ) from exc
    except StaleDataError as exc:
        db.rollback()
        raise AppError(
            409,
            "attendance_conflict",
            "The attendance record changed while the operation was in progress.",
        ) from exc
    return record


def _state_for_record(record: AttendanceRecord | None) -> AttendanceStatus:
    if record is None or record.punch_in_at is None:
        return AttendanceStatus.NOT_STARTED
    if record.punch_out_at is None:
        return AttendanceStatus.PUNCHED_IN
    return AttendanceStatus.PUNCHED_OUT


def punch_in(db: Session, employee: User) -> AttendanceRecord:
    now = _as_utc(utc_now())
    work_date = _work_date_for_employee(db, employee, now)
    record = _attendance_for_date(db, employee.id, work_date, lock=True)

    if record is not None and record.punch_in_at is not None:
        if record.punch_out_at is None:
            raise AppError(409, "already_punched_in", "You are already punched in for this work date.")
        raise AppError(409, "attendance_completed", "Attendance is already completed for this work date.")

    if record is not None and record.punch_out_at is not None:
        raise AppError(409, "attendance_invalid_state", "The attendance record is invalid.")

    if _open_attendance_elsewhere(db, employee.id, work_date) is not None:
        raise AppError(
            409,
            "attendance_open_elsewhere",
            "An earlier attendance record must be punched out before starting a new one.",
        )

    if record is None:
        record = AttendanceRecord(
            user_id=employee.id,
            work_date=work_date,
            punch_in_at=now,
        )
        db.add(record)
    else:
        record.punch_in_at = now

    return _commit_attendance(db, record, action="attendance.punch_in")


def punch_out(db: Session, employee: User) -> AttendanceRecord:
    now = _as_utc(utc_now())
    work_date = _work_date_for_employee(db, employee, now)
    record = _attendance_for_date(db, employee.id, work_date, lock=True)

    if record is None or record.punch_in_at is None:
        raise AppError(409, "attendance_not_started", "You must punch in before punching out.")
    if record.punch_out_at is not None:
        raise AppError(409, "already_punched_out", "You are already punched out for this work date.")
    if now < _as_utc(record.punch_in_at):
        raise AppError(409, "invalid_punch_time", "Punch-out time cannot precede punch-in time.")

    record.punch_out_at = now
    return _commit_attendance(db, record, action="attendance.punch_out")


def current_state(db: Session, employee: User) -> tuple[date, AttendanceRecord | None, AttendanceStatus]:
    work_date = _work_date_for_employee(db, employee, _as_utc(utc_now()))
    record = _attendance_for_date(db, employee.id, work_date)
    return work_date, record, _state_for_record(record)


def list_history(
    db: Session,
    employee: User,
    query_params: AttendanceHistoryQuery,
) -> list[AttendanceRecord]:
    query = select(AttendanceRecord).where(AttendanceRecord.user_id == employee.id)
    if query_params.from_date is not None:
        query = query.where(AttendanceRecord.work_date >= query_params.from_date)
    if query_params.to_date is not None:
        query = query.where(AttendanceRecord.work_date <= query_params.to_date)
    query = (
        query.order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.id.desc())
        .limit(query_params.limit)
        .offset(query_params.offset)
    )
    return list(db.scalars(query).all())
