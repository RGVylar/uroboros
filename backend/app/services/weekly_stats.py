"""Resumen semanal de uso para el chat de admin de Telegram.

Lo lanza el programador de notification_scheduler los lunes por la mañana.
Son las mismas cifras de cabecera que scripts/stats.sql, sin datos personales:
solo recuentos, así que nada de lo que sale de aquí identifica a nadie.

Cada línea intenta responder a «¿tengo que hacer algo?»: si la gente vuelve
(retención), si la usa de verdad (constancia), dónde se cae la gente nueva,
qué bugs hay pendientes y si queda alguien con una APK vieja.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.bug_report import BugReport
from app.models.diary import DiaryEntry
from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus
from app.models.user import User
from app.services.telegram_alerts import send_stats_summary

logger = logging.getLogger(__name__)

_PLATFORM_LABEL = {"android": "Android", "ios": "iOS", "pwa": "PWA", "web": "Web"}
# Días con registro a partir de los cuales un diario cuenta como «completo».
_FULL_WEEK_DAYS = 5


def _version_key(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(p) for p in v.split("."))
    except ValueError:
        return (-1,)


def _delta(now: int, before: int) -> str:
    if now == before:
        return "="
    return f"▲{now - before}" if now > before else f"▼{before - now}"


def _fmt(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def build_weekly_summary(db: Session, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    week_ago, two_weeks_ago, month_ago = (now - timedelta(days=d) for d in (7, 14, 30))

    total = db.scalar(select(func.count()).select_from(User)) or 0
    new_7d = db.scalar(select(func.count()).select_from(User).where(User.created_at >= week_ago)) or 0

    def loggers(*conds) -> set[int]:
        return set(db.scalars(select(DiaryEntry.user_id).where(*conds).distinct()))

    this_week = loggers(DiaryEntry.consumed_at >= week_ago)
    prev_week = loggers(DiaryEntry.consumed_at >= two_weeks_ago, DiaryEntry.consumed_at < week_ago)
    older = loggers(DiaryEntry.consumed_at < two_weeks_ago)
    active_30d = len(loggers(DiaryEntry.consumed_at >= month_ago))
    stopped = len(prev_week - this_week)
    # Volver = apuntar esta semana tras una semana entera sin hacerlo.
    returned = len((this_week - prev_week) & older)

    # Constancia: días distintos con algo apuntado, por persona.
    day_pairs = db.execute(
        select(DiaryEntry.user_id, func.date(DiaryEntry.consumed_at))
        .where(DiaryEntry.consumed_at >= week_ago)
        .distinct()
    ).all()
    days_by_user: dict[int, int] = {}
    for uid, _ in day_pairs:
        days_by_user[uid] = days_by_user.get(uid, 0) + 1
    full_weeks = sum(1 for d in days_by_user.values() if d >= _FULL_WEEK_DAYS)

    entries_7d = db.scalar(select(func.count()).select_from(DiaryEntry).where(DiaryEntry.consumed_at >= week_ago)) or 0
    couples = db.scalar(
        select(func.count()).select_from(Friendship).where(
            Friendship.kind == FriendshipKind.partner,
            Friendship.status == FriendshipStatus.accepted,
        )
    ) or 0

    # Cuentas con más de una semana que nunca han apuntado nada: si crece, el
    # problema está en el primer uso, no en la retención.
    never_logged = db.scalar(
        select(func.count()).select_from(User).where(
            User.created_at < week_ago,
            ~select(DiaryEntry.id).where(DiaryEntry.user_id == User.id).exists(),
        )
    ) or 0

    bugs_new = db.scalar(select(func.count()).select_from(BugReport).where(BugReport.created_at >= week_ago)) or 0
    bugs_open = db.scalar(select(func.count()).select_from(BugReport).where(BugReport.resolved.is_(False))) or 0

    lines = [
        "📊 *[uroboros]* Resumen semanal",
        "",
        f"👥 Usuarios: *{total}* (+{new_7d} esta semana) · {couples} parejas",
        f"📝 Activos: *{len(this_week)}* (sem. anterior {len(prev_week)}, {_delta(len(this_week), len(prev_week))})"
        f" · {active_30d} en 30 días",
    ]
    if stopped or returned:
        lines.append(f"↩️ Dejaron de apuntar: {stopped} · Volvieron: {returned}")
    if this_week:
        avg_days = len(day_pairs) / len(this_week)
        per_day = entries_7d / len(day_pairs)
        lines += [
            f"📅 Constancia: {_fmt(avg_days)}/7 días de media · {full_weeks} con {_FULL_WEEK_DAYS}+ días",
            f"🍽 Entradas: {entries_7d} ({_fmt(per_day)} por persona y día)",
        ]
    if never_logged:
        lines.append(f"💤 Nunca han apuntado (cuenta de +7 días): {never_logged}")
    lines.append(f"🐞 Bugs: {bugs_new} nuevos · {bugs_open} sin resolver")

    # Versiones: solo quien ha abierto la app en los últimos 30 días, que es lo
    # que interesa para decidir si una APK vieja todavía importa. Quien está en
    # la última es una cifra; el desglose solo para los desactualizados.
    rows = db.execute(
        select(User.app_version, User.platform, func.count())
        .where(User.last_seen_at >= month_ago)
        .group_by(User.app_version, User.platform)
    ).all()
    unknown = db.scalar(
        select(func.count()).select_from(User).where(or_(User.last_seen_at.is_(None), User.last_seen_at < month_ago))
    ) or 0
    if rows:
        latest = max((r[0] or "" for r in rows), key=_version_key)
        up_to_date = sum(n for v, _, n in rows if v == latest)
        outdated = [r for r in rows if r[0] != latest]
        lines += ["", f"📱 Al día ({latest}): {up_to_date} · desactualizados: {sum(r[2] for r in outdated)}"]
        for version, platform, n in sorted(outdated, key=lambda r: (_version_key(r[0] or ""), r[1] or ""), reverse=True):
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
