from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.models.attendance import AttendanceRecord
from app.models.audit import AuditLog
from app.models.shift import Shift
from app.models.user import User, UserRole
from app.schemas.admin import EmployeeCreate, EmployeeUpdate, ShiftCreate, ShiftUpdate
from app.services.audit import add_audit_event


def _employee_or_error(db: Session, employee_id: int, *, lock: bool = False) -> User:
    query = select(User).where(User.id == employee_id)
    if lock:
        query = query.with_for_update()
    employee = db.scalar(query)
    if employee is None or employee.role != UserRole.EMPLOYEE:
        raise AppError(404, "employee_not_found", "Employee was not found.")
    return employee


def _shift_or_error(db: Session, shift_id: int, *, lock: bool = False) -> Shift:
    query = select(Shift).where(Shift.id == shift_id)
    if lock:
        query = query.with_for_update()
    shift = db.scalar(query)
    if shift is None:
        raise AppError(404, "shift_not_found", "Shift was not found.")
    return shift


def _active_shift_or_error(db: Session, shift_id: int, *, lock: bool = False) -> Shift:
    shift = _shift_or_error(db, shift_id, lock=lock)
    if not shift.is_active:
        raise AppError(409, "shift_inactive", "Employees can only be assigned to active shifts.")
    return shift


def _ensure_unique_email(db: Session, email: str, *, exclude_user_id: int | None = None) -> None:
    query = select(User.id).where(func.lower(User.email) == email.lower())
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    if db.scalar(query) is not None:
        raise AppError(409, "duplicate_email", "An account with that email already exists.")


def _ensure_unique_shift_name(db: Session, name: str, *, exclude_shift_id: int | None = None) -> None:
    query = select(Shift.id).where(func.lower(Shift.name) == name.lower())
    if exclude_shift_id is not None:
        query = query.where(Shift.id != exclude_shift_id)
    if db.scalar(query) is not None:
        raise AppError(409, "duplicate_shift_name", "A shift with that name already exists.")


def _commit_or_error(db: Session, *, code: str, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, code, message) from exc
    except StaleDataError as exc:
        db.rollback()
        raise AppError(
            409,
            "resource_changed",
            "The resource changed while the operation was in progress.",
        ) from exc


def list_employees(db: Session) -> Sequence[User]:
    return db.scalars(
        select(User).where(User.role == UserRole.EMPLOYEE).order_by(User.id)
    ).all()


def get_employee(db: Session, employee_id: int) -> User:
    return _employee_or_error(db, employee_id)


def create_employee(
    db: Session,
    payload: EmployeeCreate,
    *,
    admin_user_id: int,
) -> User:
    _ensure_unique_email(db, str(payload.email))
    if payload.shift_id is not None:
        _active_shift_or_error(db, payload.shift_id, lock=True)

    employee = User(
        email=str(payload.email),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=UserRole.EMPLOYEE,
        shift_id=payload.shift_id,
    )
    db.add(employee)
    try:
        db.flush()
        add_audit_event(
            db,
            action="admin.employee_created",
            entity_type="user",
            entity_id=str(employee.id),
            actor_user_id=admin_user_id,
            metadata={"role": UserRole.EMPLOYEE.value},
        )
        _commit_or_error(
            db,
            code="duplicate_email",
            message="An account with that email already exists.",
        )
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "duplicate_email", "An account with that email already exists.") from exc
    return employee


def update_employee(
    db: Session,
    employee_id: int,
    payload: EmployeeUpdate,
    *,
    admin_user_id: int,
) -> User:
    employee = _employee_or_error(db, employee_id, lock=True)
    changed_fields: list[str] = []

    if "email" in payload.model_fields_set:
        email = str(payload.email)
        _ensure_unique_email(db, email, exclude_user_id=employee.id)
        if employee.email != email:
            employee.email = email
            changed_fields.append("email")

    if "full_name" in payload.model_fields_set and payload.full_name != employee.full_name:
        employee.full_name = payload.full_name
        changed_fields.append("full_name")

    if "password" in payload.model_fields_set:
        employee.password_hash = hash_password(payload.password)
        changed_fields.append("credential_changed")

    if "shift_id" in payload.model_fields_set and payload.shift_id != employee.shift_id:
        if payload.shift_id is not None:
            _active_shift_or_error(db, payload.shift_id, lock=True)
        employee.shift_id = payload.shift_id
        changed_fields.append("shift_id")

    if "is_active" in payload.model_fields_set and payload.is_active != employee.is_active:
        employee.is_active = payload.is_active
        changed_fields.append("is_active")

    if not changed_fields:
        raise AppError(400, "no_changes", "The update did not change the employee.")

    action = "admin.employee_updated"
    if changed_fields == ["is_active"]:
        action = "admin.employee_activated" if employee.is_active else "admin.employee_deactivated"
    add_audit_event(
        db,
        action=action,
        entity_type="user",
        entity_id=str(employee.id),
        actor_user_id=admin_user_id,
        metadata={"fields": changed_fields},
    )
    _commit_or_error(
        db,
        code="duplicate_email",
        message="An account with that email already exists.",
    )
    return employee


