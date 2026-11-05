from datetime import date, datetime

from pydantic import BaseModel, Field


class QuestLevel(BaseModel):
    threshold: int
    earned_at: datetime | None = None


class QuestState(BaseModel):
    """One quest for one member: how far they are and each level's date."""

    key: str
    value: int
    levels: list[QuestLevel]
    other_id: str | None = None
    """The partner (buddy) or the เทกันจัง (revenge) the count is about."""
    other_name: str | None = None


class PodiumState(BaseModel):
    """ELO tiers reached since counting started (0 Milk … 7 Absinthe)."""

    start_rank: int
    rank: int
    elo: int
    earned: list[datetime | None]


class MonthState(BaseModel):
    month: str  # "2026-12"
    target: int
    games: int
    earned_at: datetime | None = None


class SecretState(BaseModel):
    """A secret medal shows nothing about itself until it is earned."""

    key: str
    earned_at: datetime | None = None


class BadgeAward(BaseModel):
    badge: str
    level: int
    earned_at: datetime


class PlayerBadges(BaseModel):
    start_date: date
    quests: list[QuestState]
    podium: PodiumState
    month: MonthState
    past_months: list[MonthState]
    secrets: list[SecretState]
    linked: bool = True
    """Badges are for members who linked LINE. For one who hasn't, nothing
    below shows as earned; `waiting` says how many medals they already have
    in store, and `waiting_top` the grandest three, for the profile's nudge."""
    waiting: int = 0
    waiting_top: list[BadgeAward] = Field(default_factory=list)


class LineBadges(PlayerBadges):
    unseen: list[BadgeAward]
    """Medals the member hasn't been shown yet: the LINE page celebrates
    them once, then marks them seen."""


class BadgeFeedItem(BadgeAward):
    player_id: str
    nickname: str
    avatar_url: str | None = None


class SeenIn(BaseModel):
    items: list[BadgeAward] = Field(max_length=200)


class QuestSettings(BaseModel):
    start_date: date
    monthly_target: int


class QuestSettingsIn(BaseModel):
    start_date: date | None = None
    monthly_target: int | None = Field(default=None, ge=1, le=200)
