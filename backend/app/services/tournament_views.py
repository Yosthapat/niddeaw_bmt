"""What each side is shown of a tournament. The public pages and the other
team's player never see a real name or phone; the player sees their own;
the tournament's admins see everything."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from supabase import Client

from app.models.tournament import (
    AdminTeam,
    Coupons,
    GameDay,
    StandingRow,
    DrawLevel,
    DrawState,
    DrawTeam,
    Match,
    MatchSlot,
    PublicGroup,
    Entrant,
    Level,
    PublicLevel,
    PublicPlayer,
    PublicTeam,
    PublicTournament,
    SlipCheckInfo,
    Team,
    Tournament,
)
from app.services import slip_check
from app.services import tournament_draw as td
from app.services import tournament_play as tp
from app.services import tournament_service as ts

PRIVATE = ("first_name", "last_name", "phone")


@dataclass
class Snapshot:
    """One tournament's rows, read once for a page.

    Each read is its own round trip to Supabase (~0.1–0.3 s from the
    server), and a tournament page used to make seventeen of them one after
    another — the same teams six times over. Now the independent ones go out
    together and everything below works from this."""

    teams: list[dict[str, Any]]
    levels: list[dict[str, Any]]
    entrants: list[dict[str, Any]]
    matches: list[dict[str, Any]]
    players: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def by_team(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for e in self.entrants:
            out.setdefault(str(e["team_id"]), []).append(e)
        return out


def snapshot(
    supabase: Client, tournament_id: str, with_matches: bool = True, sweep: bool = True
) -> Snapshot:
    """Teams, levels, entrants and matches at once; then the players those
    entrants are. With `sweep`, runs out what has expired first (and reads
    again only if that changed anything)."""

    def read() -> Snapshot:
        with ThreadPoolExecutor(max_workers=4) as pool:
            teams_f = pool.submit(ts.teams, supabase, tournament_id)
            levels_f = pool.submit(ts.levels, supabase, tournament_id)
            ents_f = pool.submit(ts.entrants, supabase, tournament_id)
            matches_f = pool.submit(td.matches, supabase, tournament_id) if with_matches else None
            return Snapshot(
                teams=teams_f.result(),
                levels=levels_f.result(),
                entrants=ents_f.result(),
                matches=matches_f.result() if matches_f else [],
            )

    snap = read()
    if sweep and ts.sweep(supabase, tournament_id, snap.teams, snap.levels):
        snap = read()
    snap.players = ts.players_by_id(supabase, [str(e["player_id"]) for e in snap.entrants])
    return snap


def tournament_model(supabase: Client, row: dict[str, Any]) -> Tournament:
    return Tournament.model_validate(
        {
            **row,
            "levels": [Level.model_validate(lv) for lv in ts.levels(supabase, str(row["id"]))],
            "fees_locked": ts.fees_locked(supabase, str(row["id"])),
        }
    )


def _entrant(e: dict[str, Any], player: dict[str, Any] | None, private: bool) -> Entrant:
    data: dict[str, Any] = {
        **e,
        "nickname": (player or {}).get("nickname") or "?",
        "avatar_url": (player or {}).get("avatar_url"),
        "elo_level": (player or {}).get("elo_level"),
    }
    if not private:
        for key in PRIVATE:
            data[key] = None
    return Entrant.model_validate(data)


def team_model(
    team: dict[str, Any],
    ents: list[dict[str, Any]],
    players: dict[str, dict[str, Any]],
    level_names: dict[str, str],
    show_private_of: set[str] | None = None,
    everything: bool = False,
) -> Team:
    """`show_private_of`: player ids whose own details are shown (a player
    looking at their own team sees theirs, not their partner's)."""
    mine = show_private_of or set()
    return Team.model_validate(
        {
            **team,
            "level_name": level_names.get(str(team["level_id"]), "?"),
            "by_admin": team.get("created_by_admin") is not None,
            "entrants": [
                _entrant(
                    e, players.get(str(e["player_id"])), everything or str(e["player_id"]) in mine
                )
                for e in sorted(ents, key=lambda e: 0 if e["role"] == "captain" else 1)
            ],
        }
    )


def _public_team(
    t: dict[str, Any], ents: list[dict[str, Any]], players: dict[str, dict[str, Any]]
) -> PublicTeam:
    """A team as anyone may see it: its name, nicknames and avatars."""

    def player(e: dict[str, Any]) -> PublicPlayer:
        p = players.get(str(e["player_id"])) or {}
        return PublicPlayer(
            nickname=p.get("nickname") or "?",
            avatar_url=p.get("avatar_url"),
            elo_level=p.get("elo_level"),
        )

    return PublicTeam(
        id=t["id"],
        name=t["name"],
        players=[player(e) for e in sorted(ents, key=lambda e: e["role"])],
    )


def match_models(supabase: Client, tournament_id: str, snap: Snapshot | None = None) -> list[Match]:
    snap = snap or snapshot(supabase, tournament_id, sweep=False)
    found = snap.matches
    teams = {str(t["id"]): t for t in snap.teams}
    levels = {str(lv["id"]): str(lv["name"]) for lv in snap.levels}
    players = snap.players
    by_team = snap.by_team

    def side(slot: str, team: Any) -> MatchSlot:
        tid = str(team) if team else None
        if tid is None or tid not in teams:
            return MatchSlot(slot=slot)
        shown = _public_team(teams[tid], by_team.get(tid, []), players)
        return MatchSlot(slot=slot, team_id=UUID(tid), team_name=shown.name, players=shown.players)

    return [
        Match(
            id=m["id"],
            match_no=int(m["match_no"]),
            level_id=m["level_id"],
            level_name=levels.get(str(m["level_id"]), "?"),
            stage=m["stage"],
            bracket=m.get("bracket"),
            round=int(m["round"]),
            group_label=m.get("group_label"),
            a=side(m["slot_a"], m.get("team_a")),
            b=side(m["slot_b"], m.get("team_b")),
            est_start=m.get("est_start"),
            status=m.get("status") or "scheduled",
            court=m.get("court"),
            call_count=int(m.get("call_count") or 0),
            called_at=m.get("called_at"),
            finished_at=m.get("finished_at"),
            sets=m.get("sets"),
            winner=m.get("winner"),
            walkover=bool(m.get("walkover")),
            shuttles=m.get("shuttles"),
        )
        for m in found
    ]


def _groups(
    teams: list[dict[str, Any]],
    by_team: dict[str, list[dict[str, Any]]],
    players: dict[str, dict[str, Any]],
    level_matches: list[dict[str, Any]] | None = None,
) -> list[PublicGroup]:
    tables = tp.level_tables(level_matches or [], teams)
    placed = sorted(
        (t for t in teams if t.get("group_label") and t["status"] not in ts.ENDED),
        key=lambda t: (str(t["group_label"]), int(t.get("group_pos") or 0)),
    )
    return [
        PublicGroup(
            label=label,
            teams=[
                _public_team(t, by_team.get(str(t["id"]), []), players)
                for t in placed
                if t["group_label"] == label
            ],
            standings=[
                StandingRow(
                    team_id=UUID(r.team_id),
                    rank=r.rank,
                    played=r.played,
                    won=r.won,
                    drawn=r.drawn,
                    lost=r.lost,
                    points=r.points,
                    scored=r.scored,
                    conceded=r.conceded,
                    diff=r.diff,
                )
                for r in tables.get(label, [])
                if any(x.played for x in tables.get(label, []))
            ],
        )
        for label in sorted({str(t["group_label"]) for t in placed})
    ]


def public_tournament(
    supabase: Client, row: dict[str, Any], snap: Snapshot | None = None
) -> PublicTournament:
    """The groups and the match list go out only once published; until then
    the pages say "coming soon"."""
    tid = str(row["id"])
    published = bool(row.get("schedule_published_at"))
    snap = snap or snapshot(supabase, tid, with_matches=published, sweep=False)
    all_teams = snap.teams
    all_matches = snap.matches if published else []
    players = snap.players
    by_team = snap.by_team
    out_levels: list[PublicLevel] = []
    for lv in snap.levels:
        lid = str(lv["id"])
        mine = [t for t in all_teams if str(t["level_id"]) == lid]
        seated = sorted(
            (t for t in mine if t["status"] in ts.SEATED),
            key=lambda t: str(t.get("seat_held_at") or ""),
        )
        out_levels.append(
            PublicLevel.model_validate(
                {
                    **lv,
                    "seats_taken": len(seated),
                    "waitlist": sum(1 for t in mine if t["status"] == "waitlist"),
                    "teams": [
                        _public_team(t, by_team.get(str(t["id"]), []), players) for t in seated
                    ],
                    "groups": _groups(
                        mine,
                        by_team,
                        players,
                        [m for m in all_matches if str(m["level_id"]) == lid],
                    )
                    if published
                    else [],
                }
            )
        )
    return PublicTournament.model_validate(
        {
            **row,
            "taking_entries": ts.taking_entries(row),
            "levels": out_levels,
            "schedule_published": published,
            "matches": match_models(supabase, tid, snap) if published else [],
        }
    )


def draw_state(supabase: Client, tournament_id: str, sweep: bool = False) -> DrawState:
    """The admin's view of the draw: each level's confirmed teams and where
    they sit, and the match list if there is one."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        row_f = pool.submit(ts.tournament, supabase, tournament_id)
        snap = snapshot(supabase, tournament_id, sweep=sweep)
        row = row_f.result()
    all_teams = snap.teams
    players = snap.players
    by_team = snap.by_team
    out: list[DrawLevel] = []
    for lv in snap.levels:
        lid = str(lv["id"])
        mine = [t for t in all_teams if str(t["level_id"]) == lid]
        ready = sorted(
            (t for t in mine if t["status"] == "confirmed"),
            key=lambda t: (
                str(t.get("group_label") or "Z"),
                int(t.get("group_pos") or 9),
                str(t["name"]),
            ),
        )
        out.append(
            DrawLevel(
                level=Level.model_validate(lv),
                confirmed=len(ready),
                not_ready=sum(
                    1
                    for t in mine
                    if t["status"] in {"awaiting_payment", "slip_review", "waitlist"}
                ),
                groups=sorted({str(t["group_label"]) for t in ready if t.get("group_label")}),
                teams=[
                    DrawTeam(
                        id=t["id"],
                        name=t["name"],
                        status=t["status"],
                        group_label=t.get("group_label"),
                        group_pos=t.get("group_pos"),
                        players=_public_team(t, by_team.get(str(t["id"]), []), players).players,
                    )
                    for t in ready
                ],
            )
        )
    found = match_models(supabase, tournament_id, snap)
    est_end = None
    timed = [m for m in found if m.est_start]
    if timed:
        last = max(timed, key=lambda m: m.est_start or datetime.min)
        minutes = (
            int(row.get("group_minutes") or 20)
            if last.stage == "group"
            else int(row.get("ko_minutes") or 30)
        )
        est_end = max(m.est_start for m in timed if m.est_start) + timedelta(minutes=minutes)
    return DrawState(
        tournament_id=row["id"],
        levels=out,
        matches=found,
        est_end=est_end,
        published_at=row.get("schedule_published_at"),
    )


def admin_teams(supabase: Client, tournament_id: str) -> list[AdminTeam]:
    all_teams = ts.teams(supabase, tournament_id)
    ents = ts.entrants(supabase, tournament_id)
    players = ts.players_by_id(supabase, [str(e["player_id"]) for e in ents])
    level_names = {str(lv["id"]): str(lv["name"]) for lv in ts.levels(supabase, tournament_id)}
    by_team: dict[str, list[dict[str, Any]]] = {}
    for e in ents:
        by_team.setdefault(str(e["team_id"]), []).append(e)
    with_slip = [str(e["id"]) for e in ents if e.get("slip_url")]
    checks = {c["target_id"]: c for c in slip_check.checks(supabase, "tournament", with_slip)}
    out: list[AdminTeam] = []
    for t in sorted(all_teams, key=lambda t: str(t.get("created_at") or "")):
        mine = by_team.get(str(t["id"]), [])
        base = team_model(t, mine, players, level_names, everything=True)
        found: list[SlipCheckInfo] = []
        for e in mine:
            c = checks.get(str(e["id"]))
            if c:
                before = c.get("used_before") or {}
                found.append(
                    SlipCheckInfo(
                        target_id=str(e["id"]),
                        status=c["status"],
                        used_before_who=before.get("who"),
                        used_before_kind=before.get("kind"),
                        used_before_amount=before.get("amount"),
                    )
                )
        out.append(
            AdminTeam.model_validate(
                {
                    **base.model_dump(),
                    "slip_checks": found,
                    "refund_owed": sum(ts.refund_owed(t, e) for e in mine),
                }
            )
        )
    return out


def game_day(supabase: Client, tournament_id: str) -> GameDay:
    """Polled every few seconds on the day, so read once: the tournament and
    its money alongside the snapshot, and everything worked out from those."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        row_f = pool.submit(ts.tournament, supabase, tournament_id)
        money_f = pool.submit(tp.money_rows, supabase, tournament_id)
        snap = snapshot(supabase, tournament_id, sweep=False)
        row = row_f.result()
        money = money_f.result()
    found = match_models(supabase, tournament_id, snap)
    teams = {str(t["id"]): t for t in snap.teams}
    names = {str(lv["id"]): str(lv["name"]) for lv in snap.levels}
    players = snap.players
    by_team = snap.by_team
    upcoming: dict[str, int] = {}
    for m in found:
        if m.status == "scheduled":
            for side in (m.a, m.b):
                if side.team_id and str(side.team_id) not in upcoming:
                    upcoming[str(side.team_id)] = m.match_no
    held = tp.coupons(supabase, row, snap.teams, snap.matches, money)
    return GameDay(
        tournament_id=row["id"],
        courts=int(row.get("courts") or 0),
        published=bool(row.get("schedule_published_at")),
        matches=found,
        ready=[m["id"] for m in tp.ready(supabase, tournament_id, row, snap.matches)],
        coupons=sorted(
            (
                Coupons(
                    team_id=UUID(tid),
                    team_name=str(teams[tid]["name"]),
                    level_name=names.get(str(teams[tid]["level_id"]), "?"),
                    players=_public_team(teams[tid], by_team.get(tid, []), players).players,
                    next_match_no=upcoming.get(tid),
                    **c,
                )
                for tid, c in held.items()
                if tid in teams and teams[tid]["status"] not in ts.ENDED
            ),
            key=lambda c: (c.left, c.team_name),
        ),
        extra_set_price=int(row.get("extra_set_price") or 0),
        coupon_refund_price=int(row.get("coupon_refund_price") or 0),
        coupons_per_set=int(row.get("coupons_per_set") or 6),
    )
