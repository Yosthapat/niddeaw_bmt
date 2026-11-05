"""Quests and badges: public reads, the member's own medals on LINE, and the
admin's two settings (when counting started, the monthly target)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.db_utils import rows
from app.deps import AdminDep, LineMemberDep, SupabaseDep
from app.models.line import LineInvite
from app.models.quest import (
    BadgeAward,
    BadgeFeedItem,
    LineBadges,
    PlayerBadges,
    QuestSettings,
    QuestSettingsIn,
    SeenIn,
)
from app.routers.line import _member
from app.services import line_auth, line_checkin, promptpay_service, quest_store
from app.services.line_checkin import CLUB_TZ

public = APIRouter(prefix="/api/quests", tags=["public-quests"])
line = APIRouter(prefix="/api/line/badges", tags=["line"])
admin = APIRouter(prefix="/api/admin/quests", tags=["admin-quests"])


# While quests aren't switched on these answer null / empty rather than an
# error, so a page that asks simply shows no medals.


@public.get("/players/{player_id}", response_model=PlayerBadges | None)
def player_badges(player_id: UUID, supabase: SupabaseDep) -> PlayerBadges | None:
    snap = quest_store.snapshot_or_none(supabase)
    return quest_store.player_badges(snap, str(player_id)) if snap else None


@public.get("/top", response_model=dict[str, list[BadgeAward]])
def top(supabase: SupabaseDep) -> dict[str, list[BadgeAward]]:
    """Each member's three grandest medals, for the member cards."""
    snap = quest_store.snapshot_or_none(supabase)
    return quest_store.top_badges(snap) if snap else {}


@public.get("/recent", response_model=list[BadgeFeedItem])
def recent(
    supabase: SupabaseDep, limit: int = Query(default=8, ge=1, le=30)
) -> list[BadgeFeedItem]:
    snap = quest_store.snapshot_or_none(supabase)
    return quest_store.feed(snap, limit) if snap else []


@public.get("/line-invite", response_model=LineInvite | None)
def line_invite() -> LineInvite | None:
    """The club's LINE link and its QR, for the profile of a member who
    hasn't linked yet (badges are for linked members). null when LINE isn't
    set up."""
    if not line_auth.configured():
        return None
    url = line_checkin.invite_url()
    return LineInvite(url=url, qr_modules=promptpay_service.qr_modules(url))


@line.get("", response_model=LineBadges | None)
def mine(supabase: SupabaseDep, member: LineMemberDep) -> LineBadges | None:
    player = _member(supabase, member)
    snap = quest_store.snapshot_or_none(supabase)
    if snap is None:
        return None
    pid = str(player.id)
    return LineBadges(
        **quest_store.player_badges(snap, pid, linked=True).model_dump(),
        unseen=quest_store.unseen(snap, pid),
    )


@line.post("/seen", status_code=status.HTTP_204_NO_CONTENT)
def seen(payload: SeenIn, supabase: SupabaseDep, member: LineMemberDep) -> None:
    player = _member(supabase, member)
    quest_store.mark_seen(supabase, str(player.id), payload.items)


@admin.get("/settings", response_model=QuestSettings | None)
def get_settings(supabase: SupabaseDep, admin_: AdminDep) -> QuestSettings | None:
    try:
        return quest_store.load_settings(supabase)[0]
    except HTTPException as e:
        if e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            return None
        raise


@admin.put("/settings", response_model=QuestSettings)
def put_settings(
    payload: QuestSettingsIn, supabase: SupabaseDep, admin_: AdminDep
) -> QuestSettings:
    # A start in the future would count nothing: every medal would be taken
    # away, and found "new" again once the date is put back.
    if payload.start_date and payload.start_date > datetime.now(CLUB_TZ).date():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="วันเริ่มนับต้องไม่เกินวันนี้",
        )
    updates = payload.model_dump(mode="json", exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    quest_store.load_settings(supabase)  # 503 until 0038 runs
    rows(supabase.table("quest_settings").update(updates).eq("id", 1).execute())
    quest_store.invalidate()
    return quest_store.load_settings(supabase)[0]
