from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CheatDayLog(Base):
    __tablename__ = "cheat_day_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    used_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "used_date", name="uq_cheat_day_user_date"),)
