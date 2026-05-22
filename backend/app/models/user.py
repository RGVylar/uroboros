from datetime import datetime, timezone, timedelta
from typing import Literal

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TRIAL_DAYS = 0  # TODO: cambiar a 14 antes de producción
SubscriptionStatus = Literal["trial", "free", "premium"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Subscription
    subscription_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="free"
    )
    trial_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def effective_status(self) -> SubscriptionStatus:
        """Resolves 'trial' expiry at runtime."""
        if self.subscription_status == "premium":
            return "premium"
        if self.subscription_status == "trial" and self.trial_started_at:
            expires = self.trial_started_at + timedelta(days=TRIAL_DAYS)
            if datetime.now(timezone.utc) < expires:
                return "trial"
        return "free"

    @property
    def is_premium_or_trial(self) -> bool:
        return self.effective_status in ("premium", "trial")

    @property
    def trial_days_left(self) -> int | None:
        if self.subscription_status != "trial" or not self.trial_started_at:
            return None
        expires = self.trial_started_at + timedelta(days=TRIAL_DAYS)
        delta = expires - datetime.now(timezone.utc)
        return max(0, delta.days)
