"""What each side is shown of a tournament. The public pages and the other
team's player never see a real name or phone; the player sees their own;
the tournament's admins see everything."""

from typing import Any

from supabase import Client

from app.models.tournament import (
    AdminTeam,
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
from app.services import tournament_service as ts

PRIVATE = ("first_name", "last_name", "phone")


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


def public_tournament(supabase: Client, row: dict[str, Any]) -> PublicTournament:
    tid = str(row["id"])
    all_teams = ts.teams(supabase, tid)
    ents = ts.entrants(supabase, tid)
    players = ts.players_by_id(supabase, [str(e["player_id"]) for e in ents])
    by_team: dict[str, list[dict[str, Any]]] = {}
    for e in ents:
        by_team.setdefault(str(e["team_id"]), []).append(e)
    out_levels: list[PublicLevel] = []
    for lv in ts.levels(supabase, tid):
        lid = str(lv["id"])
        seated = sorted(
            (t for t in all_teams if str(t["level_id"]) == lid and t["status"] in ts.SEATED),
            key=lambda t: str(t.get("seat_held_at") or ""),
        )
        out_levels.append(
            PublicLevel.model_validate(
                {
                    **lv,
                    "seats_taken": len(seated),
                    "waitlist": sum(
                        1
                        for t in all_teams
                        if str(t["level_id"]) == lid and t["status"] == "waitlist"
                    ),
                    "teams": [
                        PublicTeam(
                            name=t["name"],
                            players=[
                                PublicPlayer(
                                    nickname=(players.get(str(e["player_id"])) or {}).get(
                                        "nickname"
                                    )
                                    or "?",
                                    avatar_url=(players.get(str(e["player_id"])) or {}).get(
                                        "avatar_url"
                                    ),
                                    elo_level=(players.get(str(e["player_id"])) or {}).get(
                                        "elo_level"
                                    ),
                                )
                                for e in sorted(
                                    by_team.get(str(t["id"]), []), key=lambda e: e["role"]
                                )
                            ],
                        )
                        for t in seated
                    ],
                }
            )
        )
    return PublicTournament.model_validate(
        {**row, "taking_entries": ts.taking_entries(row), "levels": out_levels}
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
