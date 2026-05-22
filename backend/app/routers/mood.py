from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.mood import MoodEntry

router = APIRouter(prefix="/mood", tags=["mood"])

# ── Schemas ───────────────────────────────────────────────────────────────────

MoodLevel = int | None  # 1=bad, 2=neutral, 3=good


class MoodIn(BaseModel):
    entry_date: date
    energy: MoodLevel = Field(default=None, ge=1, le=3)
    digestion: MoodLevel = Field(default=None, ge=1, le=3)
    mood: MoodLevel = Field(default=None, ge=1, le=3)
    notes: str | None = Field(default=None, max_length=500)


class MoodOut(BaseModel):
    entry_date: date
    energy: MoodLevel
    digestion: MoodLevel
    mood: MoodLevel
    notes: str | None
    # Worst level across all categories (used for diary chip)
    worst: int | None

    class Config:
        from_attributes = True


def _worst(entry: MoodEntry) -> int | None:
    vals = [v for v in [entry.energy, entry.digestion, entry.mood] if v is not None]
    return min(vals) if vals else None


def _to_out(entry: MoodEntry) -> MoodOut:
    return MoodOut(
        entry_date=entry.entry_date,
        energy=entry.energy,
        digestion=entry.digestion,
        mood=entry.mood,
        notes=entry.notes,
        worst=_worst(entry),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/day", response_model=MoodOut | None)
def get_mood(
    day: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.scalar(
        select(MoodEntry).where(
            MoodEntry.user_id == user.id,
            MoodEntry.entry_date == day,
        )
    )
    return _to_out(entry) if entry else None


@router.post("/day", response_model=MoodOut)
def upsert_mood(
    payload: MoodIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        insert(MoodEntry)
        .values(
            user_id=user.id,
            entry_date=payload.entry_date,
            energy=payload.energy,
            digestion=payload.digestion,
            mood=payload.mood,
            notes=payload.notes,
        )
        .on_conflict_do_update(
            constraint="uq_mood_user_date",
            set_={
                "energy": payload.energy,
                "digestion": payload.digestion,
                "mood": payload.mood,
                "notes": payload.notes,
            },
        )
        .returning(MoodEntry)
    )
    entry = db.execute(stmt).scalar_one()
    db.commit()
    return _to_out(entry)


@router.delete("/day", status_code=204)
def delete_mood(
    day: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.scalar(
        select(MoodEntry).where(
            MoodEntry.user_id == user.id,
            MoodEntry.entry_date == day,
        )
    )
    if entry:
        db.delete(entry)
        db.commit()


@router.get("/range", response_model=list[MoodOut])
def get_mood_range(
    date_from: date,
    date_to: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Used by the calendar to show mood icons across a date range."""
    entries = db.scalars(
        select(MoodEntry).where(
            MoodEntry.user_id == user.id,
            MoodEntry.entry_date >= date_from,
            MoodEntry.entry_date <= date_to,
        )
    ).all()
    return [_to_out(e) for e in entries]
