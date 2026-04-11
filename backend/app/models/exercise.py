from datetime import datetime, date
from sqlalchemy import DateTime, Float, ForeignKey, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Exercise(Base):
    """Ejercicio predefinido por el usuario con su gasto calórico personal."""
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(nullable=False)
    kcal_per_unit: Mapped[float] = mapped_column(Float, nullable=False)  # Calorías por 1 unidad
    unit: Mapped[str] = mapped_column(nullable=False)  # "repeticiones", "minutos", "km", etc.

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación
    session_entries: Mapped[list["ExerciseSessionEntry"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )


class ExerciseSession(Base):
    """Sesión de ejercicio diaria agrupada por usuario."""
    __tablename__ = "exercise_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Unique constraint: (user_id, session_date) - una sesión por usuario por día

    total_calories: Mapped[float] = mapped_column(Float, nullable=False, default=0)  # Cache del total

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    entries: Mapped[list["ExerciseSessionEntry"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ExerciseSessionEntry(Base):
    """Entrada individual de un ejercicio dentro de una sesión."""
    __tablename__ = "exercise_session_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("exercise_sessions.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)

    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # Cuántas unidades
    calories: Mapped[float] = mapped_column(Float, nullable=False)  # Snapshot: quantity × exercise.kcal_per_unit

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relaciones
    session: Mapped["ExerciseSession"] = relationship(back_populates="entries")
    exercise: Mapped["Exercise"] = relationship(back_populates="session_entries")
