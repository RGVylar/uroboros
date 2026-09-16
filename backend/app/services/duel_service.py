"""Weekly adherence duel between two friends.

Adherence = how well a user follows *their own* targets, so the contest is fair
regardless of goal size (a cut and a maintenance are comparable). Each counted
day scores 0–100 and the week is the mean of its counted days.

Daily score = kcal part + protein part:
  kcal     KCAL_WEIGHT points within KCAL_FREE_ZONE of the effective goal,
           then linear down to 0 at KCAL_ZERO_AT (symmetric: under and over
           count the same, so eating less is never rewarded).
  protein  PROTEIN_WEIGHT points for reaching the effective protein target,
           proportional below it; overshooting doesn't cost anything.
  A day with nothing logged scores 0. Without goals set, logging anything at
  all scores 100 (reward constancy rather than penalise).

Day states (the strip in the UI):
  perfect  score ≥ PERFECT_SCORE
  hit      score ≥ HIT_SCORE
  miss     logged but below HIT_SCORE
  empty    no entry (counts against you, scores 0)
  joker    cheat day — excluded from the divisor, no score
  today    the day in progress — not counted yet

Effective goals mirror the frontend (`lib/goals.ts`): with exercise logged,
'proportional' scales kcal and protein by the same ratio; 'performance' adds the
burned calories to kcal and keeps protein fixed; 'off' leaves both untouched.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cheat_day import CheatDayLog
from app.models.diary import DiaryEntry
from app.models.exercise import ExerciseSession
from app.models.goals import UserGoals

KCAL_WEIGHT = 70             # points the calorie part is worth
PROTEIN_WEIGHT = 30          # points the protein part is worth
KCAL_FREE_ZONE = 100.0       # |kcal - goal| up to this earns the full calorie points
KCAL_ZERO_AT = 500.0         # |kcal - goal| from here on earns none
PERFECT_SCORE = 90           # day score from which the strip shows "clavado"
HIT_SCORE = 50               # day score from which the strip shows "en objetivo"
TIE_MARGIN = 5               # final % difference below which nobody wins
PHOTO_FINISH_MARGIN = 10     # winning by less than this earns the Photo finish badge
HISTORY_WEEKS = 6            # completed weeks used for the season tally


@dataclass
class DayDetail:
    """Breakdown of one scored day, so the UI can say *why* it got its points."""
    score: int
    kcal: int                # what was eaten
    kcal_goal: int           # effective goal that day
    kcal_pts: int
    protein: int
    protein_goal: int
    protein_pts: int


@dataclass
class WeekResult:
    states: list[str]        # 7 entries, Monday → Sunday
    pct: int | None          # mean day score (0–100), None if no countable days yet
    hits: int                # counted days at or above HIT_SCORE
    counted: int
    # 7 entries aligned with `states`: the day's score, 0 for a counted day with
    # nothing logged, None for days that aren't scored (future, today, joker).
    scores: list[int | None]
    # Same alignment; None wherever there was nothing logged to break down.
    details: list[DayDetail | None]


def week_start_for(day: date) -> date:
    """Monday of the ISO week containing `day`."""
    return day - timedelta(days=day.weekday())


def _effective_goals(
    goal_kcal: float | None, goal_protein: float | None, burned: float, mode: str
) -> tuple[float | None, float | None]:
    """(kcal target, protein target) for a day, adjusted for exercise."""
    if goal_kcal is None:
        return None, goal_protein
    if burned <= 0 or mode == "off":
        return goal_kcal, goal_protein
    kcal = goal_kcal + burned
    if mode == "proportional" and goal_protein is not None and goal_kcal > 0:
        return kcal, goal_protein * (kcal / goal_kcal)
    return kcal, goal_protein


def kcal_points(delta: float) -> int:
    """Calorie part of a day score from the distance to the effective goal."""
    over = max(0.0, abs(delta) - KCAL_FREE_ZONE)
    span = KCAL_ZERO_AT - KCAL_FREE_ZONE
    return round(KCAL_WEIGHT * max(0.0, 1 - over / span))


def protein_points(protein: float, goal: float | None) -> int:
    """Protein part of a day score: full marks at the target, proportional below."""
    if goal is None or goal <= 0:
        return PROTEIN_WEIGHT
    return round(PROTEIN_WEIGHT * min(1.0, protein / goal))


def day_score(
    kcal: float, protein: float, goal_kcal: float | None, goal_protein: float | None
) -> tuple[int, int, int]:
    """(score, kcal_pts, protein_pts) for a logged day.

    No calorie goal at all → full marks: reward having logged (constancy)
    rather than penalise someone who hasn't set targets yet."""
    if goal_kcal is None:
        return 100, KCAL_WEIGHT, PROTEIN_WEIGHT
    kp = kcal_points(kcal - goal_kcal)
    pp = protein_points(protein, goal_protein)
    return kp + pp, kp, pp


