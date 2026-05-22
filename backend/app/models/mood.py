from datetime import date

from sqlalchemy import Date, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 1 = bad, 2 = neutral, 3 = good
    energy: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    digestion: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    mood: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", name="uq_mood_user_date"),
    )
