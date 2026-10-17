from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.time import utc_now
from app.models.attendance import AttendanceRecord
from app.models.shift import Shift
from app.models.user import User, UserRole
from app.schemas.reports import (
    AbsenteeismRead,
    AttendanceSummaryRead,
    MonthlyTrendPoint,
    MonthlyTrendRead,
    ReportBasis,
    ReportQuery,
    ReportScopeKind,
    ReportScopeRead,
)


@dataclass(frozen=True)
class ReportPeriod:
    month: str
    start: date
    end: date
    next_start: date


@dataclass(frozen=True)
class EmployeeScopeInfo:
    id: int
    joining_date: date
    shift_id: int | None
    working_days: set[int]


@dataclass(frozen=True)
class ReportScope:
    employee_ids: tuple[int, ...]
    kind: ReportScopeKind
    employee_id: int | None
    employees: tuple[EmployeeScopeInfo, ...] = ()

    @property
    def employee_count(self) -> int:
        return len(self.employee_ids)

    def as_read(self) -> ReportScopeRead:
        return ReportScopeRead(kind=self.kind, employee_id=self.employee_id)


@dataclass
class DailyCounts:
    present_ids: set[int]
    completed_ids: set[int]
    incomplete_ids: set[int]


@dataclass
class AttendanceReportData:
    daily_counts: dict[date, DailyCounts]
    total_working_seconds: int


def _parse_month(month: str) -> tuple[int, int]:
    year, month_number = month.split("-")
    return int(year), int(month_number)


def _period_for_month(month: str, now: datetime) -> ReportPeriod:
    year, month_number = _parse_month(month)
    now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    if (year, month_number) > (now_utc.year, now_utc.month):
        raise AppError(422, "month_in_future", "Reports are not available for a future month.")

    start = date(year, month_number, 1)
    if month_number == 12:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, month_number + 1, 1)
    end = next_start - timedelta(days=1)
    if (year, month_number) == (now_utc.year, now_utc.month):
        end = now_utc.date()
    return ReportPeriod(month=month, start=start, end=end, next_start=next_start)


def resolve_period(query: ReportQuery) -> ReportPeriod:
    return _period_for_month(query.month, utc_now())


def _joining_date_for_user(user: User) -> date:
    explicit_joining = getattr(user, "joining_date", None)
    if explicit_joining is not None:
        if isinstance(explicit_joining, datetime):
            return (
                explicit_joining.astimezone(timezone.utc).date()
                if explicit_joining.tzinfo
                else explicit_joining.date()
            )
        return explicit_joining
    created = user.created_at
    if created is None:
        return date.min
    return created.astimezone(timezone.utc).date() if created.tzinfo else created.date()


def _get_working_days(shift: Shift | None) -> set[int]:
    if shift is None:
        return {0, 1, 2, 3, 4}
    raw_days = getattr(shift, "working_days", None)
    if raw_days is None:
        return {0, 1, 2, 3, 4}
    day_map = {
        "mon": 0, "monday": 0,
        "tue": 1, "tuesday": 1,
        "wed": 2, "wednesday": 2,
        "thu": 3, "thursday": 3,
        "fri": 4, "friday": 4,
        "sat": 5, "saturday": 5,
        "sun": 6, "sunday": 6,
    }
    if isinstance(raw_days, (set, list, tuple)):
        result = set()
        for item in raw_days:
            if isinstance(item, int) and 0 <= item <= 6:
                result.add(item)
            elif isinstance(item, str):
                cleaned = item.strip().lower()
                if cleaned.isdigit() and 0 <= int(cleaned) <= 6:
                    result.add(int(cleaned))
                elif cleaned in day_map:
                    result.add(day_map[cleaned])
        return result if result else {0, 1, 2, 3, 4}
    if isinstance(raw_days, str):
        result = set()
        for part in raw_days.split(","):
            cleaned = part.strip().lower()
            if cleaned.isdigit() and 0 <= int(cleaned) <= 6:
                result.add(int(cleaned))
            elif cleaned in day_map:
                result.add(day_map[cleaned])
        return result if result else {0, 1, 2, 3, 4}
    return {0, 1, 2, 3, 4}


