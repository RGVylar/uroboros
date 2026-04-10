from datetime import date

from sqlalchemy import Date, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WaterLog(Base):
    __tablename__ = "water_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    ml: Mapped[float] = mapped_column(Float, nullable=False)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False)
