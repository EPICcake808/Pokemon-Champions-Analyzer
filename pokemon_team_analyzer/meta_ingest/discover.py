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
from .usage import team_weight

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

# Mega species arrive as catalog tokens like ``charizard-mega-y`` / ``garchomp-mega``
# / ``floette-mega`` (resolved from the held stone in ``sources/limitless.py``).
_MEGA_TOKEN_RE = re.compile(r"-mega(?:-[xy])?$")


def _is_mega_token(token: str) -> bool:
    return bool(_MEGA_TOKEN_RE.search(token))


@dataclass
class _Candidate:
    species_tokens: tuple[str, ...]
    mode_scores: dict[str, float]
    mode_labels: list[str]
    broad_mix: dict[str, float]
    team_count: int
    weight: float
    best_placing: int | None
    best_official_placing: int | None
    official_tier: str | None
    # (name, url, is_official) per distinct event this team appeared at.
    events: list[tuple[str, str, bool]]


@dataclass
class _UniqueTeam:
    species_tokens: tuple[str, ...]
    decklist: list[dict]
    count: int = 0
    weight: float = 0.0
    best_placing: int | None = None
    best_official_placing: int | None = None
    official_tier: str | None = None
    events: list[tuple[str, str, bool]] = field(default_factory=list)


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


