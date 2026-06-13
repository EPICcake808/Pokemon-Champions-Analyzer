"""Usage from sampled tournament rosters, weighted by tournament prestige + deep runs.

Two views per Pokémon:

* **raw usage** — share of sampled teams running it (every team equal). Kept for
  transparency and for apples-to-apples reconciliation against Pikalytics.
* **weighted usage** — the headline ranking. Each team contributes
  ``tier_weight(tournament) × placement_weight(placing)``, so the biggest, most
  official events (Regionals, Internationals, Worlds) and the deepest top-cut runs
  drive the board. This is what the published meta list is sorted by.

Because the authoritative official source (limitlessvgc) reports base species only
(no held items, so no observable mega form), all tokens are collapsed to a base
species for counting — honest, and it prevents the same Pokémon from splitting across
``charizard`` (official) and ``charizard-mega-y`` (grassroots).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .sources.limitless import Roster, Tournament

# Official tiers dominate online events: even a 291-player Regional outweighs the
# 6,109-player Grand Champions Festival (online, capped below the smallest official).
TIER_WEIGHT = {
    "worlds": 10.0,
    "international": 7.0,
    "players_cup": 6.0,
    "regional": 5.0,
    "special_event": 5.0,
    "other_official": 4.0,
}
_ONLINE_FLOOR = 0.5
_ONLINE_SPAN = 2.5  # online weight ranges [0.5, 3.0]; 3.0 < smallest official (4.0)
_ONLINE_SIZE_REF = 1024
_OFFICIAL_SIZE_BONUS = 2.0
_OFFICIAL_SIZE_REF = 2000

_MEGA_SUFFIX = re.compile(r"-mega(?:-[xy])?$")
# Variant tokens that must collapse to a single canonical base across sources.
_BASE_ALIASES = {"floette-mega": "floette-eternal", "floette": "floette-eternal"}


def base_species_token(token: str) -> str:
    """Collapse mega/variant tokens to one canonical base species.

    ``charizard-mega-y`` → ``charizard``; ``floette-mega`` and ``floette`` →
    ``floette-eternal`` (the only M-A-legal Floette).
    """

    stripped = _MEGA_SUFFIX.sub("", token)
    return _BASE_ALIASES.get(token, _BASE_ALIASES.get(stripped, stripped))


def tier_weight(tournament: Tournament) -> float:
    """Prestige weight for a tournament: officials high and fixed, online size-scaled."""

    base = TIER_WEIGHT.get(tournament.tier)
    if base is not None:
        size_bonus = min(tournament.players, _OFFICIAL_SIZE_REF) / _OFFICIAL_SIZE_REF * _OFFICIAL_SIZE_BONUS
        return round(base + size_bonus, 3)
    # Online/grassroots: scale with size but cap below the smallest official tier.
    return round(_ONLINE_FLOOR + min(tournament.players, _ONLINE_SIZE_REF) / _ONLINE_SIZE_REF * _ONLINE_SPAN, 3)


def placement_weight(placing: int | None) -> float:
    """Deeper tournament runs (top cut) count for more."""

    if placing is None:
        return 1.0
    if placing <= 1:
        return 2.5
    if placing <= 2:
        return 2.1
    if placing <= 4:
        return 1.8
    if placing <= 8:
        return 1.5
    if placing <= 16:
        return 1.25
    if placing <= 32:
        return 1.1
    return 1.0


def team_weight(roster: Roster) -> float:
    return tier_weight(roster.tournament) * placement_weight(roster.placing)


@dataclass(frozen=True)
class UsageEntry:
    token: str  # canonical base species token
    team_count: int
    raw_usage_pct: float
    weighted_usage_pct: float


@dataclass(frozen=True)
class UsageReport:
    entries: list[UsageEntry]
    sample_size: int
    tournament_count: int
    official_count: int
    since_days: int
    tier_breakdown: dict[str, int] = field(default_factory=dict)

    def top(self, limit: int) -> list[UsageEntry]:
        return self.entries[:limit]

    def as_token_map(self) -> dict[str, float]:
        """Headline (weighted) usage by token."""

        return {entry.token: entry.weighted_usage_pct for entry in self.entries}

    def as_raw_token_map(self) -> dict[str, float]:
        return {entry.token: entry.raw_usage_pct for entry in self.entries}


def compute_usage(
    rosters: Iterable[Roster],
    *,
    tournament_count: int,
    since_days: int,
) -> UsageReport:
    rosters = list(rosters)
    total_teams = len(rosters)
    if total_teams == 0:
        return UsageReport(
            entries=[], sample_size=0, tournament_count=tournament_count,
            official_count=0, since_days=since_days, tier_breakdown={},
        )

    raw_counts: dict[str, int] = {}
    weighted_counts: dict[str, float] = {}
    total_weight = 0.0
    tier_breakdown: dict[str, int] = {}
    official_tournaments: set[str] = set()

    for roster in rosters:
        weight = team_weight(roster)
        total_weight += weight
        tier = roster.tournament.tier
        tier_breakdown[tier] = tier_breakdown.get(tier, 0) + 1
        if roster.tournament.source == "limitlessvgc":
            official_tournaments.add(roster.tournament.id)
        base_tokens = {base_species_token(token) for token in roster.species_tokens}
        for token in base_tokens:
            raw_counts[token] = raw_counts.get(token, 0) + 1
            weighted_counts[token] = weighted_counts.get(token, 0.0) + weight

    total_weight = total_weight or 1.0
    entries = [
        UsageEntry(
            token=token,
            team_count=count,
            raw_usage_pct=round(100.0 * count / total_teams, 1),
            weighted_usage_pct=round(100.0 * weighted_counts.get(token, 0.0) / total_weight, 1),
        )
        for token, count in raw_counts.items()
    ]
    # Headline ranking is by weighted usage; raw count breaks ties.
    entries.sort(key=lambda entry: (-entry.weighted_usage_pct, -entry.team_count, entry.token))

    return UsageReport(
        entries=entries,
        sample_size=total_teams,
        tournament_count=tournament_count,
        official_count=len(official_tournaments),
        since_days=since_days,
        tier_breakdown=tier_breakdown,
    )
