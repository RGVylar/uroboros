from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BetaSignup(Base):
    """Alguien que se ha apuntado a la prueba cerrada desde /beta.

    No es un usuario: todavía no tiene la app. Play solo deja instalarla a quien
    esté en la lista de emails de la prueba cerrada, y esa lista se mantiene a
    mano en Play Console; esto es la cola de quién falta por añadir
    (scripts/beta_signups.sql la lista y la marca como añadida).
    """

    __tablename__ = "beta_signups"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Siempre en minúsculas: es la clave para no apuntar dos veces a la misma
    # persona, y Google no distingue mayúsculas en el email.
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False, server_default="")
    lang: Mapped[str] = mapped_column(String(8), nullable=False, server_default="es")
    # Ya está en la lista de testers de Play Console.
    added: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
