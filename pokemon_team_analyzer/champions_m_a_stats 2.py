"""Champions base-stat overrides.

Species and move metadata are sourced from PokeAPI, which serves *mainline* base stats.
Pokemon Champions rebalanced a number of species (Serebii's Champions dex is the
reference), so any analysis touching a rebalanced Pokemon — speed tiers, role inference,
normalized stat blocks, benchmark hits — must use the Champions line, not the mainline one.

This module holds a curated override table keyed by PokeAPI slug. Each entry is a *partial*
stat mapping: only the stats that Champions changed are listed, and they are merged over the
PokeAPI values so unaffected stats stay correct. Values are cross-referenced against
Serebii's Champions Pokedex.

The table is intentionally seeded only with stat lines that have been explicitly verified.
Add rebalanced species here as their Champions stat lines are confirmed; do not guess.
"""

from __future__ import annotations


_STAT_FIELDS = {
    "hp": "base_hp",
    "attack": "base_attack",
    "defense": "base_defense",
    "special_attack": "base_special_attack",
    "special_defense": "base_special_defense",
    "speed": "base_speed",
}


# Keyed by PokeAPI slug (the species ``api_name``). Each value lists only the stats that
# differ from mainline under Champions. Verified against Serebii's Champions dex.
CHAMPIONS_STAT_OVERRIDES: dict[str, dict[str, int]] = {
    "alakazam": {"special_attack": 175, "speed": 150},
    "gengar": {"special_attack": 170, "speed": 130},
    "delphox": {"speed": 134},
    "lopunny": {"speed": 135},
}


def champions_stat_overrides(api_name: str | None) -> dict[str, int]:
    """Return the Champions stat overrides for a PokeAPI slug, or an empty dict."""

    if not api_name:
        return {}
    return CHAMPIONS_STAT_OVERRIDES.get(api_name.strip().lower(), {})


def apply_champions_stat_overrides(api_name: str | None, base_stats: dict[str, int]) -> dict[str, int]:
    """Merge Champions overrides over a ``{stat_name: value}`` mapping (non-destructive)."""

    overrides = champions_stat_overrides(api_name)
    if not overrides:
        return base_stats
    merged = dict(base_stats)
    merged.update(overrides)
    return merged
