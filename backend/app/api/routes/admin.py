from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.admin import (
    EmployeeCreate,
    EmployeeStatusUpdate,
    EmployeeUpdate,
    ShiftCreate,
    ShiftRead,
    ShiftUpdate,
)
from app.schemas.auth import UserRead
from app.services import admin as admin_service


router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    users = db.scalars(select(User).order_by(User.id)).all()
    return [UserRead.model_validate(user) for user in users]


@router.get("/employees", response_model=list[UserRead])
def list_employees(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    return [UserRead.model_validate(employee) for employee in admin_service.list_employees(db)]


@router.post("/employees", response_model=UserRead, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserRead:
    employee = admin_service.create_employee(db, payload, admin_user_id=admin.id)
    return UserRead.model_validate(employee)


@router.get("/employees/{employee_id}", response_model=UserRead)
def get_employee(
    employee_id: int,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserRead:
    return UserRead.model_validate(admin_service.get_employee(db, employee_id))


@router.patch("/employees/{employee_id}", response_model=UserRead)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserRead:
    employee = admin_service.update_employee(
        db,
        employee_id,
        payload,
        admin_user_id=admin.id,
    )
    return UserRead.model_validate(employee)


@router.patch("/employees/{employee_id}/status", response_model=UserRead)
def update_employee_status(
    employee_id: int,
    payload: EmployeeStatusUpdate,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserRead:
    employee = admin_service.update_employee(
        db,
        employee_id,
        EmployeeUpdate(is_active=payload.is_active),
        admin_user_id=admin.id,
    )
    return UserRead.model_validate(employee)


@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(
    employee_id: int,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    admin_service.delete_employee(db, employee_id, admin_user_id=admin.id)
    return Response(status_code=204)


@router.get("/shifts", response_model=list[ShiftRead])
def list_shifts(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[ShiftRead]:
    return [ShiftRead.model_validate(shift) for shift in admin_service.list_shifts(db)]


@router.post("/shifts", response_model=ShiftRead, status_code=201)
def create_shift(
    payload: ShiftCreate,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ShiftRead:
    shift = admin_service.create_shift(db, payload, admin_user_id=admin.id)
    return ShiftRead.model_validate(shift)


@router.get("/shifts/{shift_id}", response_model=ShiftRead)
def get_shift(
    shift_id: int,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ShiftRead:
    return ShiftRead.model_validate(admin_service.get_shift(db, shift_id))


@router.patch("/shifts/{shift_id}", response_model=ShiftRead)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ShiftRead:
    shift = admin_service.update_shift(db, shift_id, payload, admin_user_id=admin.id)
    return ShiftRead.model_validate(shift)


@router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(
    shift_id: int,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    admin_service.delete_shift(db, shift_id, admin_user_id=admin.id)
    return Response(status_code=204)
