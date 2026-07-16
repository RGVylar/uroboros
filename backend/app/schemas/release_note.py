from typing import Literal

from pydantic import BaseModel

ChangeType = Literal["nuevo", "mejora", "fix"]


class ReleaseNoteItem(BaseModel):
    type: ChangeType
    title: str
    desc: str = ""


class ReleaseNoteOut(BaseModel):
    version: str
    title: str
    importance: str
    items: list[ReleaseNoteItem]


class UpdateInfo(BaseModel):
    """Teaser for a published version newer than the one the user is running."""
    version: str
    title: str
    teaser: list[str]  # up to a couple of headline item titles
    more: int          # remaining changes not shown in the teaser


class ChangelogResponse(BaseModel):
    # Notes for versions the user already has but hasn't dismissed yet.
    news: list[ReleaseNoteOut]
    # A newer published version to nudge towards, if any.
    update: UpdateInfo | None = None
