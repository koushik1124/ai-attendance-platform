from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("uq_shifts_name_lower", func.lower(name), unique=True),
    )

    employees: Mapped[list["User"]] = relationship("User", back_populates="shift")

    _working_days_registry: dict[int, set[int]] = {}

    @property
    def working_days(self) -> set[int]:
        if getattr(self, "id", None) in Shift._working_days_registry:
            return Shift._working_days_registry[self.id]
        return getattr(self, "_working_days", {0, 1, 2, 3, 4})

    @working_days.setter
    def working_days(self, days: set[int] | list[int]) -> None:
        days_set = set(days)
        self._working_days = days_set
        if getattr(self, "id", None) is not None:
            Shift._working_days_registry[self.id] = days_set


from sqlalchemy import event


@event.listens_for(Shift, "after_insert")
def _receive_after_insert(mapper, connection, target):
    if hasattr(target, "_working_days"):
        Shift._working_days_registry[target.id] = target._working_days


if TYPE_CHECKING:
    from app.models.user import User
