from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
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
    # Objetivo diario de pasos (Health Connect). Solo pinta la barra del diario.
    steps_goal: Mapped[int] = mapped_column(Integer, nullable=False, server_default="8000")
    track_creatine: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    cheat_days_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # Cuántos comodines se pueden gastar por semana (lunes a domingo). 1..7;
    # 7 equivale a "sin límite", porque la semana no da para más.
    cheat_days_per_week: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    inventory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    # How to adjust daily macro targets when exercise is logged:
    # 'off' = fixed goals (default), 'proportional' = scale all macros,
    # 'performance' = keep protein+fat fixed, add extra calories as carbs only
    macro_adjust_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default="off")

    # Perfil corporal del onboarding / calculadora de Objetivos. Nulo = no lo
    # ha dicho (cuentas anteriores a guardarlo). La propuesta semanal usa el
    # objetivo; el resto es para rellenar la calculadora la próxima vez.
    sex: Mapped[str | None] = mapped_column(String(8), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    objective: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Semana ISO ("2026-W41") en la que respondió a la propuesta semanal
    # (aplicar o ahora no): esa semana ya no se le vuelve a enseñar.
    adapt_week: Mapped[str] = mapped_column(String(10), nullable=False, server_default="")
