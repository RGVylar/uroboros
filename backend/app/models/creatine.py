from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CreatineLog(Base):
    __tablename__ = "creatine_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "logged_date", name="uq_creatine_user_date"),)
