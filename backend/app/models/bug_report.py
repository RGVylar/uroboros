from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BugReport(Base):
    """Un problema reportado desde Ajustes.

    El contexto (versión, plataforma, dispositivo) lo pone la app, no la
    persona: el primer informe de la beta costó una tarde porque nadie sabía que
    venía de un APK de julio. Con `app_version` delante se ve a la primera.

    La captura no se guarda: se reenvía a Telegram y se tira. Una captura de una
    app de comida puede llevar datos de salud, y aquí no hace falta tenerla.
    """

    __tablename__ = "bug_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # APP_VERSION del frontend que lleva el cliente. En la APK es la que vino
    # empaquetada, que es justo la que importa.
    app_version: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    # 'android' | 'ios' | 'pwa' | 'web'
    platform: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    device: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default="")
    route: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    had_screenshot: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
