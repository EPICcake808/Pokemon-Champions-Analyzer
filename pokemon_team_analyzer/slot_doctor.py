"""Slot doctor: turn a diagnosed gap into concrete, Regulation M-A-legal fixes.

For each detected weakness (Trick Room exposure, no speed control vs Tailwind, no
anti-setup tools, or a heavy defensive type hole) the doctor proposes:

* **move swaps** — a move an existing member can *legally* learn (drawn from its M-A move
  pool) to patch the gap, and
* **replacements** — curated specialist species, always filtered through ``ELIGIBLE_SPECIES``
  so a suggestion can never be illegal.

This runs on demand (its own endpoint), not on the analysis hot path, because the move-pool
lookups touch the network/cache. It reuses the analyzer's member resolution, the shared
stat formula, and the type chart so its reads match the rest of the app.
"""

from __future__ import annotations

from .analyzer import _normalized_member_stats, _resolve_members
from .champions_m_a_data import ELIGIBLE_SPECIES
from .champions_m_a_moves import get_allowed_moves_for_species
from .data import CachedPokeApiClient, MetadataProvider
from .models import TYPE_ORDER, TeamMember
from .regulations import (
    DEFAULT_REGULATION_ID,
    resolve_builder_option_source_species_name,
)
from .showdown import parse_showdown_team
from .typechart import defensive_multiplier


_ELIGIBLE = set(ELIGIBLE_SPECIES)

_TR_COUNTER_MOVES = {"taunt", "encore", "imprison", "trick-room", "fake-out", "wide-guard", "quash"}
_SPEED_CONTROL_MOVES = {"tailwind", "trick-room", "thunder-wave", "icy-wind", "electroweb", "sticky-web", "nuzzle", "glare"}
_ANTI_SETUP_MOVES = {"taunt", "haze", "clear-smog", "encore", "roar", "whirlwind", "dragon-tail", "perish-song"}

# Ordered patch moves to look for in a member's legal pool, per gap.
_TR_PATCH = ("taunt", "fake-out", "imprison", "trick-room", "wide-guard")
_TAILWIND_PATCH = ("tailwind", "icy-wind", "electroweb", "thunder-wave", "trick-room")
_SETUP_PATCH = ("taunt", "haze", "clear-smog", "encore")

# Curated specialists per mode gap (filtered to ELIGIBLE_SPECIES at runtime).
_GAP_SPECIALISTS = {
    "trick_room": ("Whimsicott", "Tornadus", "Incineroar", "Rillaboom", "Grimmsnarl"),
    "tailwind": ("Whimsicott", "Tornadus", "Talonflame", "Pelipper"),
    "setup": ("Whimsicott", "Incineroar", "Grimmsnarl"),
}

_FAST_THRESHOLD = 120
_SLOW_THRESHOLD = 85


