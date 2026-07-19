"""Aggregates completed matches into per-player Game/Win/Draw/Loss/Pts stats.

Points convention (BMBAD-style member list): win = 2 pts, draw = 1 pt, loss = 0 pts.
Avg = points / games. Sc(%) = win rate = wins / games * 100.
"""

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

WIN_POINTS = 2
DRAW_POINTS = 1
LOSS_POINTS = 0


class CompletedMatchRow(TypedDict):
    team1_player_ids: list[str]
    team2_player_ids: list[str]
    winner: str


@dataclass
class PlayerRecord:
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

    @property
    def points(self) -> int:
        return self.wins * WIN_POINTS + self.draws * DRAW_POINTS + self.losses * LOSS_POINTS

    @property
    def avg_points(self) -> float:
        return self.points / self.games if self.games else 0.0

    @property
    def score_percent(self) -> float:
        return (self.wins / self.games * 100) if self.games else 0.0


def build_player_records(
    matches: list[CompletedMatchRow],
) -> dict[UUID, PlayerRecord]:
    """matches: rows with team1_player_ids, team2_player_ids, winner (completed only)."""
    records: dict[UUID, PlayerRecord] = {}

    for match in matches:
        team1_ids = [UUID(pid) for pid in match["team1_player_ids"]]
        team2_ids = [UUID(pid) for pid in match["team2_player_ids"]]
        winner = match["winner"]

        for pid in team1_ids + team2_ids:
            records.setdefault(pid, PlayerRecord())

        for pid in team1_ids:
            records[pid].games += 1
            if winner == "team1":
                records[pid].wins += 1
            elif winner == "team2":
                records[pid].losses += 1
            else:
                records[pid].draws += 1

        for pid in team2_ids:
            records[pid].games += 1
            if winner == "team2":
                records[pid].wins += 1
            elif winner == "team1":
                records[pid].losses += 1
            else:
                records[pid].draws += 1

    return records
