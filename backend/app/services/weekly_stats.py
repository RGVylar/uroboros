"""Resumen semanal de uso para el chat de admin de Telegram.

Lo lanza el programador de notification_scheduler los lunes por la mañana.
Son las mismas cifras de cabecera que scripts/stats.sql, sin datos personales:
solo recuentos, así que nada de lo que sale de aquí identifica a nadie.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.diary import DiaryEntry
from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus
from app.models.user import User
from app.services.telegram_alerts import send_stats_summary

logger = logging.getLogger(__name__)

_PLATFORM_LABEL = {"android": "Android", "ios": "iOS", "pwa": "PWA", "web": "Web"}


def _version_key(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in v.split("."))
    except ValueError:
        return (-1,)


def build_weekly_summary(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    week_ago, month_ago = now - timedelta(days=7), now - timedelta(days=30)

    total = db.scalar(select(func.count()).select_from(User)) or 0
    new_7d = db.scalar(select(func.count()).select_from(User).where(User.created_at >= week_ago)) or 0

    def active_since(since: datetime) -> int:
        return db.scalar(
            select(func.count(func.distinct(DiaryEntry.user_id))).where(DiaryEntry.consumed_at >= since)
        ) or 0

    active_7d, active_30d = active_since(week_ago), active_since(month_ago)
    entries_7d = db.scalar(select(func.count()).select_from(DiaryEntry).where(DiaryEntry.consumed_at >= week_ago)) or 0
    couples = db.scalar(
        select(func.count()).select_from(Friendship).where(
            Friendship.kind == FriendshipKind.partner,
            Friendship.status == FriendshipStatus.accepted,
        )
    ) or 0

    # Versiones: solo quien ha abierto la app en los últimos 30 días, que es lo
    # que interesa para decidir si una APK vieja todavía importa.
    rows = db.execute(
        select(User.app_version, User.platform, func.count())
        .where(User.last_seen_at >= month_ago)
        .group_by(User.app_version, User.platform)
    ).all()
    unknown = db.scalar(
        select(func.count()).select_from(User).where(or_(User.last_seen_at.is_(None), User.last_seen_at < month_ago))
    ) or 0

    lines = [
        "📊 *[uroboros]* Resumen semanal",
        "",
        f"👥 Usuarios: *{total}* (+{new_7d} esta semana)",
        f"📝 Han registrado comida: *{active_7d}* en 7 días · {active_30d} en 30",
        f"🍽 Entradas en el diario esta semana: {entries_7d}",
        f"💑 Parejas: {couples}",
    ]
    if rows:
        lines += ["", "📱 *Versiones* (abiertas en 30 días)"]
        for version, platform, n in sorted(rows, key=lambda r: (_version_key(r[0] or ""), r[1] or ""), reverse=True):
            label = _PLATFORM_LABEL.get(platform, platform or "?")
            lines.append(f"• {version or '?'} · {label}: {n}")
    if unknown:
        lines.append(f"• Sin abrir en 30 días o sin datos: {unknown}")
    return "\n".join(lines)


def send_weekly_summary() -> None:
    """Tarea del programador (hilo aparte, sin bucle de asyncio propio)."""
    try:
        with SessionLocal() as db:
            text = build_weekly_summary(db)
        asyncio.run(send_stats_summary(text))
    except Exception:
        logger.exception("No se pudo mandar el resumen semanal")
