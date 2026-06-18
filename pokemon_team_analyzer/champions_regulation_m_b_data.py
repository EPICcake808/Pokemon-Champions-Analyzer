"""Regulation M-B ruleset data, modeled as Regulation M-A plus the M-B delta.

Regulation M-B (active 2026-06-17 through 2026-09-02, including the 2026 World
Championships) is *additive* over M-A: it keeps the entire M-A pool and adds 22 Pokemon,
16 Mega Evolutions, and 15 held items, with a small number of base-stat nerfs.

The fully-published parts (new species, new general items, and the mainline-based mega
stones, which Champions names with the established convention) are encoded directly. The
not-cleanly-published parts -- the Champions-original mega stones/abilities and the stat
nerf numbers -- are ingested from Serebii's Champions dex and corroborating sources; any
value that cannot be verified is left out and flagged rather than guessed.
"""
from __future__ import annotations

from .champions_m_a_data import (
    ALLOWED_HELD_ITEMS as _M_A_HELD_ITEMS,
    ALLOWED_MEGA_EVOLUTIONS as _M_A_MEGAS,
    ELIGIBLE_SPECIES as _M_A_SPECIES,
    MEGA_STONE_TO_BASE_SPECIES as _M_A_STONE_TO_BASE,
    MEGA_STONE_TO_MEGA_NAME as _M_A_STONE_TO_MEGA,
)


# --- Pokemon newly eligible in M-B (verbatim from Serebii's M-B ranked-battle page) ---
NEW_SPECIES = (
    "Vileplume",
    "Qwilfish",
    "Sceptile",
    "Blaziken",
    "Swampert",
    "Mawile",
    "Metagross",
    "Staraptor",
    "Musharna",
    "Scolipede",
    "Scrafty",
    "Eelektross",
    "Pyroar",
    "Malamar",
    "Barbaracle",
    "Dragalge",
    "Grimmsnarl",
    "Falinks",
    "Overqwil",
    "Houndstone",
    "Annihilape",
    "Gholdengo",
)

# --- Non-mega held items newly allowed in M-B ---
NEW_GENERAL_ITEMS = (
    "Wide Lens",
    "Muscle Band",
    "Wise Glasses",
    "Expert Belt",
    "Light Clay",
    "Life Orb",
    "Zoom Lens",
    "Metronome",
    "Iron Ball",
    "Icy Rock",
    "Smooth Rock",
    "Heat Rock",
    "Damp Rock",
    "Shed Shell",
    "Big Root",
)

# --- New Mega Evolutions: (mega_name, mega_stone, (base_species, ...)) ---
# Stone names verified against Serebii's Champions items/dex pages (the mega ability each
# grants is noted in a trailing comment for reference; abilities themselves flow through the
# metadata layer, as they already do for M-A's Champions-original megas).
NEW_MEGAS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # Mainline-based megas reuse their canonical stone names.
    ("Mega Sceptile", "Sceptilite", ("Sceptile",)),       # Lightning Rod
    ("Mega Blaziken", "Blazikenite", ("Blaziken",)),      # Speed Boost
    ("Mega Swampert", "Swampertite", ("Swampert",)),      # Swift Swim
    ("Mega Mawile", "Mawilite", ("Mawile",)),             # Huge Power
    ("Mega Metagross", "Metagrossite", ("Metagross",)),   # Tough Claws
    # Champions-original megas (Serebii-verified stones; X/Y and contracted spellings).
    ("Mega Raichu X", "Raichunite X", ("Raichu",)),       # Electric Surge
    ("Mega Raichu Y", "Raichunite Y", ("Raichu",)),       # No Guard
    ("Mega Staraptor", "Staraptite", ("Staraptor",)),     # Contrary
    ("Mega Scolipede", "Scolipite", ("Scolipede",)),      # Shell Armor
    ("Mega Scrafty", "Scraftinite", ("Scrafty",)),        # Intimidate
    ("Mega Eelektross", "Eelektrossite", ("Eelektross",)),# Elevate (new ability)
    ("Mega Pyroar", "Pyroarite", ("Pyroar",)),            # Fire Mane (new ability)
    ("Mega Malamar", "Malamarite", ("Malamar",)),         # Contrary
    ("Mega Barbaracle", "Barbaracite", ("Barbaracle",)),  # Tough Claws
    ("Mega Dragalge", "Dragalgite", ("Dragalge",)),       # Regenerator
    ("Mega Falinks", "Falinksite", ("Falinks",)),         # Defiant
)

# Base-stat changes introduced in M-B, keyed by PokeAPI slug -> partial stat map
# ({"hp"|"attack"|"defense"|"special_attack"|"special_defense"|"speed": value}), merged
# over the Champions baseline by the regulations layer.
#
# Intentionally empty: verification against Serebii's Champions dex (cross-checked with
# three patch-note sources) confirmed that M-B did NOT change any Pokemon's base stats. The
# widely-reported "nerfs" to Annihilape (lost Final Gambit; Rage Fist resets on switch) and
# Grimmsnarl (lost False Surrender, Thunder Wave) are move/mechanic changes, not stat-line
# changes. The per-regulation stat layer is kept for future regulations that do rebalance.
STAT_OVERRIDES: dict[str, dict[str, int]] = {}


def _dedupe(*sequences: tuple[str, ...]) -> tuple[str, ...]:
    """Concatenate sequences preserving order and dropping later duplicates."""
    seen: set[str] = set()
    ordered: list[str] = []
    for sequence in sequences:
        for value in sequence:
            if value not in seen:
                seen.add(value)
                ordered.append(value)
    return tuple(ordered)


_NEW_MEGA_NAMES = tuple(mega_name for mega_name, _stone, _bases in NEW_MEGAS)
_NEW_MEGA_STONES = tuple(stone for _mega_name, stone, _bases in NEW_MEGAS)

ELIGIBLE_SPECIES = _dedupe(_M_A_SPECIES, NEW_SPECIES)
ALLOWED_MEGA_EVOLUTIONS = _dedupe(_M_A_MEGAS, _NEW_MEGA_NAMES)
ALLOWED_HELD_ITEMS = _dedupe(_M_A_HELD_ITEMS, NEW_GENERAL_ITEMS, _NEW_MEGA_STONES)

MEGA_STONE_TO_BASE_SPECIES = {
    **_M_A_STONE_TO_BASE,
    **{stone: bases for _mega_name, stone, bases in NEW_MEGAS},
}
MEGA_STONE_TO_MEGA_NAME = {
    **_M_A_STONE_TO_MEGA,
    **{stone: mega_name for mega_name, stone, _bases in NEW_MEGAS},
}