def _utc_date(dt: datetime) -> date:
    """Bucket a diary timestamp by UTC day.

    Postgres returns tz-aware datetimes; SQLite returns naive ones that already
    hold the UTC wall-clock we stored. Handle both without shifting the date."""
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(timezone.utc).date()


def _gather(db: Session, user_id: int, start: date, end: date):
    """Return (kcal_by_date, protein_by_date, burned_by_date, cheat_dates) for [start, end]."""
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)

    kcal_by_date: dict[date, float] = defaultdict(float)
    protein_by_date: dict[date, float] = defaultdict(float)
    for consumed_at, cal, prot in db.execute(
        select(DiaryEntry.consumed_at, DiaryEntry.calories, DiaryEntry.protein).where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.consumed_at >= start_dt,
            DiaryEntry.consumed_at <= end_dt,
        )
    ):
        d = _utc_date(consumed_at)
        kcal_by_date[d] += cal
        protein_by_date[d] += prot or 0.0

    burned_by_date: dict[date, float] = {
        sd: tc
        for sd, tc in db.execute(
            select(ExerciseSession.session_date, ExerciseSession.total_calories).where(
                ExerciseSession.user_id == user_id,
                ExerciseSession.session_date >= start,
                ExerciseSession.session_date <= end,
            )
        )
    }

    cheat_dates: set[date] = set(
        db.scalars(
            select(CheatDayLog.used_date).where(
                CheatDayLog.user_id == user_id,
                CheatDayLog.used_date >= start,
                CheatDayLog.used_date <= end,
            )
        )
    )
    return kcal_by_date, protein_by_date, burned_by_date, cheat_dates


def _week_result(
    week_start: date,
    today: date,
    kcal_by_date: dict[date, float],
    protein_by_date: dict[date, float],
    burned_by_date: dict[date, float],
    cheat_dates: set[date],
    goal_kcal: float | None,
    goal_protein: float | None,
    mode: str,
) -> WeekResult:
    states: list[str] = []
    scores: list[int | None] = []
    details: list[DayDetail | None] = []
    hits = 0
    counted = 0
    total = 0
    for i in range(7):
        d = week_start + timedelta(days=i)
        if d > today:
            states.append("empty")  # future day, shown but not counted
            scores.append(None)
            details.append(None)
            continue
        if d == today:
            states.append("today")
            scores.append(None)
            details.append(None)
            continue
        if d in cheat_dates:
            states.append("joker")
            scores.append(None)
            details.append(None)
            continue
        # Past, non-cheat day — counts towards adherence.
        counted += 1
        if d not in kcal_by_date:
            states.append("empty")
            scores.append(0)
            details.append(None)
            continue
        eff_kcal, eff_protein = _effective_goals(
            goal_kcal, goal_protein, burned_by_date.get(d, 0.0), mode
        )
        kcal = kcal_by_date[d]
        protein = protein_by_date.get(d, 0.0)
        score, kp, pp = day_score(kcal, protein, eff_kcal, eff_protein)
        total += score
        if score >= HIT_SCORE:
            hits += 1
        states.append("perfect" if score >= PERFECT_SCORE else "hit" if score >= HIT_SCORE else "miss")
        scores.append(score)
        details.append(DayDetail(
            score=score,
            kcal=round(kcal), kcal_goal=round(eff_kcal or 0), kcal_pts=kp,
            protein=round(protein), protein_goal=round(eff_protein or 0), protein_pts=pp,
        ))
    pct = round(total / counted) if counted else None
    return WeekResult(states=states, pct=pct, hits=hits, counted=counted, scores=scores, details=details)


def _user_goal(db: Session, user_id: int) -> tuple[float | None, float | None, str]:
    goals = db.scalar(select(UserGoals).where(UserGoals.user_id == user_id))
    if not goals:
        return None, None, "off"
    return goals.kcal, goals.protein, goals.macro_adjust_mode or "off"


def current_week(db: Session, user_id: int, today: date) -> WeekResult:
    """Adherence for just the week in progress — the cheap form the
    percentile snapshot job runs per user."""
    goal_kcal, goal_protein, mode = _user_goal(db, user_id)
    ws = week_start_for(today)
    data = _gather(db, user_id, ws, ws + timedelta(days=6))
    return _week_result(ws, today, *data, goal_kcal, goal_protein, mode)


def user_weeks(db: Session, user_id: int, today: date) -> tuple[WeekResult, list[WeekResult]]:
    """Return (current_week, [past weeks newest→oldest]) for a user.

    All data for the whole window is fetched once, then bucketed per week."""
    goal_kcal, goal_protein, mode = _user_goal(db, user_id)
    current_start = week_start_for(today)
    oldest_start = current_start - timedelta(weeks=HISTORY_WEEKS)
    data = _gather(db, user_id, oldest_start, current_start + timedelta(days=6))

    def result_for(ws: date) -> WeekResult:
        return _week_result(ws, today, *data, goal_kcal, goal_protein, mode)

    current = result_for(current_start)
    past = [result_for(current_start - timedelta(weeks=n)) for n in range(1, HISTORY_WEEKS + 1)]
    return current, past
