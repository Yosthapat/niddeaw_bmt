from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.player import NemesisInfo, Player, PlayerProfile, PlayerStats
from app.services import stats_service

router = APIRouter(prefix="/api/players", tags=["public-players"])


@router.get("", response_model=list[PlayerStats])
def list_players(supabase: SupabaseDep) -> list[PlayerStats]:
    players_result = supabase.table("players").select("*").eq("is_active", True).execute()
    matches_result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids, winner")
        .eq("status", "completed")
        .execute()
    )
    records = stats_service.build_player_records(rows(matches_result))  # type: ignore[arg-type]

    stats: list[PlayerStats] = []
    for row in rows(players_result):
        player = Player.model_validate(row)
        record = records.get(player.id, stats_service.PlayerRecord())
        stats.append(
            PlayerStats(
                player=player,
                games=record.games,
                wins=record.wins,
                draws=record.draws,
                losses=record.losses,
                points=record.points,
                avg_points=record.avg_points,
                score_percent=record.score_percent,
            )
        )
    return stats


@router.get("/{player_id}", response_model=Player)
def get_player(player_id: UUID, supabase: SupabaseDep) -> Player:
    result = supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute()
    player_rows = rows(result)
    if not player_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(player_rows[0])


@router.get("/{player_id}/profile", response_model=PlayerProfile)
def get_player_profile(player_id: UUID, supabase: SupabaseDep) -> PlayerProfile:
    player_result = supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute()
    player_rows = rows(player_result)
    if not player_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    player = Player.model_validate(player_rows[0])

    matches_result = (
        supabase.table("matches")
        .select("team1_player_ids, team2_player_ids, winner")
        .eq("status", "completed")
        .execute()
    )
    all_matches = rows(matches_result)
    records = stats_service.build_player_records(all_matches)  # type: ignore[arg-type]
    record = records.get(player_id, stats_service.PlayerRecord())

    nemesis: NemesisInfo | None = None
    nemesis_result = stats_service.find_nemesis(player_id, all_matches)  # type: ignore[arg-type]
    if nemesis_result is not None:
        nemesis_id, nemesis_record = nemesis_result
        nemesis_player_result = (
            supabase.table("players").select("*").eq("id", str(nemesis_id)).limit(1).execute()
        )
        nemesis_player_rows = rows(nemesis_player_result)
        if nemesis_player_rows:
            nemesis = NemesisInfo(
                player=Player.model_validate(nemesis_player_rows[0]),
                encounters=nemesis_record.encounters,
                wins=nemesis_record.wins,
                losses=nemesis_record.losses,
                draws=nemesis_record.draws,
            )

    return PlayerProfile(
        player=player,
        games=record.games,
        wins=record.wins,
        draws=record.draws,
        losses=record.losses,
        points=record.points,
        avg_points=record.avg_points,
        score_percent=record.score_percent,
        nemesis=nemesis,
    )
