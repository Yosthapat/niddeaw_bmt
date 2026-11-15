from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from supabase import Client

from app.db_utils import rows
from app.deps import AdminDep, SupabaseDep
from app.models.match import TEAM_SIZE_BY_TYPE, Match, MatchResultSubmit, Winner
from app.models.matchmaking import (
    LockedPair,
    LockedPairCreate,
    MatchmakingConfirmRequest,
    MatchmakingEditRequest,
    MatchmakingMoveRequest,
    MatchmakingQueueResponse,
    MatchmakingSuggestionResponse,
    MatchmakingSwapRequest,
)
from app.services import elo_service, matchmaking_service, queue_service, record_service
from app.services.session_state import ensure_session_open

router = APIRouter(prefix="/api/admin/matchmaking", tags=["admin-matchmaking"])


@router.post("/locked-pairs", response_model=LockedPair, status_code=status.HTTP_201_CREATED)
def create_locked_pair(
    payload: LockedPairCreate, supabase: SupabaseDep, admin: AdminDep
) -> LockedPair:
    """Pins two checked-in players as teammates for the rest of this
    session — e.g. two friends who came together today. Never sticks to
    their profile; it's tied to this session_id and cascade-deletes with
    it."""
    existing = queue_service.fetch_locked_pairs(supabase, payload.session_id)
    already_locked = {pid for lp in existing for pid in (lp.player_a_id, lp.player_b_id)}
    if payload.player_a_id in already_locked or payload.player_b_id in already_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One of these players is already locked with someone else this session",
        )

    row = {
        "session_id": str(payload.session_id),
        "player_a_id": str(payload.player_a_id),
        "player_b_id": str(payload.player_b_id),
    }
    result = supabase.table("locked_pairs").insert(row).execute()
    return LockedPair.model_validate(rows(result)[0])