def _norm(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _display_move(api_name: str) -> str:
    return api_name.replace("-", " ").title()


def _legal_pool(species: str, cache: dict[str, dict[str, str]]) -> dict[str, str]:
    """Normalized api-name -> display-name of a species' legal M-A move pool (cached)."""
    if species in cache:
        return cache[species]
    pool: dict[str, str] = {}
    try:
        source = resolve_builder_option_source_species_name(species)
        pool = {_norm(move): move for move in get_allowed_moves_for_species(source)}
    except Exception:  # pragma: no cover - defensive: skip unresolvable pools
        pool = {}
    cache[species] = pool
    return pool


def _build_move_swaps(
    members: list[TeamMember],
    patch_moves: tuple[str, ...],
    speeds: dict[str, int],
    pool_cache: dict[str, dict[str, str]],
    limit: int = 2,
) -> list[dict[str, str]]:
    swaps: list[dict[str, str]] = []
    used: set[str] = set()
    for patch in patch_moves:
        candidates: list[tuple[str, str]] = []
        for member in members:
            name = member.pokemon_set.display_name
            if name in used:
                continue
            if any(move.api_name == patch for move in member.move_data):
                continue
            pool = _legal_pool(member.pokemon_set.species, pool_cache)
            if patch in pool:
                candidates.append((name, _display_move(patch)))
        if not candidates:
            continue
        # Fast Taunt / speed control wants the quickest legal user.
        candidates.sort(key=lambda item: speeds.get(item[0], 0), reverse=True)
        name, move_display = candidates[0]
        swaps.append(
            {
                "member": name,
                "move": move_display,
                "note": f"{name} can legally run {move_display} to patch this.",
            }
        )
        used.add(name)
        if len(swaps) >= limit:
            break
    return swaps


def _curated_replacements(gap_id: str, team_species_lower: set[str], reason: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for species in _GAP_SPECIALISTS.get(gap_id, ()):  # already eligible base names
        if species not in _ELIGIBLE:
            continue
        if species.lower() in team_species_lower:
            continue
        out.append({"species": species, "note": reason})
        if len(out) >= 3:
            break
    return out


def analyze_slots(
    team_text: str,
    metadata_provider: MetadataProvider | None = None,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> dict[str, object]:
    provider = metadata_provider or CachedPokeApiClient()
    team_sets = parse_showdown_team(team_text)
    if not team_sets:
        raise ValueError("Paste a team before running the slot doctor.")
    members = _resolve_members(team_sets, provider, regulation_id=regulation_id)

    speeds = {m.pokemon_set.display_name: _normalized_member_stats(m)["speed"] for m in members}
    team_apis = {move.api_name for m in members for move in m.move_data}
    team_species_lower = {m.pokemon_set.species.lower() for m in members}
    has_priority_attacker = any(
        move.priority > 0 and move.damage_class != "status" for m in members for move in m.move_data
    )
    team_abilities = {(m.pokemon_set.ability or "").strip().lower() for m in members}
    fast_count = sum(1 for speed in speeds.values() if speed >= _FAST_THRESHOLD)

    pool_cache: dict[str, dict[str, str]] = {}
    gaps: list[dict[str, object]] = []

    # --- Gap 1: defensive type hole ---
    exposure: list[tuple[str, float, str]] = []
    for attack_type in TYPE_ORDER:
        multipliers = [(m, defensive_multiplier(m.species_data.types, attack_type)) for m in members]
        average = sum(value for _, value in multipliers) / len(multipliers)
        worst_member = max(multipliers, key=lambda item: item[1])
        exposure.append((attack_type, average, worst_member[0].pokemon_set.display_name))
    worst_type, worst_avg, liability = max(exposure, key=lambda item: item[1])
    if worst_avg >= 1.3:
        gaps.append(
            {
                "id": "type_weakness",
                "label": f"{worst_type.title()} weakness",
                "problem": (
                    f"The team takes about {worst_avg:.2f}x from {worst_type.title()} on average — "
                    f"{liability} is the biggest liability."
                ),
                "move_swaps": [],
                "replacements": [
                    {
                        "species": None,
                        "note": (
                            f"Consider swapping {liability} for a {worst_type.title()}-resistant or "
                            f"immune Pokemon that keeps its role."
                        ),
                    }
                ],
            }
        )

    # --- Gap 2: Trick Room exposure (fast team, no answer) ---
    if fast_count >= 3 and not (team_apis & _TR_COUNTER_MOVES) and not has_priority_attacker:
        gaps.append(
            {
                "id": "trick_room",
                "label": "Folds to Trick Room",
                "problem": (
                    f"{fast_count} fast members with no Taunt, Fake Out, priority, or Trick Room of your own — "
                    "you get flipped under Trick Room."
                ),
                "move_swaps": _build_move_swaps(members, _TR_PATCH, speeds, pool_cache),
                "replacements": _curated_replacements(
                    "trick_room", team_species_lower, "Brings fast Taunt / Fake Out disruption versus Trick Room."
                ),
            }
        )

    # --- Gap 3: No speed control vs Tailwind ---
    if (
        fast_count <= 1
        and not (team_apis & {"tailwind", "trick-room", "thunder-wave", "icy-wind", "electroweb"})
        and not has_priority_attacker
    ):
        gaps.append(
            {
                "id": "tailwind",
                "label": "No answer to Tailwind",
                "problem": "No speed control or priority, and few fast members — opposing Tailwind simply outruns you.",
                "move_swaps": _build_move_swaps(members, _TAILWIND_PATCH, speeds, pool_cache),
                "replacements": _curated_replacements(
                    "tailwind", team_species_lower, "Adds your own Tailwind or speed control."
                ),
            }
        )

    # --- Gap 4: No anti-setup tools ---
    if not (team_apis & _ANTI_SETUP_MOVES) and "unaware" not in team_abilities:
        gaps.append(
            {
                "id": "setup",
                "label": "Vulnerable to setup",
                "problem": "No Taunt, Haze, Clear Smog, Encore, or phazing — opposing setup sweepers can snowball.",
                "move_swaps": _build_move_swaps(members, _SETUP_PATCH, speeds, pool_cache),
                "replacements": _curated_replacements(
                    "setup", team_species_lower, "Brings Taunt / Intimidate to deny setup."
                ),
            }
        )

    gaps = gaps[:3]
    note = (
        "Every suggested move is drawn from the member's legal Regulation M-A pool and every "
        "replacement is an eligible species, so all fixes are legal."
    )
    return {
        "ok": True,
        "team": [m.pokemon_set.display_name for m in members],
        "gaps": gaps,
        "all_clear": not gaps,
        "note": note,
    }
