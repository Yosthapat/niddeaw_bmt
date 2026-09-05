from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status
from supabase import Client

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.player import Player, PlayerCreate, PlayerUpdate
from app.services.elo_service import SCORE_FLOOR, STARTING_SCORE, get_tier

router = APIRouter(prefix="/api/admin/players", tags=["admin-players"])

AVATAR_BUCKET = "avatars"
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2MB — client resizes before upload; this is a hard backstop

# Tables with a real FK on players(id) — matches.team1/2_player_ids are plain
# uuid[] columns with no FK, so a deleted player just becomes an unresolvable
# id in old match records (expected once they're gone), but these tables
# would reject the delete outright, so check them first for a clear error
# instead of a raw Postgres FK-violation message.
_DEPENDENT_PLAYER_COLUMNS: list[tuple[str, str]] = [
    ("checkins", "player_id"),
    ("billings", "player_id"),
    ("pairing_history", "player_a_id"),
    ("pairing_history", "player_b_id"),
    ("locked_pairs", "player_a_id"),
    ("locked_pairs", "player_b_id"),
]


def _player_has_history(supabase: Client, player_id: str) -> bool:
    return any(
        rows(supabase.table(table).select("id").eq(column, player_id).limit(1).execute())
        for table, column in _DEPENDENT_PLAYER_COLUMNS
    )


@router.get("", response_model=list[Player])
def list_all_players(supabase: SupabaseDep, admin: AdminDep) -> list[Player]:
    """Full roster including inactive members — unlike the public
    /api/players list, which only shows active players with stats."""
    result = supabase.table("players").select("*").order("nickname").execute()
    return [Player.model_validate(row) for row in rows(result)]


@router.post("", response_model=Player, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreate, supabase: SupabaseDep, admin: AdminDep) -> Player:
    elo_score = max(SCORE_FLOOR, payload.elo_score) if payload.elo_score is not None else STARTING_SCORE
    row = {
        **payload.model_dump(mode="json", exclude={"elo_score"}),
        "elo_score": elo_score,
        "elo_level": get_tier(elo_score),
        "is_active": True,
    }
    result = supabase.table("players").insert(row).execute()
    return Player.model_validate(rows(result)[0])


@router.patch("/{player_id}", response_model=Player)
def update_player(
    player_id: UUID, payload: PlayerUpdate, supabase: SupabaseDep, admin: AdminDep
) -> Player:
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "elo_score" in updates and updates["elo_score"] is not None:
        clamped = max(SCORE_FLOOR, updates["elo_score"])
        updates["elo_score"] = clamped
        updates["elo_level"] = get_tier(clamped)
    result = supabase.table("players").update(updates).eq("id", str(player_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(result_rows[0])


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(player_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Hard delete — only allowed for a player with no match/checkin/billing
    history, since those tables FK-reference players(id) with no cascade.
    member_seq is never reused or shifted for the players left behind (see
    db/migrations/0008_member_profile_fields.sql), so this never touches
    anyone else's row. A player with real history should be deactivated
    instead (PATCH is_active=false), which the admin UI already supports."""
    pid = str(player_id)
    if _player_has_history(supabase, pid):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ลบไม่ได้ เนื่องจากมีประวัติการเช็คอิน/แข่ง/บิลผูกอยู่ — ปิดใช้งานแทน",
        )
    result = supabase.table("players").delete().eq("id", pid).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")


@router.post("/{player_id}/avatar", response_model=Player)
async def upload_avatar(
    player_id: UUID, file: UploadFile, supabase: SupabaseDep, admin: AdminDep
) -> Player:
    contents = await file.read()
    if len(contents) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar file too large (max 2MB) — resize before uploading",
        )
    extension = (file.filename or "avatar.jpg").rsplit(".", 1)[-1].lower()
    if extension not in {"jpg", "jpeg", "png", "webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type"
        )
    storage_path = f"{player_id}.{extension}"

    supabase.storage.from_(AVATAR_BUCKET).upload(
        storage_path,
        contents,
        {"content-type": file.content_type or "image/jpeg", "upsert": "true"},
    )
    public_url = supabase.storage.from_(AVATAR_BUCKET).get_public_url(storage_path)

    result = (
        supabase.table("players")
        .update({"avatar_url": public_url})
        .eq("id", str(player_id))
        .execute()
    )
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(result_rows[0])
