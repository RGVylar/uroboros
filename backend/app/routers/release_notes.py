"""Server-driven changelog / update nudge.

The client reports the version it is running and the last version it dismissed;
this endpoint decides what to show. Keeping the text and the trigger on the
server means patch notes (and "please update" nudges) can change without a
frontend deploy — which matters most on Android, where the bundled frontend
can lag behind the latest release.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.release_note import ReleaseNote
from app.schemas.release_note import (
    ChangelogResponse,
    ReleaseNoteItem,
    ReleaseNoteOut,
    UpdateInfo,
)

router = APIRouter(prefix="/release-notes", tags=["release-notes"])


def _parse(version: str) -> tuple[int, ...]:
    """Turn '1.10' into (1, 10) for correct numeric ordering.

    Non-numeric or empty input sorts as the lowest possible version so an
    unknown/absent client version never hides notes."""
    try:
        return tuple(int(p) for p in version.strip().split("."))
    except (ValueError, AttributeError):
        return (-1,)


# The number of headline items shown in the "update available" teaser.
_TEASER_MAX = 2

# Tipos válidos + alias heredados. Las notas viejas (p.ej. la 1.6) usan "arreglo";
# normalizamos aquí para que un tipo legado o desconocido nunca tumbe el endpoint.
_VALID_TYPES = {"nuevo", "mejora", "fix"}
_TYPE_ALIASES = {"arreglo": "fix"}


def _norm_item(it: dict) -> dict:
    t = _TYPE_ALIASES.get(it.get("type"), it.get("type"))
    if t not in _VALID_TYPES:
        t = "mejora"
    return {**it, "type": t}


@router.get("", response_model=ChangelogResponse)
def get_changelog(
    current: str = "",
    seen: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChangelogResponse:
    """Return unseen notes for the running version + an optional update nudge.

    - `current`: the version the app build reports it is running.
    - `seen`: the last version the user dismissed (from localStorage).
    """
    cur = _parse(current) if current else (10**9,)  # no version → treat as newest
    last_seen = _parse(seen)

    notes = list(db.scalars(
        select(ReleaseNote).where(ReleaseNote.published.is_(True))
    ))
    # Muted users only get feature launches, never minor notes or minor nudges.
    opted_out = user.changelog_opt_out

    # ── News: versions the user has (<= current) and hasn't dismissed yet ──
    news = sorted(
        (n for n in notes if last_seen < _parse(n.version) <= cur),
        key=lambda n: _parse(n.version),
        reverse=True,
    )
    if opted_out:
        news = [n for n in news if n.importance == "major"]

    news_out = [
        ReleaseNoteOut(
            version=n.version,
            title=n.title,
            importance=n.importance,
            items=[ReleaseNoteItem(**_norm_item(it)) for it in (n.items or [])],
        )
        for n in news
    ]

    # ── Update available: the newest published version above `current` ──
    newer = [n for n in notes if _parse(n.version) > cur]
    update: UpdateInfo | None = None
    if newer:
        latest = max(newer, key=lambda n: _parse(n.version))
        # A minor update is just noise to a muted user; a major one still nudges.
        if not (opted_out and latest.importance != "major"):
            items = latest.items or []
            teaser = [it["title"] for it in items[:_TEASER_MAX]]
            update = UpdateInfo(
                version=latest.version,
                title=latest.title,
                teaser=teaser,
                more=max(0, len(items) - len(teaser)),
            )

    return ChangelogResponse(news=news_out, update=update)
