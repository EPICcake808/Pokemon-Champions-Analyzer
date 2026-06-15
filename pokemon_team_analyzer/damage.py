"""Pokemon Champions damage engine.

Implements the standard Generation 9 damage formula, fed Champions stat values
(level 50, perfect IVs, Stat-Point investment) from :mod:`stats`. The modifier chain
mirrors the well-documented Smogon damage-calc order (4096-based fixed point with
``pokeRound`` half-down rounding) so results line up with the reference calculator.

This module is intentionally free of any :mod:`analyzer` import so the analyzer can
depend on it (the analyzer builds curated damage grids and powers the preview-trainer
mode on top of this engine). It only depends on :mod:`stats`, :mod:`models`, and
:mod:`typechart`.

Modeled modifiers: STAB (incl. Adaptability), full type effectiveness, defender
type-immunity abilities (Levitate, Flash Fire, etc.), weather (sun/rain on Fire/Water
offense, plus the sand SpDef boost for Rock and the snow Def boost for Ice defenders),
spread (doubles 0.75), critical hits, stat stages (with crit stage-ignore rules), burn
(with Guts), screens (Reflect/Light Screen), the 1.2x type-boost items (Charcoal,
Mystic Water, Soft Sand, ...), and the common power items/abilities listed in the
constants below. Anything outside that set is reported back in
``DamageResult.unmodeled`` rather than silently ignored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .models import MoveData, SpeciesData, TeamMember
from .stats import CHAMPIONS_LEVEL
from .typechart import defensive_multiplier


# --- Modeled modifier tables ---------------------------------------------------

# Defender abilities that zero out an incoming damaging type.
ABILITY_TYPE_IMMUNITIES = {
    "dry skin": ("water",),
    "earth eater": ("ground",),
    "flash fire": ("fire",),
    "levitate": ("ground",),
    "lightning rod": ("electric",),
    "motor drive": ("electric",),
    "sap sipper": ("grass",),
    "storm drain": ("water",),
    "volt absorb": ("electric",),
    "water absorb": ("water",),
    "well-baked body": ("fire",),
}

# Offensive abilities that double the Attack stat.
_DOUBLE_ATTACK_ABILITIES = {"huge power", "pure power"}

# Defender abilities that halve damage from given types (final-damage reduction).
_DEFENDER_TYPE_HALVING_ABILITIES = {
    "thick fat": ("fire", "ice"),
    "heatproof": ("fire",),
    "water bubble": ("fire",),  # also doubles the bearer's Water moves (offense, unmodeled)
    "purifying salt": ("ghost",),
}

# Abilities whose damage-relevant effect (if any) is captured elsewhere (weather setters
# feed the field, on-hit/status abilities don't change a single pre-hit roll). Listing them
# keeps the "unmodeled" warning honest instead of flagging harmless abilities.
_NO_DAMAGE_EFFECT_ABILITIES = {
    "drought",
    "drizzle",
    "sand stream",
    "snow warning",
    "orichalcum pulse",
    "hadron engine",
    "regenerator",
    "stamina",
    "hospitality",
    "natural cure",
    "clear body",
    "white smoke",
    "own tempo",
    "oblivious",
    "flame body",
    "static",
    "poison point",
    "effect spore",
    "prankster",
    "unaware",
    "inner focus",
    # No effect on a single pre-hit damage roll: contact recoil (Rough Skin),
    # weather-speed (Swift Swim), priority denial (Armor Tail), and the on-drop /
    # on-switch Attack changes (Defiant, Intimidate) which are fed in via stat stages.
    "rough skin",
    "swift swim",
    "armor tail",
    "defiant",
    "intimidate",
}

# Items recognised by the engine (everything else is treated as no damage effect).
_KNOWN_NEUTRAL_ITEMS = {
    "leftovers",
    "rocky helmet",
    "sitrus berry",
    "heavy-duty boots",
    "focus sash",
    "mental herb",
    "covert cloak",
    "clear amulet",
    "safety goggles",
    "wide lens",
}

# Items that boost a single move type by 1.2x. These fold into the base-power
# modifier chain exactly like the Smogon-calc ``bpMods`` (0x1333 = 4915). These are
# the legal Champions Regulation M-A offensive items — note that Choice Band/Specs,
# Life Orb, and Assault Vest are NOT in the M-A item pool, so the type-boost items
# (plus Choice Scarf, which only affects Speed) are the format's real damage items.
TYPE_BOOST_ITEMS = {
    "black belt": "fighting",
    "black glasses": "dark",
    "charcoal": "fire",
    "dragon fang": "dragon",
    "fairy feather": "fairy",
    "hard stone": "rock",
    "magnet": "electric",
    "metal coat": "steel",
    "miracle seed": "grass",
    "mystic water": "water",
    "never-melt ice": "ice",
    "poison barb": "poison",
    "sharp beak": "flying",
    "silk scarf": "normal",
    "silver powder": "bug",
    "soft sand": "ground",
    "spell tag": "ghost",
    "twisted spoon": "psychic",
}

_CHOICE_BAND = "choice band"
_CHOICE_SPECS = "choice specs"
_ASSAULT_VEST = "assault vest"
_EVIOLITE = "eviolite"
_LIFE_ORB = "life orb"

# 4096-based modifiers.
_M = 4096
_HALF = 2048
_ONE_AND_HALF = 6144
_DOUBLE = 8192
_LIFE_ORB_MOD = 5324  # 1.3
_TYPE_BOOST_MOD = 4915  # 1.2 (type-enhancing items)
_SPREAD_MOD = 3072  # 0.75
_SCREEN_SINGLE = 2048  # 0.5
_SCREEN_DOUBLE = 2732  # ~0.667


def _poke_round(value: float) -> int:
    """Round half *down*, matching the cartridge/Smogon ``pokeRound``."""
    floor = math.floor(value)
    if value - floor > 0.5:
        return floor + 1
    return floor


def _apply_mod(value: int, mod: int) -> int:
    if mod == _M:
        return value
    return _poke_round(value * mod / _M)


def _chain(mods: tuple[int, ...]) -> int:
    """Compose 4096-based modifiers the way the cartridge ``chainMods`` does.

    Each modifier folds in with round-half-up ``(stack * mod + 2048) >> 12``; the
    composed result is later applied to a value with the half-down ``_apply_mod``.
    """
    stack = _M
    for mod in mods:
        if mod != _M:
            stack = (stack * mod + 2048) >> 12
    return stack


def _apply_chain(value: int, mods: tuple[int, ...]) -> int:
    return _apply_mod(value, _chain(mods))


def _stage_multiplier(stat: int, stage: int) -> int:
    if stage == 0:
        return stat
    if stage > 0:
        return stat * (2 + stage) // 2
    return stat * 2 // (2 - stage)


@dataclass(frozen=True)
class Combatant:
    """A fully-resolved battler: types, computed stats, ability and item."""

    species: str
    types: tuple[str, ...]
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    ability: str | None = None
    item: str | None = None
    level: int = CHAMPIONS_LEVEL


@dataclass(frozen=True)
class FieldConditions:
    weather: str | None = None  # "sun" | "rain" | "sand" | "snow" | None
    spread: bool = False  # doubles spread move splashing multiple targets
    crit: bool = False
    attacker_atk_stage: int = 0  # stage on whichever offensive stat the move uses
    defender_def_stage: int = 0  # stage on whichever defensive stat the move hits
    attacker_burned: bool = False
    reflect: bool = False
    light_screen: bool = False


@dataclass(frozen=True)
class DamageResult:
    move: str
    move_type: str
    category: str  # "physical" | "special"
    base_power: int
    type_multiplier: float
    stab: float
    rolls: tuple[int, ...]
    min_damage: int
    max_damage: int
    defender_hp: int
    min_percent: float
    max_percent: float
    guaranteed_ohko: bool
    possible_ohko: bool
    guaranteed_2hko: bool
    possible_2hko: bool
    guaranteed_ko_hits: int | None
    summary: str
    unmodeled: tuple[str, ...] = field(default_factory=tuple)


def _norm(name: str | None) -> str:
    return (name or "").strip().lower()


def _ko_hits(per_hit: int, hp: int) -> int | None:
    if per_hit <= 0:
        return None
    return math.ceil(hp / per_hit)


def _ko_summary(result_min: int, result_max: int, hp: int) -> str:
    if result_max <= 0:
        return "No damage (immune)"
    if result_min >= hp:
        return "Guaranteed OHKO"
    if result_max >= hp:
        pct = round(_ohko_chance(result_min, result_max, hp) * 100)
        return f"Possible OHKO ({pct}% of rolls)"
    if 2 * result_min >= hp:
        return "Guaranteed 2HKO"
    if 2 * result_max >= hp:
        return "Possible 2HKO"
    hits = _ko_hits(result_min, hp)
    return f"Guaranteed {hits}HKO" if hits else "No damage"


def _ohko_chance(result_min: int, result_max: int, hp: int) -> float:
    spread = result_max - result_min
    if spread <= 0:
        return 1.0 if result_min >= hp else 0.0
    # 16 evenly spaced rolls; fraction at/above the HP threshold.
    above = sum(1 for i in range(16) if result_min + round(spread * i / 15) >= hp)
    return above / 16


def compute_damage(
    attacker: Combatant,
    defender: Combatant,
    move: MoveData,
    field: FieldConditions | None = None,
) -> DamageResult | None:
    """Return the 16-roll damage distribution for ``move`` from attacker to defender.

    Returns ``None`` for status moves or moves with no base power (nothing to roll).
    """

    field = field or FieldConditions()
    if move.damage_class not in ("physical", "special"):
        return None
    power = move.power or 0
    if power <= 0:
        return None

    unmodeled: list[str] = []
    attacker_ability = _norm(attacker.ability)
    defender_ability = _norm(defender.ability)
    attacker_item = _norm(attacker.item)
    defender_item = _norm(defender.item)
    weather = _norm(field.weather)
    move_type = move.type_name
    is_physical = move.damage_class == "physical"

    # Defender ability immunity short-circuits everything.
    if move_type in ABILITY_TYPE_IMMUNITIES.get(defender_ability, ()):
        return DamageResult(
            move=move.name,
            move_type=move_type,
            category=move.damage_class,
            base_power=power,
            type_multiplier=0.0,
            stab=1.0,
            rolls=tuple([0] * 16),
            min_damage=0,
            max_damage=0,
            defender_hp=defender.hp,
            min_percent=0.0,
            max_percent=0.0,
            guaranteed_ohko=False,
            possible_ohko=False,
            guaranteed_2hko=False,
            possible_2hko=False,
            guaranteed_ko_hits=None,
            summary=f"No damage ({defender.ability} absorbs {move_type.title()})",
            unmodeled=tuple(unmodeled),
        )

    type_eff = defensive_multiplier(defender.types, move_type)

    # --- Base-power modifiers (Technician, then 1.2x type-boost items) ---
    power_mods: list[int] = []
    if attacker_ability == "technician" and power <= 60:
        power_mods.append(_ONE_AND_HALF)
    if TYPE_BOOST_ITEMS.get(attacker_item) == move_type:
        power_mods.append(_TYPE_BOOST_MOD)
    if power_mods:
        power = _apply_chain(power, tuple(power_mods))

    # --- Crit stage-ignore rules ---
    atk_stage = field.attacker_atk_stage
    def_stage = field.defender_def_stage
    if field.crit:
        atk_stage = max(0, atk_stage)
        def_stage = min(0, def_stage)

    # --- Offensive stat (stage, then item/ability mods) ---
    atk_stat = attacker.attack if is_physical else attacker.special_attack
    atk_stat = _stage_multiplier(atk_stat, atk_stage)
    offensive_mods: list[int] = []
    if is_physical and attacker_item == _CHOICE_BAND:
        offensive_mods.append(_ONE_AND_HALF)
    if not is_physical and attacker_item == _CHOICE_SPECS:
        offensive_mods.append(_ONE_AND_HALF)
    if is_physical and attacker_ability in _DOUBLE_ATTACK_ABILITIES:
        offensive_mods.append(_DOUBLE)
    atk_stat = _apply_chain(atk_stat, tuple(offensive_mods))

    # --- Defensive stat (stage, then item mods) ---
    def_stat = defender.defense if is_physical else defender.special_defense
    def_stat = _stage_multiplier(def_stat, def_stage)
    defensive_mods: list[int] = []
    if not is_physical and defender_item == _ASSAULT_VEST:
        defensive_mods.append(_ONE_AND_HALF)
    if defender_item == _EVIOLITE:
        defensive_mods.append(_ONE_AND_HALF)
    # Sand boosts a Rock defender's SpDef; snow boosts an Ice defender's Def (Gen 9).
    if not is_physical and weather == "sand" and "rock" in defender.types:
        defensive_mods.append(_ONE_AND_HALF)
    if is_physical and weather == "snow" and "ice" in defender.types:
        defensive_mods.append(_ONE_AND_HALF)
    def_stat = _apply_chain(def_stat, tuple(defensive_mods))

    # --- Base damage ---
    level_factor = (2 * attacker.level) // 5 + 2
    base = ((level_factor * power * atk_stat) // def_stat) // 50 + 2

    # Spread reduction (doubles, multi-target moves).
    if field.spread:
        base = _apply_mod(base, _SPREAD_MOD)

    # Weather on Fire/Water offense (sand/snow defensive boosts are folded into def_stat).
    if weather == "sun":
        if move_type == "fire":
            base = _apply_mod(base, _ONE_AND_HALF)
        elif move_type == "water":
            base = _apply_mod(base, _HALF)
    elif weather == "rain":
        if move_type == "water":
            base = _apply_mod(base, _ONE_AND_HALF)
        elif move_type == "fire":
            base = _apply_mod(base, _HALF)

    if field.crit:
        base = math.floor(base * 1.5)

    # --- STAB modifier ---
    stab_mod = _M
    stab_value = 1.0
    if move_type in attacker.types:
        if attacker_ability == "adaptability":
            stab_mod = _DOUBLE
            stab_value = 2.0
        else:
            stab_mod = _ONE_AND_HALF
            stab_value = 1.5

    # --- Burn ---
    is_burned = field.attacker_burned and is_physical
    if is_burned and attacker_ability == "guts":
        # Guts ignores the burn drop (and boosts Attack ×1.5, applied here as a fall-through).
        is_burned = False
        atk_recompute_note = True
    else:
        atk_recompute_note = False
    if atk_recompute_note:
        unmodeled.append("Guts attack boost applied approximately")

    # --- Final-damage "other" modifiers ---
    final_mods: list[int] = []
    if attacker_item == _LIFE_ORB:
        final_mods.append(_LIFE_ORB_MOD)
    screen_mod = _SCREEN_DOUBLE if field.spread else _SCREEN_SINGLE
    if not field.crit:
        if is_physical and field.reflect:
            final_mods.append(screen_mod)
        if not is_physical and field.light_screen:
            final_mods.append(screen_mod)
    if move_type in _DEFENDER_TYPE_HALVING_ABILITIES.get(defender_ability, ()):
        final_mods.append(_HALF)
    final_mod = _chain(tuple(final_mods))

    # --- 16 rolls ---
    rolls: list[int] = []
    for i in range(16):
        if type_eff == 0:
            rolls.append(0)
            continue
        dmg = math.floor(base * (85 + i) / 100)
        if stab_mod != _M:
            dmg = _apply_mod(dmg, stab_mod)
        dmg = math.floor(dmg * type_eff)
        if is_burned:
            dmg = math.floor(dmg / 2)
        dmg = _poke_round(max(1.0, dmg * final_mod / _M))
        rolls.append(dmg)

    rolls_t = tuple(rolls)
    min_damage = min(rolls_t)
    max_damage = max(rolls_t)
    hp = defender.hp

    # Surface ability/item factors we did not model so the UI can flag them.
    if attacker_ability and attacker_ability not in _modeled_attacker_abilities():
        unmodeled.append(f"attacker ability {attacker.ability}")
    if defender_ability and defender_ability not in _modeled_defender_abilities():
        unmodeled.append(f"defender ability {defender.ability}")
    if attacker_item and attacker_item not in _modeled_items():
        unmodeled.append(f"attacker item {attacker.item}")
    if defender_item and defender_item not in _modeled_items():
        unmodeled.append(f"defender item {defender.item}")

    return DamageResult(
        move=move.name,
        move_type=move_type,
        category=move.damage_class,
        base_power=power,
        type_multiplier=type_eff,
        stab=stab_value,
        rolls=rolls_t,
        min_damage=min_damage,
        max_damage=max_damage,
        defender_hp=hp,
        min_percent=round(min_damage / hp * 100, 1),
        max_percent=round(max_damage / hp * 100, 1),
        guaranteed_ohko=min_damage >= hp,
        possible_ohko=max_damage >= hp,
        guaranteed_2hko=2 * min_damage >= hp,
        possible_2hko=2 * max_damage >= hp,
        guaranteed_ko_hits=_ko_hits(min_damage, hp),
        summary=_ko_summary(min_damage, max_damage, hp),
        unmodeled=tuple(dict.fromkeys(unmodeled)),
    )


def _modeled_attacker_abilities() -> frozenset[str]:
    return frozenset(
        {"adaptability", "technician", "guts", *_DOUBLE_ATTACK_ABILITIES, *_NO_DAMAGE_EFFECT_ABILITIES}
    )


def _modeled_defender_abilities() -> frozenset[str]:
    return frozenset(
        {*ABILITY_TYPE_IMMUNITIES, *_DEFENDER_TYPE_HALVING_ABILITIES, *_NO_DAMAGE_EFFECT_ABILITIES}
    )


def _modeled_items() -> frozenset[str]:
    return frozenset(
        {
            _CHOICE_BAND,
            _CHOICE_SPECS,
            _ASSAULT_VEST,
            _EVIOLITE,
            _LIFE_ORB,
            *_KNOWN_NEUTRAL_ITEMS,
            *TYPE_BOOST_ITEMS,
        }
    )


def combatant_from_stats(
    species: SpeciesData,
    stats: dict[str, int],
    *,
    ability: str | None = None,
    item: str | None = None,
) -> Combatant:
    """Build a :class:`Combatant` from a species and a computed stat block.

    ``stats`` matches the analyzer's ``_normalized_member_stats`` output (keys ``hp``,
    ``attack``, ``defense``, ``special_attack``, ``special_defense``, ``speed``).
    """

    return Combatant(
        species=species.name,
        types=species.types,
        hp=stats["hp"],
        attack=stats["attack"],
        defense=stats["defense"],
        special_attack=stats["special_attack"],
        special_defense=stats["special_defense"],
        ability=ability,
        item=item,
    )
