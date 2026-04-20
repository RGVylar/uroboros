from sqlalchemy import Boolean, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserGoals(Base):
    __tablename__ = "user_goals"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    water_ml: Mapped[float] = mapped_column(Float, nullable=False, server_default="2000")
    track_creatine: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    cheat_days_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    inventory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
