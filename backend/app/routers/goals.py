from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserGoals
from app.models.friendship import Friendship, FriendshipKind, FriendshipStatus
from app.schemas.misc import BodyProfileIn, GoalsIn, GoalsOut
from app.services.energy_balance import iso_week, weekly_proposal

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=GoalsOut)
def get_goals(
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    """Get the current user's goals, or a partner's (if can_add_food).

    Same rule as allergies: seeing someone's goals rides on the diary
    permission, both partner-only — you only need someone's goals to make
    sense of the totals you see when browsing their day.
    """
    target_id = user.id
    if user_id is not None and user_id != user.id:
        friendship = db.scalar(
            select(Friendship).where(
                Friendship.status == FriendshipStatus.accepted,
                Friendship.kind == FriendshipKind.partner,
                or_(
                    (Friendship.requester_id == user.id) & (Friendship.receiver_id == user_id) & Friendship.can_add_food.is_(True),
                    (Friendship.receiver_id == user.id) & (Friendship.requester_id == user_id) & Friendship.can_add_food_requester.is_(True),
                )
            )
        )
        if not friendship:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No permission to view this user's goals")
        target_id = user_id

    goals = db.get(UserGoals, target_id)
    if not goals:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goals not set")
    return goals


@router.put("", response_model=GoalsOut)
def upsert_goals(
    payload: GoalsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    goals = db.get(UserGoals, user.id)
    if not user.is_premium_or_trial:
        # Solo se bloquea *activar* lo Premium: quien ya lo tenía y pasó a free
        # puede seguir guardando el resto de objetivos sin tocarlo.
        prev_mode = goals.macro_adjust_mode if goals else "off"
        prev_cheat = goals.cheat_days_enabled if goals else False
        if (payload.macro_adjust_mode not in ("off", prev_mode)) or (
            payload.cheat_days_enabled and not prev_cheat
        ):
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "premium_required")
    if goals:
        # Solo lo que llega: la página de Objetivos manda kcal, macros y agua, y
        # rellenar el resto con los valores por defecto apagaba los cheat days,
        # el inventario y el ajuste de macros cada vez que se guardaba.
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(goals, k, v)
    else:
        goals = UserGoals(user_id=user.id, **payload.model_dump())
        db.add(goals)
    db.commit()
    db.refresh(goals)
    return goals


@router.patch("/profile", response_model=GoalsOut)
def update_profile(
    payload: BodyProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    """Perfil corporal (sexo, año de nacimiento, altura, actividad, objetivo).
    Solo se cambia lo que llega; hace falta tener objetivos."""
    goals = db.get(UserGoals, user.id)
    if not goals:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goals not set")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(goals, k, v)
    db.commit()
    db.refresh(goals)
    return goals


def _today() -> date:
    return datetime.now(timezone.utc).date()


@router.get("/proposal")
def get_proposal(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Propuesta semanal de objetivos a partir del gasto real.

    status: no_goals · answered (ya respondió esta semana) · not_enough_data ·
    unreliable · need_objective · on_track · proposal. `locked`: es PRO y no lo
    tiene; entonces no van los números, solo si hay propuesta.
    """
    today = _today()
    goals = db.get(UserGoals, user.id)
    if goals is None:
        return {"status": "no_goals", "locked": False}
    week = iso_week(today)
    out = asdict(weekly_proposal(db, user, today))
    out["week"] = week
    out["objective"] = goals.objective
    if goals.adapt_week == week and out["status"] in ("proposal", "need_objective"):
        out["status"] = "answered"
    out["locked"] = not user.is_premium_or_trial
    if out["locked"]:
        out = {k: out[k] for k in ("status", "locked", "week", "weighins", "logged_days", "span_days", "needs")}
    return out


class ProposalAnswer(BaseModel):
    action: Literal["apply", "dismiss"]


@router.post("/proposal", response_model=GoalsOut)
def answer_proposal(
    payload: ProposalAnswer,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserGoals:
    """Aplicar o "ahora no". Los números se recalculan aquí, no se fían del
    cliente. Cualquiera de las dos respuestas la esconde hasta la semana que viene."""
    goals = db.get(UserGoals, user.id)
    if not goals:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goals not set")
    today = _today()
    if payload.action == "apply":
        if not user.is_premium_or_trial:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "premium_required")
        p = weekly_proposal(db, user, today)
        if p is None or p.status != "proposal" or p.proposed is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "no_proposal")
        goals.kcal = p.proposed.kcal
        goals.protein = p.proposed.protein
        goals.carbs = p.proposed.carbs
        goals.fat = p.proposed.fat
    goals.adapt_week = iso_week(today)
    db.commit()
    db.refresh(goals)
    return goals
