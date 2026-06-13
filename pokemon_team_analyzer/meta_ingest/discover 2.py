"""Automatic team/shell discovery from real tournament rosters.

Modes and archetypes are inferred directly from each team's *structured* decklist
(weather-setting abilities, speed-control / Trick Room moves, the offensive/support
move mix) and related teams are clustered into representative
``tournamentTeamSnapshots``. This ports the mode/archetype inference and
grouping/weighting from the TypeScript ``live-meta-ingestion`` deep-discovery path
(``inferModesFromText`` / ``inferBroadMixFromModes`` / ``looksLikeTrackedSnapshot``).

Why not reuse the analyzer here? The analyzer's bundled species data and legality
gate are scoped to the *curated* eligible-species list, which real tournament data
shows is stale (e.g. Basculegion — the format's most-used Pokémon — is treated as
ineligible and cannot even be resolved). Driving discovery off structured decklist
signals keeps it reality-complete and independent of that curated data, and is far
faster (no per-team PokeAPI resolution).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from ..analyzer import _render_mode_label, _render_species_token
from . import DEFAULT_REGULATION_ID
from .sources.limitless import Roster

# Mirrors BROAD_MIX_KEYS in web/src/lib/live-meta-ingestion.ts.
BROAD_MIX_KEYS = ("hyper_offense", "bulky_offense", "balance", "semi_stall", "stall", "trick_room")

_WEATHER_ABILITIES = {
    "drizzle": "rain",
    "primordial sea": "rain",
    "drought": "sun",
    "orichalcum pulse": "sun",
    "desolate land": "sun",
    "sand stream": "sand",
    "snow warning": "snow",
}
_SUPPORT_MOVE_HINTS = {
    "fake out", "follow me", "rage powder", "helping hand", "protect", "wide guard",
    "ally switch", "light screen", "reflect", "aurora veil", "tailwind", "trick room",
    "icy wind", "electroweb", "thunder wave", "will-o-wisp", "spore", "sleep powder",
    "taunt", "encore", "moonblast",
}

_SPECIES_OVERLAP_FOR_CLUSTER = 4
_MAX_SNAPSHOTS = 24
_MAX_TEAMS = 400


@dataclass
class _Candidate:
    species_tokens: tuple[str, ...]
    mode_scores: dict[str, float]
    mode_labels: list[str]
    broad_mix: dict[str, float]
    team_count: int
    best_placing: int | None
    tournaments: list[str]
    tournament_urls: list[str]


@dataclass
class _UniqueTeam:
    species_tokens: tuple[str, ...]
    decklist: list[dict]
    count: int = 0
    best_placing: int | None = None
    tournaments: list[str] = field(default_factory=list)
    tournament_urls: list[str] = field(default_factory=list)


@dataclass
class DiscoveryResult:
    snapshots: list[dict[str, object]]
    teams_analyzed: int
    clusters_formed: int
    warnings: list[str]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", slug).strip("-")


def _team_signals(decklist: list[dict]) -> tuple[list[str], list[str]]:
    """Return (lowercased abilities, lowercased moves) for a team."""

    abilities = [str(m.get("ability") or "").strip().lower() for m in decklist]
    moves = [str(move).strip().lower() for m in decklist for move in (m.get("attacks") or [])]
    return [a for a in abilities if a], [mv for mv in moves if mv]


def infer_modes(decklist: list[dict]) -> tuple[list[str], dict[str, float]]:
    """Infer team modes from structured decklist signals.

    Produces catalog-aligned mode tokens (``rain_tailwind``, ``trick_room``,
    ``sun_room``, ``tailwind`` …) plus per-mode scores used when aggregating a
    cluster. Always returns at least one mode.
    """

    abilities, moves = _team_signals(decklist)
    move_set = set(moves)

    weather = None
    for ability in abilities:
        if ability in _WEATHER_ABILITIES:
            weather = _WEATHER_ABILITIES[ability]
            break

    has_trick_room = "trick room" in move_set
    has_tailwind = "tailwind" in move_set

    scores: dict[str, float] = defaultdict(float)
    if weather:
        scores[weather] += 0.6
    if has_tailwind:
        scores["tailwind"] += 0.6
    if has_trick_room:
        scores["trick_room"] += 0.6

    # Compose a primary label from the dominant signals.
    if has_trick_room and has_tailwind:
        primary = "tailroom"
    elif weather and has_tailwind:
        primary = f"{weather}_tailwind"
    elif weather and has_trick_room:
        primary = f"{weather}_room"
    elif weather:
        primary = weather
    elif has_tailwind:
        primary = "tailwind"
    elif has_trick_room:
        primary = "trick_room"
    else:
        primary = "dual_mode"

    scores[primary] += 1.0
    labels = [primary] + [mode for mode in scores if mode != primary]
    return labels, dict(scores)


def infer_broad_mix(decklist: list[dict], modes: list[str]) -> dict[str, float]:
    """Lightweight archetype mix from modes + offensive/support move balance.

    Ports ``inferBroadMixFromModes`` and nudges it by how attack-dense the team is.
    """

    _, moves = _team_signals(decklist)
    if not moves:
        return {"balance": 1.0}
    support = sum(1 for move in moves if move in _SUPPORT_MOVE_HINTS)
    support_ratio = support / len(moves)

    primary = modes[0] if modes else "dual_mode"
    if "trick_room" in primary or primary == "tailroom":
        return {"trick_room": 0.6, "bulky_offense": 0.25, "balance": 0.15}
    if "tailwind" in primary:
        base = {"hyper_offense": 0.55, "bulky_offense": 0.3, "balance": 0.15}
    elif any(weather in primary for weather in ("rain", "sun", "sand", "snow")):
        base = {"bulky_offense": 0.45, "balance": 0.35, "hyper_offense": 0.2}
    else:
        base = {"balance": 0.5, "bulky_offense": 0.3, "hyper_offense": 0.2}

    # Support-heavy teams lean bulkier; attack-heavy teams lean faster.
    if support_ratio > 0.4:
        base = {"bulky_offense": 0.45, "balance": 0.4, "hyper_offense": 0.15}
    elif support_ratio < 0.2:
        base = {"hyper_offense": 0.55, "bulky_offense": 0.3, "balance": 0.15}
    return base


def _dedupe_teams(rosters: list[Roster]) -> list[_UniqueTeam]:
    teams: dict[str, _UniqueTeam] = {}
    for roster in rosters:
        key = roster.species_key
        team = teams.get(key)
        if team is None:
            team = _UniqueTeam(species_tokens=roster.species_tokens, decklist=roster.decklist)
            teams[key] = team
        team.count += 1
        if roster.placing is not None and (team.best_placing is None or roster.placing < team.best_placing):
            team.best_placing = roster.placing
        if roster.tournament.name not in team.tournaments:
            team.tournaments.append(roster.tournament.name)
            team.tournament_urls.append(roster.tournament.url)
    return sorted(
        teams.values(),
        key=lambda team: (-team.count, team.best_placing if team.best_placing is not None else 9_999),
    )


def _build_candidate(unique_team: _UniqueTeam) -> _Candidate:
    mode_labels, mode_scores = infer_modes(unique_team.decklist)
    broad_mix = infer_broad_mix(unique_team.decklist, mode_labels)
    return _Candidate(
        species_tokens=unique_team.species_tokens,
        mode_scores=mode_scores,
        mode_labels=mode_labels,
        broad_mix=broad_mix,
        team_count=unique_team.count,
        best_placing=unique_team.best_placing,
        tournaments=unique_team.tournaments,
        tournament_urls=unique_team.tournament_urls,
    )


def _candidates_related(left: _Candidate, right: _Candidate) -> bool:
    overlap = len(set(left.species_tokens) & set(right.species_tokens))
    shared_mode = bool(set(left.mode_labels) & set(right.mode_labels))
    return overlap >= _SPECIES_OVERLAP_FOR_CLUSTER and shared_mode


def _cluster(candidates: list[_Candidate]) -> list[list[_Candidate]]:
    ordered = sorted(candidates, key=lambda c: (-c.team_count, c.best_placing or 9_999))
    clusters: list[list[_Candidate]] = []
    for candidate in ordered:
        target = next(
            (cluster for cluster in clusters if any(_candidates_related(member, candidate) for member in cluster)),
            None,
        )
        if target is None:
            clusters.append([candidate])
        else:
            target.append(candidate)
    return clusters


def _normalize_top(scores: dict[str, float], *, limit: int) -> dict[str, float]:
    positive = {key: value for key, value in scores.items() if value > 0}
    ranked = sorted(positive.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    total = sum(value for _, value in ranked) or 1.0
    return {key: round(value / total, 2) for key, value in ranked}


def _result_signal(best_placing: int | None) -> tuple[str, float]:
    if best_placing is None:
        return "tournament-tracked finish", 0.4
    if best_placing <= 1:
        return "tournament winner", 1.0
    if best_placing <= 4:
        return "top-4 finish", 0.85
    if best_placing <= 8:
        return "top-8 finish", 0.7
    if best_placing <= 16:
        return "top-16 finish", 0.55
    return "tournament-tracked finish", 0.4


def _clamp(value: float, low: float = 0.0, high: float = 2.0) -> float:
    return round(min(high, max(low, value)), 2)


def cluster_urls(cluster: list[_Candidate]) -> list[str]:
    urls: list[str] = []
    for candidate in cluster:
        for url in candidate.tournament_urls:
            if url not in urls:
                urls.append(url)
    return urls


def _build_snapshot(cluster: list[_Candidate], max_team_count: int) -> dict[str, object]:
    team_count = sum(candidate.team_count for candidate in cluster)
    best_placing = min((c.best_placing for c in cluster if c.best_placing is not None), default=None)

    species_score: dict[str, float] = defaultdict(float)
    mode_score: dict[str, float] = defaultdict(float)
    broad_mix_score: dict[str, float] = defaultdict(float)
    for candidate in cluster:
        weight = float(candidate.team_count)
        for token in candidate.species_tokens:
            species_score[token] += weight
        for mode, score in candidate.mode_scores.items():
            mode_score[mode] += score * weight
        for key, value in candidate.broad_mix.items():
            broad_mix_score[key] += value * weight

    key_pokemon = [token for token, _ in sorted(species_score.items(), key=lambda kv: (-kv[1], kv[0]))[:6]]
    mode_weights = _normalize_top(mode_score, limit=4) or {"dual_mode": 1.0}
    modes = list(mode_weights.keys())
    broad_mix = _normalize_top(broad_mix_score, limit=3) or {"balance": 1.0}

    primary_mode = modes[0]
    label_species = " ".join(_render_species_token(token) for token in key_pokemon[:2])
    label = f"{label_species} {_render_mode_label(primary_mode)}".strip()

    result_label, result_signal = _result_signal(best_placing)
    popularity_share = team_count / max_team_count if max_team_count else 0.0

    key_cores = []
    if len(key_pokemon) >= 2:
        key_cores.append(" + ".join(_render_species_token(token) for token in key_pokemon[:2]))
    if len(key_pokemon) >= 4:
        key_cores.append(" + ".join(_render_species_token(token) for token in key_pokemon[2:4]))
    if not key_cores:
        key_cores.append(_render_species_token(key_pokemon[0]))

    tournaments: list[str] = []
    for candidate in cluster:
        for name in candidate.tournaments:
            if name not in tournaments:
                tournaments.append(name)
    source = f"Limitless tournament results ({team_count} teams): {', '.join(tournaments[:2])}".strip()

    return {
        "slug": f"live-{_slugify(label) or 'shell'}",
        "label": label or "Unnamed shell",
        "source": source[:240],
        "result_label": result_label,
        "field_relevance": _clamp(0.45 + 0.5 * popularity_share + 0.15 * result_signal),
        "popularity_weight": _clamp(0.3 + 0.7 * popularity_share),
        "result_weight": _clamp(0.4 + 0.6 * result_signal),
        "modes": modes,
        "mode_weights": mode_weights,
        "broad_mix": broad_mix,
        "key_pokemon": key_pokemon,
        "key_cores": key_cores[:3],
        # Extra provenance (tolerated by the web schema; surfaced in a later pass).
        "provenance_urls": cluster_urls(cluster)[:3],
        "team_count": team_count,
    }


def _snapshot_rank(snapshot: dict[str, object]) -> float:
    return (
        0.68 * float(snapshot["popularity_weight"]) + 0.32 * float(snapshot["result_weight"])
    ) * float(snapshot["field_relevance"])


def discover_shells(
    rosters: list[Roster],
    *,
    regulation_id: str = DEFAULT_REGULATION_ID,
    max_teams_analyzed: int = _MAX_TEAMS,
    max_snapshots: int = _MAX_SNAPSHOTS,
) -> DiscoveryResult:
    unique_teams = _dedupe_teams(rosters)
    candidates = [_build_candidate(team) for team in unique_teams[:max_teams_analyzed]]
    clusters = _cluster(candidates)
    max_team_count = max((sum(c.team_count for c in cluster) for cluster in clusters), default=0)
    snapshots = [_build_snapshot(cluster, max_team_count) for cluster in clusters]
    snapshots.sort(key=lambda snapshot: (-_snapshot_rank(snapshot), str(snapshot["label"])))

    return DiscoveryResult(
        snapshots=snapshots[:max_snapshots],
        teams_analyzed=len(candidates),
        clusters_formed=len(clusters),
        warnings=[],
    )
