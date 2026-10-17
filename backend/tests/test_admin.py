import json
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.attendance import AttendanceRecord
from app.models.audit import AuditLog
from app.models.shift import Shift
from app.models.user import User


def login(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def admin_headers(client):
    return {"Authorization": f"Bearer {login(client, 'admin@example.com', 'admin-password')}"}


def employee_headers(client):
    return {"Authorization": f"Bearer {login(client, 'employee@example.com', 'employee-password')}"}


def create_employee(client, headers, *, email="new.employee@example.com", shift_id=None):
    return client.post(
        "/api/v1/admin/employees",
        headers=headers,
        json={
            "email": email,
            "full_name": "New Employee",
            "password": "employee-password",
            "shift_id": shift_id,
        },
    )


def create_shift(client, headers, *, name="Morning", is_active=True):
    return client.post(
        "/api/v1/admin/shifts",
        headers=headers,
        json={
            "name": name,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "timezone": "Asia/Kolkata",
            "is_active": is_active,
        },
    )


def test_admin_can_create_read_update_and_toggle_employee(client, users):
    headers = admin_headers(client)
    created = create_employee(client, headers, email="  New.Employee@Example.com  ")

    assert created.status_code == 201
    employee = created.json()
    assert employee["email"] == "new.employee@example.com"
    assert employee["full_name"] == "New Employee"
    assert employee["role"] == "employee"
    assert "password" not in employee
    assert "password_hash" not in employee

    listed = client.get("/api/v1/admin/employees", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == employee["id"] for item in listed.json())

    fetched = client.get(f"/api/v1/admin/employees/{employee['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == employee["id"]

    updated = client.patch(
        f"/api/v1/admin/employees/{employee['id']}",
        headers=headers,
        json={
            "email": "updated.employee@example.com",
            "full_name": "Updated Employee",
            "password": "updated-password",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "updated.employee@example.com"
    assert updated.json()["full_name"] == "Updated Employee"

    deactivated = client.patch(
        f"/api/v1/admin/employees/{employee['id']}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    activated = client.patch(
        f"/api/v1/admin/employees/{employee['id']}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    with SessionLocal() as db:
        actions = db.scalars(
            select(AuditLog.action).where(AuditLog.entity_id == str(employee["id"]))
        ).all()
        assert {
            "admin.employee_created",
            "admin.employee_updated",
            "admin.employee_deactivated",
            "admin.employee_activated",
        }.issubset(set(actions))
        audit_payload = json.dumps(
            [event.metadata_json for event in db.scalars(select(AuditLog)).all()]
        )
        assert "employee-password" not in audit_payload
        assert "updated-password" not in audit_payload


def test_admin_can_create_update_list_and_delete_unassigned_shift(client, users):
    headers = admin_headers(client)
    created = create_shift(client, headers)

    assert created.status_code == 201
    shift = created.json()
    assert shift["timezone"] == "Asia/Kolkata"
    assert shift["is_active"] is True

    listed = client.get("/api/v1/admin/shifts", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == shift["id"] for item in listed.json())

    fetched = client.get(f"/api/v1/admin/shifts/{shift['id']}", headers=headers)
    assert fetched.status_code == 200

    updated = client.patch(
        f"/api/v1/admin/shifts/{shift['id']}",
        headers=headers,
        json={"name": "Updated Morning", "end_time": "18:00:00"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated Morning"
    assert updated.json()["end_time"] == "18:00:00"

    deleted = client.delete(f"/api/v1/admin/shifts/{shift['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/admin/shifts/{shift['id']}", headers=headers).status_code == 404

    with SessionLocal() as db:
        actions = db.scalars(
            select(AuditLog.action).where(
                AuditLog.entity_type == "shift",
                AuditLog.entity_id == str(shift["id"]),
            )
        ).all()
        assert actions == [
            "admin.shift_created",
            "admin.shift_updated",
            "admin.shift_deleted",
        ]


def test_employee_can_be_deleted_only_without_attendance(client, users):
    headers = admin_headers(client)
    safe_employee = create_employee(client, headers, email="safe.employee@example.com").json()
    deleted = client.delete(f"/api/v1/admin/employees/{safe_employee['id']}", headers=headers)
    assert deleted.status_code == 204

    with SessionLocal() as db:
        assert db.get(User, safe_employee["id"]) is None
        deletion_event = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "admin.employee_deleted",
                AuditLog.entity_id == str(safe_employee["id"]),
            )
        )
        assert deletion_event is not None
        assert deletion_event.actor_user_id == users["admin"].id

    audited_employee = create_employee(
        client,
        headers,
        email="audited.employee@example.com",
    ).json()
    login(client, "audited.employee@example.com", "employee-password")
    audited_delete = client.delete(
        f"/api/v1/admin/employees/{audited_employee['id']}",
        headers=headers,
    )
    assert audited_delete.status_code == 204
    with SessionLocal() as db:
        preserved_login_event = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "auth.login_succeeded",
                AuditLog.entity_id == str(audited_employee["id"]),
            )
        )
        assert preserved_login_event is not None
        assert preserved_login_event.actor_user_id is None

    protected_employee = create_employee(
        client,
        headers,
        email="protected.employee@example.com",
    ).json()
    with SessionLocal() as db:
        db.add(
            AttendanceRecord(
                user_id=protected_employee["id"],
                work_date=date(2026, 10, 16),
            )
        )
        db.commit()

    blocked = client.delete(
        f"/api/v1/admin/employees/{protected_employee['id']}",
        headers=headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "employee_has_attendance"
    with SessionLocal() as db:
        assert db.get(User, protected_employee["id"]) is not None
        assert db.scalar(
            select(AttendanceRecord).where(AttendanceRecord.user_id == protected_employee["id"])
        ) is not None


def test_shift_deletion_is_blocked_when_assigned_or_attendance_exists(client, users):
    headers = admin_headers(client)
    shift = create_shift(client, headers, name="Assigned").json()
    assigned_employee = create_employee(
        client,
        headers,
        email="assigned.employee@example.com",
        shift_id=shift["id"],
    ).json()

    blocked_assigned = client.delete(f"/api/v1/admin/shifts/{shift['id']}", headers=headers)
    assert blocked_assigned.status_code == 409
    assert blocked_assigned.json()["error"]["code"] == "shift_in_use"

    with SessionLocal() as db:
        db.add(
            AttendanceRecord(
                user_id=assigned_employee["id"],
                work_date=date(2026, 10, 16),
            )
        )
        db.commit()

    blocked_history = client.delete(f"/api/v1/admin/shifts/{shift['id']}", headers=headers)
    assert blocked_history.status_code == 409
    assert blocked_history.json()["error"]["code"] == "shift_has_attendance"
    with SessionLocal() as db:
        persisted_shift = db.get(Shift, shift["id"])
        persisted_employee = db.get(User, assigned_employee["id"])
        assert persisted_shift is not None
        assert persisted_employee.shift_id == shift["id"]


def test_duplicate_emails_and_shift_assignments_are_rejected(client, users):
    headers = admin_headers(client)
    duplicate = create_employee(client, headers, email="ADMIN@example.com")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_email"

    inactive_shift = create_shift(client, headers, name="Inactive", is_active=False)
    assert inactive_shift.status_code == 201
    inactive_assignment = create_employee(
        client,
        headers,
        email="inactive.shift.employee@example.com",
        shift_id=inactive_shift.json()["id"],
    )
    assert inactive_assignment.status_code == 409
    assert inactive_assignment.json()["error"]["code"] == "shift_inactive"

    missing_assignment = create_employee(
        client,
        headers,
        email="missing.shift.employee@example.com",
        shift_id=99999,
    )
    assert missing_assignment.status_code == 404
    assert missing_assignment.json()["error"]["code"] == "shift_not_found"


def test_database_enforces_case_insensitive_email_uniqueness(users):
    with SessionLocal() as db:
        db.add(
            User(
                email="ADMIN@EXAMPLE.COM",
                full_name="Duplicate Admin",
                password_hash=hash_password("another-password"),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_invalid_employee_and_shift_input_has_consistent_errors(client, users):
    headers = admin_headers(client)
    invalid_employee = client.post(
        "/api/v1/admin/employees",
        headers=headers,
        json={"email": "not-an-email", "full_name": "  ", "password": "short"},
    )
    assert invalid_employee.status_code == 422
    assert invalid_employee.json()["error"]["code"] == "validation_error"

    invalid_shift = client.post(
        "/api/v1/admin/shifts",
        headers=headers,
        json={
            "name": "Invalid",
            "start_time": "09:00:00",
            "end_time": "09:00:00",
            "timezone": "Not/A_Timezone",
        },
    )
    assert invalid_shift.status_code == 422
    assert invalid_shift.json()["error"]["code"] == "validation_error"

    first_shift = create_shift(client, headers, name="Unique Shift")
    assert first_shift.status_code == 201
    duplicate_shift = create_shift(client, headers, name=" unique shift ")
    assert duplicate_shift.status_code == 409
    assert duplicate_shift.json()["error"]["code"] == "duplicate_shift_name"

    empty_update = client.patch(
        f"/api/v1/admin/shifts/{first_shift.json()['id']}",
        headers=headers,
        json={},
    )
    assert empty_update.status_code == 422
    assert empty_update.json()["error"]["code"] == "validation_error"

    null_status = client.patch(
        f"/api/v1/admin/employees/{users['employee'].id}",
        headers=headers,
        json={"is_active": None},
    )
    assert null_status.status_code == 422
    assert null_status.json()["error"]["code"] == "validation_error"

    null_shift_status = client.patch(
        f"/api/v1/admin/shifts/{first_shift.json()['id']}",
        headers=headers,
        json={"is_active": None},
    )
    assert null_shift_status.status_code == 422
    assert null_shift_status.json()["error"]["code"] == "validation_error"


def test_employee_is_denied_all_admin_resources(client, users):
    headers = employee_headers(client)
    endpoints = [
        ("get", "/api/v1/admin/employees"),
        ("post", "/api/v1/admin/employees"),
        ("get", "/api/v1/admin/employees/1"),
        ("patch", "/api/v1/admin/employees/1"),
        ("patch", "/api/v1/admin/employees/1/status"),
        ("delete", "/api/v1/admin/employees/1"),
        ("get", "/api/v1/admin/shifts"),
        ("post", "/api/v1/admin/shifts"),
        ("get", "/api/v1/admin/shifts/1"),
        ("patch", "/api/v1/admin/shifts/1"),
        ("delete", "/api/v1/admin/shifts/1"),
    ]
    bodies = {
        "post": {
            "email": "denied@example.com",
            "full_name": "Denied",
            "password": "password123",
        },
        "patch": {"full_name": "Denied"},
    }
    for method, path in endpoints:
        kwargs = {"headers": headers}
        if method == "post":
            kwargs["json"] = bodies[method]
        elif method == "patch":
            kwargs["json"] = {"is_active": False} if path.endswith("/status") else bodies[method]
        response = getattr(client, method)(path, **kwargs)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"


def test_deactivated_employee_cannot_use_existing_token_or_login(client, users):
    employee_token = login(client, "employee@example.com", "employee-password")
    headers = admin_headers(client)
    response = client.patch(
        f"/api/v1/admin/employees/{users['employee'].id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert response.status_code == 200

    existing_token_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert existing_token_response.status_code == 401
    assert existing_token_response.json()["error"]["code"] == "invalid_token"

    inactive_admin_response = client.get(
        "/api/v1/admin/employees",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert inactive_admin_response.status_code == 401
    assert inactive_admin_response.json()["error"]["code"] == "invalid_token"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@example.com", "password": "employee-password"},
    )
    assert login_response.status_code == 401
    assert login_response.json()["error"]["code"] == "invalid_credentials"
