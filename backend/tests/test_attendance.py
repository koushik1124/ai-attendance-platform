from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.attendance import AttendanceRecord
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.services import attendance as attendance_service


def login(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def employee_headers(client):
    return {"Authorization": f"Bearer {login(client, 'employee@example.com', 'employee-password')}"}


def admin_headers(client):
    return {"Authorization": f"Bearer {login(client, 'admin@example.com', 'admin-password')}"}


def test_employee_can_punch_in_out_and_read_current_history(client, users):
    headers = employee_headers(client)

    initial = client.get("/api/v1/attendance/current", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["status"] == "not_started"
    assert initial.json()["attendance"] is None

    before_punch_in = client.post("/api/v1/attendance/punch-out", headers=headers)
    assert before_punch_in.status_code == 409
    assert before_punch_in.json()["error"]["code"] == "attendance_not_started"

    punched_in = client.post("/api/v1/attendance/punch-in", headers=headers)
    assert punched_in.status_code == 201
    punched_in_body = punched_in.json()
    assert punched_in_body["status"] == "punched_in"
    assert punched_in_body["attendance"]["punch_in_at"] is not None
    assert punched_in_body["attendance"]["punch_out_at"] is None
    assert datetime.fromisoformat(punched_in_body["attendance"]["punch_in_at"]).tzinfo is not None

    duplicate_punch_in = client.post("/api/v1/attendance/punch-in", headers=headers)
    assert duplicate_punch_in.status_code == 409
    assert duplicate_punch_in.json()["error"]["code"] == "already_punched_in"

    current = client.get("/api/v1/attendance/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["status"] == "punched_in"
    assert current.json()["attendance"]["id"] == punched_in_body["attendance"]["id"]

    punched_out = client.post("/api/v1/attendance/punch-out", headers=headers)
    assert punched_out.status_code == 200
    punched_out_body = punched_out.json()
    assert punched_out_body["status"] == "punched_out"
    assert punched_out_body["attendance"]["punch_out_at"] is not None
    assert punched_out_body["attendance"]["punch_in_at"] <= punched_out_body["attendance"]["punch_out_at"]

    duplicate_punch_out = client.post("/api/v1/attendance/punch-out", headers=headers)
    assert duplicate_punch_out.status_code == 409
    assert duplicate_punch_out.json()["error"]["code"] == "already_punched_out"

    history = client.get("/api/v1/attendance/history", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == punched_in_body["attendance"]["id"]
    assert history.json()[0]["work_date"] == punched_in_body["work_date"]

    with SessionLocal() as db:
        actions = db.scalars(
            select(AuditLog.action)
            .where(
                AuditLog.action.in_(["attendance.punch_in", "attendance.punch_out"]),
                AuditLog.actor_user_id == users["employee"].id,
            )
            .order_by(AuditLog.id)
        ).all()
        assert actions == ["attendance.punch_in", "attendance.punch_out"]


def test_attendance_requires_authentication(client):
    response = client.get("/api/v1/attendance/current")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_attendance_is_employee_only_and_inactive_tokens_are_rejected(client, users):
    employee_token = login(client, "employee@example.com", "employee-password")
    admin_token = login(client, "admin@example.com", "admin-password")
    admin_headers_value = {"Authorization": f"Bearer {admin_token}"}

    for path in ("/api/v1/attendance/current", "/api/v1/attendance/history"):
        response = client.get(path, headers=admin_headers_value)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    deactivated = client.patch(
        f"/api/v1/admin/employees/{users['employee'].id}/status",
        headers=admin_headers_value,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200

    response = client.get(
        "/api/v1/attendance/current",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_attendance_history_is_scoped_to_the_authenticated_employee(client, users):
    with SessionLocal() as db:
        other_employee = User(
            email="other.employee@example.com",
            full_name="Other Employee",
            password_hash=hash_password("other-password"),
            role=UserRole.EMPLOYEE,
        )
        db.add(other_employee)
        db.flush()
        db.add(
            AttendanceRecord(
                user_id=other_employee.id,
                work_date=date(2026, 10, 17),
                punch_in_at=datetime(2026, 10, 17, 3, tzinfo=timezone.utc),
            )
        )
        db.commit()

    headers = employee_headers(client)
    history = client.get(
        "/api/v1/attendance/history?employee_id=99999",
        headers=headers,
    )
    assert history.status_code == 200
    assert history.json() == []


def test_attendance_history_validates_range_and_pagination(client, users):
    headers = employee_headers(client)

    invalid_range = client.get(
        "/api/v1/attendance/history?from_date=2026-10-18&to_date=2026-10-17",
        headers=headers,
    )
    assert invalid_range.status_code == 422
    assert invalid_range.json()["error"]["code"] == "validation_error"

    invalid_limit = client.get(
        "/api/v1/attendance/history?limit=101",
        headers=headers,
    )
    assert invalid_limit.status_code == 422
    assert invalid_limit.json()["error"]["code"] == "validation_error"


def test_history_filters_and_pagination_are_employee_scoped(client, users):
    with SessionLocal() as db:
        db.add_all(
            [
                AttendanceRecord(
                    user_id=users["employee"].id,
                    work_date=date(2026, 10, 15),
                    punch_in_at=datetime(2026, 10, 15, 3, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 15, 11, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=users["employee"].id,
                    work_date=date(2026, 10, 16),
                    punch_in_at=datetime(2026, 10, 16, 3, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 16, 11, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=users["employee"].id,
                    work_date=date(2026, 10, 17),
                    punch_in_at=datetime(2026, 10, 17, 3, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 17, 11, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()

    history = client.get(
        "/api/v1/attendance/history?from_date=2026-10-16&to_date=2026-10-17&limit=1&offset=1",
        headers=employee_headers(client),
    )
    assert history.status_code == 200
    assert [item["work_date"] for item in history.json()] == ["2026-10-16"]


def test_open_attendance_from_another_work_date_must_be_closed_first(client, users):
    with SessionLocal() as db:
        db.add(
            AttendanceRecord(
                user_id=users["employee"].id,
                work_date=date.today() - timedelta(days=1),
                punch_in_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/attendance/punch-in",
        headers=employee_headers(client),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "attendance_open_elsewhere"


def test_work_date_uses_assigned_shift_timezone(client, users, monkeypatch):
    admin = admin_headers(client)
    shift = client.post(
        "/api/v1/admin/shifts",
        headers=admin,
        json={
            "name": "India Day Shift",
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "timezone": "Asia/Kolkata",
        },
    )
    assert shift.status_code == 201

    assigned = client.patch(
        f"/api/v1/admin/employees/{users['employee'].id}",
        headers=admin,
        json={"shift_id": shift.json()["id"]},
    )
    assert assigned.status_code == 200

    monkeypatch.setattr(
        attendance_service,
        "utc_now",
        lambda: datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc),
    )
    punched_in = client.post(
        "/api/v1/attendance/punch-in",
        headers=employee_headers(client),
    )
    assert punched_in.status_code == 201
    assert punched_in.json()["work_date"] == "2026-10-17"


def test_overnight_shift_keeps_after_midnight_punches_on_prior_work_date(client, users, monkeypatch):
    admin = admin_headers(client)
    shift = client.post(
        "/api/v1/admin/shifts",
        headers=admin,
        json={
            "name": "India Night Shift",
            "start_time": "22:00:00",
            "end_time": "06:00:00",
            "timezone": "Asia/Kolkata",
        },
    )
    assert shift.status_code == 201

    assigned = client.patch(
        f"/api/v1/admin/employees/{users['employee'].id}",
        headers=admin,
        json={"shift_id": shift.json()["id"]},
    )
    assert assigned.status_code == 200

    now = {"value": datetime(2026, 10, 16, 23, 30, tzinfo=timezone.utc)}
    monkeypatch.setattr(attendance_service, "utc_now", lambda: now["value"])
    punched_in = client.post(
        "/api/v1/attendance/punch-in",
        headers=employee_headers(client),
    )
    assert punched_in.status_code == 201
    assert punched_in.json()["work_date"] == "2026-10-16"

    now["value"] = datetime(2026, 10, 17, 0, 30, tzinfo=timezone.utc)
    punched_out = client.post(
        "/api/v1/attendance/punch-out",
        headers=employee_headers(client),
    )
    assert punched_out.status_code == 200
    assert punched_out.json()["work_date"] == "2026-10-16"


def test_attendance_duration_calculation_and_incomplete_sessions():
    # 09:00 to 17:30 equals 8.5 hours (30600 seconds)
    completed = AttendanceRecord(
        user_id=1,
        work_date=date(2026, 10, 1),
        punch_in_at=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        punch_out_at=datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc),
    )
    assert completed.working_seconds == 30600
    assert completed.working_hours == 8.5

    # Incomplete session: returns None
    incomplete = AttendanceRecord(
        user_id=1,
        work_date=date(2026, 10, 2),
        punch_in_at=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
        punch_out_at=None,
    )
    assert incomplete.working_seconds is None
    assert incomplete.working_hours is None

    # Overnight session: 22:00 to 06:00 next day = 8.0 hours (28800 seconds)
    overnight = AttendanceRecord(
        user_id=1,
        work_date=date(2026, 10, 3),
        punch_in_at=datetime(2026, 10, 3, 22, 0, tzinfo=timezone.utc),
        punch_out_at=datetime(2026, 10, 4, 6, 0, tzinfo=timezone.utc),
    )
    assert overnight.working_seconds == 28800
    assert overnight.working_hours == 8.0


def test_attendance_history_exposes_working_hours_and_seconds(client, users):
    headers = employee_headers(client)

    with SessionLocal() as db:
        db.add_all(
            [
                AttendanceRecord(
                    user_id=users["employee"].id,
                    work_date=date(2026, 10, 1),
                    punch_in_at=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 1, 17, 30, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=users["employee"].id,
                    work_date=date(2026, 10, 2),
                    punch_in_at=datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc),
                    punch_out_at=None,
                ),
            ]
        )
        db.commit()

    history = client.get("/api/v1/attendance/history", headers=headers)
    assert history.status_code == 200
    records = {r["work_date"]: r for r in history.json()}

    assert "2026-10-01" in records
    assert records["2026-10-01"]["working_seconds"] == 30600
    assert records["2026-10-01"]["working_hours"] == 8.5

    assert "2026-10-02" in records
    assert records["2026-10-02"]["working_seconds"] is None
    assert records["2026-10-02"]["working_hours"] is None


def test_three_attendance_states_workflow(client, users):
    headers = employee_headers(client)

    # State 1: Not started
    state1 = client.get("/api/v1/attendance/current", headers=headers)
    assert state1.status_code == 200
    assert state1.json()["status"] == "not_started"
    assert state1.json()["attendance"] is None

    # Invalid punch-out before punch-in
    err_out = client.post("/api/v1/attendance/punch-out", headers=headers)
    assert err_out.status_code == 409
    assert err_out.json()["error"]["code"] == "attendance_not_started"

    # Transition to State 2: Punched In
    punch_in_res = client.post("/api/v1/attendance/punch-in", headers=headers)
    assert punch_in_res.status_code == 201
    assert punch_in_res.json()["status"] == "punched_in"

    state2 = client.get("/api/v1/attendance/current", headers=headers)
    assert state2.status_code == 200
    assert state2.json()["status"] == "punched_in"
    assert state2.json()["attendance"]["punch_in_at"] is not None
    assert state2.json()["attendance"]["punch_out_at"] is None
    assert state2.json()["attendance"]["working_hours"] is None

    # Duplicate punch-in rejected
    err_in = client.post("/api/v1/attendance/punch-in", headers=headers)
    assert err_in.status_code == 409
    assert err_in.json()["error"]["code"] == "already_punched_in"

    # Transition to State 3: Punched Out / Day Completed
    punch_out_res = client.post("/api/v1/attendance/punch-out", headers=headers)
    assert punch_out_res.status_code == 200
    assert punch_out_res.json()["status"] == "punched_out"

    state3 = client.get("/api/v1/attendance/current", headers=headers)
    assert state3.status_code == 200
    assert state3.json()["status"] == "punched_out"
    assert state3.json()["attendance"]["punch_in_at"] is not None
    assert state3.json()["attendance"]["punch_out_at"] is not None
    assert state3.json()["attendance"]["working_seconds"] is not None

    # Duplicate punch-out rejected
    err_out_dup = client.post("/api/v1/attendance/punch-out", headers=headers)
    assert err_out_dup.status_code == 409
    assert err_out_dup.json()["error"]["code"] == "already_punched_out"

    # Subsequent punch-in rejected after day completed
    err_in_done = client.post("/api/v1/attendance/punch-in", headers=headers)
    assert err_in_done.status_code == 409
    assert err_in_done.json()["error"]["code"] == "attendance_completed"


