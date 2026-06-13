"""Shared Pokemon Champions level-50 stat math.

Pokemon Champions uses a fixed perfect-31 IV baseline and Stat Points (SP) that add a
flat +1 per point. Crucially, the nature multiplier is applied *after* the SP are added,
matching the in-game stat screen:

    Jolly Aerodactyl with 32 Speed SP -> floor((150 + 32) * 1.1) = 200

This is the single source of truth for stat normalization. Both the analyzer's
battle-speed/stat normalization and the regulation speed benchmark catalogs call
``compute_stat`` so the two layers can never drift apart.
"""

from __future__ import annotations


CHAMPIONS_FIXED_IV = 31
CHAMPIONS_LEVEL = 50
# Total Stat Point budget that may be distributed across a single set.
CHAMPIONS_TOTAL_SPS = 66
# Maximum Stat Points that may be assigned to one stat (the single-stat investment cap).
CHAMPIONS_MAX_STAT_SPS = 32


def compute_stat(
    base_stat: int,
    sp: int = 0,
    *,
    is_hp: bool = False,
    nature: int = 0,
    level: int = CHAMPIONS_LEVEL,
) -> int:
    """Return a Pokemon Champions stat value for the given level.

    Args:
        base_stat: The species base stat.
        sp: Flat Stat Point investment (+1 per point).
        is_hp: When ``True`` use the HP formula and ignore ``nature``.
        nature: Nature direction for this stat: ``1`` boosted (+10%), ``-1`` lowered
            (-10%), ``0`` neutral.
        level: The Pokemon's level (Champions ranked play is fixed at 50).

    The nature multiplier is applied *after* the SP are added, using integer arithmetic
    (``* 11 // 10`` / ``* 9 // 10``) to match the game exactly and avoid float drift.
    """

    base_component = ((2 * base_stat + CHAMPIONS_FIXED_IV) * level) // 100
    if is_hp:
        return base_component + level + 10 + sp
    pre_nature = base_component + 5 + sp
    if nature > 0:
        return pre_nature * 11 // 10
    if nature < 0:
        return pre_nature * 9 // 10
    return pre_nature
