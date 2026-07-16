"""Weekly adherence duel between the current user and a friend.

Gated on a double opt-in (both sides), mirroring shared inventory: only the
adherence percentage crosses over, never the diary itself.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.models.friendship import Friendship, FriendshipStatus
from app.schemas.duel import (
    DuelBadgeOut,
    DuelHistoryOut,
    DuelOut,
    DuelSeasons,
    DuelSideOut,
)
from app.services.duel_service import PHOTO_FINISH_MARGIN, TIE_MARGIN, WeekResult, user_weeks

router = APIRouter(prefix="/duel", tags=["duel"])


def _winner(me: WeekResult, them: WeekResult) -> str:
    a, b = me.pct or 0, them.pct or 0
    if me.counted == 0 and them.counted == 0:
        return "tie"
    if abs(a - b) < TIE_MARGIN:
        return "tie"
    return "me" if a > b else "them"


def _badges(
    my_past: list[WeekResult], their_past: list[WeekResult], winners: list[str]
) -> list[DuelBadgeOut]:
    """All lists are aligned and ordered newest→oldest."""
    swept = any(w.counted == 7 and w.hits == 7 for w in my_past)
    # Comeback: won a week right after losing the previous one.
    comeback = any(
        winners[i] == "me" and winners[i + 1] == "them"
        for i in range(len(winners) - 1)
    )
    # Close win: took a week by a slim margin (still a win, not a tie).
    photo = any(
        winners[i] == "me"
        and abs((my_past[i].pct or 0) - (their_past[i].pct or 0)) < PHOTO_FINISH_MARGIN
        for i in range(len(winners))
    )

    return [
        DuelBadgeOut(icon="🧹", label="Barrido", desc="7 de 7 días", unlocked=swept),
        DuelBadgeOut(icon="🎢", label="Remontada", desc="Ganar tras perder", unlocked=comeback),
        DuelBadgeOut(icon="📸", label="Photo finish", desc="Ganar por poco", unlocked=photo),
    ]


@router.get("/{friend_id}", response_model=DuelOut)
def get_duel(
    friend_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DuelOut:
    friendship = db.scalar(
        select(Friendship).where(
            or_(
                (Friendship.requester_id == user.id) & (Friendship.receiver_id == friend_id),
                (Friendship.requester_id == friend_id) & (Friendship.receiver_id == user.id),
            ),
            Friendship.status == FriendshipStatus.accepted,
        )
    )
    if not friendship:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No sois amigos")

    friend = db.get(User, friend_id)
    if not friend:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    i_am_requester = friendship.requester_id == user.id
    my_opt_in = (
        friendship.duel_opt_in_requester if i_am_requester else friendship.duel_opt_in_receiver
    )
    their_opt_in = (
        friendship.duel_opt_in_receiver if i_am_requester else friendship.duel_opt_in_requester
    )

    base = DuelOut(
        active=friendship.duel_active,
        my_opt_in=my_opt_in,
        their_opt_in=their_opt_in,
        friendship_id=friendship.id,
        friend_name=friend.name,
    )
    if not friendship.duel_active:
        return base

    today = datetime.now(timezone.utc).date()
    my_cur, my_past = user_weeks(db, user.id, today)
    their_cur, their_past = user_weeks(db, friend_id, today)

    # Season tally over the completed weeks (newest → oldest).
    winners = [_winner(m, t) for m, t in zip(my_past, their_past)]
    seasons = DuelSeasons(
        me=winners.count("me"),
        them=winners.count("them"),
    )
    # Trailing streak of weeks I won.
    streak = 0
    for w in winners:
        if w == "me":
            streak += 1
        else:
            break

    # History strip: oldest → newest, with the current week last (matches the UI).
    iso_week = today.isocalendar().week
    history: list[DuelHistoryOut] = []
    for n in range(len(winners), 0, -1):  # oldest first
        wk = iso_week - n
        if wk <= 0:
            wk += 52
        history.append(DuelHistoryOut(week=wk, winner=winners[n - 1]))
    history.append(DuelHistoryOut(week=iso_week, winner="current"))

    weekday = today.weekday()
    phase = "Empieza" if weekday == 0 else "Último día" if weekday == 6 else "En curso"

    base.week = iso_week
    base.phase = phase
    base.me = DuelSideOut(name="Tú", avatar_id=user.avatar_id, pct=my_cur.pct, days=my_cur.states)
    base.them = DuelSideOut(
        name=friend.name, avatar_id=friend.avatar_id, pct=their_cur.pct, days=their_cur.states
    )
    base.seasons_won = seasons
    base.history = history
    base.streak_weeks = streak
    base.badges = _badges(my_past, their_past, winners)
    return base
