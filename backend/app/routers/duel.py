"""Weekly adherence duel between the current user and a friend.

Gated on a double opt-in (both sides), mirroring shared inventory: only the
adherence percentage crosses over, never the diary itself.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
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


@router.get("/me/percentile")
def my_percentile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Anonymous standing among this week's active users.

    My own number is computed live (cheap: one user); the population comes from
    the precomputed snapshot, so cost never grows with the user count per view.
    Also returns last week's rank and population so the client can show the
    movement ("top 12% ↑ del 20%"). No names ever leave the server — just
    counts, so a small population is reported as a plain position instead."""
    from datetime import datetime as _dt, timedelta
    from math import ceil

    from app.models.weekly_adherence import WeeklyAdherence
    from app.services.adherence_snapshot import upsert_snapshot
    from app.services.duel_service import week_start_for

    def _population(week_start) -> int:
        return db.scalar(
            select(func.count()).select_from(WeeklyAdherence).where(WeeklyAdherence.week_start == week_start)
        ) or 0

    def _standing(week_start, mine: int) -> tuple[int, int, int]:
        """(rank, population, top band) for adherence `mine` that week.

        Rank is competition-style: only *strictly better* rows push you down, so
        a pack tied at the top all share position 1 instead of burying each
        other. The band follows from the rank, and is only meaningful with a
        decent population — with 4 users the best possible band is 25%, which is
        why the client shows the raw position below `SMALL_POPULATION`."""
        n = _population(week_start)
        if not n:
            return 1, 0, 100
        better = db.scalar(
            select(func.count()).select_from(WeeklyAdherence).where(
                WeeklyAdherence.week_start == week_start, WeeklyAdherence.pct > mine,
            )
        ) or 0
        rank = better + 1
        return rank, n, ceil(rank / n * 100)

    today = _dt.now(timezone.utc).date()
    ws = week_start_for(today)

    # Live-compute *my* number (cheap: one user) but only write/commit the
    # snapshot when it actually changed — the scheduler already refreshes
    # everyone's row several times a day, so most views are read-only.
    mine, changed = upsert_snapshot(db, user.id, today)
    if changed:
        db.commit()
    if mine is None:
        # Nothing counted yet this week (e.g. it's Monday) — no standing to show.
        return {"in_ranking": False, "active_users": _population(ws), "week": today.isocalendar().week}

    rank, n, top_percent = _standing(ws, mine.pct)

    # Points to whoever is immediately ahead — the row's "next step" for anyone
    # who isn't first. Anonymous: a distance, never who it belongs to.
    gap_to_next = None
    if rank > 1:
        next_pct = db.scalar(
            select(func.min(WeeklyAdherence.pct)).where(
                WeeklyAdherence.week_start == ws, WeeklyAdherence.pct > mine.pct,
            )
        )
        if next_pct is not None:
            gap_to_next = next_pct - mine.pct

    # A medal has to be earned, not handed out: podium *and* top half. Third of
    # four is not a bronze, it's third from last — and dressing it as an award
    # is what made the row read badly in the first place.
    medal = rank if rank <= 3 and rank * 2 <= n else None

    # Week-over-week movement: my position last week, only if I ranked then.
    # Both rank and population go out because the band alone can't tell "I got
    # worse" from "the population shrank" — #1 of 5 is top 20%, #1 of 4 is top
    # 25%, and calling that a drop would be a lie.
    prev_rank = prev_active_users = prev_top_percent = None
    prev_ws = ws - timedelta(days=7)
    my_prev = db.scalar(
        select(WeeklyAdherence.pct).where(
            WeeklyAdherence.user_id == user.id,
            WeeklyAdherence.week_start == prev_ws,
        )
    )
    if my_prev is not None:
        prev_rank, prev_active_users, prev_top_percent = _standing(prev_ws, my_prev)

    return {
        "in_ranking": True,
        "pct": mine.pct,
        "rank": rank,
        "active_users": n,
        "top_percent": top_percent,
        "gap_to_next": gap_to_next,
        "medal": medal,
        "prev_rank": prev_rank,
        "prev_active_users": prev_active_users,
        "prev_top_percent": prev_top_percent,
        "week": today.isocalendar().week,
    }


