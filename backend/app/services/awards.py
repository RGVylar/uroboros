"""Podios semanales en el ranking global de adherencia.

Misma población que la fila "Tu constancia" de Ajustes: todos los que tienen
fila en weekly_adherence esa semana. Solo sale del servidor el puesto de la
persona; la población es un número, nunca nombres.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.weekly_adherence import WeeklyAdherence
from app.services.duel_service import week_start_for

# Weeks of history the awards look back on. Bounded so the query stays one
# indexed read no matter how long someone has been using the app.
AWARDS_WEEKS = 26


def weekly_awards(db: Session, user_id: int, today: date) -> dict:
    this_week = week_start_for(today)
    since = this_week - timedelta(weeks=AWARDS_WEEKS)
    # One aggregate per week I have a row in: population and how many beat me.
    # Two indexed reads however many users there are, instead of pulling
    # every row of the window into Python.
    mine_rows = db.execute(
        select(WeeklyAdherence.week_start, WeeklyAdherence.pct).where(
            WeeklyAdherence.user_id == user_id,
            WeeklyAdherence.week_start >= since,
        )
    ).all()
    result = {
        "gold": 0, "silver": 0, "bronze": 0,
        "current_rank": None, "current_total": 0,
        "best_rank": None, "best_total": None,
    }
    if not mine_rows:
        return result

    totals = dict(
        db.execute(
            select(WeeklyAdherence.week_start, func.count())
            .where(WeeklyAdherence.week_start >= since)
            .group_by(WeeklyAdherence.week_start)
        ).all()
    )

    for week_start, mine in mine_rows:
        total = totals.get(week_start, 1)
        # Same rules as the settings row: only *strictly better* pushes you down
        # (a tie at the top shares first place), and the podium is the medal:
        # 1st/2nd/3rd of the week are gold/silver/bronze, whatever the size.
        better = db.scalar(
            select(func.count()).select_from(WeeklyAdherence).where(
                WeeklyAdherence.week_start == week_start, WeeklyAdherence.pct > mine,
            )
        ) or 0
        rank = better + 1
        if week_start == this_week:
            result["current_rank"], result["current_total"] = rank, total
            continue  # the week in progress never mints metal
        if rank <= 3:
            result[("gold", "silver", "bronze")[rank - 1]] += 1
        # Best ever: the highest place, and among equal places the one won
        # against the most people.
        best, best_total = result["best_rank"], result["best_total"]
        if best is None or rank < best or (rank == best and total > (best_total or 0)):
            result["best_rank"], result["best_total"] = rank, total

    return result


