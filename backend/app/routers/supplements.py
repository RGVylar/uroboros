from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.supplement import SupplementLog, UserSupplement

router = APIRouter(prefix="/supplements", tags=["supplements"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class SupplementIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SupplementOut(BaseModel):
    id: int
    name: str
    position: int

    class Config:
        from_attributes = True


class SupplementTodayOut(BaseModel):
    supplement_id: int
    name: str
    taken: bool


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[SupplementOut])
def list_supplements(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[UserSupplement]:
    return list(db.scalars(
        select(UserSupplement)
        .where(UserSupplement.user_id == user.id)
        .order_by(UserSupplement.position, UserSupplement.id)
    ))


@router.post("", response_model=SupplementOut, status_code=status.HTTP_201_CREATED)
def create_supplement(
    payload: SupplementIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserSupplement:
    count = db.scalar(
        select(UserSupplement).where(UserSupplement.user_id == user.id)
    )
    supp = UserSupplement(user_id=user.id, name=payload.name, position=0)
    db.add(supp)
    db.commit()
    db.refresh(supp)
    return supp


@router.put("/{supp_id}", response_model=SupplementOut)
def update_supplement(
    supp_id: int,
    payload: SupplementIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserSupplement:
    supp = db.get(UserSupplement, supp_id)
    if not supp or supp.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplement not found")
    supp.name = payload.name
    db.commit()
    db.refresh(supp)
    return supp


@router.delete("/{supp_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplement(
    supp_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    supp = db.get(UserSupplement, supp_id)
    if not supp or supp.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplement not found")
    db.delete(supp)
    db.commit()


# ── Monthly summary (for calendar) ───────────────────────────────────────────

@router.get("/month", response_model=list[str])
def get_supplement_month(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[str]:
    """Returns list of YYYY-MM-DD strings where at least one supplement was taken."""
    rows = db.execute(
        select(SupplementLog.logged_date).distinct().where(
            SupplementLog.user_id == user.id,
            extract("year", SupplementLog.logged_date) == year,
            extract("month", SupplementLog.logged_date) == month,
        )
    ).scalars().all()
    return [str(d) for d in rows]


# ── Daily log ─────────────────────────────────────────────────────────────────

@router.get("/today", response_model=list[SupplementTodayOut])
def get_today(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    today = date.today()
    supps = list(db.scalars(
        select(UserSupplement)
        .where(UserSupplement.user_id == user.id)
        .order_by(UserSupplement.position, UserSupplement.id)
    ))
    taken_ids = set(db.scalars(
        select(SupplementLog.supplement_id).where(
            SupplementLog.user_id == user.id,
            SupplementLog.logged_date == today,
        )
    ))
    return [
        {"supplement_id": s.id, "name": s.name, "taken": s.id in taken_ids}
        for s in supps
    ]


@router.post("/log/{supp_id}", response_model=list[SupplementTodayOut])
def log_supplement(
    supp_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    supp = db.get(UserSupplement, supp_id)
    if not supp or supp.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplement not found")
    today = date.today()
    existing = db.scalar(
        select(SupplementLog).where(
            SupplementLog.user_id == user.id,
            SupplementLog.supplement_id == supp_id,
            SupplementLog.logged_date == today,
        )
    )
    if not existing:
        db.add(SupplementLog(user_id=user.id, supplement_id=supp_id, logged_date=today))
        db.commit()
    return get_today(db=db, user=user)


@router.delete("/log/{supp_id}", response_model=list[SupplementTodayOut])
def unlog_supplement(
    supp_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    today = date.today()
    entry = db.scalar(
        select(SupplementLog).where(
            SupplementLog.user_id == user.id,
            SupplementLog.supplement_id == supp_id,
            SupplementLog.logged_date == today,
        )
    )
    if entry:
        db.delete(entry)
        db.commit()
    return get_today(db=db, user=user)
