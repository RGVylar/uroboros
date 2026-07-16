from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReleaseNote(Base):
    """Server-driven patch notes.

    One row per app version. The frontend reports the version it is running
    (`current`) and the last version it dismissed (`seen`); the endpoint uses
    these plus `published` to decide what to show:

    - "Novedades": notes the user already has (version <= current) but hasn't
      seen yet — rendered as the full list in the changelog modal.
    - "Actualización disponible": a published version newer than `current` —
      rendered as a short teaser nudging the user to update (mainly Android,
      where the bundled frontend can lag behind).

    `items` is a JSON list of `{type, title, desc}` (type ∈ nuevo|mejora|fix),
    the same shape the modal already renders. `importance` gates the opt-out:
    'major' notes show even to users who muted the changelog, 'minor' don't.
    """

    __tablename__ = "release_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Dotted version string, e.g. "1.5". Unique — one row per version.
    version: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # 'minor' (respects opt-out) | 'major' (always shown)
    importance: Mapped[str] = mapped_column(String(10), nullable=False, server_default="minor")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