def infer_modes(decklist: list[dict], *, mega_count: int = 0) -> tuple[list[str], dict[str, float]]:
    """Infer team modes from structured decklist signals.

    Produces catalog-aligned mode tokens (``rain_tailwind``, ``trick_room``,
    ``sun_room``, ``tailwind`` …) plus per-mode scores used when aggregating a
    cluster. Always returns at least one mode.

    ``mega_count`` is the number of mega species on the team. Because Reg M-A only
    allows one mega per battle, a team carrying two or more mega stones is
    functionally a *dual-mode* team (you choose which mega to bring per matchup), so
    ``dual_mode`` is added as a prominent secondary signal without displacing the
    team's real speed-control / weather primary.
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
    if mega_count >= 2:
        # Two+ mega stones = a functional dual-mode team (only one mega per battle),
        # so surface dual_mode prominently without displacing the speed-control primary.
        scores["dual_mode"] += 0.8
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
        team.weight += team_weight(roster)
        if roster.placing is not None and (team.best_placing is None or roster.placing < team.best_placing):
            team.best_placing = roster.placing
        if roster.tournament.source == "limitlessvgc":
            if roster.placing is not None and (
                team.best_official_placing is None or roster.placing < team.best_official_placing
            ):
                team.best_official_placing = roster.placing
                team.official_tier = roster.tournament.tier
        is_official = roster.tournament.source == "limitlessvgc"
        if roster.tournament.name not in {name for name, _, _ in team.events}:
            team.events.append((roster.tournament.name, roster.tournament.url, is_official))
    # Heaviest (official top-cut) teams first — those most worth analyzing.
    return sorted(teams.values(), key=lambda team: -team.weight)


def _build_candidate(unique_team: _UniqueTeam) -> _Candidate:
    mega_count = sum(1 for token in unique_team.species_tokens if _is_mega_token(token))
    mode_labels, mode_scores = infer_modes(unique_team.decklist, mega_count=mega_count)
    broad_mix = infer_broad_mix(unique_team.decklist, mode_labels)
    return _Candidate(
        species_tokens=unique_team.species_tokens,
        mode_scores=mode_scores,
        mode_labels=mode_labels,
        broad_mix=broad_mix,
        team_count=unique_team.count,
        weight=unique_team.weight,
        best_placing=unique_team.best_placing,
        best_official_placing=unique_team.best_official_placing,
        official_tier=unique_team.official_tier,
        events=unique_team.events,
    )


def _candidates_related(left: _Candidate, right: _Candidate) -> bool:
    overlap = len(set(left.species_tokens) & set(right.species_tokens))
    shared_mode = bool(set(left.mode_labels) & set(right.mode_labels))
    return overlap >= _SPECIES_OVERLAP_FOR_CLUSTER and shared_mode


def _cluster(candidates: list[_Candidate]) -> list[list[_Candidate]]:
    ordered = sorted(candidates, key=lambda c: -c.weight)
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


_TIER_LABELS = {
    "worlds": "Worlds",
    "international": "International",
    "players_cup": "Players Cup",
    "regional": "Regional",
    "special_event": "Special Event",
    "other_official": "official event",
}


def _placement_phrase(placing: int | None) -> tuple[str, float]:
    if placing is None:
        return "tournament-tracked finish", 0.4
    if placing <= 1:
        return "winner", 1.0
    if placing <= 4:
        return "top-4 finish", 0.85
    if placing <= 8:
        return "top-8 finish", 0.7
    if placing <= 16:
        return "top-16 finish", 0.55
    if placing <= 32:
        return "top-32 finish", 0.45
    return "tournament-tracked finish", 0.4


def _result_signal(
    best_placing: int | None, best_official_placing: int | None, official_tier: str | None
) -> tuple[str, float, bool]:
    """Return (result_label, signal, is_official). Official deep runs are highlighted."""

    if best_official_placing is not None and official_tier:
        phrase, signal = _placement_phrase(best_official_placing)
        tier_label = _TIER_LABELS.get(official_tier, "official event")
        # Official results carry more signal than grassroots ones.
        return f"{tier_label} {phrase}", min(1.0, signal + 0.1), True
    phrase, signal = _placement_phrase(best_placing)
    return phrase, signal, False


def _clamp(value: float, low: float = 0.0, high: float = 2.0) -> float:
    return round(min(high, max(low, value)), 2)


def _cluster_events(cluster: list[_Candidate]) -> list[tuple[str, str, bool]]:
    """Distinct (name, url, is_official) across the cluster, official events first."""

    seen: set[str] = set()
    official: list[tuple[str, str, bool]] = []
    grassroots: list[tuple[str, str, bool]] = []
    for candidate in cluster:
        for name, url, is_official in candidate.events:
            if name in seen:
                continue
            seen.add(name)
            (official if is_official else grassroots).append((name, url, is_official))
    return official + grassroots


def cluster_urls(cluster: list[_Candidate]) -> list[str]:
    return [url for _, url, _ in _cluster_events(cluster)]


def _build_snapshot(cluster: list[_Candidate], max_weight: float) -> dict[str, object]:
    team_count = sum(candidate.team_count for candidate in cluster)
    cluster_weight = sum(candidate.weight for candidate in cluster)
    best_placing = min((c.best_placing for c in cluster if c.best_placing is not None), default=None)
    best_official_placing = min(
        (c.best_official_placing for c in cluster if c.best_official_placing is not None), default=None
    )
    official_tier = next((c.official_tier for c in cluster if c.official_tier), None)

    species_score: dict[str, float] = defaultdict(float)
    mode_score: dict[str, float] = defaultdict(float)
    broad_mix_score: dict[str, float] = defaultdict(float)
    for candidate in cluster:
        # Weight species/mode/archetype aggregation by tournament prestige + placement,
        # so official top-cut teams shape the representative shell.
        weight = max(candidate.weight, 0.01)
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

    result_label, result_signal, is_official = _result_signal(best_placing, best_official_placing, official_tier)
    popularity_share = cluster_weight / max_weight if max_weight else 0.0
    # Shells anchored by a deep official run are board-defining; lift their relevance.
    official_bonus = 0.25 if (is_official and (best_official_placing or 99) <= 16) else 0.0

    def _join_core(tokens: list[str]) -> str:
        return " + ".join(_render_species_token(token) for token in tokens)

    megas = [token for token in key_pokemon if _is_mega_token(token)]
    key_cores: list[str] = []
    if len(megas) >= 2:
        # Dual-mega teams pick one mega per battle, so players read them as each mega
        # anchoring its own core with its best support — not one mega plus filler.
        used: set[str] = set()
        non_mega = [token for token in key_pokemon if not _is_mega_token(token)]
        for mega in megas[:2]:
            used.add(mega)
            partner = next((token for token in non_mega if token not in used), None)
            if partner is not None:
                used.add(partner)
            key_cores.append(_join_core([mega, partner] if partner is not None else [mega]))
        rest = [token for token in key_pokemon if token not in used]
        if len(rest) >= 2:
            key_cores.append(_join_core(rest[:2]))
    else:
        if len(key_pokemon) >= 2:
            key_cores.append(_join_core(key_pokemon[:2]))
        if len(key_pokemon) >= 4:
            key_cores.append(_join_core(key_pokemon[2:4]))
    if not key_cores:
        key_cores.append(_render_species_token(key_pokemon[0]))

    events = _cluster_events(cluster)
    tournaments = [name for name, _, _ in events]
    source_label = "official + grassroots results" if is_official else "Limitless grassroots results"
    source = f"{source_label} ({team_count} teams): {', '.join(tournaments[:2])}".strip()

    return {
        "slug": f"live-{_slugify(label) or 'shell'}",
        "label": label or "Unnamed shell",
        "source": source[:240],
        "result_label": result_label,
        "field_relevance": _clamp(0.45 + 0.45 * popularity_share + 0.15 * result_signal + official_bonus),
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
        "is_official": is_official,
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
    max_weight = max((sum(c.weight for c in cluster) for cluster in clusters), default=0.0)
    snapshots = [_build_snapshot(cluster, max_weight) for cluster in clusters]
    snapshots.sort(key=lambda snapshot: (-_snapshot_rank(snapshot), str(snapshot["label"])))

    return DiscoveryResult(
        snapshots=snapshots[:max_snapshots],
        teams_analyzed=len(candidates),
        clusters_formed=len(clusters),
        warnings=[],
    )
