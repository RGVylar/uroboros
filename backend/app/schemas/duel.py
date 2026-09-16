from pydantic import BaseModel


class DuelDayDetailOut(BaseModel):
    """Why a day got its points: what was eaten against the effective targets."""
    score: int
    kcal: int
    kcal_goal: int
    kcal_pts: int
    protein: int
    protein_goal: int
    protein_pts: int


class DuelSideOut(BaseModel):
    name: str
    avatar_id: str | None = None
    avatar_photo: str | None = None
    pct: int | None  # mean day score of the counted days, 0-100
    days: list[str]  # 7 states Mon→Sun: perfect|hit|miss|empty|joker|today
    scores: list[int | None]  # 7 day scores; None where the day isn't scored
    details: list[DuelDayDetailOut | None]  # 7 breakdowns; None when nothing was logged


class DuelBadgeOut(BaseModel):
    icon: str
    label: str
    desc: str
    unlocked: bool


class DuelHistoryOut(BaseModel):
    week: int
    winner: str  # me|them|tie|current


class DuelSeasons(BaseModel):
    me: int
    them: int


class DuelOut(BaseModel):
    active: bool
    # Opt-in state (so the UI can show the "waiting for the other" prompt).
    my_opt_in: bool
    their_opt_in: bool
    friendship_id: int
    friend_name: str
    # Present only when active:
    week: int | None = None
    phase: str | None = None  # start|last_day|ongoing
    me: DuelSideOut | None = None
    them: DuelSideOut | None = None
    seasons_won: DuelSeasons | None = None
    history: list[DuelHistoryOut] | None = None
    streak_weeks: int | None = None
    badges: list[DuelBadgeOut] | None = None
