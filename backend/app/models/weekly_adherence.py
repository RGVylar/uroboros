from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeeklyAdherence(Base):
    """Precomputed weekly adherence snapshot, one row per user per ISO week.

    Refreshed by a scheduler job so the anonymous percentile ("top X% de
    uroboros esta semana") is a single-row read instead of computing every
    user's adherence on each view. Only the percentage is stored — never any
    diary detail — and only users with ≥1 entry that week get a row.
    """

    __tablename__ = "weekly_adherence"
    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_adherence_user_week"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    pct: Mapped[int] = mapped_column(Integer, nullable=False)
    # Days that actually counted (past, non-cheat); 0-pct rows with counted=0 never exist.
    counted: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
