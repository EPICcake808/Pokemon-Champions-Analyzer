"""Curated OHKO/2HKO damage grid against representative Regulation M-A shells.

Mirrors the philosophy of :mod:`speed_benchmarks`: reference sets are *declared* (species,
investment, item, ability, key move, field) and the damage numbers are *computed* by the
shared :mod:`damage` engine, so the grid can never drift from the analyzer's own math.

The grid answers two concrete questions for a team:

* **outgoing** — do my attackers break the common walls of the meta?
* **incoming** — do my Pokemon survive the meta's defining nukes?

Benchmark species are resolved through the same :class:`MetadataProvider` the analyzer
uses. If a provider cannot resolve a benchmark species or move (e.g. the lightweight fakes
used in unit tests), that benchmark is skipped gracefully rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .damage import Combatant, FieldConditions, compute_damage
from .data import MetadataProvider
from .models import MoveData
from .stats import compute_stat


@dataclass(frozen=True)
class _Spread:
    """A declared Champions investment spread; stats are computed, never hand-entered."""

    hp: int = 0
    atk: int = 0
    df: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0
    plus: str | None = None
    minus: str | None = None


_STAT_FIELDS = (
    ("hp", "base_hp"),
    ("attack", "base_attack"),
    ("defense", "base_defense"),
    ("special_attack", "base_special_attack"),
    ("special_defense", "base_special_defense"),
    ("speed", "base_speed"),
)
_SPREAD_KEYS = {
    "hp": "hp",
    "attack": "atk",
    "defense": "df",
    "special_attack": "spa",
    "special_defense": "spd",
    "speed": "spe",
}

# (display label, _Spread attribute) pairs in stat order, plus the long->short map
# used for the +/- nature labels.
_DISPLAY_STATS = (
    ("HP", "hp"),
    ("Atk", "atk"),
    ("Def", "df"),
    ("SpA", "spa"),
    ("SpD", "spd"),
    ("Spe", "spe"),
)
_SHORT_STAT = {
    "hp": "HP",
    "attack": "Atk",
    "defense": "Def",
    "special_attack": "SpA",
    "special_defense": "SpD",
    "speed": "Spe",
}


@dataclass(frozen=True)
class DamageBenchmark:
    slug: str
    label: str
    species: str  # name the provider can resolve
    shell: str  # which shell this set represents (sun, trick_room, ...)
    spread: _Spread
    ability: str | None = None
    item: str | None = None
    # Attacker-only fields:
    move: str | None = None  # provider-resolvable move name for incoming benchmarks
    field: FieldConditions = field(default_factory=FieldConditions)
    note: str = ""


# --- Common bulky walls (outgoing targets) ------------------------------------
WALL_BENCHMARKS: tuple[DamageBenchmark, ...] = (
    DamageBenchmark(
        "wall_amoonguss",
        "Assault Vest Amoonguss",
        "Amoonguss",
        "trick_room",
        _Spread(hp=32, spd=32, plus="special_defense", minus="speed"),
        ability="Regenerator",
        item="Assault Vest",
        note="Standard bulky redirection pivot.",
    ),
    DamageBenchmark(
        "wall_archaludon",
        "Bulky Archaludon",
        "Archaludon",
        "balance",
        _Spread(hp=32, spd=20, df=14),
        ability="Stamina",
        item="Leftovers",
        note="Common balance wall / Stalwart pivot.",
    ),
    DamageBenchmark(
        "wall_incineroar",
        "Bulky Incineroar",
        "Incineroar",
        "balance",
        _Spread(hp=32, spd=20, df=14, minus="speed"),
        ability="Intimidate",
        item="Sitrus Berry",
        note="The format's defining pivot.",
    ),
    DamageBenchmark(
        "wall_farigiraf",
        "Trick Room Farigiraf",
        "Farigiraf",
        "trick_room",
        _Spread(hp=32, df=20, spd=14, minus="speed"),
        ability="Armor Tail",
        item="Throat Spray",
        note="Common Trick Room setter and special wall.",
    ),
)


# --- Defining nukes (incoming threats) ----------------------------------------
ATTACKER_BENCHMARKS: tuple[DamageBenchmark, ...] = (
    DamageBenchmark(
        "nuke_charizard_y_heat_wave",
        "Sun Mega Charizard Y Heat Wave",
        "Charizard-Mega-Y",
        "sun",
        _Spread(spa=32, spe=32, plus="special_attack", minus="defense"),
        ability="Drought",
        item=None,
        move="Heat Wave",
        field=FieldConditions(weather="sun", spread=True),
        note="Sun-boosted spread special pressure.",
    ),
    DamageBenchmark(
        "nuke_garchomp_eq",
        "Choice Band Garchomp Earthquake",
        "Garchomp",
        "hyper_offense",
        _Spread(atk=32, spe=32, plus="attack"),
        ability="Rough Skin",
        item="Choice Band",
        move="Earthquake",
        field=FieldConditions(spread=True),
        note="Spread Ground pressure from a fast Choice attacker.",
    ),
    DamageBenchmark(
        "nuke_basculegion_wave_crash",
        "Rain Choice Band Basculegion Wave Crash",
        "Basculegion",
        "rain",
        _Spread(atk=32, spe=32, plus="attack"),
        ability="Swift Swim",
        item="Choice Band",
        move="Wave Crash",
        field=FieldConditions(weather="rain"),
        note="Rain-boosted physical Water nuke.",
    ),
    DamageBenchmark(
        "nuke_kingambit_kowtow",
        "Kingambit Kowtow Cleave",
        "Kingambit",
        "bulky_offense",
        _Spread(atk=32, hp=20, plus="attack", minus="speed"),
        ability="Defiant",
        item="Black Glasses",
        move="Kowtow Cleave",
        field=FieldConditions(),
        note="High-roll Dark physical pressure.",
    ),
)


def _combatant_from_benchmark(
    benchmark: DamageBenchmark, provider: MetadataProvider
) -> Combatant | None:
    try:
        species = provider.get_species(benchmark.species)
    except (KeyError, LookupError, ConnectionError):
        return None
    spread = benchmark.spread
    stats: dict[str, int] = {}
    for stat_name, base_field in _STAT_FIELDS:
        sp = getattr(spread, _SPREAD_KEYS[stat_name])
        nature = 1 if spread.plus == stat_name else -1 if spread.minus == stat_name else 0
        stats[stat_name] = compute_stat(
            getattr(species, base_field),
            sp,
            is_hp=stat_name == "hp",
            nature=nature,
        )
    return Combatant(
        species=species.name,
        types=species.types,
        hp=stats["hp"],
        attack=stats["attack"],
        defense=stats["defense"],
        special_attack=stats["special_attack"],
        special_defense=stats["special_defense"],
        ability=benchmark.ability,
        item=benchmark.item,
    )


def _describe_benchmark(benchmark: DamageBenchmark) -> str:
    """Human-readable build assumption, e.g. 'Assault Vest · Regenerator · 32 HP / 32 SpD (+SpD, -Spe)'."""
    spread = benchmark.spread
    investment = [f"{getattr(spread, key)} {label}" for label, key in _DISPLAY_STATS if getattr(spread, key)]
    spread_text = " / ".join(investment) if investment else "no investment"
    nature_bits: list[str] = []
    if spread.plus:
        nature_bits.append(f"+{_SHORT_STAT.get(spread.plus, spread.plus)}")
    if spread.minus:
        nature_bits.append(f"-{_SHORT_STAT.get(spread.minus, spread.minus)}")
    if nature_bits:
        spread_text = f"{spread_text} ({', '.join(nature_bits)})"
    prefix = [part for part in (benchmark.item, benchmark.ability) if part]
    return " · ".join([*prefix, spread_text])


def _resolve_move(name: str | None, provider: MetadataProvider) -> MoveData | None:
    if not name:
        return None
    try:
        return provider.get_move(name)
    except (KeyError, LookupError, ConnectionError):
        return None


def _damage_payload(result, attacker: str, defender: str, move: str, benchmark_set: str) -> dict[str, object]:
    return {
        "attacker": attacker,
        "defender": defender,
        "move": move,
        "move_type": result.move_type,
        "category": result.category,
        "min_percent": result.min_percent,
        "max_percent": result.max_percent,
        "type_multiplier": result.type_multiplier,
        "summary": result.summary,
        "guaranteed_ohko": result.guaranteed_ohko,
        "possible_ohko": result.possible_ohko,
        "guaranteed_2hko": result.guaranteed_2hko,
        "unmodeled": list(result.unmodeled),
        # The build assumed for the curated (benchmark) side of this row.
        "benchmark_set": benchmark_set,
    }


def build_damage_matchups(
    team: list[tuple[Combatant, tuple[MoveData, ...]]],
    provider: MetadataProvider,
) -> dict[str, object]:
    """Return the curated outgoing/incoming damage grid for a resolved team."""

    outgoing: list[dict[str, object]] = []
    incoming: list[dict[str, object]] = []
    used_walls: list[str] = []
    used_attackers: list[str] = []

    wall_combatants = [
        (bench, _combatant_from_benchmark(bench, provider)) for bench in WALL_BENCHMARKS
    ]
    for member_combatant, moves in team:
        damaging_moves = [m for m in moves if m.damage_class in ("physical", "special") and (m.power or 0) > 0]
        if not damaging_moves:
            continue
        for bench, wall in wall_combatants:
            if wall is None:
                continue
            best = None
            for move in damaging_moves:
                field_for_move = FieldConditions(spread=move.target_name in {
                    "all-opponents",
                    "all-other-pokemon",
                })
                result = compute_damage(member_combatant, wall, move, field_for_move)
                if result is None:
                    continue
                if best is None or result.max_percent > best.max_percent:
                    best = result
            if best is not None:
                if bench.label not in used_walls:
                    used_walls.append(bench.label)
                outgoing.append(
                    _damage_payload(
                        best,
                        member_combatant.species,
                        bench.label,
                        best.move,
                        _describe_benchmark(bench),
                    )
                )

    for bench in ATTACKER_BENCHMARKS:
        attacker = _combatant_from_benchmark(bench, provider)
        move = _resolve_move(bench.move, provider)
        if attacker is None or move is None:
            continue
        recorded = False
        benchmark_set = _describe_benchmark(bench)
        for member_combatant, _ in team:
            result = compute_damage(attacker, member_combatant, move, bench.field)
            if result is None:
                continue
            recorded = True
            incoming.append(
                _damage_payload(result, bench.label, member_combatant.species, move.name, benchmark_set)
            )
        if recorded and bench.label not in used_attackers:
            used_attackers.append(bench.label)

    return {
        "outgoing": outgoing,
        "incoming": incoming,
        "benchmark_walls": used_walls,
        "benchmark_attackers": used_attackers,
        "notes": [
            "OHKO/2HKO calls use the standard Gen 9 formula on Champions stats against curated reference sets.",
            "Reference sets assume common spreads/items; real opponents vary.",
        ],
    }