def resolve_scope(db: Session, current_user: User, query: ReportQuery) -> ReportScope:
    if current_user.role == UserRole.EMPLOYEE:
        if query.employee_id is not None:
            raise AppError(
                403,
                "forbidden",
                "Employees can only access their own attendance reports.",
            )
        shift = db.get(Shift, current_user.shift_id) if current_user.shift_id else None
        emp_info = EmployeeScopeInfo(
            id=current_user.id,
            joining_date=_joining_date_for_user(current_user),
            shift_id=current_user.shift_id,
            working_days=_get_working_days(shift),
        )
        return ReportScope(
            employee_ids=(current_user.id,),
            kind=ReportScopeKind.EMPLOYEE,
            employee_id=current_user.id,
            employees=(emp_info,),
        )

    if current_user.role != UserRole.ADMIN:
        raise AppError(403, "forbidden", "You do not have permission to access this resource.")

    if query.employee_id is not None:
        employee = db.scalar(
            select(User).where(
                User.id == query.employee_id,
                User.role == UserRole.EMPLOYEE,
            )
        )
        if employee is None:
            raise AppError(404, "employee_not_found", "Employee was not found.")
        shift = db.get(Shift, employee.shift_id) if employee.shift_id else None
        emp_info = EmployeeScopeInfo(
            id=employee.id,
            joining_date=_joining_date_for_user(employee),
            shift_id=employee.shift_id,
            working_days=_get_working_days(shift),
        )
        return ReportScope(
            employee_ids=(employee.id,),
            kind=ReportScopeKind.EMPLOYEE,
            employee_id=employee.id,
            employees=(emp_info,),
        )

    users = list(
        db.scalars(
            select(User).where(User.role == UserRole.EMPLOYEE).order_by(User.id)
        ).all()
    )
    shift_ids = {u.shift_id for u in users if u.shift_id is not None}
    shifts_by_id = (
        {s.id: s for s in db.scalars(select(Shift).where(Shift.id.in_(shift_ids))).all()}
        if shift_ids
        else {}
    )
    employees_info = tuple(
        EmployeeScopeInfo(
            id=u.id,
            joining_date=_joining_date_for_user(u),
            shift_id=u.shift_id,
            working_days=_get_working_days(shifts_by_id.get(u.shift_id)),
        )
        for u in users
    )
    return ReportScope(
        employee_ids=tuple(u.id for u in users),
        kind=ReportScopeKind.ALL_EMPLOYEES,
        employee_id=None,
        employees=employees_info,
    )


def _fetch_attendance_data(
    db: Session,
    scope: ReportScope,
    period: ReportPeriod,
) -> AttendanceReportData:
    if not scope.employee_ids:
        return AttendanceReportData(daily_counts={}, total_working_seconds=0)

    rows = db.execute(
        select(
            AttendanceRecord.user_id,
            AttendanceRecord.work_date,
            AttendanceRecord.punch_in_at,
            AttendanceRecord.punch_out_at,
        ).where(
            AttendanceRecord.user_id.in_(scope.employee_ids),
            AttendanceRecord.work_date >= period.start,
            AttendanceRecord.work_date < period.next_start,
            AttendanceRecord.work_date <= period.end,
        )
    ).all()

    statuses_by_day: dict[date, dict[int, str]] = {}
    total_working_seconds = 0

    for user_id, work_date, punch_in_at, punch_out_at in rows:
        if punch_in_at is None:
            continue
        day_statuses = statuses_by_day.setdefault(work_date, {})
        status = "completed" if punch_out_at is not None else "incomplete"
        previous_status = day_statuses.get(user_id)
        if previous_status != "completed":
            day_statuses[user_id] = status

        if punch_out_at is not None:
            pin = punch_in_at if punch_in_at.tzinfo else punch_in_at.replace(tzinfo=timezone.utc)
            pout = punch_out_at if punch_out_at.tzinfo else punch_out_at.replace(tzinfo=timezone.utc)
            total_working_seconds += max(0, int((pout - pin).total_seconds()))

    daily_counts = {
        work_date: DailyCounts(
            present_ids=set(statuses),
            completed_ids={uid for uid, st in statuses.items() if st == "completed"},
            incomplete_ids={uid for uid, st in statuses.items() if st == "incomplete"},
        )
        for work_date, statuses in statuses_by_day.items()
    }
    return AttendanceReportData(
        daily_counts=daily_counts,
        total_working_seconds=total_working_seconds,
    )


def _is_employee_expected_on_date(
    emp: EmployeeScopeInfo,
    work_date: date,
    basis: ReportBasis,
    is_present: bool,
) -> bool:
    if work_date < emp.joining_date:
        return False
    if basis == ReportBasis.CALENDAR_DAYS:
        return True
    is_scheduled = (work_date.weekday() in emp.working_days)
    return is_scheduled or is_present


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 2)


