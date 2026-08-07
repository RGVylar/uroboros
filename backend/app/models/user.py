from datetime import datetime, timezone, timedelta
from typing import Literal

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TRIAL_DAYS = 14
SubscriptionStatus = Literal["trial", "free", "premium"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Preset avatar slug (e.g. "aguacate"); null falls back to the initial disc.
    avatar_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Identity colour (OKLCH hue) shown as the avatar ring and the tint of this
    # user's rows in a partner's diary. Null falls back to the name-derived hue
    # that Avatar.svelte already computes, so old rows need no backfill.
    identity_hue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Nombre del WebP subido por el usuario (app/services/avatar_photo_service.py).
    # Tiene prioridad sobre avatar_id: quien sube foto quiere ver su foto.
    avatar_photo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Código de invitación que se comparte en vez del email para añadir amigos.
    # Nullable y generado la primera vez que se pide (app/invite_codes.py): las
    # filas antiguas no necesitan backfill y el alta no depende de acertar a la
    # primera con el índice único.
    invite_code: Mapped[str | None] = mapped_column(
        String(12), unique=True, index=True, nullable=True
    )
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
    # Launch-cohort users: full access for life, regardless of subscription.
    grandfathered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    # Opt-out of the in-app "what's new" changelog. When true, only notes marked
    # as major (feature launches) are shown; minor notes and the update nudge
    # are suppressed. It's a preference, so it lives here (syncs across devices)
    # rather than in localStorage.
    changelog_opt_out: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false()
    )
    # Features sin terminar que este usuario puede ver, p.ej. ["receipt_scan"].
    # Null = ninguna, que es lo normal. Es un permiso, no un rol: quien prueba
    # algo a medias no tiene por qué ser administrador (ver 0051 y deps.py).
    feature_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    def has_flag(self, flag: str) -> bool:
        return flag in (self.feature_flags or [])

    @property
    def effective_status(self) -> SubscriptionStatus:
        """Resolves grandfathering and 'trial'/'premium' expiry at runtime."""
        if self.grandfathered:
            return "premium"
        if self.subscription_status == "premium":
            # A real (paid) premium stays premium until its expiry, if any.
            if self.subscription_expires_at is None or datetime.now(timezone.utc) < self.subscription_expires_at:
                return "premium"
            return "free"
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
