from pydantic import BaseModel


class DuelSideOut(BaseModel):
    name: str
    avatar_id: str | None = None
    avatar_photo: str | None = None
    pct: int | None
    days: list[str]  # 7 states Mon→Sun: hit|miss|empty|joker|today


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
    phase: str | None = None
    me: DuelSideOut | None = None
    them: DuelSideOut | None = None
    seasons_won: DuelSeasons | None = None
    history: list[DuelHistoryOut] | None = None
    streak_weeks: int | None = None
    badges: list[DuelBadgeOut] | None = None