@router.delete("/locked-pairs/{lock_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_locked_pair(lock_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    result = supabase.table("locked_pairs").delete().eq("id", str(lock_id)).execute()
    if not rows(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locked pair not found")


@router.get("/suggest", response_model=MatchmakingSuggestionResponse)
def suggest(
    session_id: UUID, supabase: SupabaseDep, admin: AdminDep
) -> MatchmakingSuggestionResponse:
    suggestions, waiting = queue_service.build_suggestions(supabase, session_id)
    return MatchmakingSuggestionResponse(suggestions=suggestions, waiting_player_ids=waiting)


@router.get("/queue", response_model=MatchmakingQueueResponse)
def queue(session_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> MatchmakingQueueResponse:
    return queue_service.build_queue(supabase, session_id)


@router.post("/confirm", response_model=Match, status_code=status.HTTP_201_CREATED)
def confirm(payload: MatchmakingConfirmRequest, supabase: SupabaseDep, admin: AdminDep) -> Match:
    # Same reason as check-in: a match created after the session was billed
    # changes nobody's shuttlecock count.
    ensure_session_open(supabase, payload.session_id)
    submitted_ids = set(payload.team1_player_ids + payload.team2_player_ids)
    queued_ids = queue_service.players_in_queued_matches(supabase, payload.session_id)
    if payload.status == "in_progress":
        in_progress_ids = queue_service.players_in_progress(supabase, payload.session_id)
        conflict = submitted_ids & (in_progress_ids | queued_ids)
    else:
        conflict = submitted_ids & queued_ids
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ผู้เล่นบางคนถูกจับคู่ไว้ในแมตช์อื่นอยู่แล้ว",
        )

    round_no = queue_service.current_round_no(supabase, payload.session_id)
    now = datetime.now(timezone.utc).isoformat()

    match_row = {
        "session_id": str(payload.session_id),
        "type": payload.type,
        "team1_player_ids": [str(pid) for pid in payload.team1_player_ids],
        "team2_player_ids": [str(pid) for pid in payload.team2_player_ids],
        "status": payload.status,
        "court": payload.court,
        "created_at": now,
        "updated_at": now,
    }
    match_result = supabase.table("matches").insert(match_row).execute()
    match_result_rows = rows(match_result)
    match_id = match_result_rows[0]["id"]

    history_rows: list[dict[str, Any]] = matchmaking_service.build_pairing_history_rows(
        tuple(payload.team1_player_ids), tuple(payload.team2_player_ids), round_no
    )
    for row in history_rows:
        row["session_id"] = str(payload.session_id)
        row["match_id"] = match_id
    if history_rows:
        supabase.table("pairing_history").insert(history_rows).execute()

    return Match.model_validate(match_result_rows[0])


@router.patch("/matches/{match_id}", response_model=Match)
def edit_queued_match(
    match_id: UUID, payload: MatchmakingEditRequest, supabase: SupabaseDep, admin: AdminDep
) -> Match:
    """Rewrites a queued pairing's players/court in place. Only while it's
    still queued: an in_progress match's players are already on court, and a
    completed one's result and ELO are banked.

    Edits in place rather than cancel-and-recreate so the match keeps its id
    and its round_no — current_round_no() counts every match in the session,
    so a delete-then-insert would shift the round number and quietly rewrite
    what the fairness lookback sees."""
    match_result = supabase.table("matches").select("*").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(match_result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    match_row = match_rows[0]
    if match_row["status"] != "queued":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only a queued match can be edited"
        )

    expected = TEAM_SIZE_BY_TYPE[match_row["type"]]
    if len(payload.team1_player_ids) != expected or len(payload.team2_player_ids) != expected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"match type '{match_row['type']}' requires {expected} player(s) per team",
        )

    session_id = UUID(match_row["session_id"])
    submitted_ids = set(payload.team1_player_ids + payload.team2_player_ids)
    # Same rule confirm() applies to a queued match: a player still finishing
    # an in_progress match is a valid pick for their *next* one, so only
    # other queued matches can conflict.
    conflict = submitted_ids & queue_service.players_in_queued_matches(
        supabase, session_id, exclude_match_id=match_id
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ผู้เล่นบางคนถูกจับคู่ไว้ในแมตช์อื่นอยู่แล้ว",
        )

    return Match.model_validate(
        _rewrite_queued(
            supabase, match_row, payload.team1_player_ids, payload.team2_player_ids, payload.court
        )
    )


def _rewrite_queued(
    supabase: Client,
    match_row: dict[str, Any],
    team1: list[UUID],
    team2: list[UUID],
    court: str | None,
) -> dict[str, Any]:
    """Writes a queued match's new teams, and its pairing_history to match."""
    match_id = match_row["id"]
    session_id = match_row["session_id"]
    updated = (
        supabase.table("matches")
        .update(
            {
                "team1_player_ids": [str(pid) for pid in team1],
                "team2_player_ids": [str(pid) for pid in team2],
                "court": court,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(match_id))
        .execute()
    )

    # Keep the fairness lookback in step with who is actually paired now. The
    # round_no is read back off the existing rows rather than recomputed:
    # current_round_no() would hand back this match's round + 1. With no rows
    # to read it from, leave the history alone — under-counting a pairing
    # only weakens a future suggestion's penalty, while guessing a round
    # number would misorder the lookback for every match after it.
    history_result = (
        supabase.table("pairing_history")
        .select("round_no")
        .eq("match_id", str(match_id))
        .limit(1)
        .execute()
    )
    existing_history = rows(history_result)
    if existing_history:
        round_no = existing_history[0]["round_no"]
        # Delete first: Supabase REST has no transactions, and a crash
        # part-way leaving this match with no history (a penalty that
        # under-counts) beats one leaving both pairings counted.
        supabase.table("pairing_history").delete().eq("match_id", str(match_id)).execute()
        history_rows: list[dict[str, Any]] = matchmaking_service.build_pairing_history_rows(
            tuple(team1), tuple(team2), round_no
        )
        for row in history_rows:
            row["session_id"] = str(session_id)
            row["match_id"] = str(match_id)
        if history_rows:
            supabase.table("pairing_history").insert(history_rows).execute()

    return rows(updated)[0]


def _queued(supabase: Client, session_id: UUID | str) -> list[dict[str, Any]]:
    """The session's queued matches in queue order: the order their numbers
    run in (matches_numbered: created_at, then id)."""
    found = rows(
        supabase.table("matches")
        .select("*")
        .eq("session_id", str(session_id))
        .eq("status", "queued")
        .execute()
    )
    found = [m for m in found if m["status"] == "queued" and str(m["session_id"]) == str(session_id)]
    return sorted(found, key=lambda m: (str(m["created_at"]), str(m["id"])))


@router.post("/matches/{match_id}/move", response_model=MatchmakingQueueResponse)
def move_queued_match(
    match_id: UUID, payload: MatchmakingMoveRequest, supabase: SupabaseDep, admin: AdminDep
) -> MatchmakingQueueResponse:
    """Moves a queued match one place up or down the queue, for a pairing
    confirmed in the wrong order. The two neighbours trade created_at, so
    their match numbers trade too: the one going on first keeps the lower
    number. Nothing else reads created_at of a queued match."""
    found = rows(supabase.table("matches").select("*").eq("id", str(match_id)).limit(1).execute())
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if found[0]["status"] != "queued":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="เลื่อนได้เฉพาะแมตช์ที่รอคิวอยู่")
    queue = _queued(supabase, found[0]["session_id"])
    at = next(i for i, m in enumerate(queue) if str(m["id"]) == str(match_id))
    other = at - 1 if payload.direction == "up" else at + 1
    if 0 <= other < len(queue):
        mine, theirs = queue[at], queue[other]
        # created_at isn't unique: nudge so the two can't tie and fall back
        # on the id order they had
        a, b = str(mine["created_at"]), str(theirs["created_at"])
        if a == b:
            moment = datetime.fromisoformat(a)
            a = (moment + timedelta(microseconds=1 if other < at else -1)).isoformat()
        supabase.table("matches").update({"created_at": b}).eq("id", str(mine["id"])).execute()
        supabase.table("matches").update({"created_at": a}).eq("id", str(theirs["id"])).execute()
    return queue_service.build_queue(supabase, UUID(str(found[0]["session_id"])))


@router.post("/swap", response_model=MatchmakingQueueResponse)
def swap_players(
    payload: MatchmakingSwapRequest, supabase: SupabaseDep, admin: AdminDep
) -> MatchmakingQueueResponse:
    """Two players change places, for a pairing confirmed wrong: within a
    queued match (across the net), between two queued matches, or with
    someone waiting, who takes the other's place. Swapping the same two
    again puts things back."""
    a, b = str(payload.player_a_id), str(payload.player_b_id)
    if a == b:
        return queue_service.build_queue(supabase, payload.session_id)
    queue = _queued(supabase, payload.session_id)

    def place(pid: str) -> tuple[dict[str, Any], str, int] | None:
        for m in queue:
            for side in ("team1_player_ids", "team2_player_ids"):
                ids = [str(x) for x in m[side]]
                if pid in ids:
                    return m, side, ids.index(pid)
        return None

    pa, pb = place(a), place(b)
    if pa is None and pb is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="ต้องมีอย่างน้อยหนึ่งคนอยู่ในคิวถัดไป"
        )
    if pa is None or pb is None:
        # one of them is waiting: they must be in tonight and not resting
        waiting = b if pa is not None else a
        checkin = rows(
            supabase.table("checkins")
            .select("*")
            .eq("session_id", str(payload.session_id))
            .eq("player_id", waiting)
            .limit(1)
            .execute()
        )
        if not checkin or checkin[0].get("checkout_time") is not None or checkin[0].get("paused_at"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="คนนี้ไม่ได้รอคิวอยู่ (ยังไม่เช็คอิน กำลังพัก หรือกลับแล้ว)"
            )

    teams: dict[str, dict[str, list[str]]] = {}

    def team(m: dict[str, Any], side: str) -> list[str]:
        held = teams.setdefault(
            str(m["id"]),
            {
                "team1_player_ids": [str(x) for x in m["team1_player_ids"]],
                "team2_player_ids": [str(x) for x in m["team2_player_ids"]],
            },
        )
        return held[side]

    if pa is not None:
        team(pa[0], pa[1])[pa[2]] = b
    if pb is not None:
        team(pb[0], pb[1])[pb[2]] = a
    by_id = {str(m["id"]): m for m in queue}
    for match_id, held in teams.items():
        m = by_id[match_id]
        _rewrite_queued(
            supabase,
            m,
            [UUID(x) for x in held["team1_player_ids"]],
            [UUID(x) for x in held["team2_player_ids"]],
            m.get("court"),
        )
    return queue_service.build_queue(supabase, payload.session_id)


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_match(match_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> None:
    """Cancels a mis-paired or no-longer-needed match — only while it's still
    queued or in_progress, so a completed match's result/ELO history can't
    be erased by mistake. pairing_history rows cascade-delete with the
    match."""
    match_result = supabase.table("matches").select("status").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(match_result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match_rows[0]["status"] not in ("queued", "in_progress"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a queued or in-progress match can be cancelled",
        )
    supabase.table("matches").delete().eq("id", str(match_id)).execute()


@router.post("/matches/{match_id}/start", response_model=Match)
def start_match(match_id: UUID, supabase: SupabaseDep, admin: AdminDep) -> Match:
    """Manually promotes a queued match to in_progress — never automatic, so
    the admin decides exactly when the court is actually free (a queued
    match's players may still be finishing an earlier in_progress match)."""
    match_result = supabase.table("matches").select("*").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(match_result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    match_row = match_rows[0]
    if match_row["status"] != "queued":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only a queued match can be started"
        )

    session_id = UUID(match_row["session_id"])
    player_ids = {UUID(pid) for pid in (*match_row["team1_player_ids"], *match_row["team2_player_ids"])}
    still_playing = player_ids & queue_service.players_in_progress(supabase, session_id)
    if still_playing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ผู้เล่นบางคนยังแข่งอยู่ รอให้จบก่อนค่อยเริ่มคู่นี้",
        )

    updated = (
        supabase.table("matches")
        .update({"status": "in_progress", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(match_id))
        .execute()
    )
    return Match.model_validate(rows(updated)[0])


def _player_stats(supabase: Client, player_ids: list[UUID]) -> dict[UUID, elo_service.PlayerStatRow]:
    result = (
        supabase.table("players")
        .select("id, elo_score, games, wins, draws, losses")
        .in_("id", [str(pid) for pid in player_ids])
        .execute()
    )
    return {
        UUID(row["id"]): {
            "elo_score": row["elo_score"],
            "games": row["games"],
            "wins": row["wins"],
            "draws": row["draws"],
            "losses": row["losses"],
        }
        for row in rows(result)
    }


def _write_player_stats(supabase: Client, stats: dict[UUID, elo_service.PlayerStatRow]) -> None:
    """One update per player, each to a different row — fully independent, so
    run them concurrently instead of paying for N sequential Supabase
    round-trips on every match result (up to 4 for a doubles match)."""
    if not stats:
        return

    def write(pid: UUID, row: elo_service.PlayerStatRow) -> None:
        supabase.table("players").update(
            {
                "elo_score": row["elo_score"],
                "elo_level": elo_service.get_tier(row["elo_score"]),
                "games": row["games"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
            }
        ).eq("id", str(pid)).execute()

    with ThreadPoolExecutor(max_workers=len(stats)) as pool:
        futures = [pool.submit(write, pid, row) for pid, row in stats.items()]
        for future in futures:
            future.result()


def _team_ids(match_row: dict[str, Any]) -> tuple[list[UUID], list[UUID]]:
    return (
        [UUID(pid) for pid in match_row["team1_player_ids"]],
        [UUID(pid) for pid in match_row["team2_player_ids"]],
    )


def _load_match(supabase: Client, match_id: UUID) -> dict[str, Any]:
    result = supabase.table("matches").select("*").eq("id", str(match_id)).limit(1).execute()
    match_rows = rows(result)
    if not match_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match_rows[0]


def _save_result(
    supabase: Client, match_id: UUID, winner: Winner, delta_team1: int, delta_team2: int
) -> Match:
    updated = (
        supabase.table("matches")
        .update(
            {
                "winner": winner,
                "status": "completed",
                "elo_delta_team1": delta_team1,
                "elo_delta_team2": delta_team2,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(match_id))
        .execute()
    )
    return Match.model_validate(rows(updated)[0])


def _store_deltas(supabase: Client, match_id: UUID, delta_team1: int, delta_team2: int) -> Match:
    updated = (
        supabase.table("matches")
        .update({"elo_delta_team1": delta_team1, "elo_delta_team2": delta_team2})
        .eq("id", str(match_id))
        .execute()
    )
    return Match.model_validate(rows(updated)[0])


@router.post("/matches/{match_id}/result", response_model=Match)
def submit_result(
    match_id: UUID, payload: MatchResultSubmit, supabase: SupabaseDep, admin: AdminDep
) -> Match:
    match_row = _load_match(supabase, match_id)
    # Recording a result applies ELO and bumps every player's games/wins, so
    # doing it twice moves the whole club's ratings by double. The record
    # screen is a plain URL with the match in its query string, so the
    # browser's own Back button lands right back on live buttons.
    # A match still queued can be recorded: it just means the admin opened
    # the result screen before pressing "เริ่มแข่ง". A result recorded for
    # the wrong team is corrected with PATCH below, never by sending this
    # a second time.
    if match_row["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="แมตช์นี้บันทึกผลไปแล้ว",
        )

    # Claim the match before touching anybody's record, and let the database
    # decide who claimed it: the update only matches a row that is not
    # completed yet, so of two requests exactly one gets a row back.
    #
    # The order is the point. Writing the stats first and the status second
    # left a gap — a dropped connection between them, or a Supabase hiccup,
    # and the players kept the night's games while the match stayed
    # in_progress. The admin presses บันทึกผล again, the status guard above
    # sees a match that is not completed, and the same four players are
    # counted twice for one match. That is a profile reading ten games off
    # seven, with nothing in the match history to explain it.
    #
    # Claiming first cannot do that. If the stats write then fails, the
    # match is completed with nobody counted — an under-count, which the
    # stats audit lists and repairs, rather than an over-count that looks
    # like real play.
    claimed = (
        supabase.table("matches")
        .update(
            {
                "winner": payload.winner,
                "status": "completed",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(match_id))
        .neq("status", "completed")
        .execute()
    )
    if not rows(claimed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="แมตช์นี้บันทึกผลไปแล้ว",
        )
    record_service.invalidate()

    team1_ids, team2_ids = _team_ids(match_row)
    updated_stats, delta_team1, delta_team2 = elo_service.apply_match_result(
        _player_stats(supabase, team1_ids + team2_ids), team1_ids, team2_ids, payload.winner
    )
    _write_player_stats(supabase, updated_stats)
    # The deltas are what a correction later reverses by, so they are stored
    # once the move they describe has actually been made.
    return _store_deltas(supabase, match_id, delta_team1, delta_team2)


@router.patch("/matches/{match_id}/result", response_model=Match)
def edit_result(
    match_id: UUID, payload: MatchResultSubmit, supabase: SupabaseDep, admin: AdminDep
) -> Match:
    """Corrects a result recorded for the wrong team.

    The old outcome is reversed and the new one applied on top, so the
    players' ELO and win/loss counts land where they would have been had
    the right button been pressed in the first place. The new deltas are
    recomputed from the reversed ratings rather than mirrored, because a
    draw and a win are not the same size of move.

    A closed session's matches can be fixed too: a bill is the court fee
    plus the shuttlecock price times the games that player appeared in, so
    which side won changes nobody's total. The mistake is usually noticed
    after the night is packed up, which is exactly when the session is
    closed.

    Only a match whose deltas were stored (everything since 0023) —
    without them there is nothing to reverse by, and guessing would
    quietly skew the ladder.
    """
    match_row = _load_match(supabase, match_id)
    if match_row["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="แมตช์นี้ยังไม่ได้บันทึกผล",
        )
    if match_row["elo_delta_team1"] is None or match_row["elo_delta_team2"] is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="แมตช์นี้บันทึกไว้ก่อนระบบเก็บค่า ELO แก้ผลย้อนหลังไม่ได้",
        )
    if match_row["winner"] == payload.winner:
        return Match.model_validate(match_row)

    team1_ids, team2_ids = _team_ids(match_row)
    before: elo_service.CompletedMatchRow = {
        "team1_player_ids": match_row["team1_player_ids"],
        "team2_player_ids": match_row["team2_player_ids"],
        "winner": match_row["winner"],
        "elo_delta_team1": match_row["elo_delta_team1"],
        "elo_delta_team2": match_row["elo_delta_team2"],
    }
    reversed_stats = elo_service.reverse_match_results(
        [before], _player_stats(supabase, team1_ids + team2_ids)
    )
    updated_stats, delta_team1, delta_team2 = elo_service.apply_match_result(
        reversed_stats, team1_ids, team2_ids, payload.winner
    )
    _write_player_stats(supabase, updated_stats)
    saved = _save_result(supabase, match_id, payload.winner, delta_team1, delta_team2)
    record_service.invalidate()
    return saved