def monthly_trends(
    db: Session,
    current_user: User,
    query: ReportQuery,
) -> MonthlyTrendRead:
    period = resolve_period(query)
    scope = resolve_scope(db, current_user, query)
    report_data = _fetch_attendance_data(db, scope, period)
    daily_counts = report_data.daily_counts

    empty_counts = DailyCounts(present_ids=set(), completed_ids=set(), incomplete_ids=set())
    points: list[MonthlyTrendPoint] = []
    work_date = period.start

    while work_date <= period.end:
        counts = daily_counts.get(work_date, empty_counts)
        day_expected_count = 0
        for emp in scope.employees:
            is_present = emp.id in counts.present_ids
            if _is_employee_expected_on_date(emp, work_date, query.basis, is_present):
                day_expected_count += 1

        present_count = len(counts.present_ids)
        completed_count = len(counts.completed_ids)
        incomplete_count = len(counts.incomplete_ids)
        absent_count = max(0, day_expected_count - present_count)

        points.append(
            MonthlyTrendPoint(
                work_date=work_date,
                present_count=present_count,
                completed_count=completed_count,
                incomplete_count=incomplete_count,
                absent_count=absent_count,
            )
        )
        work_date += timedelta(days=1)

    return MonthlyTrendRead(
        month=period.month,
        period_start=period.start,
        period_end=period.end,
        scope=scope.as_read(),
        basis=query.basis,
        employee_count=scope.employee_count,
        points=points,
    )


def attendance_summary(
    db: Session,
    current_user: User,
    query: ReportQuery,
) -> AttendanceSummaryRead:
    period = resolve_period(query)
    scope = resolve_scope(db, current_user, query)
    report_data = _fetch_attendance_data(db, scope, period)
    daily_counts = report_data.daily_counts

    expected_employee_days = 0
    work_date = period.start
    empty_counts = DailyCounts(present_ids=set(), completed_ids=set(), incomplete_ids=set())

    while work_date <= period.end:
        counts = daily_counts.get(work_date, empty_counts)
        for emp in scope.employees:
            is_present = emp.id in counts.present_ids
            if _is_employee_expected_on_date(emp, work_date, query.basis, is_present):
                expected_employee_days += 1
        work_date += timedelta(days=1)

    present_employee_days = sum(len(c.present_ids) for c in daily_counts.values())
    completed_employee_days = sum(len(c.completed_ids) for c in daily_counts.values())
    incomplete_employee_days = sum(len(c.incomplete_ids) for c in daily_counts.values())
    absent_employee_days = max(0, expected_employee_days - present_employee_days)

    total_working_hours = (
        round(report_data.total_working_seconds / 3600.0, 2)
        if completed_employee_days > 0
        else 0.0
    )

    return AttendanceSummaryRead(
        month=period.month,
        period_start=period.start,
        period_end=period.end,
        scope=scope.as_read(),
        basis=query.basis,
        employee_count=scope.employee_count,
        expected_employee_days=expected_employee_days,
        present_employee_days=present_employee_days,
        completed_employee_days=completed_employee_days,
        incomplete_employee_days=incomplete_employee_days,
        absent_employee_days=absent_employee_days,
        attendance_rate=_rate(present_employee_days, expected_employee_days),
        total_working_hours=total_working_hours,
    )


def absenteeism(
    db: Session,
    current_user: User,
    query: ReportQuery,
) -> AbsenteeismRead:
    period = resolve_period(query)
    scope = resolve_scope(db, current_user, query)
    report_data = _fetch_attendance_data(db, scope, period)
    daily_counts = report_data.daily_counts

    expected_employee_days = 0
    work_date = period.start
    empty_counts = DailyCounts(present_ids=set(), completed_ids=set(), incomplete_ids=set())

    while work_date <= period.end:
        counts = daily_counts.get(work_date, empty_counts)
        for emp in scope.employees:
            is_present = emp.id in counts.present_ids
            if _is_employee_expected_on_date(emp, work_date, query.basis, is_present):
                expected_employee_days += 1
        work_date += timedelta(days=1)

    present_employee_days = sum(len(c.present_ids) for c in daily_counts.values())
    absent_employee_days = max(0, expected_employee_days - present_employee_days)

    return AbsenteeismRead(
        month=period.month,
        period_start=period.start,
        period_end=period.end,
        scope=scope.as_read(),
        basis=query.basis,
        employee_count=scope.employee_count,
        expected_employee_days=expected_employee_days,
        absent_employee_days=absent_employee_days,
        absenteeism_rate=_rate(absent_employee_days, expected_employee_days),
    )
