import json
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserSupplement(Base):
    __tablename__ = "user_supplements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(default=0)
    # JSON array of weekday ints (0=Mon … 6=Sun). NULL means every day.
    days_of_week_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    @property
    def days_of_week(self) -> list[int] | None:
        if self.days_of_week_json is None:
            return None
        return json.loads(self.days_of_week_json)

    @days_of_week.setter
    def days_of_week(self, value: list[int] | None) -> None:
        self.days_of_week_json = json.dumps(sorted(value)) if value is not None else None

    def active_today(self, weekday: int) -> bool:
        """True if this supplement should appear on the given weekday (0=Mon)."""
        days = self.days_of_week
        return days is None or weekday in days


class SupplementLog(Base):
    __tablename__ = "supplement_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    supplement_id: Mapped[int] = mapped_column(ForeignKey("user_supplements.id", ondelete="CASCADE"), nullable=False)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "supplement_id", "logged_date", name="uq_supp_log"),)
