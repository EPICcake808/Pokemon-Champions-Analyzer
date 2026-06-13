"""Real overall usage from sampled tournament rosters.

This is the metric the curated board never had: a species' usage is the share of
*real teams* that ran it (``teams_containing_species / total_teams``), not its
membership across a hand-authored shell list. A placement-weighted variant gives
top-cut teams more influence without hiding raw usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .sources.limitless import Roster


@dataclass(frozen=True)
class UsageEntry:
    token: str
    team_count: int
    usage_pct: float
    weighted_usage_pct: float


@dataclass(frozen=True)
class UsageReport:
    entries: list[UsageEntry]
    sample_size: int
    tournament_count: int
    since_days: int

    def top(self, limit: int) -> list[UsageEntry]:
        return self.entries[:limit]

    def as_token_map(self) -> dict[str, float]:
        return {entry.token: entry.usage_pct for entry in self.entries}


def placement_weight(placing: int | None) -> float:
    """Top-cut teams count for more in the weighted usage view."""

    if placing is None:
        return 1.0
    if placing <= 1:
        return 2.0
    if placing <= 2:
        return 1.8
    if placing <= 4:
        return 1.6
    if placing <= 8:
        return 1.4
    if placing <= 16:
        return 1.2
    return 1.0


def compute_usage(
    rosters: Iterable[Roster],
    *,
    tournament_count: int,
    since_days: int,
) -> UsageReport:
    rosters = list(rosters)
    total_teams = len(rosters)
    if total_teams == 0:
        return UsageReport(entries=[], sample_size=0, tournament_count=tournament_count, since_days=since_days)

    raw_counts: dict[str, int] = {}
    weighted_counts: dict[str, float] = {}
    total_weight = 0.0

    for roster in rosters:
        weight = placement_weight(roster.placing)
        total_weight += weight
        for token in set(roster.species_tokens):  # set: presence, not duplicate slots
            raw_counts[token] = raw_counts.get(token, 0) + 1
            weighted_counts[token] = weighted_counts.get(token, 0.0) + weight

    total_weight = total_weight or 1.0
    entries = [
        UsageEntry(
            token=token,
            team_count=count,
            usage_pct=round(100.0 * count / total_teams, 1),
            weighted_usage_pct=round(100.0 * weighted_counts.get(token, 0.0) / total_weight, 1),
        )
        for token, count in raw_counts.items()
    ]
    entries.sort(key=lambda entry: (-entry.usage_pct, -entry.team_count, entry.token))

    return UsageReport(
        entries=entries,
        sample_size=total_teams,
        tournament_count=tournament_count,
        since_days=since_days,
    )