def delete_employee(db: Session, employee_id: int, *, admin_user_id: int) -> None:
    employee = _employee_or_error(db, employee_id, lock=True)
    attendance_id = db.scalar(
        select(AttendanceRecord.id)
        .where(AttendanceRecord.user_id == employee.id)
        .limit(1)
    )
    if attendance_id is not None:
        raise AppError(
            409,
            "employee_has_attendance",
            "The employee cannot be deleted because attendance history exists.",
        )

    # Preserve audit history while removing the optional actor reference.
    db.execute(update(AuditLog).where(AuditLog.actor_user_id == employee.id).values(actor_user_id=None))
    add_audit_event(
        db,
        action="admin.employee_deleted",
        entity_type="user",
        entity_id=str(employee.id),
        actor_user_id=admin_user_id,
        metadata={"role": UserRole.EMPLOYEE.value},
    )
    db.delete(employee)
    _commit_or_error(
        db,
        code="employee_has_attendance",
        message="The employee cannot be deleted because related records exist.",
    )


def list_shifts(db: Session) -> Sequence[Shift]:
    return db.scalars(select(Shift).order_by(Shift.id)).all()


def get_shift(db: Session, shift_id: int) -> Shift:
    return _shift_or_error(db, shift_id)


def create_shift(db: Session, payload: ShiftCreate, *, admin_user_id: int) -> Shift:
    _ensure_unique_shift_name(db, payload.name)
    shift = Shift(
        name=payload.name,
        start_time=payload.start_time,
        end_time=payload.end_time,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )
    db.add(shift)
    try:
        db.flush()
        add_audit_event(
            db,
            action="admin.shift_created",
            entity_type="shift",
            entity_id=str(shift.id),
            actor_user_id=admin_user_id,
            metadata={"fields": ["name", "start_time", "end_time", "timezone", "is_active"]},
        )
        _commit_or_error(
            db,
            code="duplicate_shift_name",
            message="A shift with that name already exists.",
        )
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            409,
            "duplicate_shift_name",
            "A shift with that name already exists.",
        ) from exc
    return shift


def update_shift(
    db: Session,
    shift_id: int,
    payload: ShiftUpdate,
    *,
    admin_user_id: int,
) -> Shift:
    shift = _shift_or_error(db, shift_id, lock=True)
    changed_fields: list[str] = []

    if "name" in payload.model_fields_set and payload.name != shift.name:
        _ensure_unique_shift_name(db, payload.name, exclude_shift_id=shift.id)
        shift.name = payload.name
        changed_fields.append("name")

    new_start = payload.start_time if "start_time" in payload.model_fields_set else shift.start_time
    new_end = payload.end_time if "end_time" in payload.model_fields_set else shift.end_time
    if new_start == new_end:
        raise AppError(422, "invalid_shift_times", "start_time and end_time must be different.")

    for field_name in ("start_time", "end_time", "timezone", "is_active"):
        if field_name in payload.model_fields_set:
            value = getattr(payload, field_name)
            if value != getattr(shift, field_name):
                setattr(shift, field_name, value)
                changed_fields.append(field_name)

    if not changed_fields:
        raise AppError(400, "no_changes", "The update did not change the shift.")

    add_audit_event(
        db,
        action="admin.shift_updated",
        entity_type="shift",
        entity_id=str(shift.id),
        actor_user_id=admin_user_id,
        metadata={"fields": changed_fields},
    )
    _commit_or_error(
        db,
        code="duplicate_shift_name",
        message="A shift with that name already exists.",
    )
    return shift


def delete_shift(db: Session, shift_id: int, *, admin_user_id: int) -> None:
    shift = _shift_or_error(db, shift_id, lock=True)
    assigned_count = db.scalar(
        select(func.count(User.id)).where(User.shift_id == shift.id)
    )
    if assigned_count:
        attendance_id = db.scalar(
            select(AttendanceRecord.id)
            .join(User, AttendanceRecord.user_id == User.id)
            .where(User.shift_id == shift.id)
            .limit(1)
        )
        if attendance_id is not None:
            raise AppError(
                409,
                "shift_has_attendance",
                "The shift cannot be deleted because assigned employees have attendance history.",
            )
        raise AppError(
            409,
            "shift_in_use",
            "The shift cannot be deleted while employees are assigned to it.",
        )

    add_audit_event(
        db,
        action="admin.shift_deleted",
        entity_type="shift",
        entity_id=str(shift.id),
        actor_user_id=admin_user_id,
        metadata={"operation": "delete"},
    )
    db.delete(shift)
    _commit_or_error(
        db,
        code="shift_in_use",
        message="The shift cannot be deleted while employees are assigned to it.",
    )