# Weeks of history the awards look back on. Bounded so the query stays one
# indexed read no matter how long someone has been using the app.
AWARDS_WEEKS = 26


@router.get("/me/awards")
def my_awards(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Weekly podiums among the friends you duel with.

    Deliberately *not* the global podium: that one hands out three places a week
    however many people are playing, so it stops being winnable for almost
    everyone as uroboros grows. A pool of friends doesn't grow without bound, so
    a podium there stays reachable forever.

    Restricted to friendships with the duel switched on by both sides. A rank
    within a named pool leaks how you compare to specific people, and that
    opt-in is exactly what governs sharing adherence with them.
    """
    from datetime import datetime as _dt, timedelta

    from app.models.weekly_adherence import WeeklyAdherence
    from app.services.adherence_snapshot import upsert_snapshot
    from app.services.duel_service import week_start_for

    today = _dt.now(timezone.utc).date()
    this_week = week_start_for(today)

    # Refresh my own row first or "this week" would show whatever the scheduler
    # last saw. Writes only when the value actually moved.
    _, changed = upsert_snapshot(db, user.id, today)
    if changed:
        db.commit()

    friendships = db.scalars(
        select(Friendship).where(
            or_(Friendship.requester_id == user.id, Friendship.receiver_id == user.id),
            Friendship.status == FriendshipStatus.accepted,
            Friendship.blocked_by.is_(None),
        )
    ).all()
    pool = {
        f.receiver_id if f.requester_id == user.id else f.requester_id
        for f in friendships
        if f.duel_active
    }

    empty = {
        "gold": 0, "silver": 0, "bronze": 0,
        "current_rank": None, "current_total": 0,
        "best_rank": None, "best_total": None,
        "pool": len(pool),
    }
    if not pool:
        return empty

    rows = db.execute(
        select(WeeklyAdherence.user_id, WeeklyAdherence.week_start, WeeklyAdherence.pct).where(
            WeeklyAdherence.user_id.in_(pool | {user.id}),
            WeeklyAdherence.week_start >= this_week - timedelta(weeks=AWARDS_WEEKS),
        )
    ).all()

    by_week: dict[object, dict[int, int]] = {}
    for uid, week_start, pct in rows:
        by_week.setdefault(week_start, {})[uid] = pct

    result = dict(empty)
    for week_start, pcts in by_week.items():
        mine = pcts.get(user.id)
        if mine is None:
            continue
        total = len(pcts)
        # Same rules as the settings row: only *strictly better* pushes you down
        # (a tie at the top shares first place), and a medal has to be earned —
        # podium *and* top half, so third of four is not a bronze.
        rank = sum(1 for pct in pcts.values() if pct > mine) + 1
        if week_start == this_week:
            result["current_rank"], result["current_total"] = rank, total
            continue  # the week in progress never mints metal
        if rank <= 3 and rank * 2 <= total:
            result[("gold", "silver", "bronze")[rank - 1]] += 1
        # Best ever: the highest place, and among equal places the one won
        # against the most people.
        best, best_total = result["best_rank"], result["best_total"]
        if best is None or rank < best or (rank == best and total > (best_total or 0)):
            result["best_rank"], result["best_total"] = rank, total

    return result


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
    base.me = DuelSideOut(name="Tú", avatar_id=user.avatar_id, avatar_photo=user.avatar_photo, pct=my_cur.pct, days=my_cur.states)
    base.them = DuelSideOut(
        name=friend.name, avatar_id=friend.avatar_id, avatar_photo=friend.avatar_photo, pct=their_cur.pct, days=their_cur.states
    )
    base.seasons_won = seasons
    base.history = history
    base.streak_weeks = streak
    base.badges = _badges(my_past, their_past, winners)
    return base
