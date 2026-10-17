from datetime import date, datetime, time as time_obj, timezone

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.attendance import AttendanceRecord
from app.models.user import User, UserRole
from app.services import reports as reports_service


def login(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def employee_headers(client):
    return {"Authorization": f"Bearer {login(client, 'employee@example.com', 'employee-password')}"}


def admin_headers(client):
    return {"Authorization": f"Bearer {login(client, 'admin@example.com', 'admin-password')}"}


def _seed_report_data(employee_id: int) -> int:
    with SessionLocal() as db:
        other_employee = User(
            email="historical.employee@example.com",
            full_name="Historical Employee",
            password_hash=hash_password("historical-password"),
            role=UserRole.EMPLOYEE,
            is_active=False,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.add(other_employee)
        db.flush()
        db.add_all(
            [
                AttendanceRecord(
                    user_id=employee_id,
                    work_date=date(2026, 10, 1),
                    punch_in_at=datetime(2026, 10, 1, 3, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 1, 11, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=employee_id,
                    work_date=date(2026, 10, 2),
                    punch_in_at=datetime(2026, 10, 2, 3, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=other_employee.id,
                    work_date=date(2026, 10, 2),
                    # The timestamp date differs deliberately; reports use work_date.
                    punch_in_at=datetime(2026, 10, 3, 0, 30, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 3, 8, 30, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()
        return other_employee.id


def test_admin_reports_aggregate_and_employee_reports_are_scoped(client, users, monkeypatch):
    other_employee_id = _seed_report_data(users["employee"].id)
    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )

    admin = admin_headers(client)
    trends = client.get("/api/v1/reports/monthly-trends?month=2026-10", headers=admin)
    assert trends.status_code == 200
    trends_body = trends.json()
    assert trends_body["period_start"] == "2026-10-01"
    assert trends_body["period_end"] == "2026-10-03"
    assert trends_body["employee_count"] == 2
    assert trends_body["scope"] == {"kind": "all_employees", "employee_id": None}
    assert trends_body["basis"] == "scheduled_days"
    # Oct 1 (Thu) and Oct 2 (Fri) are scheduled; Oct 3 (Sat) is an unworked weekend (0 expected)
    assert trends_body["points"] == [
        {
            "work_date": "2026-10-01",
            "present_count": 1,
            "completed_count": 1,
            "incomplete_count": 0,
            "absent_count": 1,
        },
        {
            "work_date": "2026-10-02",
            "present_count": 2,
            "completed_count": 1,
            "incomplete_count": 1,
            "absent_count": 0,
        },
        {
            "work_date": "2026-10-03",
            "present_count": 0,
            "completed_count": 0,
            "incomplete_count": 0,
            "absent_count": 0,
        },
    ]

    summary = client.get("/api/v1/reports/attendance-summary?month=2026-10", headers=admin)
    assert summary.status_code == 200
    assert summary.json()["basis"] == "scheduled_days"
    assert summary.json()["expected_employee_days"] == 4
    assert summary.json()["present_employee_days"] == 3
    assert summary.json()["completed_employee_days"] == 2
    assert summary.json()["incomplete_employee_days"] == 1
    assert summary.json()["absent_employee_days"] == 1
    assert summary.json()["attendance_rate"] == 75.0
    assert summary.json()["total_working_hours"] == 16.0

    absenteeism = client.get("/api/v1/reports/absenteeism?month=2026-10", headers=admin)
    assert absenteeism.status_code == 200
    assert absenteeism.json()["basis"] == "scheduled_days"
    assert absenteeism.json()["expected_employee_days"] == 4
    assert absenteeism.json()["absent_employee_days"] == 1
    assert absenteeism.json()["absenteeism_rate"] == 25.0

    # Test explicit calendar_days query option
    summary_cal = client.get("/api/v1/reports/attendance-summary?month=2026-10&basis=calendar_days", headers=admin)
    assert summary_cal.status_code == 200
    assert summary_cal.json()["basis"] == "calendar_days"
    assert summary_cal.json()["expected_employee_days"] == 6
    assert summary_cal.json()["absent_employee_days"] == 3
    assert summary_cal.json()["attendance_rate"] == 50.0

    absenteeism_cal = client.get("/api/v1/reports/absenteeism?month=2026-10&basis=calendar_days", headers=admin)
    assert absenteeism_cal.status_code == 200
    assert absenteeism_cal.json()["basis"] == "calendar_days"
    assert absenteeism_cal.json()["expected_employee_days"] == 6
    assert absenteeism_cal.json()["absent_employee_days"] == 3
    assert absenteeism_cal.json()["absenteeism_rate"] == 50.0

    targeted = client.get(
        f"/api/v1/reports/attendance-summary?month=2026-10&employee_id={other_employee_id}",
        headers=admin,
    )
    assert targeted.status_code == 200
    assert targeted.json()["scope"] == {"kind": "employee", "employee_id": other_employee_id}
    assert targeted.json()["employee_count"] == 1
    assert targeted.json()["expected_employee_days"] == 2
    assert targeted.json()["present_employee_days"] == 1
    assert targeted.json()["absent_employee_days"] == 1
    assert targeted.json()["attendance_rate"] == 50.0

    employee_summary = client.get(
        "/api/v1/reports/attendance-summary?month=2026-10",
        headers=employee_headers(client),
    )
    assert employee_summary.status_code == 200
    assert employee_summary.json()["scope"] == {
        "kind": "employee",
        "employee_id": users["employee"].id,
    }
    assert employee_summary.json()["employee_count"] == 1
    assert employee_summary.json()["expected_employee_days"] == 2
    assert employee_summary.json()["present_employee_days"] == 2
    assert employee_summary.json()["absent_employee_days"] == 0
    assert employee_summary.json()["attendance_rate"] == 100.0

    denied_scope = client.get(
        f"/api/v1/reports/monthly-trends?month=2026-10&employee_id={other_employee_id}",
        headers=employee_headers(client),
    )
    assert denied_scope.status_code == 403
    assert denied_scope.json()["error"]["code"] == "forbidden"


def test_reports_validate_month_scope_and_authentication(client, users, monkeypatch):
    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )

    unauthenticated = client.get("/api/v1/reports/monthly-trends?month=2026-10")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "authentication_required"

    admin = admin_headers(client)
    for invalid_month in ("2026-1", "2026-13", "October-2026"):
        response = client.get(
            f"/api/v1/reports/monthly-trends?month={invalid_month}",
            headers=admin,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    future = client.get("/api/v1/reports/monthly-trends?month=2026-11", headers=admin)
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "month_in_future"

    non_employee_target = client.get(
        f"/api/v1/reports/monthly-trends?month=2026-10&employee_id={users['admin'].id}",
        headers=admin,
    )
    assert non_employee_target.status_code == 404
    assert non_employee_target.json()["error"]["code"] == "employee_not_found"

    missing_target = client.get(
        "/api/v1/reports/monthly-trends?month=2026-10&employee_id=99999",
        headers=admin,
    )
    assert missing_target.status_code == 404
    assert missing_target.json()["error"]["code"] == "employee_not_found"


def test_empty_reports_return_zero_counts_and_null_rate_for_no_employees(client, monkeypatch):
    with SessionLocal() as db:
        db.add(
            User(
                email="only.admin@example.com",
                full_name="Only Admin",
                password_hash=hash_password("admin-password"),
                role=UserRole.ADMIN,
            )
        )
        db.commit()

    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 3, 12, tzinfo=timezone.utc),
    )
    headers = {
        "Authorization": f"Bearer {login(client, 'only.admin@example.com', 'admin-password')}"
    }

    summary = client.get("/api/v1/reports/attendance-summary?month=2026-10", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["employee_count"] == 0
    assert summary.json()["expected_employee_days"] == 0
    assert summary.json()["present_employee_days"] == 0
    assert summary.json()["absent_employee_days"] == 0
    assert summary.json()["attendance_rate"] is None

    trends = client.get("/api/v1/reports/monthly-trends?month=2026-10", headers=headers)
    assert trends.status_code == 200
    assert len(trends.json()["points"]) == 3
    assert all(point["absent_count"] == 0 for point in trends.json()["points"])

    absenteeism = client.get("/api/v1/reports/absenteeism?month=2026-10", headers=headers)
    assert absenteeism.status_code == 200
    assert absenteeism.json()["absenteeism_rate"] is None


def test_reports_exclude_pre_joining_dates_and_handle_mid_month_hires(client, monkeypatch):
    with SessionLocal() as db:
        admin = User(
            email="admin.mid@example.com",
            full_name="Admin Mid",
            password_hash=hash_password("admin-password"),
            role=UserRole.ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        # Mid-month employee created on Thursday Oct 15, 2026
        mid_employee = User(
            email="mid.hire@example.com",
            full_name="Mid Hire",
            password_hash=hash_password("mid-password"),
            role=UserRole.EMPLOYEE,
            created_at=datetime(2026, 10, 15, 8, tzinfo=timezone.utc),
        )
        db.add_all([admin, mid_employee])
        db.flush()
        # Punched in on Oct 15
        db.add(
            AttendanceRecord(
                user_id=mid_employee.id,
                work_date=date(2026, 10, 15),
                punch_in_at=datetime(2026, 10, 15, 9, tzinfo=timezone.utc),
                punch_out_at=datetime(2026, 10, 15, 17, 30, tzinfo=timezone.utc),
            )
        )
        db.commit()
        admin_id = admin.id
        mid_id = mid_employee.id

    # Clock set to Friday Oct 16, 2026
    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 16, 17, tzinfo=timezone.utc),
    )
    headers = {"Authorization": f"Bearer {login(client, 'admin.mid@example.com', 'admin-password')}"}

    summary = client.get(
        f"/api/v1/reports/attendance-summary?month=2026-10&employee_id={mid_id}",
        headers=headers,
    )
    assert summary.status_code == 200
    data = summary.json()
    # Oct 1 to Oct 14 are excluded; only Oct 15 (Thu) and Oct 16 (Fri) are eligible workdays
    assert data["expected_employee_days"] == 2
    assert data["present_employee_days"] == 1
    assert data["completed_employee_days"] == 1
    assert data["incomplete_employee_days"] == 0
    assert data["absent_employee_days"] == 1
    assert data["attendance_rate"] == 50.0
    assert data["total_working_hours"] == 8.5

    trends = client.get(
        f"/api/v1/reports/monthly-trends?month=2026-10&employee_id={mid_id}",
        headers=headers,
    )
    assert trends.status_code == 200
    points = trends.json()["points"]
    # Pre-joining dates Oct 1 to Oct 14 must have 0 absent_count
    for p in points:
        if p["work_date"] < "2026-10-15":
            assert p["present_count"] == 0
            assert p["absent_count"] == 0


def test_unworked_weekends_excluded_and_worked_weekends_counted_as_present(client, monkeypatch):
    with SessionLocal() as db:
        admin = User(
            email="admin.wk@example.com",
            full_name="Admin Weekend",
            password_hash=hash_password("admin-password"),
            role=UserRole.ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        emp = User(
            email="emp.wk@example.com",
            full_name="Emp Weekend",
            password_hash=hash_password("emp-password"),
            role=UserRole.EMPLOYEE,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.add_all([admin, emp])
        db.flush()
        # Period: Oct 1 (Thu) to Oct 5 (Mon). Oct 3=Sat, Oct 4=Sun.
        # Punched in on Fri Oct 2, Sat Oct 3 (worked weekend), Mon Oct 5.
        db.add_all(
            [
                AttendanceRecord(
                    user_id=emp.id,
                    work_date=date(2026, 10, 2),
                    punch_in_at=datetime(2026, 10, 2, 9, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 2, 17, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=emp.id,
                    work_date=date(2026, 10, 3),  # Saturday worked
                    punch_in_at=datetime(2026, 10, 3, 10, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 3, 14, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=emp.id,
                    work_date=date(2026, 10, 5),
                    punch_in_at=datetime(2026, 10, 5, 9, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 5, 17, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()
        emp_id = emp.id

    # Clock set to Monday Oct 5, 2026
    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 5, 18, tzinfo=timezone.utc),
    )
    headers = {"Authorization": f"Bearer {login(client, 'admin.wk@example.com', 'admin-password')}"}

    summary = client.get(
        f"/api/v1/reports/attendance-summary?month=2026-10&employee_id={emp_id}",
        headers=headers,
    )
    assert summary.status_code == 200
    data = summary.json()
    # Expected days: 3 weekdays (Thu, Fri, Mon) + 1 worked weekend (Sat) = 4 expected days
    # Sunday Oct 4 is unworked weekend: excluded from expected days and absent days
    assert data["expected_employee_days"] == 4
    assert data["present_employee_days"] == 3
    assert data["completed_employee_days"] == 3
    assert data["absent_employee_days"] == 1  # Missed Thu Oct 1
    assert data["attendance_rate"] == 75.0
    # 8h (Oct 2) + 4h (Oct 3) + 8h (Oct 5) = 20h
    assert data["total_working_hours"] == 20.0


def test_zero_eligible_workdays_returns_null_attendance_rate(client, monkeypatch):
    with SessionLocal() as db:
        admin = User(
            email="admin.zero@example.com",
            full_name="Admin Zero",
            password_hash=hash_password("admin-password"),
            role=UserRole.ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        # Employee joins on Oct 25, 2026
        future_emp = User(
            email="future.emp@example.com",
            full_name="Future Emp",
            password_hash=hash_password("future-password"),
            role=UserRole.EMPLOYEE,
            created_at=datetime(2026, 10, 25, tzinfo=timezone.utc),
        )
        db.add_all([admin, future_emp])
        db.commit()
        emp_id = future_emp.id

    # Clock set to Oct 10, 2026 (before employee's joining date)
    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 10, 12, tzinfo=timezone.utc),
    )
    headers = {"Authorization": f"Bearer {login(client, 'admin.zero@example.com', 'admin-password')}"}

    summary = client.get(
        f"/api/v1/reports/attendance-summary?month=2026-10&employee_id={emp_id}",
        headers=headers,
    )
    assert summary.status_code == 200
    data = summary.json()
    assert data["expected_employee_days"] == 0
    assert data["present_employee_days"] == 0
    assert data["absent_employee_days"] == 0
    assert data["attendance_rate"] is None
    assert data["total_working_hours"] == 0.0

    absenteeism = client.get(
        f"/api/v1/reports/absenteeism?month=2026-10&employee_id={emp_id}",
        headers=headers,
    )
    assert absenteeism.status_code == 200
    assert absenteeism.json()["expected_employee_days"] == 0
    assert absenteeism.json()["absenteeism_rate"] is None


def test_monthly_summaries_and_trends_agree_consistently(client, monkeypatch):
    with SessionLocal() as db:
        admin = User(
            email="admin.agree@example.com",
            full_name="Admin Agree",
            password_hash=hash_password("admin-password"),
            role=UserRole.ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        emp1 = User(
            email="emp1.agree@example.com",
            full_name="Emp One",
            password_hash=hash_password("password"),
            role=UserRole.EMPLOYEE,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        emp2 = User(
            email="emp2.agree@example.com",
            full_name="Emp Two",
            password_hash=hash_password("password"),
            role=UserRole.EMPLOYEE,
            created_at=datetime(2026, 10, 3, tzinfo=timezone.utc),  # Joined Oct 3 (Sat)
        )
        db.add_all([admin, emp1, emp2])
        db.flush()
        db.add_all(
            [
                AttendanceRecord(
                    user_id=emp1.id,
                    work_date=date(2026, 10, 1),
                    punch_in_at=datetime(2026, 10, 1, 9, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 1, 17, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=emp1.id,
                    work_date=date(2026, 10, 2),
                    punch_in_at=datetime(2026, 10, 2, 9, tzinfo=timezone.utc),
                    punch_out_at=None,  # Incomplete
                ),
                AttendanceRecord(
                    user_id=emp2.id,
                    work_date=date(2026, 10, 3),  # Worked Saturday
                    punch_in_at=datetime(2026, 10, 3, 10, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 3, 14, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=emp2.id,
                    work_date=date(2026, 10, 5),
                    punch_in_at=datetime(2026, 10, 5, 9, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 5, 17, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()

    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 6, 12, tzinfo=timezone.utc),
    )
    headers = {"Authorization": f"Bearer {login(client, 'admin.agree@example.com', 'admin-password')}"}

    summary_res = client.get("/api/v1/reports/attendance-summary?month=2026-10", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()

    trends_res = client.get("/api/v1/reports/monthly-trends?month=2026-10", headers=headers)
    assert trends_res.status_code == 200
    trends = trends_res.json()

    points = trends["points"]
    # Verify exact reconciliation
    sum_present = sum(p["present_count"] for p in points)
    sum_absent = sum(p["absent_count"] for p in points)
    sum_completed = sum(p["completed_count"] for p in points)
    sum_incomplete = sum(p["incomplete_count"] for p in points)

    assert sum_present == summary["present_employee_days"]
    assert sum_absent == summary["absent_employee_days"]
    assert sum_completed == summary["completed_employee_days"]
    assert sum_incomplete == summary["incomplete_employee_days"]
    assert (sum_present + sum_absent) == summary["expected_employee_days"]


def test_assigned_shift_schedule_uses_actual_working_days(client, monkeypatch):
    from app.models.shift import Shift
    with SessionLocal() as db:
        admin = User(
            email="admin.shift@example.com",
            full_name="Admin Shift",
            password_hash=hash_password("admin-password"),
            role=UserRole.ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        # Shift working Sunday (6) through Thursday (3), with Friday (4) and Saturday (5) off
        shift = Shift(
            name="Sunday-Thursday Shift",
            start_time=time_obj(9, 0),
            end_time=time_obj(17, 0),
            timezone="UTC",
        )
        shift.working_days = {6, 0, 1, 2, 3}
        db.add(shift)
        db.flush()

        emp = User(
            email="emp.shift@example.com",
            full_name="Emp Shift",
            password_hash=hash_password("emp-password"),
            role=UserRole.EMPLOYEE,
            shift_id=shift.id,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.add_all([admin, emp])
        db.flush()
        # Period: Oct 1 (Thu, workday) to Oct 4 (Sun, workday).
        # Oct 2 (Fri, off) and Oct 3 (Sat, off).
        # Employee punches on Oct 1 and Oct 4 only.
        db.add_all(
            [
                AttendanceRecord(
                    user_id=emp.id,
                    work_date=date(2026, 10, 1),
                    punch_in_at=datetime(2026, 10, 1, 9, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 1, 17, tzinfo=timezone.utc),
                ),
                AttendanceRecord(
                    user_id=emp.id,
                    work_date=date(2026, 10, 4),
                    punch_in_at=datetime(2026, 10, 4, 9, tzinfo=timezone.utc),
                    punch_out_at=datetime(2026, 10, 4, 17, tzinfo=timezone.utc),
                ),
            ]
        )
        db.commit()
        emp_id = emp.id

    monkeypatch.setattr(
        reports_service,
        "utc_now",
        lambda: datetime(2026, 10, 4, 18, tzinfo=timezone.utc),
    )
    headers = {"Authorization": f"Bearer {login(client, 'admin.shift@example.com', 'admin-password')}"}

    summary = client.get(
        f"/api/v1/reports/attendance-summary?month=2026-10&employee_id={emp_id}",
        headers=headers,
    )
    assert summary.status_code == 200
    data = summary.json()
    # Expected: Oct 1 (Thu) and Oct 4 (Sun) = 2 days. Oct 2 (Fri) and Oct 3 (Sat) are off-days (0 expected).
    assert data["expected_employee_days"] == 2
    assert data["present_employee_days"] == 2
    assert data["absent_employee_days"] == 0
    assert data["attendance_rate"] == 100.0

