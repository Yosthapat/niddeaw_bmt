from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.player import Player, PlayerCreate, PlayerUpdate
from app.services.elo_service import SCORE_FLOOR, STARTING_SCORE, get_tier

router = APIRouter(prefix="/api/admin/players", tags=["admin-players"])

AVATAR_BUCKET = "avatars"
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2MB — client resizes before upload; this is a hard backstop


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
    result = supabase.table("players").update(updates).eq("id", str(player_id)).execute()
    result_rows = rows(result)
    if not result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(result_rows[0])


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
