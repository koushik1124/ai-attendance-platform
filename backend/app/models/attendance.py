from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("user_id", "work_date", name="uq_attendance_user_work_date"),
        CheckConstraint(
            "punch_out_at IS NULL OR punch_in_at IS NULL OR punch_out_at >= punch_in_at",
            name="ck_attendance_punch_order",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    punch_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    punch_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="attendance_records")

    @property
    def working_seconds(self) -> int | None:
        if self.punch_in_at is None or self.punch_out_at is None:
            return None
        pin = self.punch_in_at if self.punch_in_at.tzinfo else self.punch_in_at.replace(tzinfo=timezone.utc)
        pout = self.punch_out_at if self.punch_out_at.tzinfo else self.punch_out_at.replace(tzinfo=timezone.utc)
        return max(0, int((pout - pin).total_seconds()))

    @property
    def working_hours(self) -> float | None:
        sec = self.working_seconds
        if sec is None:
            return None
        return round(sec / 3600.0, 2)


if TYPE_CHECKING:
    from app.models.user import User
