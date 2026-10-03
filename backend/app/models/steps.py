from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailySteps(Base):
    """Pasos de un día, leídos de la app de salud del móvil.

    Un total por día, no muestras sueltas: Health Connect ya agrega (y quita
    duplicados entre reloj y móvil), así que aquí se guarda su suma tal cual y
    cada sincronización la sobrescribe. Un día a medias se va actualizando.
    """

    __tablename__ = "daily_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    # De dónde vienen: 'health_connect' hoy; deja sitio a otras fuentes.
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="health_connect")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_daily_steps_user_day"),)
