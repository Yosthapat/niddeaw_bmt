from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from supabase import Client

from app.db_utils import rows
from app.deps import SupabaseDep
from app.models.match import Match
from app.models.player import NemesisInfo, Player, PlayerProfile, PlayerStats
from app.services import season_service, stats_service

router = APIRouter(prefix="/api/players", tags=["public-players"])


def _record_for(player: Player) -> stats_service.PlayerRecord:
    """Builds a PlayerRecord straight from a player's own denormalized
    counters — no match-history scan needed."""
    return stats_service.PlayerRecord(
        games=player.games, wins=player.wins, draws=player.draws, losses=player.losses
    )


def _to_stats(player: Player) -> PlayerStats:
    record = _record_for(player)
    return PlayerStats(
        player=player,
        games=record.games,
        wins=record.wins,
        draws=record.draws,
        losses=record.losses,
        points=record.points,
        avg_points=record.avg_points,
        score_percent=record.score_percent,
    )


@router.get("", response_model=list[PlayerStats])
def list_players(
    supabase: SupabaseDep,
    ids: list[UUID] | None = Query(default=None),
    limit: int | None = Query(default=None, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[PlayerStats]:
    """Omit ids/limit/offset to get the full active roster (used by other
    views' name/avatar lookups). Pass both limit and offset to paginate the
    member list.

    Pass `ids` instead to fetch exactly those players — deliberately not
    filtered by is_active, unlike the full-roster path above, since a
    caller resolving names for historical data (e.g. match history) needs
    a since-deactivated player's name too, not just active ones. limit/
    offset are ignored when ids is given."""
    if ids is not None:
        if not ids:
            return []
        players_result = (
            supabase.table("players").select("*").in_("id", [str(pid) for pid in ids]).execute()
        )
        stats = [_to_stats(Player.model_validate(row)) for row in rows(players_result)]
        stats.sort(key=lambda s: s.player.nickname.lower())
        return stats

    players_result = supabase.table("players").select("*").eq("is_active", True).execute()
    stats = [_to_stats(Player.model_validate(row)) for row in rows(players_result)]
    # Alphabetical roster — points-based ranking lives on the separate
    # /api/ranking endpoint (RankingView), not here.
    stats.sort(key=lambda s: s.player.nickname.lower())

    if limit is None:
        return stats
    return stats[offset : offset + limit]


@router.get("/{player_id}", response_model=Player)
def get_player(player_id: UUID, supabase: SupabaseDep) -> Player:
    result = supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute()
    player_rows = rows(result)
    if not player_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return Player.model_validate(player_rows[0])


def _fetch_player_rows(supabase: Client, player_id: UUID) -> list[dict[str, Any]]:
    result = supabase.table("players").select("*").eq("id", str(player_id)).limit(1).execute()
    return rows(result)


def _fetch_own_matches(
    supabase: Client,
    player_id: UUID,
    *,
    columns: str = "team1_player_ids, team2_player_ids, winner",
    session_ids: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Completed matches this player was on either side of — scans only
    their own history, not every completed match site-wide, so the nemesis
    breakdown stays cheap.

    The or=(...cs...) filter below is the single place the "player is in
    team1 OR team2" predicate lives; both the nemesis breakdown and the
    per-season match list go through here so there is one query to keep
    correct. It needs the GIN indexes from migration 0024 to avoid a full
    table scan.

    `session_ids=[]` means "no sessions in the requested range" and
    short-circuits: an empty `.in_()` would match nothing anyway, but
    skipping the round-trip says so out loud.

    Sorting is tied to pagination on purpose — the nemesis path aggregates
    every row regardless of order, so it shouldn't pay for a sort.
    """
    if session_ids is not None and not session_ids:
        return []
    query = (
        supabase.table("matches")
        .select(columns)
        .eq("status", "completed")
        .or_(f"team1_player_ids.cs.{{{player_id}}},team2_player_ids.cs.{{{player_id}}}")
    )
    if session_ids is not None:
        query = query.in_("session_id", session_ids)
    if limit is not None:
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    return rows(query.execute())


def _season_session_ids(supabase: Client, season: int) -> list[str] | None:
    """Session ids inside `season`'s calendar year, or None if there is no
    such season.

    Scoped through sessions.date rather than matches.created_at, same as the
    daily ranking: a Friday session running past midnight UTC would
    otherwise split across two calendar days, and at a year boundary it
    would land in the wrong season entirely.

    Two queries rather than one PostgREST embedded-resource join — a year of
    weekly play is ~52 ids, well inside what an `in_()` list handles, and
    embedded filtering is a pattern this codebase doesn't use anywhere else.
    """
    span = season_service.find_span(season_service.fetch_seasons(supabase), season)
    if span is None:
        return None
    result = (
        supabase.table("sessions")
        .select("id")
        .gte("date", span.start_date.isoformat())
        .lte("date", span.end_date.isoformat())
        .execute()
    )
    return [row["id"] for row in rows(result)]


def _fetch_active_player_rows(supabase: Client) -> list[dict[str, Any]]:
    result = supabase.table("players").select("*").eq("is_active", True).execute()
    return rows(result)


@router.get("/{player_id}/profile", response_model=PlayerProfile)
def get_player_profile(player_id: UUID, supabase: SupabaseDep) -> PlayerProfile:
    # The player row, this player's own match history, and the active
    # roster are independent of each other — fetch all three concurrently
    # instead of one after another.
    with ThreadPoolExecutor(max_workers=3) as pool:
        player_future = pool.submit(_fetch_player_rows, supabase, player_id)
        own_matches_future = pool.submit(_fetch_own_matches, supabase, player_id)
        active_players_future = pool.submit(_fetch_active_player_rows, supabase)

        player_rows = player_future.result()
        own_matches = own_matches_future.result()
        active_player_rows = active_players_future.result()

    if not player_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    player = Player.model_validate(player_rows[0])
    record = _record_for(player)

    # Nemesis needs a per-opponent breakdown of own_matches (fetched above)
    # before it knows who to look up — stays sequential after that point.
    nemesis: NemesisInfo | None = None
    nemesis_result = stats_service.find_nemesis(player_id, own_matches)  # type: ignore[arg-type]
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

    active_players = [Player.model_validate(row) for row in active_player_rows]
    elo_rank = stats_service.elo_rank(player.elo_score, [p.elo_score for p in active_players])
    similar_ids = stats_service.nearest_by_elo(
        player.elo_score, player.id, [(p.id, p.elo_score) for p in active_players]
    )
    players_by_id = {p.id: p for p in active_players}
    similar_players = [players_by_id[pid] for pid in similar_ids]

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
        elo_rank=elo_rank,
        total_ranked_players=len(active_players),
        similar_players=similar_players,
    )


@router.get("/{player_id}/matches", response_model=list[Match])
def list_player_matches(
    player_id: UUID,
    supabase: SupabaseDep,
    season: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[Match]:
    """This player's completed matches, newest first.

    Omitting `season` returns their whole history — the season filter is a
    view onto it, not a required scope, so the endpoint is useful on its
    own. A season number past the club's last one returns an empty list
    rather than 404: it's a list endpoint, and "that season has nothing in
    it" is the same answer a real but empty season would give.

    In-progress and queued matches are deliberately absent. Those change
    minute to minute and are served by /api/live, which the profile page
    polls separately — mixing them into a paginated history would mean a
    row silently moving between pages as a match ends.
    """
    session_ids: list[str] | None = None
    if season is not None:
        session_ids = _season_session_ids(supabase, season)
        if session_ids is None:
            return []
    match_rows = _fetch_own_matches(
        supabase,
        player_id,
        columns="*",
        session_ids=session_ids,
        limit=limit,
        offset=offset,
    )
    return [Match.model_validate(row) for row in match_rows]
