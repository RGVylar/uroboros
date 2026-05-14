from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationPrefs(Base):
    """Per-user notification preferences."""

    __tablename__ = "notification_prefs"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Master switch — must be True for any push to be sent
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Quiet hours: no notifications between quiet_start and quiet_end (local hours)
    quiet_start: Mapped[int] = mapped_column(Integer, nullable=False, server_default="22")
    quiet_end: Mapped[int] = mapped_column(Integer, nullable=False, server_default="8")

    # ── Meal reminders ──────────────────────────────────────────────────────────
    # Only fires if that meal has NO entries yet for today
    breakfast_on: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    breakfast_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="'08:30'")

    lunch_on: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    lunch_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="'13:30'")

    dinner_on: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    dinner_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="'21:00'")

    # ── Streak alert ────────────────────────────────────────────────────────────
    # Fires if user has streak ≥ streak_min_days AND no entries today
    streak_on: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    streak_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="'20:00'")
    streak_min_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")

    # ── Daily summary ───────────────────────────────────────────────────────────
    # Fires if user logged ≥ 1 meal today
    summary_on: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    summary_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="'21:30'")

    # ── Water reminder ──────────────────────────────────────────────────────────
    # Fires if water < water_threshold * goal_ml
    water_on: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    water_time: Mapped[str] = mapped_column(String(5), nullable=False, server_default="'16:00'")

    # ── Timezone ────────────────────────────────────────────────────────────────
    # IANA timezone name (e.g. "Europe/Madrid"). All time comparisons use this.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="'UTC'")
