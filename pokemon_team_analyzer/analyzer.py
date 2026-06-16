from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from statistics import median, pstdev
from typing import Iterable, cast

from .champions_m_a_meta import MODE_LABEL_ORDER, TOURNAMENT_MODE_SNAPSHOTS
from .damage import Combatant
from .damage_benchmarks import build_damage_matchups
from .glossary import build_plain_language_summary
from .data import CachedPokeApiClient, MetadataProvider
from .meta_snapshots import (
    get_runtime_common_meta_pokemon,
    get_tournament_meta_provenance,
    get_tournament_team_snapshots,
)
from .models import (
    BROAD_TEAM_ARCHETYPE_ORDER,
    MODE_PACKAGE_ORDER,
    MoveData,
    POKEMON_ROLE_ORDER,
    SPEED_TIER_ORDER,
    STYLE_PACKAGE_ORDER,
    TEAM_ARCHETYPE_ORDER,
    SpeciesData,
    PokemonSet,
    TeamAnalysis,
    TeamMember,
    TYPE_ORDER,
    UTILITY_ROLE_ORDER,
    WIN_CONDITION_PACKAGE_ORDER,
)
from .regulations import (
    DEFAULT_REGULATION_ID,
    IllegalTeamError,
    resolve_regulation_pokemon_set,
    resolve_regulation_species_name,
    validate_team_legality,
)
from .showdown import parse_showdown_team
from .speed_benchmarks import (
    RegulationSpeedBenchmarkCatalog,
    SpeedBenchmarkGroup,
    get_speed_benchmark_catalog,
)
from .stats import (
    CHAMPIONS_MAX_STAT_SPS,
    compute_stat,
)
from .typechart import TYPE_EFFECTIVENESS, defensive_multiplier

PROTECTION_MOVES = {
    "baneful-bunker",
    "burning-bulwark",
    "crafty-shield",
    "detect",
    "kings-shield",
    "mat-block",
    "obstruct",
    "protect",
    "quick-guard",
    "silk-trap",
    "spiky-shield",
    "wide-guard",
}

SCREEN_MOVES = {"aurora-veil", "light-screen", "reflect"}
REDIRECTION_MOVES = {"follow-me", "rage-powder", "spotlight"}
WEATHER_MOVES = {"chilly-reception", "hail", "rain-dance", "sandstorm", "snowscape", "sunny-day"}
TERRAIN_MOVES = {"electric-terrain", "grassy-terrain", "misty-terrain", "psychic-terrain"}
PIVOT_MOVES = {
    "baton-pass",
    "chilly-reception",
    "flip-turn",
    "parting-shot",
    "shed-tail",
    "teleport",
    "u-turn",
    "volt-switch",
}
ENTRY_HAZARD_MOVES = {"ceaseless-edge", "spikes", "stealth-rock", "sticky-web", "stone-axe", "toxic-spikes"}
HAZARD_REMOVAL_MOVES = {"court-change", "defog", "mortal-spin", "rapid-spin", "tidy-up"}
ITEM_CONTROL_MOVES = {"bestow", "corrosive-gas", "knock-off", "switcheroo", "trick"}
DISRUPTION_MOVES = {"disable", "encore", "heal-block", "imprison", "perish-song", "taunt", "throat-chop", "torment"}
PHAZING_MOVES = {"circle-throw", "dragon-tail", "roar", "whirlwind"}
TRAPPING_MOVES = {
    "anchor-shot",
    "block",
    "fire-spin",
    "infestation",
    "jaw-lock",
    "magma-storm",
    "mean-look",
    "sand-tomb",
    "snap-trap",
    "spider-web",
    "spirit-shackle",
    "thousand-waves",
    "whirlpool",
}
ANTI_SETUP_MOVES = {"clear-smog", "haze", "spectral-thief", "topsy-turvy"}
HEALING_SUPPORT_MOVES = {
    "aromatherapy",
    "heal-bell",
    "heal-pulse",
    "healing-wish",
    "jungle-healing",
    "life-dew",
    "lunar-blessing",
    "lunar-dance",
    "pollen-puff",
    "wish",
}
WEATHER_SETTER_ABILITIES = {"drizzle", "drought", "sand stream", "snow warning"}
TERRAIN_SETTER_ABILITIES = {"electric surge", "grassy surge", "misty surge", "psychic surge"}
PIVOT_ABILITIES = {"intimidate", "regenerator"}
SUPPORT_ABILITIES = {"intimidate", "magic bounce", "prankster"}
MEGA_STONE_CONTEXT_ABILITIES = {
    "manectite": ("intimidate",),
}
DEFENSIVE_ABILITY_IMMUNITIES = {
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
TEAM_REDIRECTION_ABILITIES = {
    "electric": ("lightning rod",),
    "water": ("storm drain",),
}
CHOICE_ITEMS = {"choice band", "choice scarf", "choice specs"}
CHOICE_POWER_ITEMS = {"choice band", "choice specs"}
PREVIEW_ATTACKER_ROLES = {
    "physical_sweeper",
    "special_sweeper",
    "setup_sweeper",
    "cleaner",
    "bulky_attacker",
}
PREVIEW_SUPPORT_ROLES = {
    "pivot",
    "bulky_pivot",
    "bulky_support",
    "support",
    "fake_out_support",
    "tailwind_setter",
    "trick_room_setter",
    "screen_setter",
    "weather_setter",
    "terrain_setter",
    "speed_control",
    "healing_support",
    "trapper",
    "redirector",
}
PREVIEW_SETUP_ENABLER_ROLES = {
    "pivot",
    "bulky_pivot",
    "bulky_support",
    "support",
    "fake_out_support",
    "screen_setter",
    "weather_setter",
    "terrain_setter",
    "speed_control",
    "healing_support",
    "redirector",
}
PREVIEW_SETUP_PAYOFF_ROLES = {
    "setup_sweeper",
    "physical_sweeper",
    "special_sweeper",
    "bulky_attacker",
    "cleaner",
}
PREVIEW_PRIMARY_WIN_CONDITIONS = {"perish_trap", "psyspam", "screens_offense"}
DEFENSIVE_ITEMS = {
    "assault vest",
    "black sludge",
    "eviolite",
    "heavy-duty boots",
    "leftovers",
    "rocky helmet",
    "sitrus berry",
}
RECOVERY_ITEMS = {"black sludge", "leftovers"}
NATURE_MODIFIERS = {
    "lonely": ("attack", "defense"),
    "brave": ("attack", "speed"),
    "adamant": ("attack", "special_attack"),
    "naughty": ("attack", "special_defense"),
    "bold": ("defense", "attack"),
    "relaxed": ("defense", "speed"),
    "impish": ("defense", "special_attack"),
    "lax": ("defense", "special_defense"),
    "timid": ("speed", "attack"),
    "hasty": ("speed", "defense"),
    "jolly": ("speed", "special_attack"),
    "naive": ("speed", "special_defense"),
    "modest": ("special_attack", "attack"),
    "mild": ("special_attack", "defense"),
    "quiet": ("special_attack", "speed"),
    "rash": ("special_attack", "special_defense"),
    "calm": ("special_defense", "attack"),
    "gentle": ("special_defense", "defense"),
    "sassy": ("special_defense", "speed"),
    "careful": ("special_defense", "special_attack"),
}
POSITIVE_SPEED_NATURES = {nature for nature, (boosted, _) in NATURE_MODIFIERS.items() if boosted == "speed"}
NEGATIVE_SPEED_NATURES = {nature for nature, (_, lowered) in NATURE_MODIFIERS.items() if lowered == "speed"}
STAT_TO_EV_KEY = {
    "hp": "HP",
    "attack": "Atk",
    "defense": "Def",
    "special_attack": "SpA",
    "special_defense": "SpD",
    "speed": "Spe",
}
STAT_TO_SPECIES_FIELD = {
    "hp": "base_hp",
    "attack": "base_attack",
    "defense": "base_defense",
    "special_attack": "base_special_attack",
    "special_defense": "base_special_defense",
    "speed": "base_speed",
}
TEAM_FIELD_CONTEXTS = {
    "tailwind": {
        "moves": {"tailwind"},
        "abilities": set(),
    },
    "trick_room": {
        "moves": {"trick-room"},
        "abilities": set(),
    },
    "rain": {
        "moves": {"rain-dance"},
        "abilities": {"drizzle"},
    },
    "sun": {
        "moves": {"sunny-day"},
        "abilities": {"drought"},
    },
    "sand": {
        "moves": {"sandstorm"},
        "abilities": {"sand stream"},
    },
    "snow": {
        "moves": {"hail", "snowscape"},
        "abilities": {"snow warning"},
    },
    "electric_terrain": {
        "moves": {"electric-terrain"},
        "abilities": {"electric surge"},
    },
    "grassy_terrain": {
        "moves": {"grassy-terrain"},
        "abilities": {"grassy surge"},
    },
    "misty_terrain": {
        "moves": {"misty-terrain"},
        "abilities": {"misty surge"},
    },
    "psychic_terrain": {
        "moves": {"psychic-terrain"},
        "abilities": {"psychic surge"},
    },
}
SPEED_ABILITY_CONTEXTS = {
    "swift swim": {
        "slug": "rain_swift_swim",
        "label": "Rain + Swift Swim",
        "field": "rain",
        "numerator": 2,
        "denominator": 1,
    },
    "chlorophyll": {
        "slug": "sun_chlorophyll",
        "label": "Sun + Chlorophyll",
        "field": "sun",
        "numerator": 2,
        "denominator": 1,
    },
    "sand rush": {
        "slug": "sand_rush",
        "label": "Sand + Sand Rush",
        "field": "sand",
        "numerator": 2,
        "denominator": 1,
    },
    "slush rush": {
        "slug": "slush_rush",
        "label": "Snow + Slush Rush",
        "field": "snow",
        "numerator": 2,
        "denominator": 1,
    },
    "surge surfer": {
        "slug": "surge_surfer",
        "label": "Electric Terrain + Surge Surfer",
        "field": "electric_terrain",
        "numerator": 2,
        "denominator": 1,
    },
}
UNBURDEN_TERRAIN_ITEMS = {
    "electric seed": "electric_terrain",
    "grassy seed": "grassy_terrain",
    "misty seed": "misty_terrain",
    "psychic seed": "psychic_terrain",
}
UNBURDEN_WHITE_HERB_MOVES = {
    "close-combat",
    "draco-meteor",
    "leaf-storm",
    "make-it-rain",
    "overheat",
    "psycho-boost",
    "superpower",
    "v-create",
}
SUPPORT_UTILITY_ROLES = {
    "anti_setup",
    "healing_support",
    "disruption",
    "entry_hazard",
    "flinch_control",
    "hazard_removal",
    "item_control",
    "other_utility",
    "phazing",
    "pivoting",
    "protection",
    "recovery",
    "redirection",
    "screen",
    "speed_control",
    "stat_drop",
    "status_infliction",
    "terrain",
    "trapping",
    "weather",
}

SPEED_TIER_BOUNDS = (
    ("trick_room_slow", 70),
    ("slow", 99),
    ("midrange", 129),
    ("fast", 159),
    ("very_fast", 179),
)

ARCHETYPE_MATCHUP_BIAS = {
    "hyper_offense": {
        "hyper_offense": -0.2,
        "bulky_offense": -0.5,
        "balance": 0.3,
        "semi_stall": 0.9,
        "stall": 1.2,
        "trick_room": -1.0,
    },
    "bulky_offense": {
        "hyper_offense": 0.4,
        "bulky_offense": 0.0,
        "balance": 0.4,
        "semi_stall": 0.6,
        "stall": 0.6,
        "trick_room": -0.5,
    },
    "balance": {
        "hyper_offense": 0.8,
        "bulky_offense": 0.5,
        "balance": 0.0,
        "semi_stall": -0.1,
        "stall": -0.5,
        "trick_room": -0.7,
    },
    "semi_stall": {
        "hyper_offense": 0.8,
        "bulky_offense": 0.4,
        "balance": 0.2,
        "semi_stall": 0.0,
        "stall": -0.4,
        "trick_room": -0.6,
    },
    "stall": {
        "hyper_offense": 1.0,
        "bulky_offense": 0.5,
        "balance": 0.1,
        "semi_stall": 0.2,
        "stall": 0.0,
        "trick_room": -0.8,
    },
    "trick_room": {
        "hyper_offense": 1.0,
        "bulky_offense": 0.7,
        "balance": 0.2,
        "semi_stall": -0.2,
        "stall": -0.8,
        "trick_room": -0.4,
    },
}


def _has_persistent_trapping(member: TeamMember, ability_name: str, item_name: str) -> bool:
    return ability_name == "shadow tag" or (
        item_name == "gengarite" and member.species_data.api_name == "gengar"
    )

# Calibrated from ChampionsMeta Regulation M-A usage and recent tournament tags,
# where Tailwind offense, weather offense, and hybrid Trick Room shells are the
# most common pressure patterns.
M_A_TAILWIND_PRESSURE_TYPES = {
    "ground": 1.3,
    "water": 1.0,
    "ghost": 1.0,
    "rock": 0.9,
    "dark": 0.8,
    "fighting": 0.8,
    "fire": 0.8,
    "flying": 0.6,
}
M_A_WEATHER_PRESSURE_TYPES = {
    "water": 1.4,
    "ground": 1.1,
    "rock": 1.0,
    "electric": 0.7,
    "steel": 0.5,
}
M_A_TRICK_ROOM_PRESSURE_TYPES = {
    "fire": 1.1,
    "ghost": 1.0,
    "fairy": 0.9,
    "ground": 0.8,
    "dark": 0.7,
    "water": 0.7,
}
# Absolute weighting of the broad Regulation M-A *attacking* field, used to measure how
# exposed a team is to the offense it will actually face (independent of any one mode).
# Unlike the mode-specific pressure dicts above, this is a field-wide threat profile that
# anchors the absolute team-soundness penalty in ``_score_team_field_soundness``.
M_A_FIELD_THREAT_TYPES = {
    "fire": 1.2,
    "fairy": 1.0,
    "ground": 1.0,
    "ice": 1.0,
    "flying": 0.9,
    "water": 0.8,
    "fighting": 0.8,
    "rock": 0.7,
    "ghost": 0.7,
    "dragon": 0.6,
    "dark": 0.6,
}
SLEEP_INDUCING_MOVES = {
    "dark-void",
    "grasswhistle",
    "hypnosis",
    "lovely-kiss",
    "sing",
    "sleep-powder",
    "spore",
    "yawn",
}
FIRE_PRESSURE_SPECIES = {"charizard", "charizard-mega-y", "incineroar", "torkoal", "volcarona"}
RAIN_PRESSURE_SPECIES = {"archaludon", "basculegion", "pelipper", "politoed"}
ROOM_SETTER_SPECIES = {"farigiraf", "hatterene", "indeedee-f", "porygon2"}
HAZARD_PRESSURE_SPECIES = {"glimmora"}
SCREENS_PRESSURE_SPECIES = {"grimmsnarl", "sableye"}
SLEEP_PRESSURE_SPECIES = {"amoonguss", "roserade", "venusaur", "vivillon"}
BULKY_GRASS_PRESSURE_SPECIES = {"abomasnow", "hydrapple", "venusaur", "venusaur-mega"}
ILLUSION_SPECIES = {"zoroark", "zoroark-hisui"}
REDIRECTION_PRESSURE_SPECIES = {"amoonguss", "indeedee-f", "sinistcha"}
SPREAD_PRESSURE_SPECIES = {"blastoise-mega", "charizard-mega-y", "garchomp", "glimmora", "torkoal"}
SPREAD_DAMAGE_TARGET_NAMES = {"all-opponents", "all-other-pokemon", "entire-field"}
SETUP_PRESSURE_CORE_PHRASES = (
    "shell smash",
    "dual screens",
    "screens",
    "calm mind",
    "swords dance",
    "dragon dance",
    "belly drum",
    "nasty plot",
    "quiver dance",
)
SNAPSHOT_ABILITY_CLAUSE_FALLBACKS: dict[str, tuple[str, ...]] = {
    "farigiraf": ("armor tail",),
    "indeedee-f": ("psychic surge",),
}


@dataclass(frozen=True)
class ContextualMatchupProfile:
    species_tokens: set[str]
    move_counts: Counter[str]
    attack_type_counts: Counter[str]
    ability_counts: Counter[str]
    team_mode_packages: tuple[str, ...]
    team_win_condition_labels: tuple[str, ...]
    fast_members: int
    slow_members: int
    bulky_members: int
    frail_members: int
    strong_attackers: int
    weather_setters: int
    terrain_setters: int
    redirection: int
    screens: int
    protective_turns: int
    recovery_loop: int
    hazard_control: int
    priority_attacks: int
    sleep_pressure: int
    setup_pressure: float
    immediate_pressure: float
    water_resistance: int
    fire_resistance: int
    electric_resistance: int
    intimidate_support: int
    priority_block_bypass: int
    fire_exposure: float
    water_exposure: float
    rock_exposure: float
    ground_exposure: float
    flying_exposure: float
    poison_exposure: float
    grass_bias: float
    fighting_bias: float
    psychic_bias: float
    weather_punish_rain: float
    weather_punish_sun: float
    weather_punish_sand: float
    weather_punish_snow: float
    tailwind_counter_tools: float
    trick_room_counter_tools: float
    screen_counter_tools: float
    setup_counter_tools: float
    progress_pressure: float
    disruption_pressure: float
    mindgame_pressure: float
    coverage_gaps: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotTargetMatchupSummary:
    resolved_targets: int
    strong_answer_targets: int
    shaky_answer_targets: int
    fast_cleanup_targets: int
    average_offensive_pressure: float
    average_stab_pressure: float


@dataclass(frozen=True)
class SnapshotInteractionSummary:
    redirection_targets: int
    redirection_answers: int
    setup_pressure_targets: int
    setup_denial_answers: int
    spread_pressure_targets: int
    spread_answers: int
    ability_clause_targets: int
    ability_clause_answers: int
    tags: tuple[str, ...]


def analyze_team_text(
    team_text: str,
    metadata_provider: MetadataProvider | None = None,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> TeamAnalysis:
    return analyze_team(
        parse_showdown_team(team_text),
        metadata_provider=metadata_provider,
        regulation_id=regulation_id,
    )


def analyze_team(
    team: Iterable[PokemonSet],
    metadata_provider: MetadataProvider | None = None,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> TeamAnalysis:
    provider = metadata_provider or CachedPokeApiClient()
    team_sets = list(team)
    if regulation_id is not None:
        legality = validate_team_legality(team_sets, regulation_id=regulation_id)
        if not legality.is_legal:
            raise IllegalTeamError(legality)
    members = _resolve_members(team_sets, provider, regulation_id=regulation_id)
    typing_counts = {type_name: 0 for type_name in TYPE_ORDER}
    offensive_coverage = {type_name: 0 for type_name in TYPE_ORDER}
    attack_type_members: dict[str, set[str]] = {type_name: set() for type_name in TYPE_ORDER}
    defensive_profile: dict[str, dict[str, float | int]] = {}
    utility_role_counts = {role: 0 for role in UTILITY_ROLE_ORDER}
    utility_role_moves = {role: [] for role in UTILITY_ROLE_ORDER}
    pokemon_role_counts = {role: 0 for role in POKEMON_ROLE_ORDER}
    pokemon_role_members = {role: [] for role in POKEMON_ROLE_ORDER}
    member_roles: dict[str, list[str]] = {}

    physical_moves = 0
    special_moves = 0
    utility_moves = 0

    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]] = []

    for member in members:
        for type_name in member.species_data.types:
            typing_counts[type_name] += 1

        classified_moves: list[tuple[MoveData, tuple[str, ...]]] = []
        for move in member.move_data:
            utility_roles = classify_utility_roles(move)
            classified_moves.append((move, utility_roles))
            if utility_roles:
                utility_moves += 1
                for role in utility_roles:
                    utility_role_counts[role] += 1
                    utility_role_moves[role].append(move.name)

            if move.damage_class != "status":
                offensive_coverage[move.type_name] += 1
                attack_type_members[move.type_name].add(member.pokemon_set.display_name)
            if move.damage_class == "physical":
                physical_moves += 1
            elif move.damage_class == "special":
                special_moves += 1

        classified_members.append((member, classified_moves))

    for member, classified_moves in classified_members:
        inferred_roles = infer_pokemon_roles(member, classified_moves)
        display_name = member.pokemon_set.display_name
        member_roles[display_name] = list(inferred_roles)
        for role in inferred_roles:
            pokemon_role_counts[role] += 1
            pokemon_role_members[role].append(display_name)

    target_coverage = _build_target_coverage_profile(offensive_coverage)
    coverage_gaps = _rank_coverage_gaps(target_coverage)
    member_base_speeds = {
        member.pokemon_set.display_name: member.species_data.base_speed for member in members
    }
    coverage_quality = _classify_coverage_quality(target_coverage, attack_type_members, member_base_speeds)

    for attack_type in TYPE_ORDER:
        multipliers = []
        weak_members = 0
        resistant_members = 0
        immune_members = 0

        for member in members:
            multiplier = _defensive_multiplier_for_member(member, attack_type)
            multipliers.append(multiplier)
            if multiplier == 0.0:
                immune_members += 1
            elif multiplier > 1.0:
                weak_members += 1
            elif multiplier < 1.0:
                resistant_members += 1

        average_multiplier = sum(multipliers) / len(multipliers)
        average_multiplier = max(0.0, average_multiplier - _team_redirection_support_bonus(members, attack_type))

        defensive_profile[attack_type] = {
            "average_multiplier": round(average_multiplier, 4),
            "weak_members": weak_members,
            "resistant_members": resistant_members,
            "immune_members": immune_members,
        }

    top_defensive_weaknesses = [
        type_name
        for type_name, _ in sorted(
            defensive_profile.items(),
            key=lambda item: (
                item[1]["average_multiplier"],
                item[1]["weak_members"],
                -item[1]["immune_members"],
            ),
            reverse=True,
        )[:5]
    ]

    member_stats = {
        member.pokemon_set.display_name: _normalized_member_stats(member)
        for member in members
    }
    base_speeds = [(member.pokemon_set.display_name, member.species_data.base_speed) for member in members]
    battle_speeds = [
        (member.pokemon_set.display_name, member_stats[member.pokemon_set.display_name]["speed"])
        for member in members
    ]
    average_base_speed = round(sum(speed for _, speed in base_speeds) / len(base_speeds), 2)
    average_battle_speed = round(sum(speed for _, speed in battle_speeds) / len(battle_speeds), 2)
    median_battle_speed = round(float(median(speed for _, speed in battle_speeds)), 2)
    speed_standard_deviation = round(float(pstdev(speed for _, speed in battle_speeds)), 2)
    fastest = max(base_speeds, key=lambda entry: (entry[1], entry[0]))
    slowest = min(base_speeds, key=lambda entry: (entry[1], entry[0]))
    fastest_battle_speed = max(battle_speeds, key=lambda entry: (entry[1], entry[0]))
    slowest_battle_speed = min(battle_speeds, key=lambda entry: (entry[1], entry[0]))
    member_base_speeds = {member_name: speed for member_name, speed in base_speeds}
    member_battle_speeds = {member_name: speed for member_name, speed in battle_speeds}
    member_speed_tiers = {
        member_name: _speed_tier_for_stat(speed)
        for member_name, speed in member_battle_speeds.items()
    }
    speed_tier_members = {tier: [] for tier in SPEED_TIER_ORDER}
    for member_name, _ in base_speeds:
        speed_tier_members[member_speed_tiers[member_name]].append(member_name)
    speed_tier_counts = {
        tier: len(speed_tier_members[tier])
        for tier in SPEED_TIER_ORDER
    }
    team_speed_tier = _team_speed_tier(
        [speed for _, speed in battle_speeds],
        speed_tier_counts,
    )
    speed_benchmark_catalog, speed_benchmark_notes, speed_benchmark_groups, member_speed_benchmark_tags = _evaluate_speed_benchmarks(
        members,
        member_battle_speeds,
        regulation_id,
    )
    member_speed_contexts = _build_member_speed_contexts(members, member_battle_speeds)
    speed_benchmark_notes = _expand_speed_benchmark_notes(
        speed_benchmark_notes,
        team_speed_tier,
        member_battle_speeds,
        member_speed_tiers,
        speed_tier_counts,
        speed_benchmark_groups,
        member_speed_contexts,
    )
    damage_split = {"physical": physical_moves, "special": special_moves}
    primary_team_archetype, team_archetype_scores = infer_team_archetype(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
    )
    (
        primary_team_style,
        team_style_scores,
        team_mode_packages,
        team_mode_package_scores,
        team_win_condition_labels,
        team_win_condition_scores,
    ) = infer_team_packages(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
        team_archetype_scores,
    )
    contextual_matchup_profile = _build_contextual_matchup_profile(
        members,
        pokemon_role_counts,
        utility_role_counts,
        team_mode_packages,
        team_win_condition_labels,
        offensive_coverage,
        defensive_profile,
        top_defensive_weaknesses,
        coverage_gaps,
    )
    matchup_scores, matchup_details, favorable_matchups, unfavorable_matchups = infer_matchup_profile(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
        offensive_coverage,
        defensive_profile,
        top_defensive_weaknesses,
        team_archetype_scores,
        contextual_matchup_profile,
    )
    team_mode_scores, team_mode_labels, mode_matchup_scores, favorable_modes, unfavorable_modes = infer_meta_mode_profile(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
        offensive_coverage,
        defensive_profile,
        top_defensive_weaknesses,
        team_archetype_scores,
        matchup_scores,
    )
    field_soundness, field_soundness_reasons = _score_team_field_soundness(
        defensive_profile,
        top_defensive_weaknesses,
        offensive_coverage,
        pokemon_role_counts,
        utility_role_counts,
        contextual_matchup_profile,
    )
    meta_analysis = infer_meta_analysis(
        members,
        team_mode_scores,
        team_mode_labels,
        mode_matchup_scores,
        matchup_scores,
        favorable_modes,
        unfavorable_modes,
        contextual_matchup_profile,
        provider,
        regulation_id=regulation_id,
        field_soundness=field_soundness,
        field_soundness_reasons=field_soundness_reasons,
    )
    team_difficulty_label, team_difficulty_score, team_difficulty_factors = infer_team_difficulty(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
        primary_team_archetype,
    )
    beginner_guidance_notes = infer_beginner_guidance(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
        primary_team_archetype,
        team_speed_tier,
        coverage_gaps,
        team_win_condition_labels,
    )
    speed_benchmark_notes = _augment_speed_benchmark_notes_with_meta_context(
        speed_benchmark_notes,
        meta_analysis,
        team_speed_tier,
        team_mode_packages,
    )
    team_difficulty_factors, beginner_guidance_notes = _augment_team_notes_with_meta_context(
        team_difficulty_factors,
        beginner_guidance_notes,
        meta_analysis,
    )
    (
        team_preview_plans,
        team_preview_watch_teams,
        team_preview_watch_pokemon,
        team_preview_strategy_notes,
        team_preview_counterplay_notes,
    ) = infer_team_preview(
        members,
        member_roles,
        member_battle_speeds,
        member_speed_tiers,
        primary_team_style,
        team_mode_packages,
        team_win_condition_labels,
        unfavorable_matchups,
        unfavorable_modes,
        top_defensive_weaknesses,
        pokemon_role_counts,
        utility_role_counts,
        meta_analysis,
    )

    vector_labels: list[str] = []
    vector: list[float] = []

    for type_name in TYPE_ORDER:
        vector_labels.append(f"typing_{type_name}")
        vector.append(float(typing_counts[type_name]))

    for type_name in TYPE_ORDER:
        vector_labels.append(f"defense_avg_multiplier_{type_name}")
        vector.append(float(defensive_profile[type_name]["average_multiplier"]))

    for type_name in TYPE_ORDER:
        vector_labels.append(f"offense_{type_name}")
        vector.append(float(offensive_coverage[type_name]))

    vector_labels.extend(
        [
            "average_base_speed",
            "fastest_base_speed",
            "slowest_base_speed",
            "physical_moves",
            "special_moves",
            "utility_moves",
        ]
    )
    vector.extend(
        [
            average_base_speed,
            float(fastest[1]),
            float(slowest[1]),
            float(physical_moves),
            float(special_moves),
            float(utility_moves),
        ]
    )

    for role in UTILITY_ROLE_ORDER:
        vector_labels.append(f"utility_role_{role}")
        vector.append(float(utility_role_counts[role]))

    for role in POKEMON_ROLE_ORDER:
        vector_labels.append(f"pokemon_role_{role}")
        vector.append(float(pokemon_role_counts[role]))

    for archetype in TEAM_ARCHETYPE_ORDER:
        vector_labels.append(f"team_archetype_{archetype}")
        vector.append(float(team_archetype_scores[archetype]))

    damage_matchups = _build_damage_matchups(members, provider)
    try:
        speed_coverage = _build_speed_coverage(members, member_battle_speeds, provider, regulation_id)
    except Exception:  # pragma: no cover - defensive: coverage is non-essential
        speed_coverage = {"available": False, "sample_species": 0, "members": [], "note": ""}

    plain_summary = build_plain_language_summary(
        archetype=primary_team_archetype,
        style=primary_team_style,
        mode_labels=team_mode_packages,
        win_condition_labels=team_win_condition_labels,
        speed_tier=team_speed_tier,
        favorable_matchups=favorable_matchups,
        unfavorable_matchups=unfavorable_matchups,
        unfavorable_modes=unfavorable_modes,
        top_defensive_weaknesses=top_defensive_weaknesses,
        difficulty_label=team_difficulty_label,
        difficulty_score=team_difficulty_score,
    )

    return TeamAnalysis(
        regulation_id=regulation_id,
        team_size=len(members),
        typing_counts=typing_counts,
        defensive_profile=defensive_profile,
        offensive_coverage=offensive_coverage,
        target_coverage=target_coverage,
        coverage_gaps=coverage_gaps,
        coverage_quality=coverage_quality,
        average_base_speed=average_base_speed,
        average_battle_speed=average_battle_speed,
        median_battle_speed=median_battle_speed,
        speed_standard_deviation=speed_standard_deviation,
        team_speed_tier=team_speed_tier,
        fastest_pokemon=fastest,
        slowest_pokemon=slowest,
        fastest_battle_speed_pokemon=fastest_battle_speed,
        slowest_battle_speed_pokemon=slowest_battle_speed,
        member_base_speeds=member_base_speeds,
        member_battle_speeds=member_battle_speeds,
        member_stats=member_stats,
        member_speed_tiers=member_speed_tiers,
        speed_tier_counts=speed_tier_counts,
        speed_tier_members=speed_tier_members,
        speed_benchmark_catalog=speed_benchmark_catalog,
        speed_benchmark_notes=speed_benchmark_notes,
        speed_benchmark_groups=speed_benchmark_groups,
        member_speed_benchmark_tags=member_speed_benchmark_tags,
        member_speed_contexts=member_speed_contexts,
        damage_split=damage_split,
        damage_matchups=damage_matchups,
        speed_coverage=speed_coverage,
        plain_summary=plain_summary,
        utility_moves=utility_moves,
        utility_role_counts=utility_role_counts,
        utility_role_moves=utility_role_moves,
        pokemon_role_counts=pokemon_role_counts,
        pokemon_role_members=pokemon_role_members,
        member_roles=member_roles,
        primary_team_archetype=primary_team_archetype,
        team_archetype_scores=team_archetype_scores,
        primary_team_style=primary_team_style,
        team_style_scores=team_style_scores,
        team_mode_packages=team_mode_packages,
        team_mode_package_scores=team_mode_package_scores,
        team_win_condition_labels=team_win_condition_labels,
        team_win_condition_scores=team_win_condition_scores,
        matchup_scores=matchup_scores,
        matchup_details=matchup_details,
        favorable_matchups=favorable_matchups,
        unfavorable_matchups=unfavorable_matchups,
        team_mode_scores=team_mode_scores,
        team_mode_labels=team_mode_labels,
        mode_matchup_scores=mode_matchup_scores,
        favorable_modes=favorable_modes,
        unfavorable_modes=unfavorable_modes,
        team_difficulty_label=team_difficulty_label,
        team_difficulty_score=team_difficulty_score,
        beginner_guidance_notes=beginner_guidance_notes,
        team_difficulty_factors=team_difficulty_factors,
        team_preview_plans=team_preview_plans,
        team_preview_watch_teams=team_preview_watch_teams,
        team_preview_watch_pokemon=team_preview_watch_pokemon,
        team_preview_strategy_notes=team_preview_strategy_notes,
        team_preview_counterplay_notes=team_preview_counterplay_notes,
        meta_analysis=meta_analysis,
        top_defensive_weaknesses=top_defensive_weaknesses,
        vector_labels=vector_labels,
        vector=vector,
    )


def _member_context_ability_names(member: TeamMember) -> tuple[str, ...]:
    ability_names: list[str] = []

    ability_name = _normalized_ability_name(member.pokemon_set.ability)
    if ability_name:
        ability_names.append(ability_name)

    item_name = _normalized_item_name(member.pokemon_set.item)
    for extra_ability in MEGA_STONE_CONTEXT_ABILITIES.get(item_name, ()): 
        if extra_ability not in ability_names:
            ability_names.append(extra_ability)

    return tuple(ability_names)


def _defensive_multiplier_for_member(member: TeamMember, attack_type: str) -> float:
    multiplier = defensive_multiplier(member.species_data.types, attack_type)
    immunity_types = DEFENSIVE_ABILITY_IMMUNITIES.get(_normalized_ability_name(member.pokemon_set.ability), ())
    if attack_type in immunity_types:
        return 0.0
    return multiplier


def _team_redirection_support_bonus(members: list[TeamMember], attack_type: str) -> float:
    redirect_abilities = TEAM_REDIRECTION_ABILITIES.get(attack_type, ())
    if not redirect_abilities:
        return 0.0

    redirectors = sum(
        1
        for member in members
        if _normalized_ability_name(member.pokemon_set.ability) in redirect_abilities
    )
    if redirectors == 0:
        return 0.0

    weak_members = sum(1 for member in members if _defensive_multiplier_for_member(member, attack_type) > 1.0)
    return min(0.75, 0.32 * redirectors + 0.15 * weak_members)


def _build_target_coverage_profile(offensive_coverage: dict[str, int]) -> dict[str, dict[str, float | int]]:
    profile: dict[str, dict[str, float | int]] = {}

    for defending_type in TYPE_ORDER:
        best_multiplier = 0.0
        super_effective_lines = 0
        neutral_or_better_lines = 0
        resisted_lines = 0
        immune_lines = 0

        for attack_type, attack_count in offensive_coverage.items():
            if attack_count <= 0:
                continue

            multiplier = defensive_multiplier((defending_type,), attack_type)
            best_multiplier = max(best_multiplier, multiplier)

            if multiplier > 1.0:
                super_effective_lines += attack_count
                neutral_or_better_lines += attack_count
            elif multiplier == 1.0:
                neutral_or_better_lines += attack_count
            elif multiplier == 0.0:
                immune_lines += attack_count
            else:
                resisted_lines += attack_count

        profile[defending_type] = {
            "best_multiplier": round(best_multiplier, 2),
            "super_effective_lines": super_effective_lines,
            "neutral_or_better_lines": neutral_or_better_lines,
            "resisted_lines": resisted_lines,
            "immune_lines": immune_lines,
        }

    return profile


def _rank_coverage_gaps(target_coverage: dict[str, dict[str, float | int]], limit: int = 5) -> list[str]:
    ranked = sorted(
        target_coverage.items(),
        key=lambda item: (
            float(item[1]["best_multiplier"]),
            int(item[1]["super_effective_lines"]),
            int(item[1]["neutral_or_better_lines"]),
            -int(item[1]["immune_lines"]),
            item[0],
        ),
    )
    return [type_name for type_name, _ in ranked[:limit]]


# How a defending type's offensive coverage reads once you account for reliability, not just
# presence. A type with a super-effective answer is never a "hard gap"; it may still be thin,
# carried by a single Pokemon, or only reachable through slow/awkward attackers.
COVERAGE_QUALITY_SLOW_SPEED = 60


def _classify_coverage_quality(
    target_coverage: dict[str, dict[str, float | int]],
    attack_type_members: dict[str, set[str]],
    member_base_speeds: dict[str, int],
    limit: int = 5,
) -> list[dict[str, object]]:
    """Classify the team's weakest offensive coverage by *reliability* rather than absence.

    Mirrors GPT feedback #6: ``hard_gap`` (no super-effective pressure), ``thin`` (one narrow
    line), ``centralized`` (a single Pokemon carries the answer), and ``positioning_dependent``
    (an answer exists but only from slow attackers). Anything better is dropped from the list.
    """
    ranked = sorted(
        target_coverage.items(),
        key=lambda item: (
            float(item[1]["best_multiplier"]),
            int(item[1]["super_effective_lines"]),
            int(item[1]["neutral_or_better_lines"]),
            -int(item[1]["immune_lines"]),
            item[0],
        ),
    )
    flagged: list[dict[str, object]] = []
    for defending_type, profile in ranked:
        super_effective_lines = int(profile["super_effective_lines"])
        contributors: set[str] = set()
        for attack_type, holders in attack_type_members.items():
            if holders and defensive_multiplier((defending_type,), attack_type) > 1.0:
                contributors |= holders

        if super_effective_lines <= 0:
            quality = "hard_gap"
        elif super_effective_lines == 1:
            quality = "thin"
        elif len(contributors) <= 1:
            quality = "centralized"
        elif contributors and all(
            member_base_speeds.get(name, 0) <= COVERAGE_QUALITY_SLOW_SPEED for name in contributors
        ):
            quality = "positioning_dependent"
        else:
            quality = "covered"

        if quality == "covered":
            continue
        flagged.append(
            {
                "type": defending_type,
                "quality": quality,
                "super_effective_lines": super_effective_lines,
                "best_multiplier": float(profile["best_multiplier"]),
                "contributors": sorted(contributors),
            }
        )
        if len(flagged) >= limit:
            break
    return flagged


def _normalized_battle_speed(member: TeamMember) -> int:
    return _normalized_member_stats(member)["speed"]


def _combatant_from_member(member: TeamMember) -> Combatant:
    stats = _normalized_member_stats(member)
    return Combatant(
        species=member.pokemon_set.display_name,
        types=member.species_data.types,
        hp=stats["hp"],
        attack=stats["attack"],
        defense=stats["defense"],
        special_attack=stats["special_attack"],
        special_defense=stats["special_defense"],
        ability=member.pokemon_set.ability,
        item=member.pokemon_set.item,
    )


def _build_damage_matchups(members: list[TeamMember], provider: MetadataProvider) -> dict[str, object]:
    """Curated OHKO/2HKO grid; resilient so benchmark data issues never break analysis."""
    try:
        team = [(_combatant_from_member(member), member.move_data) for member in members]
        return build_damage_matchups(team, provider)
    except Exception:  # pragma: no cover - defensive: grid is non-essential
        return {"outgoing": [], "incoming": [], "benchmark_walls": [], "benchmark_attackers": [], "notes": []}


def _speed_coverage_share(
    meta_speeds: list[tuple[int, float]],
    my_speed: int,
    total: float,
    *,
    faster_wins: bool,
) -> float:
    """Usage-weighted share of the meta this speed moves before.

    ``faster_wins`` is True for +0/Tailwind (you win by being faster) and False under
    Trick Room (you win by being slower). Speed ties split the share 50/50.
    """
    value = 0.0
    for assumed_speed, share in meta_speeds:
        if my_speed == assumed_speed:
            value += 0.5 * share
        elif (my_speed > assumed_speed) == faster_wins:
            value += share
    return round(100 * value / total, 1) if total else 0.0


def _build_speed_coverage(
    members: list[TeamMember],
    member_battle_speeds: dict[str, int],
    provider: MetadataProvider,
    regulation_id: str | None,
) -> dict[str, object]:
    """Per-member usage-weighted outspeed coverage at +0, under Tailwind, and under Trick Room."""
    note = (
        "Each common meta Pokemon is weighted by usage share and assumed to run a max-speed "
        "set, so the +0 and Tailwind figures are conservative."
    )
    try:
        common = _build_common_meta_pokemon(regulation_id)
    except Exception:  # pragma: no cover - defensive
        common = []

    resolved_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    meta_speeds: list[tuple[int, float]] = []
    sampled: list[str] = []
    for row in common:
        species_name = str(row.get("species", ""))
        share = float(row.get("meta_share", 0.0) or 0.0)
        if not species_name or share <= 0:
            continue
        try:
            canonical = resolve_regulation_species_name(species_name, regulation_id=resolved_regulation_id) or species_name
            species = provider.get_species(canonical)
        except (KeyError, LookupError, ConnectionError):
            continue
        assumed_speed = compute_stat(species.base_speed, CHAMPIONS_MAX_STAT_SPS, nature=1)
        meta_speeds.append((assumed_speed, share))
        sampled.append(species_name)

    total = sum(share for _, share in meta_speeds)
    if not meta_speeds or total <= 0:
        return {"available": False, "sample_species": 0, "members": [], "note": note}

    members_out = [
        {
            "pokemon": member.pokemon_set.display_name,
            "battle_speed": member_battle_speeds[member.pokemon_set.display_name],
            "natural_pct": _speed_coverage_share(
                meta_speeds, member_battle_speeds[member.pokemon_set.display_name], total, faster_wins=True
            ),
            "tailwind_pct": _speed_coverage_share(
                meta_speeds, member_battle_speeds[member.pokemon_set.display_name] * 2, total, faster_wins=True
            ),
            "trick_room_pct": _speed_coverage_share(
                meta_speeds, member_battle_speeds[member.pokemon_set.display_name], total, faster_wins=False
            ),
        }
        for member in members
    ]

    return {
        "available": True,
        "weighted": True,
        "sample_species": len(meta_speeds),
        "sampled_pokemon": sampled,
        "contexts": ["natural", "tailwind", "trick_room"],
        "members": members_out,
        "note": note,
    }


def _normalized_member_stats(member: TeamMember) -> dict[str, int]:
    nature = member.pokemon_set.nature
    evs = member.pokemon_set.evs
    species = member.species_data
    return {
        "hp": compute_stat(species.base_hp, evs.get("HP", 0), is_hp=True),
        "attack": compute_stat(
            species.base_attack,
            evs.get("Atk", 0),
            nature=_nature_direction(nature, "attack"),
        ),
        "defense": compute_stat(
            species.base_defense,
            evs.get("Def", 0),
            nature=_nature_direction(nature, "defense"),
        ),
        "special_attack": compute_stat(
            species.base_special_attack,
            evs.get("SpA", 0),
            nature=_nature_direction(nature, "special_attack"),
        ),
        "special_defense": compute_stat(
            species.base_special_defense,
            evs.get("SpD", 0),
            nature=_nature_direction(nature, "special_defense"),
        ),
        "speed": compute_stat(
            species.base_speed,
            evs.get("Spe", 0),
            nature=_nature_direction(nature, "speed"),
        ),
    }


def _normalized_hp_stat(base_stat: int, ev: int, *, level: int = 50) -> int:
    return compute_stat(base_stat, ev, is_hp=True, level=level)


def _normalized_non_hp_stat(base_stat: int, ev: int, *, level: int = 50, nature: int = 0) -> int:
    return compute_stat(base_stat, ev, nature=nature, level=level)


def _nature_direction(nature: str | None, stat_name: str) -> int:
    normalized_nature = (nature or "").strip().lower()
    if normalized_nature not in NATURE_MODIFIERS:
        return 0
    boosted_stat, lowered_stat = NATURE_MODIFIERS[normalized_nature]
    if stat_name == boosted_stat:
        return 1
    if stat_name == lowered_stat:
        return -1
    return 0


def _speed_nature_multiplier(nature: str | None) -> float:
    normalized_nature = (nature or "").strip().lower()
    if normalized_nature in POSITIVE_SPEED_NATURES:
        return 1.1
    if normalized_nature in NEGATIVE_SPEED_NATURES:
        return 0.9
    return 1.0


def _speed_tier_for_stat(speed_stat: int) -> str:
    for tier_name, upper_bound in SPEED_TIER_BOUNDS:
        if speed_stat <= upper_bound:
            return tier_name
    return "elite_fast"


def _team_speed_tier(member_speeds: list[int], speed_tier_counts: dict[str, int]) -> str:
    if not member_speeds:
        return "midrange"

    average_speed = sum(member_speeds) / len(member_speeds)
    speed_range = max(member_speeds) - min(member_speeds)
    slow_members = speed_tier_counts["trick_room_slow"] + speed_tier_counts["slow"]
    fast_members = speed_tier_counts["fast"] + speed_tier_counts["very_fast"] + speed_tier_counts["elite_fast"]
    very_fast_members = speed_tier_counts["very_fast"] + speed_tier_counts["elite_fast"]

    if slow_members >= 2 and fast_members >= 2 and speed_range >= 60:
        return "mixed"
    if speed_tier_counts["trick_room_slow"] >= 2 and average_speed <= 90:
        return "trick_room_slow"
    if very_fast_members >= 3 and average_speed >= 150:
        return "very_fast"
    if fast_members >= 3 and average_speed >= 125:
        return "fast"
    if slow_members >= 3 and average_speed <= 100:
        return "slow"
    return "midrange"


def _evaluate_speed_benchmarks(
    members: list[TeamMember],
    member_battle_speeds: dict[str, int],
    regulation_id: str | None,
) -> tuple[dict[str, str] | None, list[str], dict[str, dict[str, object]], dict[str, list[dict[str, object]]]]:
    benchmark_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    catalog = get_speed_benchmark_catalog(benchmark_regulation_id)
    if catalog is None:
        if regulation_id is None:
            return None, [], {}, {}
        return (
            {"regulation_id": regulation_id, "display_name": regulation_id},
            ["No curated speed benchmark table is defined for this regulation yet."],
            {},
            {},
        )

    natural_context = dict(member_battle_speeds)
    tailwind_context = _tailwind_context_speeds(members, member_battle_speeds)
    choice_scarf_context = _choice_scarf_context_speeds(members, member_battle_speeds)
    trick_room_context = _trick_room_context_speeds(members, member_battle_speeds)
    contexts = {
        "natural": natural_context,
        "tailwind": tailwind_context,
        "choice_scarf": choice_scarf_context,
        "trick_room": trick_room_context,
    }

    group_payloads: dict[str, dict[str, object]] = {}
    member_tags = {member_name: [] for member_name in member_battle_speeds}
    notes: list[str] = []
    for group in catalog.groups:
        context_speeds = contexts[group.slug]
        group_payload, group_member_tags = _evaluate_speed_benchmark_group(group, context_speeds)
        group_payloads[group.slug] = group_payload
        for member_name, tags in group_member_tags.items():
            member_tags.setdefault(member_name, []).extend(tags)
        note = _summarize_speed_benchmark_group(group, group_payload)
        if note:
            notes.append(note)

    return (
        {
            "regulation_id": catalog.regulation_id,
            "display_name": catalog.display_name,
            "notes": catalog.notes,
        },
        notes,
        group_payloads,
        member_tags,
    )


def _tailwind_context_speeds(
    members: list[TeamMember],
    member_battle_speeds: dict[str, int],
) -> dict[str, int]:
    if not any(move.api_name == "tailwind" for member in members for move in member.move_data):
        return {}
    return {
        member_name: speed * 2
        for member_name, speed in member_battle_speeds.items()
    }


def _choice_scarf_context_speeds(
    members: list[TeamMember],
    member_battle_speeds: dict[str, int],
) -> dict[str, int]:
    scarf_speeds: dict[str, int] = {}
    for member in members:
        if (member.pokemon_set.item or "").strip().lower() != "choice scarf":
            continue
        member_name = member.pokemon_set.display_name
        scarf_speeds[member_name] = member_battle_speeds[member_name] * 3 // 2
    return scarf_speeds


def _trick_room_context_speeds(
    members: list[TeamMember],
    member_battle_speeds: dict[str, int],
) -> dict[str, int]:
    if not any(move.api_name == "trick-room" for member in members for move in member.move_data):
        return {}
    return dict(member_battle_speeds)


def _build_member_speed_contexts(
    members: list[TeamMember],
    member_battle_speeds: dict[str, int],
) -> dict[str, list[dict[str, object]]]:
    available_fields = _available_team_field_contexts(members)
    member_contexts: dict[str, list[dict[str, object]]] = {}

    for member in members:
        member_name = member.pokemon_set.display_name
        modifiers: list[tuple[str, str, int, int]] = []

        if "tailwind" in available_fields:
            modifiers.append(("tailwind", "Tailwind", 2, 1))

        if _normalized_item_name(member.pokemon_set.item) == "choice scarf":
            modifiers.append(("choice_scarf", "Choice Scarf", 3, 2))

        ability_modifier = _speed_ability_modifier(member, available_fields)
        if ability_modifier is not None:
            modifiers.append(ability_modifier)

        contexts: list[dict[str, object]] = []
        for modifier_count in range(1, len(modifiers) + 1):
            for combo in combinations(modifiers, modifier_count):
                speed = member_battle_speeds[member_name]
                for _, _, numerator, denominator in combo:
                    speed = speed * numerator // denominator
                if speed <= member_battle_speeds[member_name]:
                    continue
                contexts.append(
                    {
                        "slug": "_".join(modifier[0] for modifier in combo),
                        "label": " + ".join(modifier[1] for modifier in combo),
                        "speed": speed,
                    }
                )

        member_contexts[member_name] = sorted(
            contexts,
            key=lambda context: (cast(int, context["speed"]), cast(str, context["label"])),
            reverse=True,
        )

    return member_contexts


def _available_team_field_contexts(members: list[TeamMember]) -> set[str]:
    available_contexts: set[str] = set()
    present_moves = {move.api_name for member in members for move in member.move_data}
    present_abilities = {
        _normalized_ability_name(member.pokemon_set.ability)
        for member in members
        if _normalized_ability_name(member.pokemon_set.ability)
    }

    for context_name, signals in TEAM_FIELD_CONTEXTS.items():
        if present_moves.intersection(signals["moves"]) or present_abilities.intersection(signals["abilities"]):
            available_contexts.add(context_name)

    return available_contexts


def _speed_ability_modifier(
    member: TeamMember,
    available_fields: set[str],
) -> tuple[str, str, int, int] | None:
    ability_name = _normalized_ability_name(member.pokemon_set.ability)
    if ability_name in SPEED_ABILITY_CONTEXTS:
        context = SPEED_ABILITY_CONTEXTS[ability_name]
        if context["field"] in available_fields:
            return (
                cast(str, context["slug"]),
                cast(str, context["label"]),
                cast(int, context["numerator"]),
                cast(int, context["denominator"]),
            )

    if ability_name == "unburden":
        terrain_seed_context = UNBURDEN_TERRAIN_ITEMS.get(_normalized_item_name(member.pokemon_set.item))
        if terrain_seed_context and terrain_seed_context in available_fields:
            return ("unburden", "Unburden", 2, 1)
        if _normalized_item_name(member.pokemon_set.item) == "white herb" and any(
            move.api_name in UNBURDEN_WHITE_HERB_MOVES for move in member.move_data
        ):
            return ("unburden", "Unburden", 2, 1)

    return None


def _evaluate_speed_benchmark_group(
    group: SpeedBenchmarkGroup,
    context_speeds: dict[str, int],
) -> tuple[dict[str, object], dict[str, list[dict[str, object]]]]:
    if context_speeds:
        comparator = min if group.comparison == "slower" else max
        best_member_name, best_speed = comparator(context_speeds.items(), key=lambda item: (item[1], item[0]))
    else:
        best_member_name = None
        best_speed = None

    ordered_context_speeds = _sorted_context_speeds(group, context_speeds)
    member_tags = {member_name: [] for member_name in context_speeds}
    benchmarks: list[dict[str, object]] = []
    for benchmark in group.benchmarks:
        hit_members = [
            member_name
            for member_name, speed in ordered_context_speeds
            if _benchmark_status(group, speed, benchmark.target_speed) in {_success_status(group), "tie"}
        ]
        tied = [
            member_name
            for member_name, speed in ordered_context_speeds
            if speed == benchmark.target_speed
        ]
        status = "miss"
        if hit_members:
            status = _success_status(group)
        if tied:
            status = "tie"

        for member_name, speed in ordered_context_speeds:
            member_status = _benchmark_status(group, speed, benchmark.target_speed)
            if member_status == "miss":
                continue
            member_tags[member_name].append(
                {
                    "group": group.slug,
                    "group_label": group.label,
                    "comparison": group.comparison,
                    "benchmark_slug": benchmark.slug,
                    "benchmark_label": benchmark.label,
                    "target_speed": benchmark.target_speed,
                    "status": member_status,
                    "context_speed": speed,
                }
            )

        benchmarks.append(
            {
                "slug": benchmark.slug,
                "label": benchmark.label,
                "target_speed": benchmark.target_speed,
                "source": benchmark.source,
                "comparison": group.comparison,
                "status": status,
                "hit_members": hit_members,
                "tie_members": tied,
            }
        )

    return (
        {
            "label": group.label,
            "comparison": group.comparison,
            "available": bool(context_speeds),
            "best_member": best_member_name,
            "best_speed": best_speed,
            "benchmarks": benchmarks,
        },
        member_tags,
    )


def _summarize_speed_benchmark_group(group: SpeedBenchmarkGroup, group_payload: dict[str, object]) -> str | None:
    available = bool(group_payload["available"])
    label = str(group_payload["label"])
    best_member = group_payload["best_member"]
    best_speed = group_payload["best_speed"]
    benchmarks = cast(list[dict[str, object]], group_payload["benchmarks"])

    if not available:
        if group.slug == "tailwind":
            return "Tailwind Speed: the team has no Tailwind move, so it cannot create its own doubled-Speed mode."
        if group.slug == "choice_scarf":
            return "Choice Scarf Speed: no Choice Scarf holder is present, so the team has no item-based emergency speed line."
        if group.slug == "trick_room":
            return "Trick Room underspeed: the team has no Trick Room setter, so it cannot create its own slower-first mode."
        return None

    reached = [benchmark for benchmark in benchmarks if benchmark["status"] in {_success_status(group), "tie"}]
    missed = [benchmark for benchmark in benchmarks if benchmark["status"] == "miss"]
    reached_selector = min if group.comparison == "slower" else max
    missed_selector = max if group.comparison == "slower" else min
    hardest_reached = reached_selector(reached, key=lambda benchmark: cast(int, benchmark["target_speed"]), default=None)
    next_miss = missed_selector(missed, key=lambda benchmark: cast(int, benchmark["target_speed"]), default=None)

    best_speed_value = cast(int, best_speed)
    if group.slug == "natural":
        line_phrase = "fastest unboosted line"
    elif group.slug == "tailwind":
        line_phrase = "fastest Tailwind line"
    elif group.slug == "choice_scarf":
        line_phrase = "best Choice Scarf line"
    else:
        line_phrase = "slowest Trick Room-ready line"

    if hardest_reached is None and next_miss is not None:
        if group.comparison == "slower":
            return (
                f"{label}: {best_member} is your {line_phrase} at {best_speed_value}. "
                f"That is still faster than {next_miss['label']} ({next_miss['target_speed']}), so this mode does not yet win any current slower-than reference points."
            )
        return (
            f"{label}: {best_member} is your {line_phrase} at {best_speed_value}. "
            f"That is still below {next_miss['label']} ({next_miss['target_speed']}), so this mode does not clear any current curated benchmark."
        )

    qualifying_members = cast(list[str], hardest_reached["hit_members"]) if hardest_reached is not None else []
    members_phrase = _render_series(qualifying_members)

    if hardest_reached is not None and next_miss is not None:
        reached_status = _benchmark_status(group, best_speed_value, cast(int, hardest_reached["target_speed"]))
        if group.comparison == "slower":
            relation = "ties" if reached_status == "tie" else "is slower than"
            uncovered_phrase = f"it is still faster than {next_miss['label']} ({next_miss['target_speed']})"
            member_suffix = f" Members at that mark or slower: {members_phrase}." if members_phrase else ""
        else:
            relation = "ties" if reached_status == "tie" else "outruns"
            uncovered_phrase = f"the next uncovered mark is {next_miss['label']} at {next_miss['target_speed']}"
            member_suffix = f" Members at that mark or faster: {members_phrase}." if members_phrase else ""
        return (
            f"{label}: {best_member} is your {line_phrase} at {best_speed_value}. "
            f"That {relation} {hardest_reached['label']} ({hardest_reached['target_speed']}); {uncovered_phrase}."
            f"{member_suffix}"
        )

    if hardest_reached is not None:
        reached_status = _benchmark_status(group, best_speed_value, cast(int, hardest_reached["target_speed"]))
        if group.comparison == "slower":
            relation = "ties" if reached_status == "tie" else "is slower than"
            direction_phrase = "down through"
            member_suffix = f" Members at that mark or slower: {members_phrase}." if members_phrase else ""
        else:
            relation = "ties" if reached_status == "tie" else "outruns"
            direction_phrase = "up through"
            member_suffix = f" Members at that mark or faster: {members_phrase}." if members_phrase else ""
        return (
            f"{label}: {best_member} is your {line_phrase} at {best_speed_value}. "
            f"That {relation} every current curated benchmark in this group, {direction_phrase} "
            f"{hardest_reached['label']} ({hardest_reached['target_speed']})."
            f"{member_suffix}"
        )
    return None


def _benchmark_members_for_group(group_payload: dict[str, object]) -> list[str]:
    members: set[str] = set()
    for benchmark in cast(list[dict[str, object]], group_payload.get("benchmarks", [])):
        members.update(cast(list[str], benchmark.get("hit_members", [])))
    return sorted(members)


def _summarize_team_speed_shape_note(
    team_speed_tier: str,
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    speed_tier_counts: dict[str, int],
) -> str | None:
    if not member_battle_speeds:
        return None

    fastest_member, fastest_speed = max(member_battle_speeds.items(), key=lambda item: (item[1], item[0]))
    slowest_member, slowest_speed = min(member_battle_speeds.items(), key=lambda item: (item[1], item[0]))
    fast_members = speed_tier_counts["fast"] + speed_tier_counts["very_fast"] + speed_tier_counts["elite_fast"]
    slow_members = speed_tier_counts["trick_room_slow"] + speed_tier_counts["slow"]

    if team_speed_tier == "mixed":
        summary = (
            f"The roster has {fast_members} fast member{'s' if fast_members != 1 else ''} and {slow_members} slow member{'s' if slow_members != 1 else ''}, "
            "so preview planning matters more than on a one-speed team."
        )
    elif team_speed_tier == "trick_room_slow":
        summary = (
            f"The roster is heavily slow leaning, with {slow_members} member{'s' if slow_members != 1 else ''} already in the lower speed bands."
        )
    elif team_speed_tier == "slow":
        summary = "Most of the roster is naturally slow, so it usually wants control tools instead of pure speed races."
    elif team_speed_tier == "fast":
        summary = "Most of the roster already lives in the fast bands, so it can pressure mid-speed teams without much extra help."
    elif team_speed_tier == "very_fast":
        summary = "The roster is built to race immediately, with several members already sitting in the very fast bands."
    else:
        summary = "Most members sit in the middle speed bands, so support and positioning often decide who actually moves first."

    return (
        f"Team speed shape: {summary} Raw battle Speed runs from {slowest_member} at {slowest_speed} "
        f"({_render_mode_label(member_speed_tiers[slowest_member])}) to {fastest_member} at {fastest_speed} "
        f"({_render_mode_label(member_speed_tiers[fastest_member])})."
    )


def _summarize_benchmark_depth_note(speed_benchmark_groups: dict[str, dict[str, object]]) -> str | None:
    fragments: list[str] = []
    for slug in ("natural", "tailwind", "choice_scarf", "trick_room"):
        payload = speed_benchmark_groups.get(slug)
        if not payload or not bool(payload.get("available")):
            continue

        member_count = len(_benchmark_members_for_group(payload))
        if slug == "natural":
            fragments.append(
                f"{member_count} member{'s' if member_count != 1 else ''} reach at least one natural-speed anchor"
            )
        elif slug == "tailwind":
            fragments.append(
                f"{member_count} member{'s' if member_count != 1 else ''} reach at least one Tailwind anchor"
            )
        elif slug == "choice_scarf":
            fragments.append(
                f"{member_count} Scarf line{'s' if member_count != 1 else ''} clear at least one curated Scarf anchor"
            )
        else:
            fragments.append(
                f"{member_count} member{'s' if member_count != 1 else ''} underspeed at least one Trick Room anchor"
            )

    if not fragments:
        return None

    return "Benchmark depth: " + "; ".join(fragments) + "."


def _summarize_speed_dependency_note(
    team_speed_tier: str,
    speed_benchmark_groups: dict[str, dict[str, object]],
) -> str | None:
    natural_payload = speed_benchmark_groups.get("natural")
    if natural_payload and bool(natural_payload.get("available")):
        natural_members = _benchmark_members_for_group(natural_payload)
        if len(natural_members) == 1 and team_speed_tier not in {"fast", "very_fast"}:
            return (
                f"Natural speed pressure is concentrated in {natural_members[0]} alone. Most of the roster still wants mode support "
                "or positioning help before it can race the faster benchmark tiers."
            )

    trick_room_payload = speed_benchmark_groups.get("trick_room")
    if trick_room_payload and bool(trick_room_payload.get("available")):
        trick_room_members = _benchmark_members_for_group(trick_room_payload)
        if 0 < len(trick_room_members) <= 2:
            return (
                f"Only {_render_series(trick_room_members)} consistently sits under the main Trick Room anchors, "
                "so the slow mode is narrower than the team preview might suggest."
            )

    return None


def _summarize_speed_context_spikes(
    member_speed_contexts: dict[str, list[dict[str, object]]],
    member_battle_speeds: dict[str, int],
) -> str | None:
    standout_rows: list[tuple[int, str, str, int]] = []

    for member_name, contexts in member_speed_contexts.items():
        for context in contexts:
            slug = cast(str, context["slug"])
            if slug in {"tailwind", "choice_scarf"}:
                continue
            standout_rows.append(
                (
                    cast(int, context["speed"]),
                    member_name,
                    cast(str, context["label"]),
                    member_battle_speeds[member_name],
                )
            )
            break

    if not standout_rows:
        return None

    standout_rows.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    fragments = [
        f"{member_name} jumps from {base_speed} to {boosted_speed} with {label}"
        for boosted_speed, member_name, label, base_speed in standout_rows[:3]
    ]
    return "Additional speed spikes: " + "; ".join(fragments) + "."


def _expand_speed_benchmark_notes(
    base_notes: list[str],
    team_speed_tier: str,
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    speed_tier_counts: dict[str, int],
    speed_benchmark_groups: dict[str, dict[str, object]],
    member_speed_contexts: dict[str, list[dict[str, object]]],
) -> list[str]:
    notes: list[str] = []

    speed_shape_note = _summarize_team_speed_shape_note(
        team_speed_tier,
        member_battle_speeds,
        member_speed_tiers,
        speed_tier_counts,
    )
    if speed_shape_note:
        notes.append(speed_shape_note)

    notes.extend(base_notes)

    benchmark_depth_note = _summarize_benchmark_depth_note(speed_benchmark_groups)
    if benchmark_depth_note:
        notes.append(benchmark_depth_note)

    speed_dependency_note = _summarize_speed_dependency_note(team_speed_tier, speed_benchmark_groups)
    if speed_dependency_note:
        notes.append(speed_dependency_note)

    speed_context_note = _summarize_speed_context_spikes(member_speed_contexts, member_battle_speeds)
    if speed_context_note:
        notes.append(speed_context_note)

    return notes


def _augment_speed_benchmark_notes_with_meta_context(
    benchmark_notes: list[str],
    meta_analysis: dict[str, object],
    team_speed_tier: str,
    team_mode_packages: list[str],
) -> list[str]:
    rows = cast(list[dict[str, object]], meta_analysis.get("tournament_rows", []))
    if not rows:
        return benchmark_notes

    notes = list(benchmark_notes)
    room_pref = team_speed_tier in {"trick_room_slow", "slow"} or any(
        _team_preview_is_trick_room_mode(mode_name) for mode_name in team_mode_packages
    )
    if room_pref:
        room_rows = [
            row
            for row in rows
            if any("room" in mode_name.lower() for mode_name in cast(list[str], row.get("modes", [])))
        ]
        room_anchor = _pick_meta_context_row(room_rows, meta_analysis, prefer_pressure=False)
        if room_anchor is not None:
            room_context = _render_meta_team_note_context(room_anchor)
            notes.append(
                f"Those slower benchmark lines matter on the live board because {room_context} still turn those games into real underspeed checks, so keeping your underspeed pieces intact matters more than winning the first natural-speed exchange."
            )
            return notes

    fast_rows = [
        row
        for row in rows
        if _row_has_fast_meta_pressure(row)
    ]
    fast_anchor = _pick_meta_context_row(fast_rows, meta_analysis, prefer_pressure=True)
    if fast_anchor is not None:
        interaction_summary = cast(dict[str, object], fast_anchor.get("interaction_summary", {}))
        interaction_tags = cast(list[str], interaction_summary.get("tags", []))
        fast_context = _render_meta_team_note_context(fast_anchor)
        if "spread counterplay" in interaction_tags:
            notes.append(
                f"Those benchmark lines matter most into {fast_context}, where fast tempo plus spread pressure punishes any missed speed-control turn."
            )
        elif "setup denial" in interaction_tags:
            notes.append(
                f"Those benchmark lines matter into {fast_context}, where the first speed exchange often decides whether their setup branch gets a safe turn."
            )
        else:
            notes.append(
                f"Those benchmark lines matter most into {fast_context}, where the live board still rewards the side that controls the first speed exchange."
            )

    return notes


def _pick_meta_context_row(
    rows: list[dict[str, object]],
    meta_analysis: dict[str, object],
    *,
    prefer_pressure: bool,
) -> dict[str, object] | None:
    if not rows:
        return None

    preferred_labels = set(
        cast(list[str], meta_analysis.get("pressured_targets" if prefer_pressure else "strongest_targets", []))
    )
    preferred_rows = [row for row in rows if cast(str, row.get("label", "")) in preferred_labels]
    ranked_rows = preferred_rows or rows
    return max(
        ranked_rows,
        key=lambda row: (cast(float, row.get("meta_share", 0.0)), abs(cast(float, row.get("matchup_score", 0.0)))),
    )


def _row_has_fast_meta_pressure(row: dict[str, object]) -> bool:
    modes = [mode_name.lower() for mode_name in cast(list[str], row.get("modes", []))]
    target_summary = cast(dict[str, object], row.get("target_summary", {}))
    return any("tailwind" in mode_name for mode_name in modes) or cast(int, target_summary.get("fast_cleanup_targets", 0)) > 0


def _augment_team_notes_with_meta_context(
    difficulty_factors: list[str],
    guidance_notes: list[str],
    meta_analysis: dict[str, object],
) -> tuple[list[str], list[str]]:
    rows = cast(list[dict[str, object]], meta_analysis.get("tournament_rows", []))
    if not rows:
        return difficulty_factors, guidance_notes

    updated_difficulty = list(difficulty_factors)
    updated_guidance = list(guidance_notes)

    pressured_row = _pick_meta_context_row(rows, meta_analysis, prefer_pressure=True)
    strongest_row = _pick_meta_context_row(rows, meta_analysis, prefer_pressure=False)

    if pressured_row is not None:
        pressured_context = _render_meta_team_note_context(pressured_row)
        interaction_summary = cast(dict[str, object], pressured_row.get("interaction_summary", {}))
        interaction_tags = cast(list[str], interaction_summary.get("tags", []))
        if interaction_tags:
            updated_difficulty.append(
                f"The live board adds extra sequencing pressure because {pressured_context} still demand {_render_series(interaction_tags[:2])}, not just a generic mode answer."
            )
        else:
            updated_difficulty.append(
                f"The live board adds extra sequencing pressure because {pressured_context} still create a real current pressure point, so preview choices matter more than the broad archetype label suggests."
            )

        reason_text = ""
        context_reasons = cast(list[str], pressured_row.get("context_reasons", []))
        if context_reasons:
            reason_text = context_reasons[0].rstrip(".")
            if reason_text and reason_text[0].isupper():
                reason_text = reason_text[0].lower() + reason_text[1:]
        if reason_text:
            updated_guidance.append(
                f"Start your matchup reps into {pressured_context}. That kind of board is one of the clearest current checks on this build, and {reason_text}."
            )
        else:
            updated_guidance.append(
                f"Start your matchup reps into {pressured_context}. That kind of board is one of the clearest current checks on this build, so practice that board before defaulting to generic archetype guesses."
            )

    if strongest_row is not None and strongest_row is not pressured_row:
        updated_guidance.append(
            f"Your cleanest live-field punish currently shows up into {_render_meta_team_note_context(strongest_row)}, so use those games to learn which four actually cash in your main mode instead of defaulting to the same opener every round."
        )

    return updated_difficulty[:7], updated_guidance[:8]


def _render_meta_team_note_context(row: dict[str, object]) -> str:
    interaction_summary = cast(dict[str, object], row.get("interaction_summary", {}))
    key_pokemon = cast(list[str], row.get("key_pokemon", []))
    modes = cast(list[str], row.get("modes", []))

    examples = _render_meta_team_note_examples(key_pokemon)
    mode_prefix = _render_meta_team_note_mode_prefix(modes)

    if cast(int, interaction_summary.get("ability_clause_targets", 0)) > 0:
        if "Farigiraf" in key_pokemon:
            return "teams with Farigiraf-style Armor Tail support"
        if examples:
            return f"{mode_prefix} with key ability pressure from pieces like {examples}"
        return "teams with key ability clauses protecting their main attackers"

    if cast(int, interaction_summary.get("setup_pressure_targets", 0)) > 0:
        if examples:
            return f"{mode_prefix} with setup pressure from pieces like {examples}"
        return f"{mode_prefix} that lean on early setup pressure"

    if cast(int, interaction_summary.get("spread_pressure_targets", 0)) > 0:
        return f"{mode_prefix} with repeated spread pressure"

    if cast(int, interaction_summary.get("redirection_targets", 0)) > 0:
        return f"{mode_prefix} with layered redirection support"

    if examples:
        return f"{mode_prefix} using pieces like {examples}"
    return "the current high-pressure meta teams"


def _render_meta_team_note_examples(key_pokemon: list[str]) -> str:
    if not key_pokemon:
        return ""
    if len(key_pokemon) == 1:
        return key_pokemon[0]
    return f"{key_pokemon[0]} or {key_pokemon[1]}"


def _render_meta_team_note_mode_prefix(modes: list[str]) -> str:
    if not modes:
        return "teams"

    primary_mode = modes[0]
    if primary_mode == "Dual Mode":
        return "teams that can pivot between multiple speed modes"
    return f"{primary_mode} teams"


def _sorted_context_speeds(
    group: SpeedBenchmarkGroup,
    context_speeds: dict[str, int],
) -> list[tuple[str, int]]:
    return sorted(
        context_speeds.items(),
        key=lambda item: (item[1], item[0]),
        reverse=group.comparison != "slower",
    )


def _benchmark_status(group: SpeedBenchmarkGroup, speed: int, target_speed: int) -> str:
    if speed == target_speed:
        return "tie"
    if group.comparison == "slower":
        return "underspeed" if speed < target_speed else "miss"
    return "outspeed" if speed > target_speed else "miss"


def _success_status(group: SpeedBenchmarkGroup) -> str:
    return "underspeed" if group.comparison == "slower" else "outspeed"


def _success_relation(group: SpeedBenchmarkGroup) -> str:
    return "underspeeds" if group.comparison == "slower" else "outruns"


def _render_series(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _resolve_members(
    team_sets: list[PokemonSet],
    provider: MetadataProvider,
    regulation_id: str | None = None,
) -> list[TeamMember]:
    members: list[TeamMember] = []
    resolved_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    for pokemon_set in team_sets:
        pokemon_set = resolve_regulation_pokemon_set(
            pokemon_set,
            regulation_id=resolved_regulation_id,
            normalize_species=regulation_id is not None,
        )
        species_name = pokemon_set.species
        if regulation_id is not None:
            species_name = resolve_regulation_species_name(pokemon_set.species, regulation_id=regulation_id) or species_name
        species_data = provider.get_species(species_name)
        move_data = tuple(provider.get_move(move_name) for move_name in pokemon_set.moves)
        members.append(TeamMember(pokemon_set=pokemon_set, species_data=species_data, move_data=move_data))
    return members


def classify_utility_roles(move: MoveData) -> tuple[str, ...]:
    roles: list[str] = []
    api_name = move.api_name.lower()
    short_effect = move.short_effect.lower()

    if _is_protection_move(api_name, short_effect):
        roles.append("protection")
    if _is_screen_move(api_name, short_effect):
        roles.append("screen")
    if _is_redirection_move(api_name, short_effect):
        roles.append("redirection")
    if _is_weather_move(api_name, short_effect):
        roles.append("weather")
    if _is_terrain_move(api_name, short_effect):
        roles.append("terrain")
    if _is_speed_control_move(move, short_effect):
        roles.append("speed_control")
    if _is_recovery_move(move, short_effect):
        roles.append("recovery")
    if _is_healing_support_move(move, api_name, short_effect):
        roles.append("healing_support")
    if _is_pivoting_move(api_name, short_effect):
        roles.append("pivoting")
    if _is_entry_hazard_move(api_name, short_effect):
        roles.append("entry_hazard")
    if _is_hazard_removal_move(api_name, short_effect):
        roles.append("hazard_removal")
    if _is_disruption_move(api_name, short_effect):
        roles.append("disruption")
    if _is_item_control_move(api_name, short_effect):
        roles.append("item_control")
    if _is_phazing_move(move, api_name, short_effect):
        roles.append("phazing")
    if _is_trapping_move(api_name, short_effect):
        roles.append("trapping")
    if _is_anti_setup_move(api_name, short_effect):
        roles.append("anti_setup")
    if _guarantees_flinch(move):
        roles.append("flinch_control")
    if _guarantees_ailment(move):
        roles.append("status_infliction")
    if _guarantees_positive_stat_change(move):
        roles.append("stat_boost")
    if _guarantees_negative_stat_change(move):
        roles.append("stat_drop")

    if move.damage_class == "status" and not roles:
        roles.append("other_utility")

    role_set = set(roles)
    return tuple(role for role in UTILITY_ROLE_ORDER if role in role_set)


def infer_pokemon_roles(
    member: TeamMember,
    classified_moves: list[tuple[MoveData, tuple[str, ...]]],
) -> tuple[str, ...]:
    role_presence: set[str] = set()
    damaging_moves = 0
    physical_damaging_moves = 0
    special_damaging_moves = 0
    support_move_count = 0
    status_support_move_count = 0
    status_support_categories: set[str] = set()
    has_fake_out = False
    has_tailwind = False
    has_trick_room = False
    has_priority_attack = False

    for move, move_roles in classified_moves:
        support_roles = tuple(role for role in move_roles if role in SUPPORT_UTILITY_ROLES)

        if move.damage_class != "status":
            damaging_moves += 1
            if move.damage_class == "physical":
                physical_damaging_moves += 1
            elif move.damage_class == "special":
                special_damaging_moves += 1
            if move.priority > 0:
                has_priority_attack = True
        if move_roles:
            role_presence.update(move_roles)
            if support_roles:
                support_move_count += 1
                if move.damage_class == "status":
                    status_support_move_count += 1
                    status_support_categories.update(support_roles)
        if move.api_name == "fake-out":
            has_fake_out = True
        elif move.api_name == "tailwind":
            has_tailwind = True
        elif move.api_name == "trick-room":
            has_trick_room = True

    support_categories = role_presence & SUPPORT_UTILITY_ROLES
    ability_name = _normalized_ability_name(member.pokemon_set.ability)
    context_ability_names = set(_member_context_ability_names(member))
    item_name = _normalized_item_name(member.pokemon_set.item)
    weather_from_ability = bool(context_ability_names & WEATHER_SETTER_ABILITIES)
    terrain_from_ability = bool(context_ability_names & TERRAIN_SETTER_ABILITIES)
    has_regenerator = "regenerator" in context_ability_names
    has_choice_power_item = item_name in CHOICE_POWER_ITEMS
    has_choice_scarf = item_name == "choice scarf"
    has_assault_vest = item_name == "assault vest"
    has_light_clay = item_name == "light clay"
    has_defensive_item = item_name in DEFENSIVE_ITEMS
    has_recovery_item = item_name in RECOVERY_ITEMS
    has_eviolite = item_name == "eviolite"
    has_pivot_ability = bool(context_ability_names & PIVOT_ABILITIES)
    has_support_ability = bool(context_ability_names & SUPPORT_ABILITIES)
    has_persistent_trapping = _has_persistent_trapping(member, ability_name, item_name)
    wall_bulk_threshold = 260 if has_eviolite else 280

    offense = max(member.species_data.base_attack, member.species_data.base_special_attack)
    bulk = (
        member.species_data.base_hp
        + member.species_data.base_defense
        + member.species_data.base_special_defense
    )
    speed = member.species_data.base_speed

    roles: list[str] = []

    if "entry_hazard" in role_presence or ability_name == "toxic debris":
        roles.append("hazard_setter")
    if "hazard_removal" in role_presence:
        roles.append("hazard_control")
    if "screen" in role_presence:
        roles.append("screen_setter")
    if "weather" in role_presence or weather_from_ability:
        roles.append("weather_setter")
    if "terrain" in role_presence or terrain_from_ability:
        roles.append("terrain_setter")
    if has_tailwind:
        roles.append("tailwind_setter")
    if has_trick_room:
        roles.append("trick_room_setter")
    if "speed_control" in role_presence:
        roles.append("speed_control")
    if has_fake_out:
        roles.append("fake_out_support")
    if "healing_support" in role_presence:
        roles.append("healing_support")
    if "trapping" in role_presence or has_persistent_trapping:
        roles.append("trapper")
    if "redirection" in role_presence:
        roles.append("redirector")

    if "pivoting" in role_presence and damaging_moves >= 2 and (offense >= 100 or speed >= 95 or has_choice_scarf):
        roles.append("pivot")
    if (
        ("pivoting" in role_presence or has_pivot_ability)
        and (bulk >= 240 or has_pivot_ability or has_defensive_item or "recovery" in role_presence)
    ):
        roles.append("bulky_pivot")

    if "stat_boost" in role_presence and damaging_moves >= 2 and (offense >= 100 or speed >= 90):
        roles.append("setup_sweeper")
    if damaging_moves >= 2 and status_support_move_count <= 2:
        if (
            physical_damaging_moves >= special_damaging_moves
            and physical_damaging_moves >= 2
            and (member.species_data.base_attack >= 110 or (has_choice_power_item and member.species_data.base_attack >= 100))
        ):
            roles.append("physical_sweeper")
        elif (
            special_damaging_moves > physical_damaging_moves
            and special_damaging_moves >= 2
            and (
                member.species_data.base_special_attack >= 110
                or (has_choice_power_item and member.species_data.base_special_attack >= 100)
            )
        ):
            roles.append("special_sweeper")
    if (
        damaging_moves >= 3
        and status_support_move_count <= 1
        and (
            has_choice_scarf
            or (speed >= 110 and offense >= 100)
            or (has_priority_attack and offense >= 110 and speed >= 70)
        )
    ):
        roles.append("cleaner")
    if (
        bulk >= wall_bulk_threshold
        and ("recovery" in role_presence or has_regenerator or has_recovery_item or has_eviolite)
        and (support_move_count >= 1 or offense <= 110)
    ):
        roles.append("bulky_support")
    # A Choice Scarf set spends its item on speed, not defensive investment, so a naturally bulky
    # statline does not make it a bulky attacker — it is a fast revenge killer / cleaner (#14).
    if not has_choice_scarf and (
        (bulk >= 260 and offense >= 100 and damaging_moves >= 2 and speed < 95)
        or (has_assault_vest and bulk >= 230 and offense >= 100 and damaging_moves >= 2)
    ):
        roles.append("bulky_attacker")
    if (
        len(status_support_categories) >= 3
        or (len(status_support_categories) >= 2 and damaging_moves <= 2)
        or (has_support_ability and len(support_categories) >= 2)
        or (has_light_clay and "screen" in role_presence)
    ):
        roles.append("support")

    role_set = set(roles)
    return tuple(role for role in POKEMON_ROLE_ORDER if role in role_set)


def infer_team_archetype(
    members: list[TeamMember],
    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
) -> tuple[str, dict[str, float]]:
    move_counts: Counter[str] = Counter()
    item_counts: Counter[str] = Counter()
    ability_counts: Counter[str] = Counter()
    damaging_type_counts: Counter[str] = Counter()
    slow_members = 0
    very_slow_members = 0
    fast_members = 0

    for member, classified_moves in classified_members:
        for ability_name in _member_context_ability_names(member):
            ability_counts[ability_name] += 1

        item_name = _normalized_item_name(member.pokemon_set.item)
        if item_name:
            item_counts[item_name] += 1

        if member.species_data.base_speed <= 70:
            slow_members += 1
        if member.species_data.base_speed <= 50:
            very_slow_members += 1
        if member.species_data.base_speed >= 100:
            fast_members += 1

        for move, _ in classified_moves:
            move_counts[move.api_name] += 1
            if move.damage_class != "status":
                damaging_type_counts[move.type_name] += 1

    physical_sweepers = pokemon_role_counts["physical_sweeper"]
    special_sweepers = pokemon_role_counts["special_sweeper"]
    sweepers = physical_sweepers + special_sweepers
    setup_sweepers = pokemon_role_counts["setup_sweeper"]
    cleaners = pokemon_role_counts["cleaner"]
    bulky_supports = pokemon_role_counts["bulky_support"]
    bulky_attackers = pokemon_role_counts["bulky_attacker"]
    pivots = pokemon_role_counts["pivot"]
    bulky_pivots = pokemon_role_counts["bulky_pivot"]
    supports = pokemon_role_counts["support"]
    hazard_setters = pokemon_role_counts["hazard_setter"]
    hazard_control = pokemon_role_counts["hazard_control"]
    screen_setters = pokemon_role_counts["screen_setter"]
    speed_control_roles = pokemon_role_counts["speed_control"]
    healing_supports = pokemon_role_counts["healing_support"]
    trappers = pokemon_role_counts["trapper"]
    redirectors = pokemon_role_counts["redirector"]
    recovery_moves = utility_role_counts["recovery"]
    phazing_moves = utility_role_counts["phazing"]
    disruption_moves = utility_role_counts["disruption"]
    trapping_moves = utility_role_counts["trapping"]
    protection_moves = utility_role_counts["protection"]

    choice_items = sum(item_counts[item_name] for item_name in CHOICE_ITEMS)
    power_choice_items = sum(item_counts[item_name] for item_name in CHOICE_POWER_ITEMS)
    defensive_items = sum(item_counts[item_name] for item_name in DEFENSIVE_ITEMS)
    focus_sash_count = item_counts["focus sash"]
    light_clay_count = item_counts["light clay"]
    tailwind_moves = move_counts["tailwind"]
    perish_song_moves = move_counts["perish-song"]
    trick_room_moves = move_counts["trick-room"]
    rain_sources = move_counts["rain-dance"] + ability_counts["drizzle"]
    sun_sources = move_counts["sunny-day"] + ability_counts["drought"]
    sand_sources = move_counts["sandstorm"] + ability_counts["sand stream"]
    snow_sources = move_counts["hail"] + move_counts["snowscape"] + ability_counts["snow warning"]
    electric_terrain_sources = move_counts["electric-terrain"] + ability_counts["electric surge"]
    grassy_terrain_sources = move_counts["grassy-terrain"] + ability_counts["grassy surge"]
    misty_terrain_sources = move_counts["misty-terrain"] + ability_counts["misty surge"]
    psychic_terrain_sources = move_counts["psychic-terrain"] + ability_counts["psychic surge"]
    fire_pressure = damaging_type_counts["fire"]
    water_pressure = damaging_type_counts["water"]
    grass_pressure = damaging_type_counts["grass"]
    ice_pressure = damaging_type_counts["ice"]
    electric_pressure = damaging_type_counts["electric"]
    psychic_pressure = damaging_type_counts["psychic"]
    sand_pressure = (
        damaging_type_counts["rock"]
        + damaging_type_counts["ground"]
        + damaging_type_counts["steel"]
    )

    offense_core = sweepers + setup_sweepers + pivots + 0.5 * cleaners
    balanced_defense = bulky_supports + bulky_attackers + bulky_pivots + supports
    offensive_roles = sweepers + setup_sweepers + cleaners
    support_load = supports + bulky_supports + healing_supports + screen_setters + speed_control_roles
    distinct_weather_modes = sum(1 for source_count in (rain_sources, sun_sources, sand_sources, snow_sources) if source_count > 0)

    scores = {
        "hyper_offense": (
            2.0 * offense_core
            + 1.3 * screen_setters
            + 1.0 * hazard_setters
            + 0.8 * power_choice_items
            + 0.7 * focus_sash_count
            + 0.5 * fast_members
            + 0.5 * light_clay_count
            - 1.4 * bulky_supports
            - 0.9 * hazard_control
            - 0.8 * healing_supports
            - 0.7 * bulky_pivots
        ),
        "bulky_offense": (
            1.6 * offense_core
            + 1.2 * (pivots + bulky_pivots + bulky_attackers)
            + 0.7 * hazard_setters
            + 0.5 * hazard_control
            + 0.4 * choice_items
            + 0.3 * defensive_items
            - 0.8 * bulky_supports
            - 0.5 * healing_supports
            - 0.5 * supports
        ),
        "balance": (
            1.5 * min(offense_core, balanced_defense)
            + 1.0 * hazard_setters
            + 1.0 * hazard_control
            + 0.8 * healing_supports
            + 0.7 * bulky_pivots
            + 0.4 * defensive_items
            - 0.5 * light_clay_count
            - 0.4 * choice_items
        ),
        "semi_stall": (
            1.8 * bulky_supports
            + 0.8 * supports
            + 1.0 * healing_supports
            + 0.8 * hazard_setters
            + 0.8 * hazard_control
            + 0.8 * phazing_moves
            + 0.7 * recovery_moves
            + 0.6 * (setup_sweepers + bulky_attackers)
            + 0.4 * defensive_items
            - 1.2 * offense_core
            - 0.6 * choice_items
            - 0.8 * screen_setters
            - 0.4 * pivots
        ),
        "stall": (
            2.2 * bulky_supports
            + 0.9 * supports
            + 1.1 * healing_supports
            + 1.0 * hazard_setters
            + 1.0 * hazard_control
            + 1.0 * phazing_moves
            + 0.9 * recovery_moves
            + 0.8 * bulky_pivots
            + 0.2 * defensive_items
            - 1.8 * offense_core
            - 1.0 * choice_items
            - 0.5 * fast_members
            - 0.8 * screen_setters
            - 0.5 * pivots
        ),
        "trick_room": (
            3.0 * trick_room_moves
            + 1.1 * slow_members
            + 0.8 * very_slow_members
            + 0.7 * (bulky_supports + bulky_attackers + sweepers)
            + 0.6 * redirectors
            + 0.5 * supports
            - 1.2 * fast_members
            - 1.0 * move_counts["tailwind"]
            - 1.2 * item_counts["choice scarf"]
        ),
        "rain": (
            2.1 * rain_sources
            + 0.9 * water_pressure
            + 0.6 * (bulky_pivots + supports)
            + 0.4 * speed_control_roles
            - 0.6 * sun_sources
        ),
        "sun": (
            2.1 * sun_sources
            + 1.0 * fire_pressure
            + 0.6 * (setup_sweepers + grass_pressure)
            + 0.4 * supports
            - 0.6 * rain_sources
        ),
        "sand": (
            2.2 * sand_sources
            + 0.9 * sand_pressure
            + 0.7 * (bulky_attackers + bulky_pivots)
            + 0.6 * hazard_setters
            + 0.4 * supports
            - 0.5 * trick_room_moves
        ),
        "snow": (
            2.0 * snow_sources
            + 0.9 * ice_pressure
            + 0.8 * screen_setters
            + 0.5 * fast_members
            + 0.4 * supports
            - 0.4 * sun_sources
        ),
        "electric_terrain": (
            2.2 * electric_terrain_sources
            + 0.8 * electric_pressure
            + 0.6 * fast_members
            + 0.5 * sweepers
            + 0.4 * supports
            + 0.3 * speed_control_roles
            - 0.4 * trick_room_moves
        ),
        "grassy_terrain": (
            2.0 * grassy_terrain_sources
            + 0.8 * grass_pressure
            + 0.7 * (bulky_attackers + bulky_pivots)
            + 0.5 * setup_sweepers
            + 0.4 * supports
            - 0.3 * tailwind_moves
        ),
        "misty_terrain": (
            2.0 * misty_terrain_sources
            + 0.7 * supports
            + 0.6 * bulky_pivots
            + 0.5 * healing_supports
            + 0.4 * speed_control_roles
            - 0.4 * offense_core
        ),
        "psychic_terrain": (
            2.2 * psychic_terrain_sources
            + 0.8 * psychic_pressure
            + 0.8 * special_sweepers
            + 0.5 * fast_members
            + 0.4 * supports
            - 0.4 * bulky_supports
        ),
        "tailwind": (
            2.4 * tailwind_moves
            + 1.4 * offense_core
            + 0.9 * fast_members
            + 0.7 * speed_control_roles
            + 0.5 * focus_sash_count
            + 0.4 * screen_setters
            - 1.0 * trick_room_moves
            - 0.6 * bulky_supports
            - 0.4 * very_slow_members
        ),
        "semiroom": (
            2.2 * trick_room_moves
            + 0.8 * slow_members
            + 0.7 * (bulky_attackers + supports + bulky_pivots)
            + 0.4 * fast_members
            + 0.3 * pivots
            - 0.8 * tailwind_moves
            - 0.5 * very_slow_members
        ),
        "rain_tailwind": (
            2.5 * min(rain_sources, tailwind_moves)
            + 1.2 * rain_sources
            + 1.2 * tailwind_moves
            + 1.2 * offense_core
            + 0.9 * fast_members
            + 0.7 * water_pressure
            + 0.4 * bulky_pivots
            - 1.0 * trick_room_moves
            - 0.5 * bulky_supports
        ),
        "sun_tailwind": (
            2.5 * min(sun_sources, tailwind_moves)
            + 1.2 * sun_sources
            + 1.2 * tailwind_moves
            + 1.2 * offense_core
            + 0.9 * fast_members
            + 0.8 * fire_pressure
            + 0.5 * (setup_sweepers + grass_pressure)
            - 1.0 * trick_room_moves
            - 0.5 * bulky_supports
            - 0.3 * bulky_pivots
        ),
        "sand_tailwind": (
            2.5 * min(sand_sources, tailwind_moves)
            + 1.1 * sand_sources
            + 1.1 * tailwind_moves
            + 1.0 * offense_core
            + 0.8 * sand_pressure
            + 0.6 * fast_members
            + 0.5 * bulky_attackers
            - 0.8 * trick_room_moves
        ),
        "snow_tailwind": (
            2.4 * min(snow_sources, tailwind_moves)
            + 1.1 * snow_sources
            + 1.1 * tailwind_moves
            + 0.9 * fast_members
            + 0.8 * ice_pressure
            + 0.7 * screen_setters
            + 0.4 * supports
            - 0.8 * trick_room_moves
        ),
        "rain_room": (
            2.6 * min(rain_sources, trick_room_moves)
            + 1.0 * rain_sources
            + 1.1 * trick_room_moves
            + 0.8 * slow_members
            + 0.7 * (bulky_attackers + redirectors)
            + 0.6 * water_pressure
            - 0.8 * tailwind_moves
        ),
        "sun_room": (
            2.6 * min(sun_sources, trick_room_moves)
            + 1.0 * sun_sources
            + 1.1 * trick_room_moves
            + 0.8 * slow_members
            + 0.7 * (bulky_attackers + redirectors)
            + 0.7 * fire_pressure
            - 0.8 * tailwind_moves
        ),
        "sand_room": (
            2.4 * min(sand_sources, trick_room_moves)
            + 1.0 * sand_sources
            + 1.0 * trick_room_moves
            + 0.8 * slow_members
            + 0.7 * sand_pressure
            + 0.7 * bulky_attackers
            + 0.4 * supports
            - 0.7 * tailwind_moves
        ),
        "snow_room": (
            2.4 * min(snow_sources, trick_room_moves)
            + 1.0 * snow_sources
            + 1.0 * trick_room_moves
            + 0.8 * slow_members
            + 0.7 * ice_pressure
            + 0.6 * screen_setters
            + 0.5 * supports
            - 0.7 * tailwind_moves
        ),
        "tailroom": (
            2.2 * min(tailwind_moves, trick_room_moves)
            + 1.0 * tailwind_moves
            + 1.0 * trick_room_moves
            + 0.9 * offense_core
            + 0.8 * supports
            + 0.6 * redirectors
            + 0.5 * fast_members
            + 0.5 * slow_members
            - 0.6 * choice_items
        ),
        "rain_tailroom": (
            2.8 * min(rain_sources, tailwind_moves, trick_room_moves)
            + 1.0 * rain_sources
            + 0.9 * tailwind_moves
            + 0.9 * trick_room_moves
            + 0.6 * supports
            + 0.5 * fast_members
            + 0.5 * slow_members
            + 0.5 * water_pressure
            - 0.5 * choice_items
        ),
        "sun_tailroom": (
            2.8 * min(sun_sources, tailwind_moves, trick_room_moves)
            + 1.0 * sun_sources
            + 0.9 * tailwind_moves
            + 0.9 * trick_room_moves
            + 0.6 * supports
            + 0.5 * fast_members
            + 0.5 * slow_members
            + 0.6 * fire_pressure
            - 0.5 * choice_items
        ),
        "screens_offense": (
            2.6 * screen_setters
            + 1.6 * light_clay_count
            + 1.3 * offense_core
            + 0.9 * setup_sweepers
            + 0.6 * fast_members
            + 0.6 * focus_sash_count
            - 0.8 * bulky_supports
            - 0.5 * trick_room_moves
        ),
        "dual_mode": (
            2.0 * min(tailwind_moves + rain_sources + sun_sources + max(fast_members - 2, 0), trick_room_moves + slow_members)
            + 0.9 * offense_core
            + 0.8 * supports
            + 0.7 * redirectors
            + 0.6 * bulky_supports
            + 0.4 * bulky_pivots
            - 0.4 * power_choice_items
        ),
        "psyspam": (
            3.2 * psychic_terrain_sources
            + 1.6 * move_counts["expanding-force"]
            + 1.2 * max(psychic_pressure - 1, 0)
            + 0.9 * special_sweepers
            + 0.5 * fast_members
            + 0.3 * tailwind_moves
            - 0.7 * bulky_supports
        ),
        "perish_trap": (
            3.4 * perish_song_moves
            + 1.4 * trapping_moves
            + 1.2 * trappers
            + 0.9 * redirectors
            + 0.7 * supports
            + 0.5 * (bulky_supports + bulky_pivots)
            + 0.4 * disruption_moves
            + 0.3 * protection_moves
            + 0.3 * utility_role_counts["speed_control"]
            - 0.7 * setup_sweepers
            - 0.5 * fast_members
            - 0.3 * power_choice_items
        ),
    }

    if trick_room_moves == 0:
        scores["trick_room"] -= 4.0
        scores["semiroom"] -= 4.0
        scores["rain_room"] -= 4.0
        scores["sun_room"] -= 4.0
        scores["sand_room"] -= 4.0
        scores["snow_room"] -= 4.0
        scores["tailroom"] -= 4.0
        scores["rain_tailroom"] -= 4.0
        scores["sun_tailroom"] -= 4.0
        scores["dual_mode"] -= 4.0
    if tailwind_moves == 0:
        scores["tailwind"] -= 4.0
        scores["rain_tailwind"] -= 4.0
        scores["sun_tailwind"] -= 4.0
        scores["sand_tailwind"] -= 4.0
        scores["snow_tailwind"] -= 4.0
        scores["tailroom"] -= 4.0
        scores["rain_tailroom"] -= 4.0
        scores["sun_tailroom"] -= 4.0
        if rain_sources == 0 and sun_sources == 0 and sand_sources == 0 and snow_sources == 0 and fast_members < 3:
            scores["dual_mode"] -= 4.0
    if rain_sources == 0:
        scores["rain"] -= 4.0
        scores["rain_tailwind"] -= 4.0
        scores["rain_room"] -= 4.0
        scores["rain_tailroom"] -= 4.0
    if sun_sources == 0:
        scores["sun"] -= 4.0
        scores["sun_tailwind"] -= 4.0
        scores["sun_room"] -= 4.0
        scores["sun_tailroom"] -= 4.0
    if sand_sources == 0:
        scores["sand"] -= 4.0
        scores["sand_tailwind"] -= 4.0
        scores["sand_room"] -= 4.0
    if snow_sources == 0:
        scores["snow"] -= 4.0
        scores["snow_tailwind"] -= 4.0
        scores["snow_room"] -= 4.0
    if electric_terrain_sources == 0:
        scores["electric_terrain"] -= 4.0
    if grassy_terrain_sources == 0:
        scores["grassy_terrain"] -= 4.0
    if misty_terrain_sources == 0:
        scores["misty_terrain"] -= 4.0
    if psychic_terrain_sources == 0:
        scores["psychic_terrain"] -= 4.0
        scores["psyspam"] -= 5.0
    if offensive_roles <= 2 and offense_core < 3 and support_load >= 4:
        scores["hyper_offense"] -= 4.0
    if distinct_weather_modes > 1:
        competing_weather_penalty = 2.0 * (distinct_weather_modes - 1)
        for weather_archetype in (
            "rain",
            "sun",
            "sand",
            "snow",
            "rain_tailwind",
            "sun_tailwind",
            "sand_tailwind",
            "snow_tailwind",
            "rain_room",
            "sun_room",
            "sand_room",
            "snow_room",
            "rain_tailroom",
            "sun_tailroom",
        ):
            scores[weather_archetype] -= competing_weather_penalty
        scores["dual_mode"] -= 1.5 * (distinct_weather_modes - 1)
    if psychic_pressure < 2 and move_counts["expanding-force"] == 0:
        scores["psyspam"] -= 4.0
    if screen_setters == 0:
        scores["screens_offense"] = min(scores["screens_offense"] - 6.0, 0.0)
    elif offense_core < 3 and setup_sweepers == 0:
        scores["screens_offense"] -= 2.0
    if perish_song_moves == 0:
        scores["perish_trap"] -= 6.0
    if trappers == 0:
        scores["perish_trap"] -= 9.0
    if redirectors == 0 and supports < 2:
        scores["perish_trap"] -= 1.5
    if bulky_supports < 2:
        scores["semi_stall"] -= 4.0
    if bulky_supports < 2:
        scores["stall"] -= 5.0

    rounded_scores = {
        archetype: round(score, 2)
        for archetype, score in scores.items()
    }
    archetype_priority = {archetype: index for index, archetype in enumerate(TEAM_ARCHETYPE_ORDER)}
    primary_archetype = max(
        TEAM_ARCHETYPE_ORDER,
        key=lambda archetype: (rounded_scores[archetype], archetype_priority[archetype]),
    )
    return primary_archetype, rounded_scores


def infer_team_packages(
    members: list[TeamMember],
    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    team_archetype_scores: dict[str, float],
) -> tuple[str, dict[str, float], list[str], dict[str, float], list[str], dict[str, float]]:
    style_scores = {
        style: round(team_archetype_scores[style], 2)
        for style in STYLE_PACKAGE_ORDER
    }
    supportive_structure = (
        pokemon_role_counts["support"]
        + pokemon_role_counts["bulky_support"]
        + pokemon_role_counts["bulky_pivot"]
        + pokemon_role_counts["redirector"]
        + pokemon_role_counts["healing_support"]
        + pokemon_role_counts["hazard_control"]
    )
    proactive_pressure = (
        pokemon_role_counts["physical_sweeper"]
        + pokemon_role_counts["special_sweeper"]
        + pokemon_role_counts["setup_sweeper"]
        + pokemon_role_counts["cleaner"]
        + pokemon_role_counts["bulky_attacker"]
    )
    structured_identity_score = max(
        team_archetype_scores["sand"],
        team_archetype_scores["snow"],
        team_archetype_scores["electric_terrain"],
        team_archetype_scores["grassy_terrain"],
        team_archetype_scores["misty_terrain"],
        team_archetype_scores["psychic_terrain"],
        team_archetype_scores["semiroom"],
        team_archetype_scores["tailroom"],
        team_archetype_scores["dual_mode"],
        team_archetype_scores["rain_tailwind"],
        team_archetype_scores["sun_tailwind"],
        team_archetype_scores["sand_tailwind"],
        team_archetype_scores["snow_tailwind"],
        team_archetype_scores["rain_room"],
        team_archetype_scores["sun_room"],
        team_archetype_scores["sand_room"],
        team_archetype_scores["snow_room"],
        team_archetype_scores["rain_tailroom"],
        team_archetype_scores["sun_tailroom"],
    )
    specialized_shell_score = max(
        team_archetype_scores["perish_trap"],
        team_archetype_scores["screens_offense"],
        team_archetype_scores["psyspam"],
    )
    if (
        supportive_structure >= 4
        and proactive_pressure >= 3
        and structured_identity_score >= 8.0
        and specialized_shell_score < 10.0
    ):
        structure_delta = structured_identity_score - 8.0
        style_scores["balance"] = round(style_scores["balance"] + 0.9 + 0.06 * structure_delta, 2)
        style_scores["hyper_offense"] = round(style_scores["hyper_offense"] - (0.7 + 0.05 * structure_delta), 2)
        style_scores["semi_stall"] = round(style_scores["semi_stall"] - (1.1 + 0.08 * structure_delta), 2)
        style_scores["stall"] = round(style_scores["stall"] - (1.7 + 0.1 * structure_delta), 2)
    elif supportive_structure >= 5 and supportive_structure >= proactive_pressure:
        # Dense board-control/support density (redirection, screens, healing, pivots) is a bulky/control
        # identity, not Hyper Offense, even when the team also stacks attackers or sets screens (#1). The
        # specialized-shell gate above can miss this, so demote Hyper Offense toward bulky offense/balance.
        support_delta = supportive_structure - proactive_pressure
        demotion = 1.6 + 0.2 * support_delta
        style_scores["hyper_offense"] = round(style_scores["hyper_offense"] - demotion, 2)
        style_scores["bulky_offense"] = round(style_scores["bulky_offense"] + 0.6, 2)
        style_scores["balance"] = round(style_scores["balance"] + 0.6, 2)

    style_priority = {style: index for index, style in enumerate(STYLE_PACKAGE_ORDER)}
    primary_style = max(STYLE_PACKAGE_ORDER, key=lambda style: (style_scores[style], style_priority[style]))

    mode_scores = {
        "tailwind": round(
            max(
                team_archetype_scores["tailwind"],
                team_archetype_scores["rain_tailwind"],
                team_archetype_scores["sun_tailwind"],
                team_archetype_scores["sand_tailwind"],
                team_archetype_scores["snow_tailwind"],
                team_archetype_scores["tailroom"],
                team_archetype_scores["rain_tailroom"],
                team_archetype_scores["sun_tailroom"],
            ),
            2,
        ),
        "trick_room": round(
            max(
                team_archetype_scores["trick_room"],
                team_archetype_scores["semiroom"],
                team_archetype_scores["rain_room"],
                team_archetype_scores["sun_room"],
                team_archetype_scores["sand_room"],
                team_archetype_scores["snow_room"],
                team_archetype_scores["tailroom"],
                team_archetype_scores["rain_tailroom"],
                team_archetype_scores["sun_tailroom"],
            ),
            2,
        ),
        "semiroom": round(team_archetype_scores["semiroom"], 2),
        "tailroom": round(team_archetype_scores["tailroom"], 2),
        "dual_mode": round(team_archetype_scores["dual_mode"], 2),
        "rain": round(
            max(
                team_archetype_scores["rain"],
                team_archetype_scores["rain_tailwind"],
                team_archetype_scores["rain_room"],
                team_archetype_scores["rain_tailroom"],
            ),
            2,
        ),
        "sun": round(
            max(
                team_archetype_scores["sun"],
                team_archetype_scores["sun_tailwind"],
                team_archetype_scores["sun_room"],
                team_archetype_scores["sun_tailroom"],
            ),
            2,
        ),
        "sand": round(max(team_archetype_scores["sand"], team_archetype_scores["sand_tailwind"], team_archetype_scores["sand_room"]), 2),
        "snow": round(max(team_archetype_scores["snow"], team_archetype_scores["snow_tailwind"], team_archetype_scores["snow_room"]), 2),
        "electric_terrain": round(team_archetype_scores["electric_terrain"], 2),
        "grassy_terrain": round(team_archetype_scores["grassy_terrain"], 2),
        "misty_terrain": round(team_archetype_scores["misty_terrain"], 2),
        "psychic_terrain": round(max(team_archetype_scores["psychic_terrain"], team_archetype_scores["psyspam"]), 2),
        "rain_tailwind": round(team_archetype_scores["rain_tailwind"], 2),
        "sun_tailwind": round(team_archetype_scores["sun_tailwind"], 2),
        "sand_tailwind": round(team_archetype_scores["sand_tailwind"], 2),
        "snow_tailwind": round(team_archetype_scores["snow_tailwind"], 2),
        "rain_room": round(team_archetype_scores["rain_room"], 2),
        "sun_room": round(team_archetype_scores["sun_room"], 2),
        "sand_room": round(team_archetype_scores["sand_room"], 2),
        "snow_room": round(team_archetype_scores["snow_room"], 2),
        "rain_tailroom": round(team_archetype_scores["rain_tailroom"], 2),
        "sun_tailroom": round(team_archetype_scores["sun_tailroom"], 2),
    }
    team_mode_packages = _rank_identity_labels(
        mode_scores,
        minimum_score=1.5,
        max_delta=99.0,
        limit=4,
        preferred_order=MODE_PACKAGE_ORDER,
    )

    setup_sweep_score = round(
        1.8 * pokemon_role_counts["setup_sweeper"]
        + 0.7 * (pokemon_role_counts["physical_sweeper"] + pokemon_role_counts["special_sweeper"])
        + 0.5 * pokemon_role_counts["redirector"]
        + 0.4 * pokemon_role_counts["screen_setter"]
        + 0.3 * utility_role_counts["speed_control"],
        2,
    )
    win_condition_scores = {
        "perish_trap": round(team_archetype_scores["perish_trap"], 2),
        "screens_offense": round(team_archetype_scores["screens_offense"], 2),
        "setup_sweep": setup_sweep_score,
        "psyspam": round(team_archetype_scores["psyspam"], 2),
    }
    team_win_condition_labels = _rank_identity_labels(
        win_condition_scores,
        minimum_score=2.0,
        max_delta=99.0,
        limit=2,
        preferred_order=WIN_CONDITION_PACKAGE_ORDER,
        allow_empty=True,
    )

    return (
        primary_style,
        style_scores,
        team_mode_packages,
        mode_scores,
        team_win_condition_labels,
        win_condition_scores,
    )


def _rank_identity_labels(
    scores: dict[str, float],
    *,
    minimum_score: float,
    max_delta: float,
    limit: int,
    preferred_order: tuple[str, ...] | None = None,
    allow_empty: bool = False,
) -> list[str]:
    if not scores:
        return []

    order_lookup = {label: index for index, label in enumerate(preferred_order or ())}
    ranked_scores = sorted(
        scores.items(),
        key=lambda item: (-item[1], order_lookup.get(item[0], len(order_lookup)), item[0]),
    )
    best_score = ranked_scores[0][1]
    labels = [
        label
        for label, score in ranked_scores
        if score >= minimum_score and score >= best_score - max_delta
    ][:limit]
    if labels:
        return labels
    if allow_empty:
        return []
    return [ranked_scores[0][0]]


def infer_matchup_profile(
    members: list[TeamMember],
    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    offensive_coverage: dict[str, int],
    defensive_profile: dict[str, dict[str, float | int]],
    top_defensive_weaknesses: list[str],
    team_archetype_scores: dict[str, float],
    contextual_matchup_profile: ContextualMatchupProfile,
) -> tuple[dict[str, float], dict[str, dict[str, object]], list[str], list[str]]:
    move_counts = Counter()
    ability_counts = Counter()
    item_counts = Counter()
    fast_members = 0
    slow_members = 0
    very_slow_members = 0
    priority_attack_count = 0

    for member, classified_moves in classified_members:
        ability_name = _normalized_ability_name(member.pokemon_set.ability)
        if ability_name:
            ability_counts[ability_name] += 1

        item_name = _normalized_item_name(member.pokemon_set.item)
        if item_name:
            item_counts[item_name] += 1

        if member.species_data.base_speed >= 100:
            fast_members += 1
        if member.species_data.base_speed <= 70:
            slow_members += 1
        if member.species_data.base_speed <= 50:
            very_slow_members += 1

        for move, _ in classified_moves:
            move_counts[move.api_name] += 1
            if move.priority > 0 and move.damage_class != "status":
                priority_attack_count += 1

    own_archetype = max(
        BROAD_TEAM_ARCHETYPE_ORDER,
        key=lambda archetype: (team_archetype_scores[archetype], archetype),
    )
    sweepers = pokemon_role_counts["physical_sweeper"] + pokemon_role_counts["special_sweeper"]
    setup_sweepers = pokemon_role_counts["setup_sweeper"]
    cleaners = pokemon_role_counts["cleaner"]
    bulky_supports = pokemon_role_counts["bulky_support"]
    bulky_attackers = pokemon_role_counts["bulky_attacker"]
    pivots = pokemon_role_counts["pivot"]
    bulky_pivots = pokemon_role_counts["bulky_pivot"]
    supports = pokemon_role_counts["support"]
    screen_setters = pokemon_role_counts["screen_setter"]
    speed_control_roles = pokemon_role_counts["speed_control"]
    redirectors = pokemon_role_counts["redirector"]
    hazard_setters = pokemon_role_counts["hazard_setter"]
    hazard_control = pokemon_role_counts["hazard_control"]

    pressure = sweepers + setup_sweepers + pivots + 0.5 * cleaners
    resilience = bulky_supports + bulky_attackers + bulky_pivots
    progress_tools = hazard_setters + utility_role_counts["item_control"] + utility_role_counts["phazing"] + utility_role_counts["trapping"]
    control = speed_control_roles + utility_role_counts["disruption"] + utility_role_counts["anti_setup"] + utility_role_counts["stat_drop"]
    coverage_breadth = sum(1 for count in offensive_coverage.values() if count > 0)
    trick_room_moves = move_counts["trick-room"]
    choice_items = sum(item_counts[item_name] for item_name in CHOICE_ITEMS)
    fake_out_count = move_counts["fake-out"]
    wide_guard_count = move_counts["wide-guard"]
    taunt_count = move_counts["taunt"]
    encore_count = move_counts["encore"]
    imprison_count = move_counts["imprison"]
    intimidate_count = ability_counts["intimidate"]
    priority_block_bypass = int(fake_out_count > 0 and ability_counts["mold breaker"] > 0)
    distinct_weather_modes = sum(
        1
        for source_count in (
            ability_counts["drizzle"] + move_counts["rain-dance"],
            ability_counts["drought"] + move_counts["sunny-day"],
            ability_counts["sand stream"] + move_counts["sandstorm"],
            ability_counts["snow warning"] + move_counts["hail"] + move_counts["snowscape"],
        )
        if source_count > 0
    )
    competing_weather_count = max(0, distinct_weather_modes - 1)
    mode_sprawl_penalty = competing_weather_count * (1.1 + 0.4 * int(move_counts["tailwind"] > 0 and trick_room_moves > 0))
    bias = ARCHETYPE_MATCHUP_BIAS[own_archetype]

    tailwind_counterplay = (
        0.7 * utility_role_counts["speed_control"]
        + 0.5 * speed_control_roles
        + 0.8 * wide_guard_count
        + 0.8 * fake_out_count
        + 0.6 * priority_attack_count
        + 0.5 * utility_role_counts["screen"]
        + 0.4 * redirectors
        + 0.2 * hazard_control
    )
    weather_counterplay = (
        0.6 * min(2, pokemon_role_counts["weather_setter"] + utility_role_counts["weather"])
        + 0.8 * wide_guard_count
        + 0.4 * offensive_coverage["electric"]
        + 0.4 * offensive_coverage["grass"]
        + 0.3 * offensive_coverage["rock"]
    )
    if competing_weather_count:
        weather_counterplay = max(0.0, weather_counterplay - 1.1 * competing_weather_count)
    trick_room_counterplay = (
        1.0 * taunt_count
        + 1.0 * encore_count
        + 1.2 * imprison_count
        + 0.8 * trick_room_moves
        + 0.6 * fake_out_count
        + 0.6 * wide_guard_count
        + 0.6 * priority_attack_count
        + 0.4 * utility_role_counts["speed_control"]
        + 0.5 * utility_role_counts["anti_setup"]
        + 0.4 * utility_role_counts["phazing"]
        + 0.8 * priority_block_bypass
        + 0.4 * intimidate_count
    )
    stallbreak_tools = (
        0.9 * utility_role_counts["item_control"]
        + 0.8 * utility_role_counts["phazing"]
        + 0.7 * utility_role_counts["trapping"]
        + 0.8 * taunt_count
        + 0.5 * sweepers
        + 0.4 * setup_sweepers
        + 0.2 * hazard_setters
    )
    trick_room_mode_tension = max(0, fast_members - (trick_room_moves + taunt_count + encore_count))
    tailwind_exposure = _weighted_defensive_exposure(
        defensive_profile,
        top_defensive_weaknesses,
        M_A_TAILWIND_PRESSURE_TYPES,
    )
    weather_exposure = _weighted_defensive_exposure(
        defensive_profile,
        top_defensive_weaknesses,
        M_A_WEATHER_PRESSURE_TYPES,
    )
    trick_room_exposure = _weighted_defensive_exposure(
        defensive_profile,
        top_defensive_weaknesses,
        M_A_TRICK_ROOM_PRESSURE_TYPES,
    )

    raw_scores = {
        "hyper_offense": (
            bias["hyper_offense"]
            + 0.7 * control
            + 0.7 * resilience
            + 0.65 * tailwind_counterplay
            + 0.35 * trick_room_counterplay
            + 0.25 * weather_counterplay
            + 0.3 * hazard_control
            + 0.2 * screen_setters
            + 0.2 * pressure
            - 0.45 * tailwind_exposure
            - 0.15 * weather_exposure
            - 0.5 * max(0, very_slow_members - trick_room_moves)
            - 0.75 * mode_sprawl_penalty
        ),
        "bulky_offense": (
            bias["bulky_offense"]
            + 0.7 * pressure
            + 0.4 * control
            + 0.5 * resilience
            + 0.3 * progress_tools
            + 0.25 * weather_counterplay
            + 0.2 * stallbreak_tools
            + 0.1 * coverage_breadth
            - 0.35 * tailwind_exposure
            - 0.5 * weather_exposure
            - 0.4 * mode_sprawl_penalty
        ),
        "balance": (
            bias["balance"]
            + 0.7 * pressure
            + 0.5 * progress_tools
            + 0.35 * control
            + 0.25 * stallbreak_tools
            + 0.1 * coverage_breadth
            - 0.2 * supports
            - 0.2 * tailwind_exposure
            - 0.15 * trick_room_exposure
            - 0.2 * mode_sprawl_penalty
        ),
        "semi_stall": (
            bias["semi_stall"]
            + 0.8 * pressure
            + 0.6 * progress_tools
            + 0.6 * utility_role_counts["item_control"]
            + 0.3 * control
            + 0.45 * stallbreak_tools
            - 0.4 * bulky_supports
            - 0.2 * supports
        ),
        "stall": (
            bias["stall"]
            + 0.8 * pressure
            + 0.8 * progress_tools
            + 0.8 * utility_role_counts["item_control"]
            + 0.4 * utility_role_counts["disruption"]
            + 0.55 * stallbreak_tools
            + 0.2 * coverage_breadth
            - 0.5 * bulky_supports
            - 0.4 * supports
        ),
        "trick_room": (
            bias["trick_room"]
            + 1.2 * trick_room_counterplay
            + 0.4 * speed_control_roles
            + 0.4 * utility_role_counts["protection"]
            + 0.2 * pressure
            + 0.3 * redirectors
            + 0.4 * trick_room_moves
            - 0.45 * trick_room_exposure
            - 0.35 * trick_room_mode_tension
            - 0.6 * choice_items
            + 0.3 * slow_members
            - 0.8 * mode_sprawl_penalty
        ),
    }

    contextual_adjustments: dict[str, float] = {}
    matchup_detail_map: dict[str, dict[str, object]] = {}
    adjusted_raw_scores: dict[str, float] = {}
    for archetype in BROAD_TEAM_ARCHETYPE_ORDER:
        contextual_adjustment, contextual_reasons = _score_broad_contextual_matchup(
            archetype,
            contextual_matchup_profile,
        )
        contextual_adjustments[archetype] = contextual_adjustment
        adjusted_raw_scores[archetype] = raw_scores[archetype] + contextual_adjustment
        matchup_detail_map[archetype] = {
            "base_score": round(raw_scores[archetype], 2),
            "contextual_adjustment": contextual_adjustment,
            "reasons": _finalize_context_reasons(contextual_reasons),
            **_bucket_context_reasons(contextual_reasons),
        }

    average_score = sum(adjusted_raw_scores.values()) / len(adjusted_raw_scores)
    matchup_scores = {
        archetype: round(adjusted_raw_scores[archetype] - average_score, 2)
        for archetype in BROAD_TEAM_ARCHETYPE_ORDER
    }
    for archetype in BROAD_TEAM_ARCHETYPE_ORDER:
        detail = matchup_detail_map[archetype]
        relative_score = matchup_scores[archetype]
        detail["score"] = relative_score
        # A clearly +/- verdict whose edge is purely the archetype clash carries no contextual
        # reason, which would render as an unexplained (or one-sided) matchup. Backfill a structural
        # reason so every meaningful matchup states why it leans the way it does (GPT feedback #2).
        if relative_score <= -0.5 and not detail["negatives"]:
            structural = _structural_matchup_reason(own_archetype, archetype, negative=True)
            detail["negatives"] = [structural]
            detail["failure_condition"] = structural
        elif relative_score >= 0.5 and not detail["positives"]:
            detail["positives"] = [_structural_matchup_reason(own_archetype, archetype, negative=False)]
    favorable_ranked = sorted(matchup_scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    unfavorable_ranked = sorted(matchup_scores.items(), key=lambda item: (item[1], item[0]))
    favorable_matchups = [archetype for archetype, score in favorable_ranked if score > 0][:2]
    unfavorable_matchups = [archetype for archetype, score in unfavorable_ranked if score < 0][:2]

    if not favorable_matchups:
        favorable_matchups = [favorable_ranked[0][0]]
    if not unfavorable_matchups:
        unfavorable_matchups = [unfavorable_ranked[0][0]]

    return matchup_scores, matchup_detail_map, favorable_matchups, unfavorable_matchups


def infer_meta_mode_profile(
    members: list[TeamMember],
    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    offensive_coverage: dict[str, int],
    defensive_profile: dict[str, dict[str, float | int]],
    top_defensive_weaknesses: list[str],
    team_archetype_scores: dict[str, float],
    broad_matchup_scores: dict[str, float],
) -> tuple[dict[str, float], list[str], dict[str, float], list[str], list[str]]:
    move_counts = Counter()
    ability_counts = Counter()
    species_tokens: set[str] = set()
    fast_members = 0
    slow_members = 0
    priority_attack_count = 0

    for member, classified_moves in classified_members:
        for ability_name in _member_context_ability_names(member):
            ability_counts[ability_name] += 1
        species_tokens.update(_species_tokens_for_member(member))

        if member.species_data.base_speed >= 100:
            fast_members += 1
        if member.species_data.base_speed <= 70:
            slow_members += 1

        for move, _ in classified_moves:
            move_counts[move.api_name] += 1
            if move.priority > 0 and move.damage_class != "status":
                priority_attack_count += 1

    sweepers = pokemon_role_counts["physical_sweeper"] + pokemon_role_counts["special_sweeper"]
    setup_sweepers = pokemon_role_counts["setup_sweeper"]
    cleaners = pokemon_role_counts["cleaner"]
    bulky_supports = pokemon_role_counts["bulky_support"]
    bulky_attackers = pokemon_role_counts["bulky_attacker"]
    pivots = pokemon_role_counts["pivot"]
    bulky_pivots = pokemon_role_counts["bulky_pivot"]
    screen_setters = pokemon_role_counts["screen_setter"]
    speed_control_roles = pokemon_role_counts["speed_control"]
    redirectors = pokemon_role_counts["redirector"]
    hazard_control = pokemon_role_counts["hazard_control"]

    pressure = sweepers + setup_sweepers + pivots + 0.5 * cleaners
    resilience = bulky_supports + bulky_attackers + bulky_pivots
    trick_room_moves = move_counts["trick-room"]
    fake_out_count = move_counts["fake-out"]
    wide_guard_count = move_counts["wide-guard"]
    taunt_count = move_counts["taunt"]
    encore_count = move_counts["encore"]
    imprison_count = move_counts["imprison"]
    tailwind_sources = move_counts["tailwind"]
    rain_sources = move_counts["rain-dance"] + ability_counts["drizzle"]
    sand_sources = move_counts["sandstorm"] + ability_counts["sand stream"]
    sun_sources = move_counts["sunny-day"] + ability_counts["drought"]
    snow_sources = move_counts["snowscape"] + move_counts["hail"] + ability_counts["snow warning"]
    electric_terrain_sources = move_counts["electric-terrain"]
    grassy_terrain_sources = move_counts["grassy-terrain"]
    misty_terrain_sources = move_counts["misty-terrain"]
    psychic_terrain_sources = move_counts["psychic-terrain"]
    expanding_force_count = move_counts["expanding-force"]
    intimidate_count = ability_counts["intimidate"]
    priority_block_bypass = int(fake_out_count > 0 and ability_counts["mold breaker"] > 0)

    tailwind_counterplay = (
        0.7 * utility_role_counts["speed_control"]
        + 0.5 * speed_control_roles
        + 0.8 * wide_guard_count
        + 0.8 * fake_out_count
        + 0.6 * priority_attack_count
        + 0.5 * utility_role_counts["screen"]
        + 0.4 * redirectors
        + 0.2 * hazard_control
    )
    weather_counterplay = (
        0.6 * (pokemon_role_counts["weather_setter"] + utility_role_counts["weather"])
        + 0.8 * wide_guard_count
        + 0.4 * offensive_coverage["electric"]
        + 0.4 * offensive_coverage["grass"]
        + 0.3 * offensive_coverage["rock"]
    )
    trick_room_counterplay = (
        1.0 * taunt_count
        + 1.0 * encore_count
        + 1.2 * imprison_count
        + 0.8 * trick_room_moves
        + 0.6 * fake_out_count
        + 0.6 * wide_guard_count
        + 0.6 * priority_attack_count
        + 0.4 * utility_role_counts["speed_control"]
        + 0.5 * utility_role_counts["anti_setup"]
        + 0.4 * utility_role_counts["phazing"]
        + 0.8 * priority_block_bypass
        + 0.4 * intimidate_count
    )

    feature_values = {
        "tailwind": float(tailwind_sources),
        "rain": float(rain_sources),
        "trick_room": float(trick_room_moves),
        "sand": float(sand_sources),
        "snow": float(snow_sources),
        "sun": float(sun_sources),
        "electric_terrain": float(electric_terrain_sources),
        "grassy_terrain": float(grassy_terrain_sources),
        "misty_terrain": float(misty_terrain_sources),
        "psychic_terrain": float(psychic_terrain_sources),
        "pressure": float(pressure),
        "resilience": float(resilience),
        "speed_control": float(utility_role_counts["speed_control"] + speed_control_roles),
        "priority": float(priority_attack_count),
        "wide_guard": float(wide_guard_count),
        "screens": float(screen_setters),
        "redirection": float(redirectors),
        "healing_support": float(utility_role_counts["healing_support"]),
        "expanding_force": float(expanding_force_count),
        "tailwind_counterplay": tailwind_counterplay,
        "weather_counterplay": weather_counterplay,
        "trick_room_counterplay": trick_room_counterplay,
        "electric_punish_coverage": float(offensive_coverage["electric"]),
        "grass_punish_coverage": float(offensive_coverage["grass"]),
        "fairy_punish_coverage": float(offensive_coverage["fairy"]),
        "psychic_punish_coverage": float(offensive_coverage["psychic"]),
        "rain_punish_coverage": float(
            offensive_coverage["electric"] + offensive_coverage["grass"] + offensive_coverage["rock"]
        ),
        "sand_punish_coverage": float(
            offensive_coverage["water"]
            + offensive_coverage["grass"]
            + offensive_coverage["fighting"]
            + offensive_coverage["ground"]
        ),
        "snow_punish_coverage": float(
            offensive_coverage["fire"] + offensive_coverage["rock"] + offensive_coverage["steel"]
        ),
        "sun_punish_coverage": float(
            offensive_coverage["water"] + offensive_coverage["ground"] + offensive_coverage["rock"]
        ),
        "tailwind_shell": max(team_archetype_scores["tailwind"], 0.0),
        "trick_room_shell": max(team_archetype_scores["trick_room"], 0.0),
        "semiroom_shell": max(team_archetype_scores["semiroom"], 0.0),
        "tailroom_shell": max(team_archetype_scores["tailroom"], 0.0),
        "dual_mode_shell": max(team_archetype_scores["dual_mode"], 0.0),
        "rain_shell": max(team_archetype_scores["rain"], 0.0),
        "sun_shell": max(team_archetype_scores["sun"], 0.0),
        "sand_shell": max(team_archetype_scores["sand"], 0.0),
        "snow_shell": max(team_archetype_scores["snow"], 0.0),
        "electric_terrain_shell": max(team_archetype_scores["electric_terrain"], 0.0),
        "grassy_terrain_shell": max(team_archetype_scores["grassy_terrain"], 0.0),
        "misty_terrain_shell": max(team_archetype_scores["misty_terrain"], 0.0),
        "psychic_terrain_shell": max(team_archetype_scores["psychic_terrain"], team_archetype_scores["psyspam"], 0.0),
        "rain_tailwind_shell": max(team_archetype_scores["rain_tailwind"], 0.0),
        "sun_tailwind_shell": max(team_archetype_scores["sun_tailwind"], 0.0),
        "sand_tailwind_shell": max(team_archetype_scores["sand_tailwind"], 0.0),
        "snow_tailwind_shell": max(team_archetype_scores["snow_tailwind"], 0.0),
        "rain_room_shell": max(team_archetype_scores["rain_room"], 0.0),
        "sun_room_shell": max(team_archetype_scores["sun_room"], 0.0),
        "sand_room_shell": max(team_archetype_scores["sand_room"], 0.0),
        "snow_room_shell": max(team_archetype_scores["snow_room"], 0.0),
        "rain_tailroom_shell": max(team_archetype_scores["rain_tailroom"], 0.0),
        "sun_tailroom_shell": max(team_archetype_scores["sun_tailroom"], 0.0),
    }

    raw_team_mode_scores: dict[str, float] = {}
    raw_mode_matchup_scores: dict[str, float] = {}

    for mode in MODE_LABEL_ORDER:
        snapshot = TOURNAMENT_MODE_SNAPSHOTS[mode]
        identity_score = 0.25 * snapshot["tournament_weight"]
        identity_score += sum(
            weight
            for species_name, weight in snapshot["signature_species"].items()
            if species_name in species_tokens
        )
        identity_score += sum(
            feature_values[feature_name] * weight
            for feature_name, weight in snapshot["identity_feature_weights"].items()
        )
        for feature_name in snapshot["required_features"]:
            if feature_values[feature_name] > 0:
                identity_score += 0.35
            else:
                identity_score -= 1.1
        raw_team_mode_scores[mode] = identity_score

        base_score = sum(
            broad_matchup_scores[archetype] * weight
            for archetype, weight in snapshot["broad_mix"].items()
        )
        counterplay_score = sum(
            feature_values[feature_name] * weight
            for feature_name, weight in snapshot["counterplay_feature_weights"].items()
        )
        exposure_score = snapshot["exposure_weight"] * _weighted_defensive_exposure(
            defensive_profile,
            top_defensive_weaknesses,
            snapshot["pressure_types"],
        )
        raw_mode_matchup_scores[mode] = base_score + counterplay_score - exposure_score

    team_mode_scores = {
        mode: round(raw_team_mode_scores[mode], 2)
        for mode in MODE_LABEL_ORDER
    }
    ranked_team_modes = sorted(team_mode_scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    highest_team_mode_score = ranked_team_modes[0][1]
    team_mode_labels = [
        mode
        for mode, score in ranked_team_modes
        if score >= 1.75 and score >= highest_team_mode_score - 1.25
    ][:2]
    if not team_mode_labels:
        team_mode_labels = [ranked_team_modes[0][0]]

    average_mode_matchup_score = sum(raw_mode_matchup_scores.values()) / len(raw_mode_matchup_scores)
    mode_matchup_scores = {
        mode: round(raw_mode_matchup_scores[mode] - average_mode_matchup_score, 2)
        for mode in MODE_LABEL_ORDER
    }
    favorable_ranked = sorted(mode_matchup_scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    unfavorable_ranked = sorted(mode_matchup_scores.items(), key=lambda item: (item[1], item[0]))
    favorable_modes = [mode for mode, score in favorable_ranked if score > 0][:2]
    unfavorable_modes = [mode for mode, score in unfavorable_ranked if score < 0][:2]

    if not favorable_modes:
        favorable_modes = [favorable_ranked[0][0]]
    if not unfavorable_modes:
        unfavorable_modes = [unfavorable_ranked[0][0]]

    return team_mode_scores, team_mode_labels, mode_matchup_scores, favorable_modes, unfavorable_modes


def _build_contextual_matchup_profile(
    members: list[TeamMember],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    team_mode_packages: list[str],
    team_win_condition_labels: list[str],
    offensive_coverage: dict[str, int],
    defensive_profile: dict[str, dict[str, float | int]],
    top_defensive_weaknesses: list[str],
    coverage_gaps: list[str],
) -> ContextualMatchupProfile:
    move_counts: Counter[str] = Counter()
    attack_type_counts: Counter[str] = Counter()
    ability_counts: Counter[str] = Counter()
    species_tokens: set[str] = set()
    fast_members = 0
    slow_members = 0
    bulky_members = 0
    frail_members = 0
    strong_attackers = 0
    priority_attacks = 0
    sleep_pressure = 0

    for member in members:
        species_tokens.update(_species_tokens_for_member(member))
        for ability_name in _member_context_ability_names(member):
            ability_counts[ability_name] += 1

        stats = _normalized_member_stats(member)
        bulk_total = stats["hp"] + stats["defense"] + stats["special_defense"]
        offense_total = max(stats["attack"], stats["special_attack"])
        speed_total = stats["speed"]

        if speed_total >= 145:
            fast_members += 1
        if speed_total <= 95:
            slow_members += 1
        if bulk_total >= 340:
            bulky_members += 1
        if bulk_total <= 290:
            frail_members += 1
        if offense_total >= 155:
            strong_attackers += 1

        for move in member.move_data:
            move_counts[move.api_name] += 1
            if move.damage_class != "status":
                attack_type_counts[move.type_name] += 1
                if move.priority > 0:
                    priority_attacks += 1
            if move.api_name in SLEEP_INDUCING_MOVES:
                sleep_pressure += 1

    total_damaging_lines = sum(attack_type_counts.values()) or 1
    weather_setters = pokemon_role_counts["weather_setter"] + utility_role_counts["weather"]
    terrain_setters = pokemon_role_counts["terrain_setter"] + utility_role_counts["terrain"]
    redirection = pokemon_role_counts["redirector"]
    screens = pokemon_role_counts["screen_setter"] + utility_role_counts["screen"]
    protective_turns = utility_role_counts["protection"]
    recovery_loop = utility_role_counts["recovery"] + utility_role_counts["healing_support"]
    hazard_control = pokemon_role_counts["hazard_control"]
    setup_pressure = round(
        1.0 * pokemon_role_counts["setup_sweeper"]
        + 0.5 * utility_role_counts["stat_boost"]
        + 0.35 * redirection
        + 0.25 * screens,
        2,
    )
    immediate_pressure = round(
        float(strong_attackers)
        + 0.6 * pokemon_role_counts["cleaner"]
        + 0.3 * priority_attacks,
        2,
    )

    def _resistance_count(type_name: str) -> int:
        return int(defensive_profile[type_name]["resistant_members"]) + int(defensive_profile[type_name]["immune_members"])

    water_resistance = _resistance_count("water")
    fire_resistance = _resistance_count("fire")
    electric_resistance = _resistance_count("electric")
    intimidate_support = ability_counts["intimidate"]
    priority_block_bypass = int(move_counts["fake-out"] > 0 and ability_counts["mold breaker"] > 0)
    fire_exposure = round(
        _weighted_defensive_exposure(defensive_profile, top_defensive_weaknesses, {"fire": 1.0}),
        2,
    )
    water_exposure = round(
        _weighted_defensive_exposure(defensive_profile, top_defensive_weaknesses, {"water": 1.0}),
        2,
    )
    rock_exposure = round(
        _weighted_defensive_exposure(defensive_profile, top_defensive_weaknesses, {"rock": 1.0}),
        2,
    )
    ground_exposure = round(
        _weighted_defensive_exposure(defensive_profile, top_defensive_weaknesses, {"ground": 1.0}),
        2,
    )
    flying_exposure = round(
        _weighted_defensive_exposure(defensive_profile, top_defensive_weaknesses, {"flying": 1.0}),
        2,
    )
    poison_exposure = round(
        _weighted_defensive_exposure(defensive_profile, top_defensive_weaknesses, {"poison": 1.0}),
        2,
    )

    grass_bias = round(attack_type_counts["grass"] / total_damaging_lines, 3)
    fighting_bias = round(attack_type_counts["fighting"] / total_damaging_lines, 3)
    psychic_bias = round(attack_type_counts["psychic"] / total_damaging_lines, 3)
    weather_punish_rain = round(
        float(offensive_coverage["grass"] + offensive_coverage["electric"])
        + 0.6 * weather_setters
        + 0.35 * water_resistance,
        2,
    )
    weather_punish_sun = round(
        float(offensive_coverage["water"] + offensive_coverage["ground"] + offensive_coverage["rock"])
        + 0.6 * weather_setters
        + 0.3 * fire_resistance,
        2,
    )
    weather_punish_sand = round(
        float(
            offensive_coverage["water"]
            + offensive_coverage["grass"]
            + offensive_coverage["fighting"]
            + offensive_coverage["ground"]
        )
        + 0.2 * bulky_members,
        2,
    )
    weather_punish_snow = round(
        float(offensive_coverage["fire"] + offensive_coverage["rock"] + offensive_coverage["steel"])
        + 0.2 * bulky_members,
        2,
    )
    tailwind_counter_tools = round(
        0.9 * move_counts["encore"]
        + 0.8 * move_counts["fake-out"]
        + 0.8 * move_counts["wide-guard"]
        + 0.7 * priority_attacks
        + 0.5 * pokemon_role_counts["speed_control"]
        + 0.35 * redirection
        + 0.25 * protective_turns,
        2,
    )
    # Only genuine Trick Room *denial* counts here (Taunt/Encore/Imprison the setter, your own
    # Trick Room to flip it, Fake Out to flinch the setup turn, sleep, anti-setup). Wide Guard and
    # Intimidate are spread/physical *mitigation*, not Room denial, and are credited separately with
    # accurate wording below so the matchup text never claims they "counter" Trick Room.
    trick_room_counter_tools = round(
        1.1 * move_counts["taunt"]
        + 1.0 * move_counts["encore"]
        + 1.25 * move_counts["imprison"]
        + 0.9 * move_counts["trick-room"]
        + 0.75 * move_counts["fake-out"]
        + 0.45 * utility_role_counts["anti_setup"]
        + 0.35 * sleep_pressure,
        2,
    )
    trick_room_counter_tools = round(
        trick_room_counter_tools + 0.8 * priority_block_bypass,
        2,
    )
    screen_counter_tools = round(
        0.9 * utility_role_counts["item_control"]
        + 0.8 * setup_pressure
        + 0.6 * utility_role_counts["anti_setup"]
        + 0.45 * strong_attackers,
        2,
    )
    setup_counter_tools = round(
        1.0 * move_counts["taunt"]
        + 0.9 * move_counts["encore"]
        + 0.8 * utility_role_counts["anti_setup"]
        + 0.5 * utility_role_counts["disruption"]
        + 0.35 * priority_attacks
        + 0.35 * sleep_pressure,
        2,
    )
    progress_pressure = round(
        float(
            utility_role_counts["item_control"]
            + utility_role_counts["trapping"]
            + utility_role_counts["phazing"]
        )
        + 0.6 * utility_role_counts["disruption"],
        2,
    )
    disruption_pressure = round(
        float(utility_role_counts["disruption"] + utility_role_counts["anti_setup"])
        + 0.7 * move_counts["encore"]
        + 0.8 * move_counts["taunt"],
        2,
    )
    mindgame_pressure = round(
        0.55 * ability_counts["illusion"]
        + 0.12 * int("dual_mode" in team_mode_packages)
        + 0.08
        * int(
            any(
                mode_name in {"tailroom", "rain_tailroom", "sun_tailroom"}
                for mode_name in team_mode_packages
            )
        )
        + 0.05 * utility_role_counts["pivoting"],
        2,
    )

    return ContextualMatchupProfile(
        species_tokens=species_tokens,
        move_counts=move_counts,
        attack_type_counts=attack_type_counts,
        ability_counts=ability_counts,
        team_mode_packages=tuple(team_mode_packages),
        team_win_condition_labels=tuple(team_win_condition_labels),
        fast_members=fast_members,
        slow_members=slow_members,
        bulky_members=bulky_members,
        frail_members=frail_members,
        strong_attackers=strong_attackers,
        weather_setters=weather_setters,
        terrain_setters=terrain_setters,
        redirection=redirection,
        screens=screens,
        protective_turns=protective_turns,
        recovery_loop=recovery_loop,
        hazard_control=hazard_control,
        priority_attacks=priority_attacks,
        sleep_pressure=sleep_pressure,
        setup_pressure=setup_pressure,
        immediate_pressure=immediate_pressure,
        water_resistance=water_resistance,
        fire_resistance=fire_resistance,
        electric_resistance=electric_resistance,
        intimidate_support=intimidate_support,
        priority_block_bypass=priority_block_bypass,
        fire_exposure=fire_exposure,
        water_exposure=water_exposure,
        rock_exposure=rock_exposure,
        ground_exposure=ground_exposure,
        flying_exposure=flying_exposure,
        poison_exposure=poison_exposure,
        grass_bias=grass_bias,
        fighting_bias=fighting_bias,
        psychic_bias=psychic_bias,
        weather_punish_rain=weather_punish_rain,
        weather_punish_sun=weather_punish_sun,
        weather_punish_sand=weather_punish_sand,
        weather_punish_snow=weather_punish_snow,
        tailwind_counter_tools=tailwind_counter_tools,
        trick_room_counter_tools=trick_room_counter_tools,
        screen_counter_tools=screen_counter_tools,
        setup_counter_tools=setup_counter_tools,
        progress_pressure=progress_pressure,
        disruption_pressure=disruption_pressure,
        mindgame_pressure=mindgame_pressure,
        coverage_gaps=tuple(coverage_gaps),
    )


def _push_context_reason(reasons: list[tuple[float, str]], impact: float, text: str) -> None:
    if abs(impact) < 0.05:
        return
    reasons.append((impact, text))


def _finalize_context_reasons(reasons: list[tuple[float, str]], limit: int = 3) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for _, text in sorted(reasons, key=lambda item: (abs(item[0]), item[1]), reverse=True):
        if text in seen:
            continue
        seen.add(text)
        ordered.append(text)
        if len(ordered) >= limit:
            break
    return ordered


def _bucket_context_reasons(reasons: list[tuple[float, str]], limit: int = 3) -> dict[str, object]:
    """Split signed matchup reasons into "why you have play" vs "why this is dangerous".

    A net-negative verdict can still carry positive mitigation reasons; surfacing them in one flat
    list reads as contradictory (e.g. a -2.2 Trick Room score "explained" by a survival note). We
    bucket by the sign of each reason's impact so a negative matchup always shows *why* it is
    negative, and expose the single strongest negative as the failure condition.
    """
    positives = _finalize_context_reasons([item for item in reasons if item[0] > 0], limit=limit)
    negatives = _finalize_context_reasons([item for item in reasons if item[0] < 0], limit=limit)
    return {
        "positives": positives,
        "negatives": negatives,
        "failure_condition": negatives[0] if negatives else None,
    }


def _structural_matchup_reason(own_archetype: str, target_archetype: str, *, negative: bool) -> str:
    """Explain a matchup whose edge comes from the broad archetype clash itself.

    The base archetype bias can drive a strongly +/- verdict with no contextual reason attached;
    without this, a -2.5 matchup could render with only mitigation notes (GPT feedback #2).
    """
    own = own_archetype.replace("_", " ")
    target = target_archetype.replace("_", " ")
    if negative:
        return (
            f"Structurally, {own} builds tend to give ground to {target} shells, and nothing on this "
            f"roster fully offsets that base disadvantage."
        )
    return f"Structurally, {own} builds tend to hold the edge into {target} shells."


# Display labels for the disruptive "tools" that matchup reason strings may cite. Reason
# strings must only name a tool when the team actually carries the move, so these labels are
# resolved against the team's real ``move_counts`` before they appear in any explainer.
COUNTER_TOOL_MOVE_LABELS: dict[str, str] = {
    "encore": "Encore",
    "fake-out": "Fake Out",
    "taunt": "Taunt",
    "wide-guard": "Wide Guard",
    "imprison": "Imprison",
    "trick-room": "reverse Trick Room",
    "haze": "Haze",
    "clear-smog": "Clear Smog",
}


def _join_clause(parts: list[str], conjunction: str = "and") -> str:
    cleaned = [part for part in parts if part]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} {conjunction} {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, {conjunction} {cleaned[-1]}"


def _present_move_labels(profile: ContextualMatchupProfile, move_keys: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    for key in move_keys:
        if profile.move_counts.get(key, 0) > 0:
            label = COUNTER_TOOL_MOVE_LABELS.get(key, key)
            if label not in labels:
                labels.append(label)
    return labels


def _team_has_item_control(profile: ContextualMatchupProfile) -> bool:
    return any(profile.move_counts.get(move_name, 0) > 0 for move_name in ITEM_CONTROL_MOVES)


def _counter_reason(
    tools: list[str],
    fallback: str,
    *,
    plural_verb: str,
    singular_verb: str,
    suffix: str,
) -> str:
    """Build a reason sentence that only cites tools actually present on the team.

    ``tools`` is the list of present tool labels; when empty the generic ``fallback`` noun
    phrase is used so the sentence never asserts a specific move the team does not run.
    """

    if not tools:
        subject, verb = fallback, plural_verb
    elif len(tools) == 1:
        subject, verb = tools[0], singular_verb
    else:
        subject, verb = _join_clause(tools), plural_verb
    return f"{subject} {verb} {suffix}"


def _fast_offense_counter_tools(profile: ContextualMatchupProfile, *, include_protect: bool) -> list[str]:
    tools = _present_move_labels(profile, ("encore", "fake-out", "wide-guard"))
    if profile.priority_attacks > 0:
        tools.append("priority")
    if profile.redirection > 0:
        tools.append("redirection")
    if include_protect and profile.protective_turns > 0:
        tools.append("layered Protect")
    return tools


# The strict set of moves that actually deny or contest Trick Room (not merely survive under it).
# Reused by the score term and the label helper so the two can never drift back out of sync.
TRICK_ROOM_DENIAL_MOVES = ("taunt", "encore", "imprison", "trick-room", "fake-out")


def _trick_room_counter_tool_labels(profile: ContextualMatchupProfile) -> list[str]:
    tools = _present_move_labels(profile, TRICK_ROOM_DENIAL_MOVES)
    if profile.priority_block_bypass > 0 and "Fake Out" not in tools:
        tools.append("Mold Breaker Fake Out")
    return tools


def _setup_counter_tool_labels(profile: ContextualMatchupProfile) -> list[str]:
    tools = _present_move_labels(profile, ("encore", "taunt", "haze"))
    if profile.priority_attacks > 0:
        tools.append("priority")
    return tools


def _screen_counter_tool_labels(profile: ContextualMatchupProfile) -> list[str]:
    tools: list[str] = []
    if _team_has_item_control(profile):
        tools.append("item control")
    tools.extend(_present_move_labels(profile, ("taunt", "encore", "haze")))
    return tools


def _score_broad_contextual_matchup(
    archetype: str,
    contextual_matchup_profile: ContextualMatchupProfile,
) -> tuple[float, list[tuple[float, str]]]:
    score = 0.0
    reasons: list[tuple[float, str]] = []

    if archetype == "hyper_offense":
        tailwind_help = 0.09 * min(contextual_matchup_profile.tailwind_counter_tools, 3.0)
        score += tailwind_help
        _push_context_reason(
            reasons,
            tailwind_help,
            _counter_reason(
                _fast_offense_counter_tools(contextual_matchup_profile, include_protect=True),
                "Its speed-control tools",
                plural_verb="give",
                singular_verb="gives",
                suffix="it real ways to blunt fast offense.",
            ),
        )

        bulk_help = 0.05 * min(contextual_matchup_profile.bulky_members, 4)
        score += bulk_help
        _push_context_reason(reasons, bulk_help, "The roster has enough raw bulk to survive the first fast tempo cycle.")

        setup_help = 0.03 * min(contextual_matchup_profile.setup_pressure, 3.0)
        score += setup_help
        _push_context_reason(reasons, setup_help, "Its setup pressure means one protected turn can flip the damage race.")

        if contextual_matchup_profile.weather_setters >= 3 and len(contextual_matchup_profile.team_mode_packages) >= 3:
            score -= 0.08
            _push_context_reason(reasons, -0.08, "Heavy weather and mode overlap can still make the opening anti-offense plan less coherent in practice.")

        if (
            contextual_matchup_profile.fast_members < 2
            and contextual_matchup_profile.move_counts["trick-room"] == 0
            and contextual_matchup_profile.move_counts["encore"] == 0
            and contextual_matchup_profile.move_counts["fake-out"] == 0
        ):
            score -= 0.18
            _push_context_reason(reasons, -0.18, "Low natural speed leaves little margin if the first fast turn cycle goes cleanly for the opponent.")

        fire_penalty = -0.08 * max(0.0, contextual_matchup_profile.fire_exposure)
        score += fire_penalty
        _push_context_reason(reasons, fire_penalty, "Repeated fire pressure is still hard for this roster to absorb cleanly.")

        flying_penalty = -0.08 * max(0.0, contextual_matchup_profile.flying_exposure)
        score += flying_penalty
        _push_context_reason(reasons, flying_penalty, "Fast flying pressure can force awkward trades into the back line.")

    elif archetype == "bulky_offense":
        immediate_help = 0.05 * min(contextual_matchup_profile.immediate_pressure, 4.0)
        score += immediate_help
        _push_context_reason(reasons, immediate_help, "The team still presents immediate enough damage to pressure bulky attackers before they snowball.")

        sustain_help = 0.05 * min(contextual_matchup_profile.recovery_loop, 3)
        score += sustain_help
        _push_context_reason(reasons, sustain_help, "Recovery and healing support help it survive the first trade cycle against bulky offense.")

        counter_help = 0.05 * min(contextual_matchup_profile.setup_counter_tools, 2.5)
        score += counter_help
        _push_context_reason(
            reasons,
            counter_help,
            _counter_reason(
                _setup_counter_tool_labels(contextual_matchup_profile),
                "Its anti-setup tools",
                plural_verb="make",
                singular_verb="makes",
                suffix="opposing setup windows less free.",
            ),
        )

        if contextual_matchup_profile.progress_pressure < 1.5:
            score -= 0.1
            _push_context_reason(reasons, -0.1, "It can struggle to force progress if bulky offense stabilizes the board early.")

    elif archetype == "balance":
        stabilize_help = 0.04 * min(contextual_matchup_profile.recovery_loop + contextual_matchup_profile.redirection, 4)
        score += stabilize_help
        _push_context_reason(reasons, stabilize_help, "Redirection and healing give it real midgame reset options against balance shells.")

        setup_help = 0.04 * min(contextual_matchup_profile.setup_pressure, 3.0)
        score += setup_help
        _push_context_reason(reasons, setup_help, "A credible setup plan helps it punish passive balance turns.")

        if contextual_matchup_profile.progress_pressure < 1.5 and contextual_matchup_profile.immediate_pressure < 3.0:
            score -= 0.14
            _push_context_reason(reasons, -0.14, "If it does not claim momentum early, patient balance teams can drag the game into slower trades.")

    elif archetype == "semi_stall":
        break_help = 0.06 * min(contextual_matchup_profile.setup_pressure + contextual_matchup_profile.progress_pressure, 4.0)
        score += break_help
        _push_context_reason(reasons, break_help, "Setup pressure and progress tools stop semi-stall shells from sitting comfortably forever.")

        disrupt_help = 0.04 * min(contextual_matchup_profile.disruption_pressure, 3.0)
        score += disrupt_help
        _push_context_reason(reasons, disrupt_help, "Disruption tools help it deny recovery loops and overly passive turns.")

        if contextual_matchup_profile.setup_pressure < 1.5 and contextual_matchup_profile.progress_pressure < 1.5:
            score -= 0.18
            _push_context_reason(reasons, -0.18, "Without real progress pressure, semi-stall can outlast it through repeated positioning turns.")

    elif archetype == "stall":
        break_help = 0.08 * min(contextual_matchup_profile.setup_pressure + contextual_matchup_profile.progress_pressure, 4.0)
        score += break_help
        _push_context_reason(reasons, break_help, "Its best stall matchups come from having a real setup or progress plan instead of only chip damage.")

        mindgame_help = 0.06 * min(contextual_matchup_profile.mindgame_pressure, 2.0)
        score += mindgame_help
        _push_context_reason(reasons, mindgame_help, "Mindgame pressure matters more against slower shells that give free scouting turns.")

        if contextual_matchup_profile.recovery_loop == 0 and contextual_matchup_profile.progress_pressure < 2.0:
            score -= 0.14
            _push_context_reason(reasons, -0.14, "If it cannot snowball quickly, long games against full stall can still become awkward.")

    elif archetype == "trick_room":
        contest_help = 0.09 * min(contextual_matchup_profile.trick_room_counter_tools, 3.0)
        score += contest_help
        _push_context_reason(
            reasons,
            contest_help,
            _counter_reason(
                _trick_room_counter_tool_labels(contextual_matchup_profile),
                "Its anti-room tools",
                plural_verb="give",
                singular_verb="gives",
                suffix="it real setup contesting play.",
            ),
        )

        bypass_help = 0.08 * contextual_matchup_profile.priority_block_bypass
        score += bypass_help
        _push_context_reason(reasons, bypass_help, "Mold Breaker Fake Out gives it a real line through Armor Tail-style setup turns.")

        intimidate_help = 0.06 * min(contextual_matchup_profile.intimidate_support, 2)
        score += intimidate_help
        _push_context_reason(reasons, intimidate_help, "Intimidate softens the physical Room attackers that usually punish fast teams once Room is active.")

        slow_help = 0.04 * min(contextual_matchup_profile.slow_members + contextual_matchup_profile.bulky_members, 5)
        score += slow_help
        _push_context_reason(reasons, slow_help, "Enough bulky or slower members still function if Trick Room goes up.")

        if (
            contextual_matchup_profile.fast_members >= 3
            and contextual_matchup_profile.move_counts["trick-room"] == 0
            and contextual_matchup_profile.move_counts["encore"] == 0
            and contextual_matchup_profile.move_counts["taunt"] == 0
            and contextual_matchup_profile.move_counts["fake-out"] == 0
            and contextual_matchup_profile.priority_block_bypass == 0
        ):
            score -= 0.18
            _push_context_reason(reasons, -0.18, "A very speed-heavy structure with no direct Room contest usually folds once Trick Room sticks.")

        fire_penalty = -0.05 * max(0.0, contextual_matchup_profile.fire_exposure)
        score += fire_penalty
        _push_context_reason(reasons, fire_penalty, "Common Room fire attackers can still punish awkward defensive overlaps.")

    return round(score, 2), reasons


def infer_meta_analysis(
    members: list[TeamMember],
    team_mode_scores: dict[str, float],
    team_mode_labels: list[str],
    mode_matchup_scores: dict[str, float],
    broad_matchup_scores: dict[str, float],
    favorable_modes: list[str],
    unfavorable_modes: list[str],
    contextual_matchup_profile: ContextualMatchupProfile,
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
    field_soundness: float = 0.0,
    field_soundness_reasons: list[str] | None = None,
) -> dict[str, object]:
    total_mode_weight = sum(TOURNAMENT_MODE_SNAPSHOTS[mode]["tournament_weight"] for mode in MODE_LABEL_ORDER)
    weighted_entries: list[dict[str, object]] = []

    for mode in MODE_LABEL_ORDER:
        tournament_weight = TOURNAMENT_MODE_SNAPSHOTS[mode]["tournament_weight"]
        matchup_score = mode_matchup_scores[mode]
        impact_score = round(tournament_weight * matchup_score, 2)
        weighted_entries.append(
            {
                "mode": mode,
                "tournament_weight": round(tournament_weight, 2),
                "meta_share": round(100 * tournament_weight / total_mode_weight, 1),
                "matchup_score": matchup_score,
                "impact_score": impact_score,
                "identity_score": team_mode_scores[mode],
                "standing": _classify_meta_matchup_standing(matchup_score),
            }
        )

    strongest_modes = [
        cast(str, entry["mode"])
        for entry in sorted(
            weighted_entries,
            key=lambda entry: (cast(float, entry["impact_score"]), cast(float, entry["tournament_weight"]), cast(str, entry["mode"])),
            reverse=True,
        )
        if cast(float, entry["impact_score"]) > 0
    ][:3]
    pressured_modes = [
        cast(str, entry["mode"])
        for entry in sorted(
            weighted_entries,
            key=lambda entry: (cast(float, entry["impact_score"]), -cast(float, entry["tournament_weight"]), cast(str, entry["mode"])),
        )
        if cast(float, entry["impact_score"]) < 0
    ][:3]

    top_weighted_entries = sorted(
        weighted_entries,
        key=lambda entry: (-cast(float, entry["tournament_weight"]), -abs(cast(float, entry["impact_score"])), cast(str, entry["mode"])),
    )
    tournament_rows = _build_tournament_meta_rows(
        members,
        mode_matchup_scores,
        broad_matchup_scores,
        contextual_matchup_profile,
        metadata_provider,
        regulation_id=regulation_id,
        field_soundness=field_soundness,
    )
    high_presence_team_modes = [
        mode_name
        for mode_name in team_mode_labels
        if TOURNAMENT_MODE_SNAPSHOTS[mode_name]["tournament_weight"] >= 0.55
    ]

    total_tournament_weight = sum(cast(float, row["meta_weight"]) for row in tournament_rows) or 1.0
    overall_score = round(
        sum(cast(float, row["matchup_score"]) * cast(float, row["meta_weight"]) for row in tournament_rows)
        / total_tournament_weight,
        2,
    )
    positive_weight_share = round(
        100
        * sum(cast(float, row["meta_weight"]) for row in tournament_rows if cast(float, row["matchup_score"]) >= 0.25)
        / total_tournament_weight,
        1,
    )
    negative_weight_share = round(
        100
        * sum(cast(float, row["meta_weight"]) for row in tournament_rows if cast(float, row["matchup_score"]) <= -0.25)
        / total_tournament_weight,
        1,
    )
    meta_label = _label_team_meta_standing(overall_score)
    common_pokemon = _build_common_meta_pokemon(regulation_id)

    strongest_targets = [
        cast(str, row["label"])
        for row in sorted(
            tournament_rows,
            key=lambda row: (cast(float, row["impact_score"]), cast(float, row["meta_share"]), cast(str, row["label"])),
            reverse=True,
        )
        if cast(float, row["impact_score"]) > 0
    ][:3]
    pressured_targets = [
        cast(str, row["label"])
        for row in sorted(
            tournament_rows,
            key=lambda row: (cast(float, row["impact_score"]), -cast(float, row["meta_share"]), cast(str, row["label"])),
        )
        if cast(float, row["impact_score"]) < 0
    ][:3]
    closest_pressure_targets = [
        cast(str, row["label"])
        for row in sorted(
            tournament_rows,
            key=lambda row: (cast(float, row["matchup_score"]), -cast(float, row["meta_share"]), cast(str, row["label"])),
        )
    ][:3]
    if not pressured_targets:
        pressured_targets = closest_pressure_targets

    positive_board_rows = [
        row for row in tournament_rows if cast(float, row["matchup_score"]) >= 0.25
    ]
    negative_board_rows = [
        row for row in tournament_rows if cast(float, row["matchup_score"]) <= -0.25
    ]
    even_board_count = len(tournament_rows) - len(positive_board_rows) - len(negative_board_rows)
    displayed_strongest_modes = strongest_modes or favorable_modes[:2]
    displayed_pressured_modes = pressured_modes or unfavorable_modes[:2]
    strongest_mode_share = round(
        sum(
            cast(float, entry["meta_share"])
            for entry in weighted_entries
            if cast(str, entry["mode"]) in displayed_strongest_modes
        ),
        1,
    )
    pressured_mode_share = round(
        sum(
            cast(float, entry["meta_share"])
            for entry in weighted_entries
            if cast(str, entry["mode"]) in displayed_pressured_modes
        ),
        1,
    )
    best_mode_entry = next(
        (
            entry
            for entry in sorted(
                weighted_entries,
                key=lambda entry: (
                    cast(float, entry["impact_score"]),
                    cast(float, entry["tournament_weight"]),
                    cast(str, entry["mode"]),
                ),
                reverse=True,
            )
            if cast(float, entry["impact_score"]) > 0
        ),
        top_weighted_entries[0] if top_weighted_entries else None,
    )
    weakest_mode_entry = next(
        (
            entry
            for entry in sorted(
                weighted_entries,
                key=lambda entry: (
                    cast(float, entry["impact_score"]),
                    -cast(float, entry["tournament_weight"]),
                    cast(str, entry["mode"]),
                ),
            )
            if cast(float, entry["impact_score"]) < 0
        ),
        None,
    )
    top_board_anchors = tournament_rows[:2]

    notes = [
        (
            f"Weighted against current Regulation M-A tournament-result teams, using mode, broad-style, and shell-context signals, this team grades as "
            f"{meta_label.replace('_', ' ')} at {overall_score}, with {positive_weight_share}% of the tracked board "
            f"scoring favorable and {negative_weight_share}% scoring pressured."
        )
    ]
    if field_soundness < 0 and field_soundness_reasons:
        soundness_points = _render_series(field_soundness_reasons)
        notes.append(
            f"That grade already reflects an absolute soundness penalty of {field_soundness:.2f} applied across the "
            f"whole board, because {soundness_points}."
        )
    if strongest_targets:
        strong_weight = round(
            sum(cast(float, row["meta_weight"]) for row in tournament_rows if cast(str, row["label"]) in strongest_targets)
            / total_tournament_weight
            * 100,
            1,
        )
        notes.append(
            f"The cleanest current team-level edges are into {_render_series(strongest_targets[:3])}, which together represent about {strong_weight}% of the tracked high-performing field."
        )
    if pressured_targets:
        pressured_weight = round(
            sum(cast(float, row["meta_weight"]) for row in tournament_rows if cast(str, row["label"]) in pressured_targets)
            / total_tournament_weight
            * 100,
            1,
        )
        if negative_weight_share > 0:
            notes.append(
                f"The heaviest current team-level pressure comes from {_render_series(pressured_targets[:2])}, which together account for about {pressured_weight}% of the tracked high-performing field."
            )
        else:
            notes.append(
                f"No board-level team is currently scored as a true losing matchup, but {_render_series(pressured_targets[:3])} are the closest live-field checks and still represent about {pressured_weight}% of the tracked high-performing field."
            )
    notes.append(
        f"Across the {len(tournament_rows)} current results-backed board teams, {len(positive_board_rows)} are favorable, {even_board_count} land in the even band, and {len(negative_board_rows)} are currently pressured by the board thresholds."
    )
    if displayed_strongest_modes:
        notes.append(
            f"At the mode layer, the cleanest weighted edges are into {_render_series([_render_mode_label(mode) for mode in displayed_strongest_modes])}, which together make up about {strongest_mode_share}% of tracked mode share."
        )
    if displayed_pressured_modes:
        if pressured_mode_share > 0:
            notes.append(
                f"The most relevant mode-level checks come from {_render_series([_render_mode_label(mode) for mode in displayed_pressured_modes])}, which together account for about {pressured_mode_share}% of tracked mode share."
            )
        else:
            notes.append(
                f"No tracked mode currently clears the pressure threshold, but the weakest live mode checks are {_render_series([_render_mode_label(mode) for mode in displayed_pressured_modes])}."
            )
    if best_mode_entry is not None:
        notes.append(
            f"The single best weighted mode edge is {_render_mode_label(cast(str, best_mode_entry['mode']))} at matchup {cast(float, best_mode_entry['matchup_score']):.2f} over {cast(float, best_mode_entry['meta_share']):.1f}% of mode share."
        )
    if weakest_mode_entry is not None:
        notes.append(
            f"The sharpest mode-level check is {_render_mode_label(cast(str, weakest_mode_entry['mode']))} at matchup {cast(float, weakest_mode_entry['matchup_score']):.2f} over {cast(float, weakest_mode_entry['meta_share']):.1f}% of mode share."
        )
    elif top_weighted_entries:
        fallback_mode_entry = top_weighted_entries[-1]
        notes.append(
            f"Even without a true pressured mode, the softest weighted check is {_render_mode_label(cast(str, fallback_mode_entry['mode']))} at matchup {cast(float, fallback_mode_entry['matchup_score']):.2f}."
        )
    if top_board_anchors:
        anchor_notes = [
            (
                f"{cast(str, row['label'])} ({cast(float, row['meta_share']):.1f}% share, "
                f"{cast(float, row['matchup_score']):+.2f} matchup)"
            )
            for row in top_board_anchors
        ]
        notes.append(
            f"The biggest current board anchors are {_render_series(anchor_notes)}, so those shells define a large share of the live-field positioning check by themselves."
        )
    if high_presence_team_modes:
        notes.append(
            f"The roster itself already overlaps with high-traffic M-A shells like {_render_series([_render_mode_label(mode) for mode in high_presence_team_modes])}, so it is not trying to win from a completely off-meta position."
        )
    else:
        notes.append(
            "The roster is leaning more on matchup quality than on directly mirroring the most repeated tournament shells."
        )

    return {
        "label": meta_label,
        "overall_score": overall_score,
        "positive_weight_share": positive_weight_share,
        "negative_weight_share": negative_weight_share,
        "strongest_modes": strongest_modes or favorable_modes[:2],
        "pressured_modes": pressured_modes or unfavorable_modes[:2],
        "strongest_targets": strongest_targets,
        "pressured_targets": pressured_targets,
        "tournament_rows": tournament_rows,
        "weighted_matchups": top_weighted_entries,
        "common_pokemon": common_pokemon,
        "notes": notes,
        "provenance": get_tournament_meta_provenance(regulation_id),
    }


def _build_tournament_meta_rows(
    members: list[TeamMember],
    mode_matchup_scores: dict[str, float],
    broad_matchup_scores: dict[str, float],
    contextual_matchup_profile: ContextualMatchupProfile,
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
    field_soundness: float = 0.0,
) -> list[dict[str, object]]:
    eligible_snapshots = [
        snapshot
        for snapshot in get_tournament_team_snapshots(regulation_id)
        if _is_meta_board_snapshot(snapshot)
    ]
    total_weight = sum(_tournament_snapshot_weight(snapshot) for snapshot in eligible_snapshots) or 1.0
    rows: list[dict[str, object]] = []

    for snapshot in eligible_snapshots:
        meta_weight = _tournament_snapshot_weight(snapshot)
        mode_score = _tournament_snapshot_mode_score(snapshot, mode_matchup_scores)
        broad_score = _tournament_snapshot_broad_score(snapshot, broad_matchup_scores)
        contextual_score, context_reasons, target_summary, interaction_summary = _score_tournament_snapshot_contextual_matchup(
            snapshot,
            contextual_matchup_profile,
            members,
            metadata_provider,
            regulation_id=regulation_id,
        )
        # ``field_soundness`` is an absolute, team-level offset (≤ 0 for structurally weak
        # teams) added uniformly to every shell, so relative shell ranking is preserved
        # while the overall grade reflects how field-viable the team actually is.
        matchup_score = round(
            0.34 * mode_score + 0.1 * broad_score + 0.56 * contextual_score + field_soundness, 2
        )
        rendered_key_pokemon = [
            _render_species_token(species_token)
            for species_token in cast(tuple[str, ...], snapshot["key_pokemon"])
        ]
        specific_reason = _meta_row_specific_reason(rendered_key_pokemon, contextual_matchup_profile, matchup_score)
        row_reasons = [specific_reason, *context_reasons] if specific_reason else context_reasons
        rows.append(
            {
                "slug": snapshot["slug"],
                "label": snapshot["label"],
                "source": snapshot["source"],
                "result_label": snapshot["result_label"],
                "modes": [_render_mode_label(mode_name) for mode_name in cast(tuple[str, ...], snapshot["modes"])],
                "key_cores": list(cast(tuple[str, ...], snapshot["key_cores"])),
                "key_pokemon": rendered_key_pokemon,
                "popularity_score": round(100 * cast(float, snapshot["popularity_weight"]), 1),
                "result_score": round(100 * cast(float, snapshot["result_weight"]), 1),
                "meta_weight": round(meta_weight, 4),
                "meta_share": round(100 * meta_weight / total_weight, 1),
                "contextual_score": contextual_score,
                "context_reasons": row_reasons,
                "target_summary": {
                    "resolved_targets": target_summary.resolved_targets,
                    "strong_answer_targets": target_summary.strong_answer_targets,
                    "shaky_answer_targets": target_summary.shaky_answer_targets,
                    "fast_cleanup_targets": target_summary.fast_cleanup_targets,
                    "average_offensive_pressure": target_summary.average_offensive_pressure,
                    "average_stab_pressure": target_summary.average_stab_pressure,
                },
                "interaction_summary": {
                    "redirection_targets": interaction_summary.redirection_targets,
                    "redirection_answers": interaction_summary.redirection_answers,
                    "setup_pressure_targets": interaction_summary.setup_pressure_targets,
                    "setup_denial_answers": interaction_summary.setup_denial_answers,
                    "spread_pressure_targets": interaction_summary.spread_pressure_targets,
                    "spread_answers": interaction_summary.spread_answers,
                    "ability_clause_targets": interaction_summary.ability_clause_targets,
                    "ability_clause_answers": interaction_summary.ability_clause_answers,
                    "tags": list(interaction_summary.tags),
                },
                "matchup_score": matchup_score,
                "impact_score": round(meta_weight * matchup_score, 2),
                "standing": _classify_meta_matchup_standing(matchup_score),
            }
        )

    return sorted(
        rows,
        key=lambda row: (-cast(float, row["meta_share"]), -abs(cast(float, row["impact_score"])), cast(str, row["label"])),
    )


def _meta_row_specific_reason(
    key_pokemon: list[str],
    profile: ContextualMatchupProfile,
    matchup_score: float,
) -> str | None:
    """A board-specific headline naming one concrete opposing threat and one concrete team tool (#8).

    Generic "Wide Guard and priority give you play" lines are too vague to explain a specific board;
    this ties an actual board anchor to a tool the roster actually runs (or to the absence of one).
    """
    if not key_pokemon:
        return None
    threat = key_pokemon[0]
    answers = _present_move_labels(profile, ("fake-out", "taunt", "encore", "wide-guard", "trick-room", "imprison"))
    if profile.redirection > 0:
        answers.append("redirection")
    if profile.screens > 0:
        answers.append("screens")
    if profile.priority_attacks > 0:
        answers.append("priority")
    if matchup_score >= 0.1 and answers:
        return f"Into {threat}-led boards, lean on your {_render_series(answers[:2])} to keep this matchup playable."
    if matchup_score <= -0.1:
        if answers:
            return f"{threat} headlines this board and your {answers[0]} only partly checks it, so expect to play from behind."
        return f"{threat} headlines this board and the roster has no dedicated tool to blunt it."
    return None


def _score_tournament_snapshot_contextual_matchup(
    snapshot: dict[str, object],
    contextual_matchup_profile: ContextualMatchupProfile,
    members: list[TeamMember],
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[float, list[str], SnapshotTargetMatchupSummary, SnapshotInteractionSummary]:
    modes = set(cast(tuple[str, ...], snapshot["modes"]))
    key_tokens = set(cast(tuple[str, ...], snapshot["key_pokemon"]))
    key_cores = cast(tuple[str, ...], snapshot["key_cores"])
    broad_mix = cast(dict[str, float], snapshot["broad_mix"])
    label_text = cast(str, snapshot["label"]).lower()
    core_text = " ".join(core.lower() for core in key_cores)
    score = 0.0
    reasons: list[tuple[float, str]] = []
    target_summary = _build_snapshot_target_matchup_summary(
        snapshot,
        members,
        metadata_provider,
        regulation_id=regulation_id,
    )
    interaction_summary = _build_snapshot_interaction_summary(
        snapshot,
        members,
        metadata_provider,
        regulation_id=regulation_id,
    )

    if target_summary.resolved_targets >= 2:
        target_pressure_bonus = 0.008 * min(target_summary.average_offensive_pressure, 2.5)
        score += target_pressure_bonus
        _push_context_reason(
            reasons,
            target_pressure_bonus,
            "The actual move pool gives it real pressure into several of this board's dual-type anchors.",
        )

        strong_target_threshold = max(2, (target_summary.resolved_targets + 2) // 3)
        if target_summary.strong_answer_targets >= strong_target_threshold:
            strong_target_bonus = 0.008 * min(target_summary.strong_answer_targets, 3)
            score += strong_target_bonus
            _push_context_reason(
                reasons,
                strong_target_bonus,
                "Several key anchors already face clean super-effective lines instead of only neutral trading.",
            )

        shaky_target_threshold = max(2, (target_summary.resolved_targets + 1) // 2)
        if target_summary.shaky_answer_targets >= shaky_target_threshold:
            shaky_target_penalty = -0.06 * min(target_summary.shaky_answer_targets, 3)
            score += shaky_target_penalty
            _push_context_reason(
                reasons,
                shaky_target_penalty,
                "Several anchors only face neutral pressure, so their dual-type pivots stay hard to punish cleanly.",
            )

        fast_cleanup_bonus = 0.02 * min(target_summary.fast_cleanup_targets, 2)
        score += fast_cleanup_bonus
        _push_context_reason(
            reasons,
            fast_cleanup_bonus,
            "Priority and real speed answers keep some of the board's faster payoffs from being safe endgame pieces.",
        )

        stab_shell_adjustment = (
            0.03 * max(0.0, -target_summary.average_stab_pressure)
            - 0.03 * max(0.0, target_summary.average_stab_pressure)
        )
        score += stab_shell_adjustment
        if target_summary.average_stab_pressure <= -0.08:
            _push_context_reason(
                reasons,
                stab_shell_adjustment,
                "Its defensive shell lines up reasonably well into the board's main STAB mix.",
            )
        elif target_summary.average_stab_pressure >= 0.08:
            _push_context_reason(
                reasons,
                stab_shell_adjustment,
                "The board's actual STAB mix still strains the current defensive shell even when the mode matchup looks playable.",
            )

    if interaction_summary.redirection_targets > 0:
        if interaction_summary.redirection_answers > 0:
            redirection_bonus = 0.04 * min(interaction_summary.redirection_answers, 2)
            score += redirection_bonus
            _push_context_reason(
                reasons,
                redirection_bonus,
                "Spread damage and board control give it real play through the redirection pieces protecting this shell's anchors.",
            )
        else:
            redirection_penalty = -0.04 * min(interaction_summary.redirection_targets, 2)
            score += redirection_penalty
            _push_context_reason(
                reasons,
                redirection_penalty,
                "The board's redirection support still makes it harder to turn neutral hits into clean progress.",
            )

    if interaction_summary.setup_pressure_targets > 0:
        if interaction_summary.setup_denial_answers > 0:
            setup_bonus = 0.04 * min(interaction_summary.setup_denial_answers, 2)
            score += setup_bonus
            _push_context_reason(
                reasons,
                setup_bonus,
                "Its anti-setup buttons give it a cleaner answer into the board's dedicated snowball lines.",
            )
        else:
            setup_penalty = -0.05 * min(interaction_summary.setup_pressure_targets, 2)
            score += setup_penalty
            _push_context_reason(
                reasons,
                setup_penalty,
                "The board still has real setup branches that are awkward to stop once the first turn stabilizes.",
            )

    if interaction_summary.spread_pressure_targets > 0:
        if interaction_summary.spread_answers > 0:
            spread_bonus = 0.01 * max(0, min(interaction_summary.spread_answers, 2) - 1)
            score += spread_bonus
            if spread_bonus > 0:
                _push_context_reason(
                    reasons,
                    spread_bonus,
                    "Wide Guard and layered Protect turns keep the board's main spread-damage shells from snowballing freely.",
                )
        else:
            spread_penalty = -0.04 * min(interaction_summary.spread_pressure_targets, 2)
            score += spread_penalty
            _push_context_reason(
                reasons,
                spread_penalty,
                "Repeated spread damage still forces awkward trades because the team has limited direct answers to it.",
            )

    if interaction_summary.ability_clause_targets > 0:
        if interaction_summary.ability_clause_answers > 0:
            ability_bonus = 0.04 * min(interaction_summary.ability_clause_answers, 2)
            score += ability_bonus
            _push_context_reason(
                reasons,
                ability_bonus,
                "Ability-specific lines are already covered, so the board's defensive clauses are not fully safe.",
            )
        else:
            ability_penalty = -0.03 * min(interaction_summary.ability_clause_targets, 2)
            score += ability_penalty
            _push_context_reason(
                reasons,
                ability_penalty,
                "One of the board's ability clauses still blanks a clean line unless the positioning turn goes perfectly.",
            )

    shared_modes = modes & set(contextual_matchup_profile.team_mode_packages)
    if shared_modes:
        shared_mode_bonus = 0.04 * len(shared_modes)
        score += shared_mode_bonus
        _push_context_reason(
            reasons,
            shared_mode_bonus,
            f"The roster already plays into {', '.join(_render_mode_label(mode_name) for mode_name in sorted(shared_modes))} patterns, so the pacing is familiar.",
        )

    if any(_team_preview_is_tailwind_mode(mode_name) for mode_name in modes):
        tailwind_counter_bonus = 0.08 * min(contextual_matchup_profile.tailwind_counter_tools, 3.0)
        score += tailwind_counter_bonus
        _push_context_reason(
            reasons,
            tailwind_counter_bonus,
            _counter_reason(
                _fast_offense_counter_tools(contextual_matchup_profile, include_protect=False),
                "Its speed-control tools",
                plural_verb="give",
                singular_verb="gives",
                suffix="it real play into Tailwind tempo.",
            ),
        )

        protect_bonus = 0.02 * min(contextual_matchup_profile.protective_turns, 4)
        score += protect_bonus
        _push_context_reason(reasons, protect_bonus, "Multiple Protect turns help it waste opposing Tailwind cycles.")
        if broad_mix.get("hyper_offense", 0.0) >= 0.4:
            immediate_pressure_bonus = 0.02 * min(contextual_matchup_profile.immediate_pressure, 3.0)
            score += immediate_pressure_bonus
            _push_context_reason(reasons, immediate_pressure_bonus, "It can push enough immediate damage to punish fragile fast leads.")
        if (
            contextual_matchup_profile.frail_members >= 3
            and contextual_matchup_profile.protective_turns < 3
            and contextual_matchup_profile.redirection == 0
        ):
            score -= 0.18
            _push_context_reason(reasons, -0.18, "Too many frail members with limited shielding makes the opening damage race shaky.")
        if (
            contextual_matchup_profile.slow_members >= 3
            and contextual_matchup_profile.move_counts["trick-room"] == 0
            and contextual_matchup_profile.move_counts["encore"] == 0
        ):
            score -= 0.12
            _push_context_reason(reasons, -0.12, "The team can get pinned if Tailwind shells force it to play from behind on speed.")
        if (
            broad_mix.get("hyper_offense", 0.0) >= 0.45
            and contextual_matchup_profile.fast_members < 3
            and contextual_matchup_profile.priority_attacks == 0
            and contextual_matchup_profile.move_counts["fake-out"] == 0
        ):
            score -= 0.32
            _push_context_reason(reasons, -0.32, "Very fast hyper-offense shells are dangerous when the roster lacks natural speed, priority, and Fake Out.")

    if any(_team_preview_is_trick_room_mode(mode_name) for mode_name in modes):
        trick_room_counter_bonus = 0.13 * min(contextual_matchup_profile.trick_room_counter_tools, 3.0)
        score += trick_room_counter_bonus
        _push_context_reason(
            reasons,
            trick_room_counter_bonus,
            _counter_reason(
                _trick_room_counter_tool_labels(contextual_matchup_profile),
                "Its anti-room tools",
                plural_verb="give",
                singular_verb="gives",
                suffix="it real Trick Room counterplay.",
            ),
        )

        intimidate_room_bonus = 0.05 * min(contextual_matchup_profile.intimidate_support, 2)
        score += intimidate_room_bonus
        _push_context_reason(reasons, intimidate_room_bonus, "Intimidate helps it survive the physical payoffs that normally cash in once Room goes up.")

        recovery_bonus = 0.04 * min(contextual_matchup_profile.recovery_loop, 3)
        score += recovery_bonus
        _push_context_reason(reasons, recovery_bonus, "Healing support keeps it from auto-losing long Room cycles.")

        wide_guard_room_bonus = 0.05 * min(contextual_matchup_profile.move_counts["wide-guard"], 2)
        score += wide_guard_room_bonus
        _push_context_reason(
            reasons,
            wide_guard_room_bonus,
            "Wide Guard blunts the spread attackers that cash in under Trick Room, but it does not stop the Room itself.",
        )
        if (
            contextual_matchup_profile.fast_members >= 3
            and contextual_matchup_profile.move_counts["trick-room"] == 0
            and contextual_matchup_profile.move_counts["taunt"] == 0
            and contextual_matchup_profile.move_counts["encore"] == 0
            and contextual_matchup_profile.move_counts["fake-out"] == 0
            and contextual_matchup_profile.priority_block_bypass == 0
        ):
            score -= 0.2
            _push_context_reason(reasons, -0.2, "A speed-heavy shell with no direct Trick Room contest is fragile once Room sticks.")
        if contextual_matchup_profile.slow_members >= 2:
            score += 0.08
            _push_context_reason(reasons, 0.08, "It still has enough slower pieces to function under opposing Trick Room.")

    if "rain" in modes:
        rain_punish_bonus = 0.08 * min(contextual_matchup_profile.weather_punish_rain, 3.5)
        score += rain_punish_bonus
        _push_context_reason(reasons, rain_punish_bonus, "Grass and Electric pressure give it real leverage into rain payoffs.")

        water_resist_bonus = 0.03 * min(contextual_matchup_profile.water_resistance, 3)
        score += water_resist_bonus
        _push_context_reason(reasons, water_resist_bonus, "The roster has enough water resistances to avoid drowning in rain chip races.")
    if "sun" in modes:
        sun_punish_bonus = 0.04 * min(contextual_matchup_profile.weather_punish_sun, 3.5)
        score += sun_punish_bonus
        _push_context_reason(reasons, sun_punish_bonus, "Rock, Ground, and Water coverage keeps sun from getting fully free turns.")

        fire_penalty = -0.24 * max(0.0, contextual_matchup_profile.fire_exposure)
        score += fire_penalty
        _push_context_reason(reasons, fire_penalty, "Its defensive shell still takes real strain from concentrated fire pressure.")

        flying_penalty = -0.1 * max(0.0, contextual_matchup_profile.flying_exposure)
        score += flying_penalty
        _push_context_reason(reasons, flying_penalty, "Flying coverage from sun shells creates awkward endgames for this build.")

        grass_penalty = -0.16 * contextual_matchup_profile.grass_bias
        score += grass_penalty
        _push_context_reason(reasons, grass_penalty, "A grass-heavy attack profile is naturally less comfortable into opposing sun.")
    if "sand" in modes:
        sand_bonus = 0.06 * min(contextual_matchup_profile.weather_punish_sand, 3.5)
        score += sand_bonus
        _push_context_reason(reasons, sand_bonus, "Water, Grass, and Fighting lines give it counterpressure into sand cores.")

        ground_penalty = -0.08 * max(0.0, contextual_matchup_profile.ground_exposure)
        score += ground_penalty
        _push_context_reason(reasons, ground_penalty, "Repeated Ground pressure still taxes the roster's positioning.")
    if "snow" in modes:
        snow_bonus = 0.05 * min(contextual_matchup_profile.weather_punish_snow, 3.0)
        score += snow_bonus
        _push_context_reason(reasons, snow_bonus, "Fire, Rock, and Steel coverage gives it useful counterplay into snow boards.")

        rock_penalty = -0.06 * max(0.0, contextual_matchup_profile.rock_exposure)
        score += rock_penalty
        _push_context_reason(reasons, rock_penalty, "Rock weakness still makes snow chip turns harder to navigate.")

    if any("screen" in core.lower() for core in key_cores) or "screens" in label_text:
        screens_bonus = 0.12 * min(contextual_matchup_profile.screen_counter_tools, 2.5)
        score += screens_bonus
        _push_context_reason(
            reasons,
            screens_bonus,
            _counter_reason(
                _screen_counter_tool_labels(contextual_matchup_profile),
                "Its offensive pressure",
                plural_verb="stop",
                singular_verb="stops",
                suffix="screens from becoming a free snowball.",
            ),
        )
    if "shell smash" in core_text:
        shell_smash_bonus = 0.11 * min(contextual_matchup_profile.setup_counter_tools, 2.5)
        score += shell_smash_bonus
        _push_context_reason(
            reasons,
            shell_smash_bonus,
            _counter_reason(
                _setup_counter_tool_labels(contextual_matchup_profile),
                "Its anti-setup tools",
                plural_verb="keep",
                singular_verb="keeps",
                suffix="Shell Smash lines more honest.",
            ),
        )

    if broad_mix.get("hyper_offense", 0.0) >= 0.45:
        ho_pressure_bonus = 0.04 * min(contextual_matchup_profile.immediate_pressure, 4.0)
        score += ho_pressure_bonus
        _push_context_reason(reasons, ho_pressure_bonus, "Its own immediate pressure helps it trade back into hyper-offense shells.")
        if (
            "setup_sweep" in contextual_matchup_profile.team_win_condition_labels
            and contextual_matchup_profile.redirection + contextual_matchup_profile.screens > 0
        ):
            score += 0.06
            _push_context_reason(reasons, 0.06, "Redirection or screens let its own setup plan punish reckless offensive lines.")
    if broad_mix.get("balance", 0.0) + broad_mix.get("semi_stall", 0.0) >= 0.55:
        balance_break_bonus = 0.04 * min(contextual_matchup_profile.setup_pressure, 3.0)
        score += balance_break_bonus
        _push_context_reason(reasons, balance_break_bonus, "Setup pressure stops slower boards from sitting in neutral forever.")
        if "perish_trap" in contextual_matchup_profile.team_win_condition_labels:
            score += 0.06
            _push_context_reason(reasons, 0.06, "Perish Trap-style endgames punish slower, positioning-heavy boards especially well.")

    if any(token in key_tokens for token in FIRE_PRESSURE_SPECIES):
        fire_answer_lines = (
            contextual_matchup_profile.attack_type_counts["ground"]
            + contextual_matchup_profile.attack_type_counts["rock"]
            + contextual_matchup_profile.attack_type_counts["water"]
        )
        fire_answer_bonus = 0.02 * min(fire_answer_lines, 4)
        score += fire_answer_bonus
        _push_context_reason(reasons, fire_answer_bonus, "The roster has at least some direct lines into common fire attackers.")
        if fire_answer_lines == 0:
            score -= 0.14
            _push_context_reason(reasons, -0.14, "It lacks direct offensive punishment for the board's main fire threats.")
        fire_shell_penalty = -0.14 * max(0.0, contextual_matchup_profile.fire_exposure)
        score += fire_shell_penalty
        _push_context_reason(reasons, fire_shell_penalty, "Its defensive overlaps still make sustained fire pressure uncomfortable.")
        if any(token in key_tokens for token in {"charizard", "charizard-mega-y"}):
            charizard_penalty = -0.12 * max(0.0, contextual_matchup_profile.flying_exposure)
            score += charizard_penalty
            _push_context_reason(reasons, charizard_penalty, "Charizard-style flying pressure pushes especially hard on the current defensive shell.")
        if contextual_matchup_profile.grass_bias >= 0.35:
            score -= 0.14
            _push_context_reason(reasons, -0.14, "Leaning this hard into Grass attacks makes repeated fire pivots much scarier.")
    if any(token in key_tokens for token in RAIN_PRESSURE_SPECIES):
        rain_answer_lines = (
            contextual_matchup_profile.attack_type_counts["grass"]
            + contextual_matchup_profile.attack_type_counts["electric"]
        )
        rain_answer_bonus = 0.03 * min(rain_answer_lines, 4)
        score += rain_answer_bonus
        _push_context_reason(reasons, rain_answer_bonus, "Grass and Electric hits give it clean punish lines into rain enablers.")
    if "archaludon" in key_tokens:
        coverage_into_archaludon = (
            contextual_matchup_profile.attack_type_counts["ground"]
            + contextual_matchup_profile.attack_type_counts["fighting"]
        )
        archaludon_bonus = 0.04 * min(coverage_into_archaludon, 3)
        score += archaludon_bonus
        _push_context_reason(reasons, archaludon_bonus, "Ground and Fighting pressure keeps Archaludon from feeling invulnerable.")
        if coverage_into_archaludon == 0:
            score -= 0.16
            _push_context_reason(reasons, -0.16, "Without Ground or Fighting pressure, Archaludon can anchor long sequences too safely.")
    if any(token in key_tokens for token in ROOM_SETTER_SPECIES):
        room_setter_bonus = 0.05 * min(contextual_matchup_profile.trick_room_counter_tools, 3)
        score += room_setter_bonus
        _push_context_reason(reasons, room_setter_bonus, "The roster has real lines to contest dedicated Trick Room setters.")
        if "farigiraf" in key_tokens and contextual_matchup_profile.priority_block_bypass > 0:
            armor_tail_bonus = 0.12 * contextual_matchup_profile.priority_block_bypass
            score += armor_tail_bonus
            _push_context_reason(reasons, armor_tail_bonus, "Mold Breaker Fake Out means Armor Tail does not make the setup turn fully safe.")
    if any(token in key_tokens for token in HAZARD_PRESSURE_SPECIES):
        hazard_answer_bonus = 0.04 * min(
            contextual_matchup_profile.attack_type_counts["ground"]
            + contextual_matchup_profile.attack_type_counts["steel"],
            2,
        )
        score += hazard_answer_bonus
        _push_context_reason(reasons, hazard_answer_bonus, "Ground and Steel coverage helps it pressure common hazard pieces.")
        if contextual_matchup_profile.hazard_control == 0:
            score -= 0.28
            _push_context_reason(reasons, -0.28, "With no hazard control, repeated chip from Glimmora-style boards adds up quickly.")
        poison_penalty = -0.12 * max(0.0, contextual_matchup_profile.poison_exposure)
        score += poison_penalty
        _push_context_reason(reasons, poison_penalty, "Poison exposure makes hazard-heavy boards noticeably harder to pivot around.")
        if broad_mix.get("hyper_offense", 0.0) >= 0.45 and contextual_matchup_profile.protective_turns < 5:
            score -= 0.12
            _push_context_reason(reasons, -0.12, "Hazard hyper-offense gets more dangerous when the roster cannot buy enough Protect turns.")
        if any(token in key_tokens for token in FIRE_PRESSURE_SPECIES):
            score -= 0.24
            _push_context_reason(reasons, -0.24, "Hazards layered with fire pressure create especially punishing chip races for this shell.")
    if "sneasler" in key_tokens:
        sneasler_answer_lines = min(
            contextual_matchup_profile.attack_type_counts["flying"]
            + contextual_matchup_profile.attack_type_counts["psychic"]
            + contextual_matchup_profile.priority_attacks
            + contextual_matchup_profile.intimidate_support,
            4,
        )
        sneasler_bonus = 0.04 * sneasler_answer_lines
        score += sneasler_bonus
    if any(token in key_tokens for token in SCREENS_PRESSURE_SPECIES):
        screen_species_bonus = 0.05 * min(contextual_matchup_profile.screen_counter_tools, 2.0)
        score += screen_species_bonus
        _push_context_reason(reasons, screen_species_bonus, "The build has enough screen-breaking tools to avoid getting buried under reflected bulk.")
    if any(token in key_tokens for token in SLEEP_PRESSURE_SPECIES):
        sleep_protect_bonus = 0.03 * min(contextual_matchup_profile.protective_turns, 4)
        score += sleep_protect_bonus
        _push_context_reason(reasons, sleep_protect_bonus, "Protect lets it stall sleep turns and scout powder lines more safely.")
        if contextual_matchup_profile.terrain_setters > 0:
            score += 0.06
            _push_context_reason(reasons, 0.06, "Its own terrain control helps blunt sleep-based openings.")
        if (
            contextual_matchup_profile.sleep_pressure == 0
            and contextual_matchup_profile.protective_turns < 3
            and contextual_matchup_profile.fast_members < 2
        ):
            score -= 0.12
            _push_context_reason(reasons, -0.12, "Low speed and limited Protect usage make sleep pressure harder to absorb.")
    if any(token in key_tokens for token in BULKY_GRASS_PRESSURE_SPECIES):
        anti_grass_lines = (
            contextual_matchup_profile.attack_type_counts["fire"]
            + contextual_matchup_profile.attack_type_counts["flying"]
            + contextual_matchup_profile.attack_type_counts["ice"]
            + contextual_matchup_profile.attack_type_counts["psychic"]
        )
        anti_grass_bonus = 0.03 * min(anti_grass_lines, 4)
        score += anti_grass_bonus
        _push_context_reason(reasons, anti_grass_bonus, "It carries enough anti-Grass coverage to keep bulky grasses from stonewalling the game.")
        if contextual_matchup_profile.grass_bias >= 0.35 and anti_grass_lines == 0:
            score -= 0.18
            _push_context_reason(reasons, -0.18, "Grass-on-Grass trades are rough when the build lacks real anti-Grass punishment.")
    if "kingambit" in key_tokens:
        kingambit_bonus = 0.02 * min(
            contextual_matchup_profile.attack_type_counts["fighting"]
            + contextual_matchup_profile.attack_type_counts["ground"],
            4,
        )
        score += kingambit_bonus
        _push_context_reason(reasons, kingambit_bonus, "Ground and Fighting hits keep Kingambit endgames more manageable.")
    if any(token in key_tokens for token in ILLUSION_SPECIES):
        illusion_penalty = -0.07 * max(0, 3 - contextual_matchup_profile.protective_turns)
        score += illusion_penalty
        _push_context_reason(reasons, illusion_penalty, "Limited Protect usage makes Zoroark-style illusion scouting more punishing.")

        illusion_bonus = 0.05 * contextual_matchup_profile.mindgame_pressure
        score += illusion_bonus
        _push_context_reason(reasons, illusion_bonus, "Its own layered modes and scouting tools reduce how badly illusion mindgames can snowball.")

    if "grassy_terrain" in contextual_matchup_profile.team_mode_packages and "sun" in modes and contextual_matchup_profile.fire_exposure > 0:
        score -= 0.12
        _push_context_reason(reasons, -0.12, "A Grassy shell into sun still amplifies the existing fire-pressure issue.")
    if "grassy_terrain" in contextual_matchup_profile.team_mode_packages and "rain" in modes:
        score += 0.08
        _push_context_reason(reasons, 0.08, "Grassy Terrain naturally gives it a better footing into rain sequences.")
    if (
        "misty_terrain" in contextual_matchup_profile.team_mode_packages
        and any(token in key_tokens for token in SLEEP_PRESSURE_SPECIES)
    ):
        score += 0.08
        _push_context_reason(reasons, 0.08, "Misty Terrain is a real asset into sleep-oriented boards.")
    if (
        "psyspam" in contextual_matchup_profile.team_win_condition_labels
        and any(token in key_tokens for token in {"archaludon", "incineroar", "kingambit", "scizor", "scizor-mega"})
    ):
        score -= 0.08
        _push_context_reason(reasons, -0.08, "Dark and Steel anchors make pure Psyspam-style progress less reliable here.")

    if (
        any(type_name in {"fire", "flying", "steel"} for type_name in contextual_matchup_profile.coverage_gaps)
        and (
            any(_team_preview_is_tailwind_mode(mode_name) for mode_name in modes)
            or "sun" in modes
        )
    ):
        score -= 0.16
        _push_context_reason(reasons, -0.16, "Current coverage gaps line up badly into the fast fire-flying tempo shells on this board.")
    if (
        "poison" in contextual_matchup_profile.coverage_gaps
        and any(token in key_tokens for token in HAZARD_PRESSURE_SPECIES)
    ):
        score -= 0.08
        _push_context_reason(reasons, -0.08, "A poison coverage gap shows up more when the opposing shell leans on hazard setters.")

    if broad_mix.get("hyper_offense", 0.0) >= 0.4 or any(_team_preview_is_tailwind_mode(mode_name) for mode_name in modes):
        mindgame_bonus = 0.04 * contextual_matchup_profile.mindgame_pressure
        score += mindgame_bonus
        _push_context_reason(reasons, mindgame_bonus, "Flexible mode presentation helps it avoid becoming fully predictable in preview.")

    bounded_score = max(-1.5, min(1.5, round(score, 2)))
    return bounded_score, _finalize_context_reasons(reasons), target_summary, interaction_summary


def _build_snapshot_target_matchup_summary(
    snapshot: dict[str, object],
    members: list[TeamMember],
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> SnapshotTargetMatchupSummary:
    if not members:
        return SnapshotTargetMatchupSummary(0, 0, 0, 0, 0.0, 0.0)

    offensive_pressures: list[float] = []
    stab_pressures: list[float] = []
    strong_answer_targets = 0
    shaky_answer_targets = 0
    fast_cleanup_targets = 0

    for species_token in cast(tuple[str, ...], snapshot["key_pokemon"]):
        target_species = _resolve_snapshot_species_data(
            species_token,
            metadata_provider,
            regulation_id=regulation_id,
        )
        if target_species is None:
            continue

        target_speed = compute_stat(
            target_species.base_speed,
            CHAMPIONS_MAX_STAT_SPS,
            nature=1,
        )
        best_multiplier = 0.0
        super_effective_lines = 0
        neutral_or_better_lines = 0
        fast_answers = 0
        priority_answers = 0

        for member in members:
            member_speed = _normalized_member_stats(member)["speed"]
            for move in member.move_data:
                if move.damage_class == "status":
                    continue

                multiplier = defensive_multiplier(target_species.types, move.type_name)
                best_multiplier = max(best_multiplier, multiplier)
                if multiplier >= 1.0:
                    neutral_or_better_lines += 1
                    if member_speed >= target_speed:
                        fast_answers += 1
                    if move.priority > 0:
                        priority_answers += 1
                if multiplier > 1.0:
                    super_effective_lines += 1

        offensive_pressure = min(
            3.0,
            max(0.0, best_multiplier - 1.0)
            + 0.18 * min(super_effective_lines, 4)
            + 0.05 * min(neutral_or_better_lines, 6)
            + 0.1 * int(fast_answers > 0)
            + 0.12 * int(target_species.base_speed >= 100 and priority_answers > 0),
        )
        offensive_pressures.append(offensive_pressure)

        if offensive_pressure >= 0.95:
            strong_answer_targets += 1
        elif offensive_pressure <= 0.2:
            shaky_answer_targets += 1

        if target_species.base_speed >= 100 and (priority_answers > 0 or fast_answers > 0):
            fast_cleanup_targets += 1

        target_stab_pressures = [
            (
                sum(_defensive_multiplier_for_member(member, target_type) for member in members) / len(members)
                - 1.0
            )
            for target_type in target_species.types
        ]
        stab_pressures.append(sum(target_stab_pressures) / len(target_stab_pressures))

    resolved_targets = len(offensive_pressures)
    if resolved_targets == 0:
        return SnapshotTargetMatchupSummary(0, 0, 0, 0, 0.0, 0.0)

    return SnapshotTargetMatchupSummary(
        resolved_targets=resolved_targets,
        strong_answer_targets=strong_answer_targets,
        shaky_answer_targets=shaky_answer_targets,
        fast_cleanup_targets=fast_cleanup_targets,
        average_offensive_pressure=round(sum(offensive_pressures) / resolved_targets, 2),
        average_stab_pressure=round(sum(stab_pressures) / resolved_targets, 2),
    )


def _build_snapshot_interaction_summary(
    snapshot: dict[str, object],
    members: list[TeamMember],
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> SnapshotInteractionSummary:
    if not members:
        return SnapshotInteractionSummary(0, 0, 0, 0, 0, 0, 0, 0, ())

    key_tokens = cast(tuple[str, ...], snapshot["key_pokemon"])
    label_text = cast(str, snapshot["label"]).lower()
    core_text = " ".join(core.lower() for core in cast(tuple[str, ...], snapshot["key_cores"]))
    move_names = {
        move.api_name
        for member in members
        for move in member.move_data
    }
    spread_damage_count = sum(
        1
        for member in members
        for move in member.move_data
        if _is_spread_damage_move(move)
    )
    protect_turns = sum(
        1
        for member in members
        for move in member.move_data
        if move.api_name in PROTECTION_MOVES
    )
    wide_guard_count = sum(
        1
        for member in members
        for move in member.move_data
        if move.api_name == "wide-guard"
    )
    setup_denial_tools = sum(
        1
        for move_name in move_names
        if move_name in ANTI_SETUP_MOVES | {"taunt", "encore", "imprison", "roar", "whirlwind", "dragon-tail", "fake-out", "psychic-fangs", "brick-break"}
    )
    mold_breaker_fake_out = any(
        "mold breaker" in _member_context_ability_names(member)
        and any(move.api_name == "fake-out" for move in member.move_data)
        for member in members
    )
    non_priority_room_contest = bool(move_names & {"taunt", "encore", "imprison", "trick-room"})

    redirection_targets = sum(1 for species_token in key_tokens if species_token in REDIRECTION_PRESSURE_SPECIES)
    setup_pressure_targets = sum(1 for phrase in SETUP_PRESSURE_CORE_PHRASES if phrase in core_text or phrase in label_text)
    spread_pressure_targets = sum(1 for species_token in key_tokens if species_token in SPREAD_PRESSURE_SPECIES)
    if "helping hand" in core_text and any(species_token in SPREAD_PRESSURE_SPECIES for species_token in key_tokens):
        spread_pressure_targets += 1

    redirection_answers = min(2, int(spread_damage_count > 0) + int(bool(move_names & {"taunt", "encore"})))
    setup_denial_answers = min(2, int(setup_denial_tools > 0) + int(setup_denial_tools >= 3))
    spread_answers = min(2, int(wide_guard_count > 0) + int(protect_turns >= 4))

    ability_clause_targets = 0
    ability_clause_answers = 0
    for species_token in key_tokens:
        target_species = _resolve_snapshot_species_data(
            species_token,
            metadata_provider,
            regulation_id=regulation_id,
        )
        for ability_name in _resolve_snapshot_ability_names(
            species_token,
            metadata_provider,
            regulation_id=regulation_id,
        ):
            if ability_name == "armor tail":
                ability_clause_targets += 1
                if mold_breaker_fake_out or non_priority_room_contest:
                    ability_clause_answers += 1
                continue
            blocked_types = DEFENSIVE_ABILITY_IMMUNITIES.get(ability_name, ())
            if not blocked_types or target_species is None:
                continue
            ability_clause_targets += 1
            if _team_has_unblocked_pressure_into_target(target_species, blocked_types, members):
                ability_clause_answers += 1

    tags: list[str] = []
    if redirection_targets > 0 and redirection_answers > 0:
        tags.append("redirection counterplay")
    if setup_pressure_targets > 0 and setup_denial_answers > 0:
        tags.append("setup denial")
    if spread_pressure_targets > 0 and spread_answers > 0:
        tags.append("spread counterplay")
    if ability_clause_targets > 0 and ability_clause_answers > 0:
        tags.append("ability-aware counterplay")

    return SnapshotInteractionSummary(
        redirection_targets=redirection_targets,
        redirection_answers=redirection_answers,
        setup_pressure_targets=setup_pressure_targets,
        setup_denial_answers=setup_denial_answers,
        spread_pressure_targets=spread_pressure_targets,
        spread_answers=spread_answers,
        ability_clause_targets=ability_clause_targets,
        ability_clause_answers=ability_clause_answers,
        tags=tuple(tags),
    )


def _resolve_snapshot_ability_names(
    species_token: str,
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[str, ...]:
    get_species_abilities = getattr(metadata_provider, "get_species_abilities", None)
    if callable(get_species_abilities):
        for candidate_name in _snapshot_species_name_candidates(species_token, regulation_id=regulation_id):
            try:
                ability_names = tuple(
                    ability_name
                    for ability_name in (
                        _normalized_ability_name(name)
                        for name in cast(Iterable[str], get_species_abilities(candidate_name))
                    )
                    if ability_name
                )
            except Exception:
                continue
            if ability_names:
                return ability_names
    return SNAPSHOT_ABILITY_CLAUSE_FALLBACKS.get(species_token, ())


def _team_has_unblocked_pressure_into_target(
    target_species: SpeciesData,
    blocked_types: tuple[str, ...],
    members: list[TeamMember],
) -> bool:
    blocked_type_names = set(blocked_types)
    return any(
        move.damage_class != "status"
        and move.type_name not in blocked_type_names
        and defensive_multiplier(target_species.types, move.type_name) >= 1.0
        for member in members
        for move in member.move_data
    )


def _is_spread_damage_move(move: MoveData) -> bool:
    return move.damage_class != "status" and move.target_name in SPREAD_DAMAGE_TARGET_NAMES


def _resolve_snapshot_species_data(
    species_token: str,
    metadata_provider: MetadataProvider,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> SpeciesData | None:
    for candidate_name in _snapshot_species_name_candidates(species_token, regulation_id=regulation_id):
        try:
            return metadata_provider.get_species(candidate_name)
        except Exception:
            continue
    return None


def _snapshot_species_name_candidates(
    species_token: str,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[str, ...]:
    rendered_name = _render_species_token(species_token)
    candidates: list[str] = []

    def _push(candidate: str | None) -> None:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    _push(rendered_name)
    _push(species_token)
    if regulation_id is not None:
        _push(resolve_regulation_species_name(rendered_name, regulation_id=regulation_id))
        _push(resolve_regulation_species_name(species_token, regulation_id=regulation_id))

    if rendered_name.startswith("Mega "):
        base_name = rendered_name[len("Mega "):]
        if base_name.endswith(" X") or base_name.endswith(" Y"):
            _push(f"{base_name[:-2]}-Mega-{base_name[-1]}")
        _push(f"{base_name}-Mega")
    if rendered_name.startswith("Alolan "):
        _push(f"{rendered_name[len('Alolan '):]}-Alola")
    if rendered_name.startswith("Hisuian "):
        _push(f"{rendered_name[len('Hisuian '):]}-Hisui")
    if rendered_name.endswith(" (M)"):
        base_name = rendered_name[:-4]
        _push(f"{base_name} (Male)")
        _push(f"{base_name}-M")
    if rendered_name.endswith(" (F)"):
        base_name = rendered_name[:-4]
        _push(f"{base_name} (Female)")
        _push(f"{base_name}-F")
    if species_token == "basculegion":
        _push("Basculegion (M)")
        _push("Basculegion (Male)")

    return tuple(candidates)


COMMON_META_POKEMON_CONTEXT: dict[str, dict[str, str]] = {
    "sinistcha": {
        "why_used": "It compresses redirection, healing, and slower-mode insurance into one slot, so balance, room, and hybrid shells can stay consistent without losing support density.",
        "what_it_does": "It keeps partners healthy with Hospitality or healing support, redirects key turns with Rage Powder, and still threatens real board progress with Matcha Gotcha or Trick Room positioning.",
    },
    "incineroar": {
        "why_used": "It remains one of the safest glue pieces because Intimidate and positioning utility patch physical pressure without forcing teams to give up tempo.",
        "what_it_does": "It slows openings with Fake Out and pivot pressure, softens setup attempts, and buys cleaner entry turns for the field's main sweepers and weather payoffs.",
    },
    "whimsicott": {
        "why_used": "Prankster speed control and disruption are still premium, so fast offenses keep reaching for it when they want immediate tempo without spending their mega slot on support.",
        "what_it_does": "It gets Tailwind online quickly, threatens Encore-style disruption, and creates fast openings for attackers like Garchomp, Mega Charizard Y, and Kingambit.",
    },
    "garchomp": {
        "why_used": "It fits into several current shells because it threatens offense immediately while still scaling well with Tailwind, sun, or bulky positioning support.",
        "what_it_does": "It applies broad physical pressure with strong Ground coverage and spread damage, forcing awkward switches and punishing teams that fall behind on speed control.",
    },
    "basculegion": {
        "why_used": "Rain and fast-offense shells keep it around because it converts speed control into immediate KOs better than most physical cleaners in the format.",
        "what_it_does": "It acts as the rain-enabled cleaner that cashes in on chipped boards and forces endgames once Pelipper, Tailwind, or support positioning has opened the field.",
    },
    "torkoal": {
        "why_used": "Sun and Trick Room teams still lean on it because one clean positioning turn can translate directly into overwhelming damage output.",
        "what_it_does": "It sets sun, threatens huge spread Fire damage, and gives slower control teams a direct punish once Trick Room or redirection support sticks.",
    },
    "charizard-mega-y": {
        "why_used": "Sun structures still lean on it because it gives them a self-contained weather engine and one of the format's best special nukes in a single slot.",
        "what_it_does": "It turns the board hostile immediately with harsh sunlight and high-output Fire pressure, especially once Tailwind or support positioning has already stabilized the turn order.",
    },
    "archaludon": {
        "why_used": "Rain and screens variants keep returning to it because it is both hard to remove and devastating once supported properly.",
        "what_it_does": "It functions as the bulky special payoff that converts rain, screens, or healing turns into snowball pressure and awkward trades for the opponent.",
    },
    "pelipper": {
        "why_used": "It is still the cleanest rain enabler for the format's Archaludon and Basculegion shells, so teams keep starting from it when they want consistent weather offense.",
        "what_it_does": "It sets rain, supports fast modes with Tailwind in relevant builds, and makes the backline start threatening boosted damage immediately.",
    },
    "kingambit": {
        "why_used": "Balance and offense teams both value it because it keeps priority endgames honest and punishes passive or overly defensive lines.",
        "what_it_does": "It acts as a cleaner and trade punisher, usually closing games with strong Dark or Steel pressure and priority once its partners have chipped the field.",
    },
    "aerodactyl": {
        "why_used": "Fast offense still likes it because it gives reliable speed control and immediate utility without demanding much support around it.",
        "what_it_does": "It threatens Tailwind leads, fast chip, and disruptive positioning turns that let stronger backline attackers start the game ahead on tempo.",
    },
    "glimmora": {
        "why_used": "Hazard-centric offenses use it because it pressures positioning from turn one while still fitting aggressive Tailwind shells.",
        "what_it_does": "It chips the opposing side, punishes contact and bad switching, and helps faster partners convert early momentum into lasting board damage.",
    },
    "sneasler": {
        "why_used": "Fast offense and dual-mega shells keep reaching for it because Unburden turns a single consumed item into a speed tier almost nothing outruns, letting it close games before slower control teams stabilize.",
        "what_it_does": "It opens with Fake Out, then snowballs with fast Fighting and Poison pressure and Dire Claw status, cleaning chipped boards and punishing teams that fall behind on speed.",
    },
    "floette-eternal": {
        "why_used": "Balance, Trick Room, and dual-mega shells lean on it because its Mega folds a top-tier Fairy special attacker and a durable support body into one flexible slot.",
        "what_it_does": "It threatens high-output Fairy damage through Light of Ruin while Flower Veil and its bulk let it stay in to support partners, anchoring both slow Trick Room and fast dual-mode lines.",
    },
    "charizard": {
        "why_used": "Sun and fast-offense shells lean on it because its Mega forms fold a self-contained weather engine and one of the format's best nukes into a single, flexible slot.",
        "what_it_does": "As Mega Charizard Y it sets harsh sunlight and fires off high-output special Fire damage; as Mega Charizard X it offers a physical Dragon/Fire alternative — either way it turns Tailwind and support turns straight into KO pressure.",
    },
    "tyranitar": {
        "why_used": "Sand and bulky-offense shells build around it because Sand Stream chips the field for free and its Mega gives them a hard-hitting, hard-to-remove backbone in one slot.",
        "what_it_does": "It sets sand to wear down the opposing side, soaks special hits, and threatens heavy Rock and Dark damage that punishes passive trades and fragile special attackers.",
    },
    "hydreigon": {
        "why_used": "Offense and dual-mode shells like it because Levitate plus a broad special movepool gives them safe pivots into Ground attacks and reliable spread damage without much support.",
        "what_it_does": "It pressures the field with strong Dark and Dragon coverage, weakens special attackers with Snarl, and forces awkward switches thanks to its immunity to Ground.",
    },
    "rotom-wash": {
        "why_used": "Balance and bulky shells keep it as glue because it pivots safely, spreads status, and answers the format's Water- and Ground-weak attackers from one resilient slot.",
        "what_it_does": "It pivots with Volt Switch, cripples physical threats with Will-O-Wisp, and chips the field with Hydro Pump while its Electric/Water typing dodges common offensive types.",
    },
    "corviknight": {
        "why_used": "Defensive and pivot-heavy shells rely on it because it patches physical pressure, provides speed control, and keeps recovering without giving up tempo.",
        "what_it_does": "It pivots with U-turn, sets Tailwind or stalls with Roost, and punishes contact and grounded attackers with Body Press behind its Steel/Flying bulk.",
    },
    "froslass": {
        "why_used": "Fast offense leans on it because it gives reliable speed control and disruption from turn one, and its Mega trades up into a real offensive threat without changing the lead plan.",
        "what_it_does": "It threatens fast Tailwind, hazards, and Destiny Bond trades, opening clean turns for the backline while its Ice/Ghost coverage chips key targets.",
    },
    "farigiraf": {
        "why_used": "Trick Room and balance shells value it because Armor Tail shuts off opposing priority and one bulky slot can both set the room and protect the win condition.",
        "what_it_does": "It sets Trick Room under pressure, supports with Helping Hand and Foul Play, and keeps slow attackers safe while the team flips the speed order.",
    },
}

MAX_COMMON_META_POKEMON = 10


# Families whose distinct forms demand different matchup prep but collapse to one base-species usage
# row (#7). The usage weight stays aggregated (forms share a base species), but we surface a per-row
# breakdown so prep isn't blurred across forms that need opposite answers.
META_FORM_BREAKDOWNS: dict[str, list[dict[str, str]]] = {
    "charizard": [
        {
            "form": "Mega Charizard Y",
            "plan": "Sun special attacker — Drought powers Heat Wave / Solar Beam; check it with rain or sand and special bulk.",
        },
        {
            "form": "Mega Charizard X",
            "plan": "Physical Dragon Dance setup attacker — Tough Claws Flare Blitz; check it with speed control or a physical wall.",
        },
    ],
}


def _annotate_meta_form_breakdowns(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Attach a form breakdown to any row whose species family needs form-specific prep (#7).

    Matches whether the board aggregates the family to one base row ("Charizard") or surfaces a single
    form ("Mega Charizard Y"); either way the breakdown lists every form that needs its own answer.
    """
    for row in rows:
        token = str(row.get("species", "")).strip().lower().replace(" ", "-")
        family = next((name for name in META_FORM_BREAKDOWNS if name in token), None)
        if family:
            row["form_breakdown"] = [dict(form) for form in META_FORM_BREAKDOWNS[family]]
    return rows


def _build_common_meta_pokemon(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> list[dict[str, object]]:
    # Prefer real overall usage from the live feed (share of sampled tournament teams
    # running each Pokemon). Only fall back to curated board-share derivation when no
    # live usage feed is configured/available.
    runtime_usage = get_runtime_common_meta_pokemon(regulation_id)
    if runtime_usage:
        return _annotate_meta_form_breakdowns([dict(row) for row in runtime_usage][:MAX_COMMON_META_POKEMON])

    eligible_snapshots = [
        snapshot
        for snapshot in get_tournament_team_snapshots(regulation_id)
        if _is_meta_board_snapshot(snapshot)
    ]
    total_weight = sum(_tournament_snapshot_weight(snapshot) for snapshot in eligible_snapshots) or 1.0
    species_weights: dict[str, float] = {}
    species_featured_teams: dict[str, list[tuple[float, str]]] = {}

    for snapshot in eligible_snapshots:
        meta_weight = _tournament_snapshot_weight(snapshot)
        snapshot_label = cast(str, snapshot["label"])
        for species_token in cast(tuple[str, ...], snapshot["key_pokemon"]):
            species_weights[species_token] = species_weights.get(species_token, 0.0) + meta_weight
            species_featured_teams.setdefault(species_token, []).append((meta_weight, snapshot_label))

    common_pokemon: list[dict[str, object]] = []
    ranked_species = sorted(
        species_weights.items(),
        key=lambda item: (-item[1], _render_species_token(item[0])),
    )[:MAX_COMMON_META_POKEMON]

    for species_token, weighted_presence in ranked_species:
        species_name = _render_species_token(species_token)
        context = COMMON_META_POKEMON_CONTEXT.get(species_token)
        featured_teams: list[str] = []
        seen_featured_teams: set[str] = set()
        for _, team_label in sorted(
            species_featured_teams.get(species_token, []),
            key=lambda item: (-item[0], item[1]),
        ):
            if team_label in seen_featured_teams:
                continue
            featured_teams.append(team_label)
            seen_featured_teams.add(team_label)
            if len(featured_teams) >= 3:
                break

        if context is None:
            if featured_teams:
                featured_shell_text = _render_series(featured_teams[:2])
                why_used = (
                    f"{species_name} keeps turning up in high-performing shells like {featured_shell_text}, "
                    f"and that spread across different team styles is what keeps it on the meta board."
                )
            else:
                why_used = (
                    f"{species_name} keeps turning up across a range of high-performing shells rather than "
                    f"being tied to one team style, which is what keeps it on the meta board."
                )
            what_it_does = (
                "Its spot here comes from broad usage across top teams rather than one signature role; "
                "teams reach for it in both offensive and supportive builds."
            )
        else:
            why_used = context["why_used"]
            what_it_does = context["what_it_does"]

        common_pokemon.append(
            {
                "species": species_name,
                "meta_share": round(100 * weighted_presence / total_weight, 1),
                "why_used": why_used,
                "what_it_does": what_it_does,
                "featured_teams": featured_teams,
            }
        )

    return _annotate_meta_form_breakdowns(common_pokemon)


def _tournament_snapshot_weight(snapshot: dict[str, object]) -> float:
    base_weight = 0.68 * cast(float, snapshot["popularity_weight"]) + 0.32 * cast(float, snapshot["result_weight"])
    field_relevance = cast(float, snapshot.get("field_relevance", 1.0))
    return base_weight * field_relevance


def _is_meta_board_snapshot(snapshot: dict[str, object]) -> bool:
    return cast(float, snapshot.get("field_relevance", 1.0)) >= 0.7


def _tournament_snapshot_mode_score(
    snapshot: dict[str, object],
    mode_matchup_scores: dict[str, float],
) -> float:
    mode_weights = cast(dict[str, float], snapshot.get("mode_weights", {}))
    if mode_weights:
        total_weight = sum(mode_weights.values()) or 1.0
        return sum(mode_matchup_scores[mode_name] * weight for mode_name, weight in mode_weights.items()) / total_weight

    modes = cast(tuple[str, ...], snapshot["modes"])
    if not modes:
        return 0.0
    return sum(mode_matchup_scores[mode_name] for mode_name in modes) / len(modes)


def _tournament_snapshot_broad_score(
    snapshot: dict[str, object],
    broad_matchup_scores: dict[str, float],
) -> float:
    broad_mix = cast(dict[str, float], snapshot["broad_mix"])
    total_weight = sum(broad_mix.values()) or 1.0
    return sum(broad_matchup_scores[archetype] * weight for archetype, weight in broad_mix.items()) / total_weight


def _classify_meta_matchup_standing(matchup_score: float) -> str:
    if matchup_score >= 0.75:
        return "favored"
    if matchup_score >= 0.15:
        return "slightly_favored"
    if matchup_score <= -0.75:
        return "pressured"
    if matchup_score <= -0.15:
        return "slightly_pressured"
    return "even"


def _label_team_meta_standing(overall_score: float) -> str:
    # Bands retuned alongside the absolute soundness penalty so "solid"/"strong" mean
    # genuine field positioning rather than the default, and structurally weak teams land
    # clearly in the shaky/pressured range.
    if overall_score >= 0.55:
        return "strong"
    if overall_score >= 0.3:
        return "solid"
    if overall_score > -0.15:
        return "even"
    if overall_score > -0.5:
        return "shaky"
    return "pressured"


def infer_team_difficulty(
    members: list[TeamMember],
    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    primary_team_archetype: str,
) -> tuple[str, float, list[str]]:
    move_counts = Counter()
    fast_members = 0
    very_slow_members = 0

    for member, classified_moves in classified_members:
        if member.species_data.base_speed >= 100:
            fast_members += 1
        if member.species_data.base_speed <= 50:
            very_slow_members += 1
        for move, _ in classified_moves:
            move_counts[move.api_name] += 1

    setup_sweepers = pokemon_role_counts["setup_sweeper"]
    supports = pokemon_role_counts["support"]
    screen_setters = pokemon_role_counts["screen_setter"]
    pivots = pokemon_role_counts["pivot"] + pokemon_role_counts["bulky_pivot"]
    field_setters = pokemon_role_counts["weather_setter"] + pokemon_role_counts["terrain_setter"]
    defensive_backbone = pokemon_role_counts["bulky_support"] + pokemon_role_counts["bulky_attacker"] + pokemon_role_counts["bulky_pivot"]
    trapping_tools = utility_role_counts["trapping"] + pokemon_role_counts["trapper"]
    trick_room_moves = move_counts["trick-room"]
    perish_song_moves = move_counts["perish-song"]
    support_branches = supports + screen_setters + pokemon_role_counts["redirector"]
    speed_modes = pokemon_role_counts["speed_control"] + pokemon_role_counts["tailwind_setter"] + pokemon_role_counts["trick_room_setter"]

    difficulty_score = 3.0
    difficulty_factors: list[str] = []

    if trick_room_moves >= 2:
        difficulty_score += 2.0
        difficulty_factors.append(
            f"The team has {trick_room_moves} Trick Room setters, so you need to manage when to reverse move order and count those turns carefully."
        )
    elif trick_room_moves == 1:
        difficulty_score += 1.2
        difficulty_factors.append(
            "The team carries one Trick Room line, which adds a second speed plan you need to deploy at the right moment."
        )

    if setup_sweepers >= 2:
        difficulty_score += 1.0
        difficulty_factors.append(
            f"There are {setup_sweepers} setup sweepers, so many games hinge on choosing the correct turn to boost instead of attacking immediately."
        )
    elif setup_sweepers == 1:
        difficulty_score += 0.4
        difficulty_factors.append(
            "One of the main win routes is a setup sweeper, so finding even a single safe boost turn matters."
        )

    if support_branches >= 3:
        difficulty_score += 0.8
        difficulty_factors.append(
            f"The team has {support_branches} major support pieces through support roles, screens, or redirection, so each turn can branch into many reasonable lines."
        )
    elif support_branches >= 2:
        difficulty_score += 0.4
        difficulty_factors.append(
            "Support sequencing matters here: early utility turns often decide whether the attackers get clean openings later."
        )

    if pivots >= 2 or utility_role_counts["pivoting"] >= 2:
        difficulty_score += 0.8
        difficulty_factors.append(
            "The team leans on pivoting and repositioning, so tempo and safe switches matter more than on a straight damage team."
        )

    if field_setters >= 1:
        difficulty_score += 0.6
        difficulty_factors.append(
            "Weather or terrain management matters here, so part of the difficulty is keeping the right field effect active at the right time."
        )

    if speed_modes >= 3:
        difficulty_score += 0.4
        difficulty_factors.append(
            f"The team has {speed_modes} speed-control pieces, which is powerful but means you need to choose the right speed mode for each matchup."
        )

    if fast_members >= 2 and very_slow_members >= 2:
        difficulty_score += 1.0
        difficulty_factors.append(
            "Fast attackers and very slow attackers are both present, so the team can pull in opposite directions if you commit to the wrong mode."
        )

    if perish_song_moves >= 1 and trapping_tools >= 1:
        difficulty_score += 1.4
        difficulty_factors.append(
            "Perish Trap endgames are detail-heavy because you must track the timer, the switch map, and which board states are actually winning."
        )

    if primary_team_archetype == "trick_room":
        difficulty_score += 0.8
    elif primary_team_archetype == "perish_trap":
        difficulty_score += 0.8
    elif primary_team_archetype == "balance":
        difficulty_score -= 0.6
        difficulty_factors.append(
            "The balance shell is a forgiving point: you usually have more than one playable line instead of one all-in mode."
        )
    elif primary_team_archetype == "bulky_offense":
        difficulty_score -= 0.4
        difficulty_factors.append(
            "Bulky offense is usually easier to pilot than pure setup or hard room because your damage plan still has some room for mistakes."
        )
    elif primary_team_archetype == "hyper_offense" and screen_setters >= 1:
        difficulty_score -= 0.5
        difficulty_factors.append(
            "Screens make the opening turns more scripted, which lowers the execution load once that support is in place."
        )

    if defensive_backbone >= 3:
        difficulty_score -= 0.4
        difficulty_factors.append(
            "A solid bulky backbone gives the team some room to absorb a bad turn or an awkward trade."
        )

    difficulty_score = round(min(max(difficulty_score, 1.0), 10.0), 2)
    if difficulty_score <= 3.5:
        difficulty_label = "low"
    elif difficulty_score <= 5.5:
        difficulty_label = "moderate"
    elif difficulty_score <= 7.5:
        difficulty_label = "high"
    else:
        difficulty_label = "very_high"

    if not difficulty_factors:
        difficulty_factors.append(
            "The game plan is fairly direct: attack, trade well, and use only a small number of support branches."
        )

    return difficulty_label, difficulty_score, difficulty_factors[:6]


def infer_beginner_guidance(
    members: list[TeamMember],
    classified_members: list[tuple[TeamMember, list[tuple[MoveData, tuple[str, ...]]]]],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    primary_team_archetype: str,
    team_speed_tier: str,
    coverage_gaps: list[str],
    team_win_condition_labels: list[str],
) -> list[str]:
    notes: list[str] = []
    move_counts: Counter[str] = Counter()
    total_moves = 0
    status_moves = 0
    utility_tilt_moves = 0
    support_tilted_members: list[str] = []
    physical_moves = 0
    special_moves = 0

    for member, classified_moves in classified_members:
        member_name = member.pokemon_set.display_name
        item_name = _normalized_item_name(member.pokemon_set.item)
        rendered_item = member.pokemon_set.item or "its Choice item"
        member_support_actions = 0
        member_damaging_moves = 0
        protection_conflicts: list[str] = []
        choice_status_conflicts: list[str] = []

        for move, move_roles in classified_moves:
            total_moves += 1
            move_counts[move.api_name] += 1
            if move.damage_class == "status":
                status_moves += 1
            else:
                member_damaging_moves += 1
                if move.damage_class == "physical":
                    physical_moves += 1
                elif move.damage_class == "special":
                    special_moves += 1

            if move.damage_class == "status" or move_roles:
                utility_tilt_moves += 1
                member_support_actions += 1

            if item_name in CHOICE_ITEMS:
                if _is_protection_move(move.api_name, move.short_effect.lower()):
                    protection_conflicts.append(move.name)
                elif move.damage_class == "status":
                    choice_status_conflicts.append(move.name)

        if member_support_actions >= 3 and member_damaging_moves <= 1:
            support_tilted_members.append(member_name)

        if protection_conflicts:
            notes.append(
                f"{member_name} is holding {rendered_item} but also has {_render_series(protection_conflicts)}. Choice items lock the user into its first move, so protection usually clashes with that set."
            )
        elif choice_status_conflicts:
            notes.append(
                f"{member_name} is holding {rendered_item} with status move {_render_series(choice_status_conflicts)}. Choice users usually want four attacks unless that utility move is the whole plan."
            )

    damaging_moves = total_moves - status_moves
    offensive_roles = sum(
        pokemon_role_counts[role]
        for role in (
            "physical_sweeper",
            "special_sweeper",
            "setup_sweeper",
            "cleaner",
            "bulky_attacker",
        )
    )

    if utility_tilt_moves >= max(14, damaging_moves + 2):
        note = (
            f"This build is very support-heavy: {utility_tilt_moves} of {total_moves} moves are support or board-control actions. "
            "That gives you options, but newer players still need a clear plan for which members are actually supposed to finish games."
        )
        if support_tilted_members:
            note += f" The most dedicated support slots are {_render_series(support_tilted_members)}."
        notes.append(note)
    elif utility_tilt_moves >= 12:
        notes.append(
            f"This build leans support-first: {utility_tilt_moves} of {total_moves} moves are support or board-control actions. Make sure each support turn is buying a later knockout or safer board state."
        )

    if utility_tilt_moves >= 12 and offensive_roles <= 2:
        notes.append(
            f"Only {offensive_roles} member{'s' if offensive_roles != 1 else ''} currently read as primary attackers or cleaners. Identify your main damage plan before the battle starts."
        )

    if move_counts["tailwind"] + move_counts["trick-room"] + utility_role_counts["speed_control"] == 0:
        if team_speed_tier in {"fast", "very_fast"}:
            notes.append(
                "The team has no dedicated speed-control move. It is relying on natural Speed instead, so opposing Tailwind or Trick Room can flip games quickly."
            )
        else:
            notes.append(
                "The team has no dedicated speed-control move. If it falls behind in Speed, it has very few tools to take control of move order back."
            )

    stabilizing_tools = (
        pokemon_role_counts["fake_out_support"]
        + pokemon_role_counts["redirector"]
        + utility_role_counts["screen"]
        + utility_role_counts["pivoting"]
    )
    if stabilizing_tools == 0:
        notes.append(
            "The team has no Fake Out, redirection, screens, or pivoting move to buy a safer turn. When the board gets awkward, it mostly has to attack straight through it."
        )

    anti_setup_tools = utility_role_counts["disruption"] + utility_role_counts["anti_setup"] + utility_role_counts["phazing"]
    if anti_setup_tools == 0:
        notes.append(
            "The team has no clear anti-setup button such as Taunt, Haze, Encore, or phazing. Opposing setup usually has to be answered with direct damage."
        )

    if team_speed_tier == "mixed" and move_counts["tailwind"] + move_counts["trick-room"] <= 1:
        notes.append(
            "The roster mixes fast and slow attackers, but it only has one real speed-mode button. Some members may be stranded if that single mode is denied."
        )

    if team_speed_tier in {"slow", "trick_room_slow"} and move_counts["trick-room"] == 0:
        notes.append(
            "The roster is naturally slow, but it has no Trick Room button of its own. Faster teams can force it to take hits before it gets to play its preferred pace."
        )

    if pokemon_role_counts["setup_sweeper"] >= 1 and stabilizing_tools <= 1:
        notes.append(
            "The team wants setup turns, but it has very few tools like Fake Out, redirection, screens, or pivoting to create those openings safely."
        )

    if not team_win_condition_labels and offensive_roles <= 2:
        notes.append(
            "The analyzer does not see one strong endgame package yet. Before preview ends, decide which member or pairing is actually supposed to close games."
        )

    if physical_moves >= 8 and special_moves <= 2:
        notes.append(
            "Damage is heavily physical, so Intimidate and strong physical walls can tax the team unless positioning or support breaks them first."
        )
    elif special_moves >= 8 and physical_moves <= 2:
        notes.append(
            "Damage is heavily special, so Assault Vest cores and special walls may be harder to crack without setup or field control."
        )

    if (
        primary_team_archetype in {"balance", "bulky_offense", "semi_stall", "stall"}
        and utility_role_counts["recovery"] + pokemon_role_counts["healing_support"] == 0
    ):
        notes.append(
            "For a slower or bulkier team, there is very little recovery or healing support. Long games may become harder once chip damage starts to stick."
        )

    if utility_role_counts["protection"] <= 1 and primary_team_archetype not in {"hyper_offense", "perish_trap"}:
        notes.append(
            f"The team only carries {utility_role_counts['protection']} protection move{'s' if utility_role_counts['protection'] != 1 else ''}. In doubles, that makes it harder to scout targets or stall out Tailwind, weather, and Trick Room turns."
        )

    if len(coverage_gaps) >= 4:
        highlighted_gaps = ", ".join(type_name.replace("_", " ").title() for type_name in coverage_gaps[:3])
        notes.append(
            f"The current attack spread still struggles to pressure {highlighted_gaps}. Against those types, support turns need to create especially clean damage positions."
        )

    # Fairy / Mega Floette defensive-pressure check (#9): hitting Fairy super-effectively is NOT the
    # same as having a defensive switch-in. Flag a team with no Fairy resist even when it runs Steel.
    fairy_resists = any(_defensive_multiplier_for_member(member, "fairy") < 1.0 for member in members)
    if not fairy_resists:
        has_fairy_offense = any(
            move.damage_class != "status" and move.type_name in {"steel", "poison"}
            for _, classified_moves in classified_members
            for move, _ in classified_moves
        )
        if has_fairy_offense:
            notes.append(
                "No member resists Fairy. You can hit Fairy attackers super-effectively, but offensive "
                "Steel/Poison coverage is not a defensive answer: nothing here safely sponges Dazzling "
                "Gleam or denies a Mega Floette the room to set up."
            )
        else:
            notes.append(
                "No member resists Fairy and the team has no Steel or Poison attack to pressure it, so "
                "Fairy attackers like Mega Floette can chip and set up almost unchecked."
            )

    if not notes:
        notes.append(
            "No major beginner-facing build issues stand out. Focus on picking the right speed plan and knowing which members are meant to close games."
        )

    return notes[:8]


def infer_team_preview(
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    primary_team_style: str,
    team_mode_packages: list[str],
    team_win_condition_labels: list[str],
    unfavorable_matchups: list[str],
    unfavorable_modes: list[str],
    top_defensive_weaknesses: list[str],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    meta_analysis: dict[str, object],
) -> tuple[list[dict[str, object]], list[str], list[str], list[str], list[str]]:
    plan_focuses = _build_team_preview_focuses(primary_team_style, team_mode_packages, team_win_condition_labels)
    plan_descriptors = _build_team_preview_descriptors(plan_focuses, meta_analysis)
    bring_plans: list[dict[str, object]] = []
    member_lookup = {member.pokemon_set.display_name: member for member in members}

    for index, descriptor in enumerate(plan_descriptors):
        focus = cast(str, descriptor["focus"])
        opponent_mode = cast(str | None, descriptor.get("opponent_mode"))
        recommended_into = cast(list[str], descriptor.get("recommended_into", []))
        board_anchor = cast(dict[str, object] | None, descriptor.get("board_anchor"))
        lead_pair, pick_four = _select_team_preview_plan(
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            opponent_mode,
            bring_plans,
            board_anchor,
        )
        back_line = [member_name for member_name in pick_four if member_name not in lead_pair]
        if not pick_four:
            continue

        member_reasons = _build_team_preview_member_reasons(
            pick_four,
            lead_pair,
            back_line,
            member_lookup,
            member_roles,
            focus,
            opponent_mode,
            board_anchor,
        )
        bring_plans.append(
            {
                "label": _render_team_preview_plan_label(focus, index, opponent_mode),
                "summary": _summarize_team_preview_plan(
                    focus,
                    lead_pair,
                    back_line,
                    opponent_mode,
                    board_anchor,
                    member_lookup,
                    member_roles,
                ),
                "leads": lead_pair,
                "back": back_line,
                "pick_four": pick_four,
                "recommended_into": recommended_into,
                "member_reasons": member_reasons,
            }
        )

    if not bring_plans:
        fallback_pick_four = [member.pokemon_set.display_name for member in members[:4]]
        fallback_leads = fallback_pick_four[:2]
        fallback_back = fallback_pick_four[2:4]
        bring_plans.append(
            {
                "label": "Default plan",
                "summary": _summarize_team_preview_plan(
                    "safe_default",
                    fallback_leads,
                    fallback_back,
                    None,
                    None,
                    member_lookup,
                    member_roles,
                ),
                "leads": fallback_leads,
                "back": fallback_back,
                "pick_four": fallback_pick_four,
                "recommended_into": [],
                "member_reasons": _build_team_preview_member_reasons(
                    fallback_pick_four,
                    fallback_leads,
                    fallback_back,
                    member_lookup,
                    member_roles,
                    "safe_default",
                    None,
                    None,
                ),
            }
        )

    watch_teams = _build_team_preview_watch_teams(unfavorable_matchups, unfavorable_modes)
    watch_pokemon = _build_team_preview_watch_pokemon(members, unfavorable_modes)
    strategy_notes = _build_team_preview_strategy_notes(
        members,
        member_roles,
        team_mode_packages,
        team_win_condition_labels,
        bring_plans,
    )
    counterplay_notes = _build_team_preview_counterplay_notes(
        member_roles,
        team_win_condition_labels,
        unfavorable_matchups,
        unfavorable_modes,
        top_defensive_weaknesses,
        pokemon_role_counts,
        utility_role_counts,
    )
    return bring_plans, watch_teams[:5], watch_pokemon[:6], strategy_notes[:4], counterplay_notes[:4]


def _build_team_preview_descriptors(
    plan_focuses: list[str],
    meta_analysis: dict[str, object],
) -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = []
    primary_focus = plan_focuses[0] if plan_focuses else "safe_default"
    descriptors.append(
        {
            "focus": primary_focus,
            "opponent_mode": None,
            "recommended_into": [],
        }
    )

    for opponent_mode in _build_team_preview_matchup_modes(primary_focus, meta_analysis):
        board_anchor = _select_team_preview_board_anchor(opponent_mode, meta_analysis)
        recommended_into = [_render_mode_label(opponent_mode)]
        if board_anchor is not None:
            recommended_into.append(cast(str, board_anchor["label"]))
        descriptors.append(
            {
                "focus": primary_focus,
                "opponent_mode": opponent_mode,
                "recommended_into": recommended_into,
                "board_anchor": board_anchor,
            }
        )
    return descriptors


def _select_team_preview_board_anchor(
    opponent_mode: str,
    meta_analysis: dict[str, object],
) -> dict[str, object] | None:
    rendered_mode = _render_mode_label(opponent_mode)
    tournament_rows = cast(list[dict[str, object]], meta_analysis.get("tournament_rows", []))
    matching_rows = [
        row
        for row in tournament_rows
        if rendered_mode in cast(list[str], row.get("modes", []))
    ]
    if not matching_rows:
        return None
    return max(
        matching_rows,
        key=lambda row: (cast(float, row.get("meta_share", 0.0)), abs(cast(float, row.get("matchup_score", 0.0)))),
    )


def _build_team_preview_matchup_modes(
    primary_focus: str,
    meta_analysis: dict[str, object],
) -> list[str]:
    weighted_matchups = cast(list[dict[str, object]], meta_analysis.get("weighted_matchups", []))
    matchup_modes = [cast(str, entry["mode"]) for entry in weighted_matchups]
    if (
        primary_focus in MODE_LABEL_ORDER
        and TOURNAMENT_MODE_SNAPSHOTS[primary_focus]["tournament_weight"] >= 0.55
        and primary_focus not in matchup_modes
    ):
        matchup_modes.append(primary_focus)

    return _dedupe_preserving_order(matchup_modes)


def _build_team_preview_focuses(
    primary_team_style: str,
    team_mode_packages: list[str],
    team_win_condition_labels: list[str],
) -> list[str]:
    focuses: list[str] = []
    primary_mode = team_mode_packages[0] if team_mode_packages else ""

    for win_condition in team_win_condition_labels:
        if win_condition in PREVIEW_PRIMARY_WIN_CONDITIONS:
            focuses.append(win_condition)

    if primary_mode == "dual_mode":
        focuses.extend(["tailwind", "trick_room"])
    elif primary_mode == "tailroom":
        focuses.extend(["tailwind", "trick_room"])
    elif primary_mode in {"rain_tailroom", "sun_tailroom"}:
        focuses.extend([primary_mode, primary_mode.replace("tailroom", "room")])
    elif primary_mode:
        focuses.append(primary_mode)

    if len(team_mode_packages) > 1:
        focuses.append(team_mode_packages[1])

    if team_win_condition_labels:
        focuses.append(team_win_condition_labels[0])

    if primary_team_style in {"balance", "bulky_offense", "semi_stall", "stall"}:
        focuses.append("safe_default")
    else:
        focuses.append(primary_team_style)

    deduped: list[str] = []
    for focus in focuses:
        if focus and focus not in deduped:
            deduped.append(focus)
    return deduped[:3]


def _select_team_preview_leads(
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None = None,
) -> list[str]:
    member_names = [member.pokemon_set.display_name for member in members]
    if len(member_names) <= 2:
        return member_names

    ranked_pairs = sorted(
        combinations(member_names, 2),
        key=lambda pair: _score_team_preview_pair(
            pair,
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            opponent_mode,
            board_anchor,
        ),
        reverse=True,
    )
    return list(ranked_pairs[0]) if ranked_pairs else member_names[:2]


def _select_team_preview_plan(
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    opponent_mode: str | None,
    existing_plans: list[dict[str, object]],
    board_anchor: dict[str, object] | None = None,
) -> tuple[list[str], list[str]]:
    member_names = [member.pokemon_set.display_name for member in members]
    if len(member_names) <= 2:
        return member_names, member_names
    if len(member_names) <= 4 and not existing_plans:
        return member_names[:2], member_names[:4]

    ranked_pairs = sorted(
        combinations(member_names, 2),
        key=lambda pair: _score_team_preview_pair(
            pair,
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            opponent_mode,
            board_anchor,
        ),
        reverse=True,
    )

    best_plan: tuple[list[str], list[str]] | None = None
    best_score = float("-inf")
    fallback_plan: tuple[list[str], list[str]] | None = None
    fallback_score = float("-inf")

    for pair in ranked_pairs:
        lead_pair = list(pair)
        pick_four = _select_team_preview_pick_four(
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            lead_pair,
            opponent_mode,
            existing_plans,
            board_anchor,
        )
        if not pick_four:
            continue

        plan_score = _score_team_preview_plan(
            lead_pair,
            pick_four,
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            opponent_mode,
            existing_plans,
            board_anchor,
        )
        if _is_duplicate_team_preview_plan(lead_pair, pick_four, existing_plans):
            if plan_score > fallback_score:
                fallback_plan = (lead_pair, pick_four)
                fallback_score = plan_score
            continue

        if plan_score > best_score:
            best_plan = (lead_pair, pick_four)
            best_score = plan_score

    if best_plan:
        return best_plan
    if fallback_plan:
        return fallback_plan

    fallback_leads = _select_team_preview_leads(
        members,
        member_roles,
        member_battle_speeds,
        member_speed_tiers,
        focus,
        opponent_mode,
        board_anchor,
    )
    fallback_pick_four = _select_team_preview_pick_four(
        members,
        member_roles,
        member_battle_speeds,
        member_speed_tiers,
        focus,
        fallback_leads,
        opponent_mode,
        board_anchor=board_anchor,
    )
    return fallback_leads, fallback_pick_four


def _select_team_preview_pick_four(
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    lead_pair: list[str],
    opponent_mode: str | None,
    existing_plans: list[dict[str, object]] | None = None,
    board_anchor: dict[str, object] | None = None,
) -> list[str]:
    target_size = min(4, len(members))
    if len(lead_pair) >= target_size:
        return list(lead_pair[:target_size])

    prior_plans = existing_plans or []
    member_lookup = {member.pokemon_set.display_name: member for member in members}
    remaining = [member.pokemon_set.display_name for member in members if member.pokemon_set.display_name not in lead_pair]
    slots_remaining = target_size - len(lead_pair)
    if slots_remaining <= 0 or not remaining:
        return list(lead_pair)

    best_pick_four: list[str] = list(lead_pair)
    best_score = float("-inf")

    for candidate_members in combinations(remaining, slots_remaining):
        ordered_pick_four = _order_team_preview_pick_four_candidate(
            list(lead_pair),
            list(candidate_members),
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            member_lookup,
            opponent_mode,
            board_anchor,
        )
        candidate_score = _score_team_preview_plan(
            list(lead_pair),
            ordered_pick_four,
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            opponent_mode,
            prior_plans,
            board_anchor,
        )
        if candidate_score > best_score:
            best_pick_four = ordered_pick_four
            best_score = candidate_score

    return best_pick_four


def _order_team_preview_pick_four_candidate(
    lead_pair: list[str],
    candidate_members: list[str],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    member_lookup: dict[str, TeamMember],
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None = None,
) -> list[str]:
    ordered_pick_four = list(lead_pair)
    remaining = list(candidate_members)

    while remaining:
        next_member = max(
            remaining,
            key=lambda member_name: _score_team_preview_member_selection(
                member_lookup[member_name],
                set(member_roles.get(member_name, [])),
                member_battle_speeds[member_name],
                member_speed_tiers[member_name],
                focus,
                ordered_pick_four,
                member_roles,
                member_lookup,
                opponent_mode,
                board_anchor,
            ),
        )
        ordered_pick_four.append(next_member)
        remaining.remove(next_member)

    return ordered_pick_four


def _score_team_preview_plan(
    lead_pair: list[str],
    pick_four: list[str],
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    opponent_mode: str | None,
    existing_plans: list[dict[str, object]],
    board_anchor: dict[str, object] | None = None,
) -> float:
    member_lookup = {member.pokemon_set.display_name: member for member in members}
    score = _score_team_preview_pair(
        (lead_pair[0], lead_pair[1]),
        members,
        member_roles,
        member_battle_speeds,
        member_speed_tiers,
        focus,
        opponent_mode,
        board_anchor,
    )
    selected = list(lead_pair)
    for member_name in pick_four:
        if member_name in selected:
            continue
        score += _score_team_preview_member_selection(
            member_lookup[member_name],
            set(member_roles.get(member_name, [])),
            member_battle_speeds[member_name],
            member_speed_tiers[member_name],
            focus,
            selected,
            member_roles,
            member_lookup,
            opponent_mode,
            board_anchor,
        )
        selected.append(member_name)
    score += _score_team_preview_plan_diversity(lead_pair, pick_four, existing_plans, opponent_mode)
    return score


def _score_team_preview_plan_diversity(
    lead_pair: list[str],
    pick_four: list[str],
    existing_plans: list[dict[str, object]],
    opponent_mode: str | None,
) -> float:
    if not existing_plans:
        return 0.0

    lead_signature = set(_team_preview_signature(lead_pair))
    pick_signature = set(_team_preview_signature(pick_four))
    score = 0.0

    for existing_plan in existing_plans:
        existing_leads = set(_team_preview_signature(cast(list[str], existing_plan.get("leads", []))))
        existing_pick_four = set(_team_preview_signature(cast(list[str], existing_plan.get("pick_four", []))))
        shared_leads = len(lead_signature & existing_leads)
        shared_pick_four = len(pick_signature & existing_pick_four)

        if pick_signature == existing_pick_four:
            score -= 5.2
        elif shared_pick_four >= 3:
            score -= 1.7
        elif shared_pick_four <= 2:
            score += 0.5

        if lead_signature == existing_leads:
            score -= 3.4
        elif shared_leads == 0:
            score += 0.9 if opponent_mode else 0.5

    return score


def _is_duplicate_team_preview_plan(
    lead_pair: list[str],
    pick_four: list[str],
    existing_plans: list[dict[str, object]],
) -> bool:
    lead_signature = _team_preview_signature(lead_pair)
    pick_four_signature = _team_preview_signature(pick_four)
    return any(
        lead_signature == _team_preview_signature(cast(list[str], existing_plan.get("leads", [])))
        and pick_four_signature == _team_preview_signature(cast(list[str], existing_plan.get("pick_four", [])))
        for existing_plan in existing_plans
    )


def _team_preview_signature(members: list[str]) -> tuple[str, ...]:
    return tuple(sorted(members))


def _team_preview_is_setup_enabler(roles: set[str]) -> bool:
    return bool(roles & PREVIEW_SETUP_ENABLER_ROLES)


def _team_preview_is_setup_payoff(roles: set[str]) -> bool:
    return bool(roles & PREVIEW_SETUP_PAYOFF_ROLES)


def _score_team_preview_pair(
    pair: tuple[str, str],
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None = None,
) -> float:
    member_lookup = {member.pokemon_set.display_name: member for member in members}
    first_name, second_name = pair
    first_roles = set(member_roles.get(first_name, []))
    second_roles = set(member_roles.get(second_name, []))
    first_move_names = _team_preview_move_names(member_lookup[first_name])
    second_move_names = _team_preview_move_names(member_lookup[second_name])
    pair_roles = first_roles | second_roles
    focus_flags = _team_preview_focus_flags(focus)
    attacker_count = sum(1 for roles in (first_roles, second_roles) if roles & PREVIEW_ATTACKER_ROLES)
    support_count = sum(1 for roles in (first_roles, second_roles) if roles & PREVIEW_SUPPORT_ROLES)
    setup_enabler_count = sum(1 for roles in (first_roles, second_roles) if _team_preview_is_setup_enabler(roles))
    setup_payoff_count = sum(1 for roles in (first_roles, second_roles) if _team_preview_is_setup_payoff(roles))
    tailwind_setter_count = sum(1 for roles in (first_roles, second_roles) if "tailwind_setter" in roles)
    trick_room_setter_count = sum(1 for roles in (first_roles, second_roles) if "trick_room_setter" in roles)
    perish_user_count = sum(1 for move_names in (first_move_names, second_move_names) if "perish-song" in move_names)
    trap_tool_count = sum(
        1
        for roles, move_names in ((first_roles, first_move_names), (second_roles, second_move_names))
        if "trapper" in roles or bool(move_names & TRAPPING_MOVES)
    )
    redirection_support_count = sum(
        1
        for roles, move_names in ((first_roles, first_move_names), (second_roles, second_move_names))
        if roles & {"redirector", "bulky_support", "support", "fake_out_support"} or bool(move_names & REDIRECTION_MOVES)
    )
    terrain_setter_count = sum(1 for roles in (first_roles, second_roles) if "terrain_setter" in roles)
    score = (
        _score_team_preview_member_base(
            member_lookup[first_name],
            first_roles,
            member_battle_speeds[first_name],
            member_speed_tiers[first_name],
            focus,
            lead_slot=True,
            opponent_mode=opponent_mode,
        )
        + _score_team_preview_member_base(
            member_lookup[second_name],
            second_roles,
            member_battle_speeds[second_name],
            member_speed_tiers[second_name],
            focus,
            lead_slot=True,
            opponent_mode=opponent_mode,
        )
    )

    if attacker_count >= 1 and support_count >= 1:
        score += 1.8
    if attacker_count == 0:
        score -= 1.5
    if focus_flags["setup"]:
        if setup_enabler_count == 0:
            score -= 3.8
        else:
            score += 2.4
        if setup_payoff_count == 0:
            score -= 2.8
        else:
            score += 1.5 * setup_payoff_count
        if setup_enabler_count >= 1 and setup_payoff_count >= 1:
            score += 3.1
        if "screen_setter" in pair_roles and setup_payoff_count >= 1:
            score += 2.2
        if pair_roles & {"fake_out_support", "redirector", "bulky_support"} and setup_payoff_count >= 1:
            score += 1.7
        if "weather_setter" in pair_roles and setup_payoff_count >= 1:
            score += 1.2
    if focus_flags["tailwind"]:
        if tailwind_setter_count == 0:
            score -= 4.2
        elif tailwind_setter_count == 1:
            score += 3.2
            if attacker_count >= 1:
                score += 1.8
        else:
            score -= 1.2
        if attacker_count >= 1:
            score += 1.4
    if focus_flags["trick_room"]:
        if trick_room_setter_count == 0:
            score -= 4.5
        elif trick_room_setter_count == 1:
            score += 3.3
            if pair_roles & {"fake_out_support", "redirector", "bulky_support"}:
                score += 2.4
        else:
            score -= 2.8
        if any(
            member_speed_tiers[name] in {"trick_room_slow", "slow"}
            and set(member_roles.get(name, [])) & PREVIEW_ATTACKER_ROLES
            for name in pair
        ):
            score += 1.4
    if focus_flags["screens"] and "screen_setter" in pair_roles:
        score += 3.0
    if focus_flags["perish"]:
        if perish_user_count == 0:
            score -= 4.0
        else:
            score += 3.0
        if trap_tool_count == 0:
            score -= 2.8
        else:
            score += 2.4
        if perish_user_count >= 1 and trap_tool_count >= 1:
            score += 2.2
        if redirection_support_count >= 1:
            score += 1.4
    if focus_flags["terrain"] and "terrain_setter" in pair_roles:
        score += 2.6
    if focus_flags["weather"] and "weather_setter" in pair_roles:
        score += 2.6
    if focus_flags["psyspam"]:
        if terrain_setter_count == 0:
            score -= 4.0
        else:
            score += 2.8
        if "terrain_setter" in pair_roles and pair_roles & {"special_sweeper", "setup_sweeper"}:
            score += 2.4
    if first_roles & {"setup_sweeper"} and second_roles & {"setup_sweeper"}:
        score -= 1.0
    score += _score_team_preview_opponent_pair_context(
        member_lookup[first_name],
        first_roles,
        member_lookup[second_name],
        second_roles,
        opponent_mode,
    )
    score += _score_team_preview_board_anchor_pair_context(
        member_lookup[first_name],
        first_roles,
        member_lookup[second_name],
        second_roles,
        board_anchor,
    )
    return score


def _score_team_preview_member_selection(
    member: TeamMember,
    roles: set[str],
    battle_speed: int,
    speed_tier: str,
    focus: str,
    selected: list[str],
    member_roles: dict[str, list[str]],
    member_lookup: dict[str, TeamMember],
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None = None,
) -> float:
    score = _score_team_preview_member_base(
        member,
        roles,
        battle_speed,
        speed_tier,
        focus,
        lead_slot=False,
        opponent_mode=opponent_mode,
    )
    selected_role_sets = [set(member_roles.get(member_name, [])) for member_name in selected]
    selected_attackers = sum(1 for role_set in selected_role_sets if role_set & PREVIEW_ATTACKER_ROLES)
    selected_supports = sum(1 for role_set in selected_role_sets if role_set & PREVIEW_SUPPORT_ROLES)
    selected_has_setup_enabler = any(_team_preview_is_setup_enabler(role_set) for role_set in selected_role_sets)
    selected_setup_payoff_count = sum(1 for role_set in selected_role_sets if _team_preview_is_setup_payoff(role_set))
    focus_flags = _team_preview_focus_flags(focus)
    move_names = _team_preview_move_names(member)

    if selected_attackers < 2 and roles & PREVIEW_ATTACKER_ROLES:
        score += 1.3
    if selected_supports == 0 and roles & PREVIEW_SUPPORT_ROLES:
        score += 1.2
    if focus_flags["setup"]:
        if not selected_has_setup_enabler and _team_preview_is_setup_enabler(roles):
            score += 2.6
        if selected_setup_payoff_count == 0 and _team_preview_is_setup_payoff(roles):
            score += 2.4
        if selected_has_setup_enabler and _team_preview_is_setup_payoff(roles):
            score += 1.8
        if selected_setup_payoff_count >= 1 and _team_preview_is_setup_enabler(roles):
            score += 1.3
        if "screen_setter" in roles and selected_setup_payoff_count >= 1:
            score += 1.6
    if focus_flags["tailwind"] and not any("tailwind_setter" in role_set for role_set in selected_role_sets) and "tailwind_setter" in roles:
        score += 2.0
    if focus_flags["trick_room"] and not any("trick_room_setter" in role_set for role_set in selected_role_sets) and "trick_room_setter" in roles:
        score += 2.1
    if focus_flags["screens"] and not any("screen_setter" in role_set for role_set in selected_role_sets) and "screen_setter" in roles:
        score += 1.8
    if focus_flags["weather"] and not any("weather_setter" in role_set for role_set in selected_role_sets) and "weather_setter" in roles:
        score += 1.8
    if focus_flags["terrain"] and not any("terrain_setter" in role_set for role_set in selected_role_sets) and "terrain_setter" in roles:
        score += 1.8
    if focus_flags["perish"]:
        selected_move_sets = [
            _team_preview_move_names(member_lookup[member_name])
            for member_name in selected
        ]
        selected_has_perish = any("perish-song" in selected_move_set for selected_move_set in selected_move_sets)
        selected_trapper_count = sum(
            1
            for role_set, selected_move_set in zip(selected_role_sets, selected_move_sets)
            if "trapper" in role_set or bool(selected_move_set & TRAPPING_MOVES)
        )
        selected_has_trapper = selected_trapper_count > 0 or any(
            bool(selected_move_set & TRAPPING_MOVES) for selected_move_set in selected_move_sets
        )
        selected_has_redirector = any("redirector" in role_set for role_set in selected_role_sets)
        if not selected_has_perish and "perish-song" in move_names:
            score += 3.2
        if not selected_has_trapper and ("trapper" in roles or bool(move_names & TRAPPING_MOVES)):
            score += 2.4
        if selected_trapper_count < 2 and ("trapper" in roles or bool(move_names & TRAPPING_MOVES)):
            score += 2.1
        if not selected_has_redirector and ("redirector" in roles or bool(move_names & REDIRECTION_MOVES)):
            score += 3.0
    if focus_flags["psyspam"] and not any("terrain_setter" in role_set for role_set in selected_role_sets) and "terrain_setter" in roles:
        score += 2.4
    score += _score_team_preview_opponent_selection_context(
        member,
        roles,
        speed_tier,
        opponent_mode,
        selected,
        selected_role_sets,
        member_lookup,
    )
    score += _score_team_preview_board_anchor_member_context(member, roles, board_anchor, lead_slot=False)
    return score


def _score_team_preview_member_base(
    member: TeamMember,
    roles: set[str],
    battle_speed: int,
    speed_tier: str,
    focus: str,
    *,
    lead_slot: bool,
    opponent_mode: str | None = None,
) -> float:
    speed_rank = {tier_name: index for index, tier_name in enumerate(SPEED_TIER_ORDER)}[speed_tier]
    slow_rank = len(SPEED_TIER_ORDER) - speed_rank - 1
    focus_flags = _team_preview_focus_flags(focus)
    item_name = _normalized_item_name(member.pokemon_set.item)
    move_names = _team_preview_move_names(member)
    types = set(member.species_data.types)

    score = 0.0
    if roles & {"fake_out_support"}:
        score += 1.6 if lead_slot else 0.6
    if roles & {"pivot", "bulky_pivot"}:
        score += 1.4 if lead_slot else 0.9
    if roles & {"support", "bulky_support", "redirector", "healing_support"}:
        score += 1.1 if lead_slot else 0.8
    if roles & {"physical_sweeper", "special_sweeper", "cleaner"}:
        score += 0.9 if lead_slot else 1.4
    if roles & {"setup_sweeper"}:
        score += 0.5 if lead_slot else 1.9
    if roles & {"bulky_attacker"}:
        score += 0.9 if lead_slot else 1.5
    if item_name == "focus sash" and lead_slot:
        score += 0.5
    if item_name == "choice scarf":
        score += 0.8
    if item_name == "light clay" and focus_flags["screens"]:
        score += 1.1

    if focus_flags["setup"]:
        if _team_preview_is_setup_enabler(roles):
            score += 1.8 if lead_slot else 0.8
        if _team_preview_is_setup_payoff(roles):
            score += 1.0 if lead_slot else 1.7
        if "screen_setter" in roles:
            score += 2.6 if lead_slot else 0.9
        if roles & {"fake_out_support", "redirector", "healing_support", "bulky_support"}:
            score += 1.3 if lead_slot else 0.6
        if roles & {"setup_sweeper"}:
            score += 1.3

    if focus_flags["tailwind"]:
        score += 0.7 * speed_rank
        if "tailwind_setter" in roles:
            score += 3.4 if lead_slot else 1.0
        if speed_tier in {"slow", "trick_room_slow"} and not roles & {"tailwind_setter", "support", "bulky_support"}:
            score -= 1.0
    if focus_flags["trick_room"]:
        score += 0.8 * slow_rank
        if "trick_room_setter" in roles:
            score += 3.5 if lead_slot else 1.1
        if roles & {"fake_out_support", "redirector", "bulky_support"}:
            score += 1.5 if lead_slot else 0.8
        if speed_tier in {"very_fast", "elite_fast"} and not roles & {"fake_out_support", "support", "pivot"}:
            score -= 0.9
    if focus_flags["screens"]:
        if "screen_setter" in roles:
            score += 3.4 if lead_slot else 1.0
        if roles & {"setup_sweeper", "cleaner", "physical_sweeper", "special_sweeper"}:
            score += 1.4
    if focus_flags["perish"]:
        if roles & {"trapper", "redirector", "bulky_support", "support"}:
            score += 1.9
        if "perish-song" in move_names:
            score += 2.8
        if move_names & TRAPPING_MOVES:
            score += 2.2
        if move_names & PROTECTION_MOVES:
            score += 0.4
    if focus_flags["psyspam"]:
        if "terrain_setter" in roles:
            score += 3.0 if lead_slot else 1.0
        if roles & {"special_sweeper", "setup_sweeper", "trick_room_setter"}:
            score += 1.6
        if "psychic" in types:
            score += 0.7
        if "expanding-force" in move_names:
            score += 1.6
    weather_name = cast(str | None, focus_flags["weather"])
    if weather_name:
        if "weather_setter" in roles:
            score += 3.0 if lead_slot else 1.0
        if weather_name == "rain" and types & {"water", "electric"}:
            score += 1.1
        elif weather_name == "sun" and types & {"fire", "grass"}:
            score += 1.1
        elif weather_name == "sand" and types & {"rock", "ground", "steel"}:
            score += 0.9
        elif weather_name == "snow" and types & {"ice"}:
            score += 0.9
    terrain_name = cast(str | None, focus_flags["terrain"])
    if terrain_name:
        if "terrain_setter" in roles:
            score += 2.6 if lead_slot else 0.8
        if terrain_name == "electric" and types & {"electric"}:
            score += 0.8
        elif terrain_name == "grassy" and types & {"grass"}:
            score += 0.8
        elif terrain_name == "misty" and types & {"fairy"}:
            score += 0.7
        elif terrain_name == "psychic" and types & {"psychic"}:
            score += 0.8

    if focus == "safe_default":
        score += 0.015 * battle_speed
        if roles & {"bulky_pivot", "bulky_support", "cleaner", "bulky_attacker"}:
            score += 0.8
    score += _score_team_preview_opponent_member_context(
        member,
        roles,
        speed_tier,
        opponent_mode,
        lead_slot,
    )
    return score


def _team_preview_focus_flags(focus: str) -> dict[str, str | bool | None]:
    flags: dict[str, str | bool | None] = {
        "tailwind": False,
        "trick_room": False,
        "setup": focus in {"setup_sweep", "screens_offense"},
        "screens": focus == "screens_offense",
        "perish": focus == "perish_trap",
        "psyspam": focus == "psyspam",
        "weather": None,
        "terrain": None,
    }
    if focus in {"tailwind", "tailroom", "dual_mode"} or "tailwind" in focus or "tailroom" in focus:
        flags["tailwind"] = True
    if focus in {"trick_room", "semiroom", "tailroom", "dual_mode"} or focus.endswith("_room") or focus.endswith("_tailroom"):
        flags["trick_room"] = True
    for weather_name in ("rain", "sun", "sand", "snow"):
        if focus == weather_name or focus.startswith(f"{weather_name}_"):
            flags["weather"] = weather_name
            break
    for terrain_name in ("electric", "grassy", "misty", "psychic"):
        terrain_focus = f"{terrain_name}_terrain"
        if focus == terrain_focus or (focus == "psyspam" and terrain_name == "psychic"):
            flags["terrain"] = terrain_name
            break
    return flags


def _render_team_preview_plan_label(focus: str, index: int, opponent_mode: str | None) -> str:
    if opponent_mode:
        rendered_mode = _render_mode_label(opponent_mode)
        if focus == opponent_mode or (focus == "tailwind" and "tailwind" in opponent_mode) or (focus == "trick_room" and "room" in opponent_mode):
            return f"{rendered_mode} mirror plan"
        return f"Into {rendered_mode}"
    if focus == "safe_default":
        return "Safer default plan"
    prefix = "Primary" if index == 0 else "Alternate"
    if focus in MODE_LABEL_ORDER or focus in MODE_PACKAGE_ORDER:
        return f"{prefix} {_render_mode_label(focus)} plan"
    return f"{prefix} {focus.replace('_', ' ').title()} plan"


def _team_preview_move_names(member: TeamMember) -> set[str]:
    return {move.api_name for move in member.move_data}


def _team_preview_attack_types(member: TeamMember) -> set[str]:
    return {move.type_name for move in member.move_data if move.damage_class != "status"}


def _team_preview_has_priority_pressure(member: TeamMember) -> bool:
    return any(move.priority > 0 and move.damage_class != "status" for move in member.move_data)


def _team_preview_is_trick_room_mode(mode_name: str) -> bool:
    return mode_name in {"trick_room", "semiroom", "tailroom"} or mode_name.endswith("_room") or mode_name.endswith("_tailroom")


def _team_preview_is_tailwind_mode(mode_name: str) -> bool:
    return mode_name == "tailwind" or "tailwind" in mode_name or mode_name == "tailroom"


def _team_preview_board_anchor_tags(board_anchor: dict[str, object] | None) -> set[str]:
    if not board_anchor:
        return set()

    interaction_summary = cast(dict[str, object], board_anchor.get("interaction_summary", {}))
    return set(cast(list[str], interaction_summary.get("tags", [])))


def _team_preview_has_spread_move(member: TeamMember) -> bool:
    return any(move.target_name in SPREAD_DAMAGE_TARGET_NAMES for move in member.move_data)


def _team_preview_has_setup_disruption(member: TeamMember) -> bool:
    move_names = _team_preview_move_names(member)
    return bool(move_names & {"taunt", "encore", "imprison", "haze", "clear-smog", "psychic-fangs", "brick-break", "fake-out"})


def _score_team_preview_board_anchor_pair_context(
    first_member: TeamMember,
    first_roles: set[str],
    second_member: TeamMember,
    second_roles: set[str],
    board_anchor: dict[str, object] | None,
) -> float:
    interaction_tags = _team_preview_board_anchor_tags(board_anchor)
    if not interaction_tags:
        return 0.0

    pair_move_names = _team_preview_move_names(first_member) | _team_preview_move_names(second_member)
    score = 0.0

    if "spread counterplay" in interaction_tags:
        if "wide-guard" in pair_move_names:
            score += 1.6
        if any(move_name in pair_move_names for move_name in PROTECTION_MOVES):
            score += 0.4
    if "setup denial" in interaction_tags and (
        _team_preview_has_setup_disruption(first_member) or _team_preview_has_setup_disruption(second_member)
    ):
        score += 1.5
    if "redirection counterplay" in interaction_tags and (
        _team_preview_has_spread_move(first_member) or _team_preview_has_spread_move(second_member)
    ):
        score += 1.2
    if "ability-aware counterplay" in interaction_tags:
        first_ability_names = set(_member_context_ability_names(first_member))
        second_ability_names = set(_member_context_ability_names(second_member))
        if (
            ("mold breaker" in first_ability_names and "fake-out" in _team_preview_move_names(first_member))
            or ("mold breaker" in second_ability_names and "fake-out" in _team_preview_move_names(second_member))
        ):
            score += 1.8
        elif pair_move_names & {"taunt", "encore", "imprison", "trick-room"}:
            score += 0.9

    if first_roles & PREVIEW_ATTACKER_ROLES and second_roles & PREVIEW_SUPPORT_ROLES:
        score += 0.2

    return score


def _score_team_preview_board_anchor_member_context(
    member: TeamMember,
    roles: set[str],
    board_anchor: dict[str, object] | None,
    *,
    lead_slot: bool,
) -> float:
    interaction_tags = _team_preview_board_anchor_tags(board_anchor)
    if not interaction_tags:
        return 0.0

    move_names = _team_preview_move_names(member)
    ability_names = set(_member_context_ability_names(member))
    score = 0.0

    if "spread counterplay" in interaction_tags:
        if "wide-guard" in move_names:
            score += 1.8 if lead_slot else 1.2
        elif move_names & PROTECTION_MOVES:
            score += 0.6 if lead_slot else 0.3
    if "setup denial" in interaction_tags and _team_preview_has_setup_disruption(member):
        score += 1.5 if lead_slot else 1.0
    if "redirection counterplay" in interaction_tags:
        if _team_preview_has_spread_move(member):
            score += 1.3 if lead_slot else 0.9
        elif move_names & {"taunt", "encore"}:
            score += 1.0 if lead_slot else 0.7
    if "ability-aware counterplay" in interaction_tags:
        if "mold breaker" in ability_names and "fake-out" in move_names:
            score += 1.9 if lead_slot else 1.1
        elif move_names & {"taunt", "encore", "imprison", "trick-room"}:
            score += 1.1 if lead_slot else 0.7

    if roles & PREVIEW_ATTACKER_ROLES and any(tag in interaction_tags for tag in {"redirection counterplay", "spread counterplay"}):
        score += 0.3

    return score


def _team_preview_opponent_weather(mode_name: str) -> str | None:
    for weather_name in ("rain", "sun", "sand", "snow"):
        if mode_name == weather_name or mode_name.startswith(f"{weather_name}_"):
            return weather_name
    return None


def _team_preview_opponent_terrain(mode_name: str) -> str | None:
    for terrain_name in ("electric", "grassy", "misty", "psychic"):
        terrain_mode = f"{terrain_name}_terrain"
        if mode_name == terrain_mode:
            return terrain_name
    return None


def _team_preview_weather_punish_types(weather_name: str) -> tuple[str, ...]:
    if weather_name == "rain":
        return ("electric", "grass", "rock")
    if weather_name == "sun":
        return ("water", "ground", "rock")
    if weather_name == "sand":
        return ("water", "grass", "fighting", "ground")
    return ("fire", "rock", "steel")


def _team_preview_terrain_punish_types(terrain_name: str) -> tuple[str, ...]:
    if terrain_name == "electric":
        return ("ground",)
    if terrain_name == "grassy":
        return ("fire", "ice", "flying", "bug", "poison")
    if terrain_name == "misty":
        return ("steel", "poison")
    return ("dark", "ghost", "steel")


def _score_team_preview_opponent_pair_context(
    first_member: TeamMember,
    first_roles: set[str],
    second_member: TeamMember,
    second_roles: set[str],
    opponent_mode: str | None,
) -> float:
    if not opponent_mode:
        return 0.0

    pair_roles = first_roles | second_roles
    pair_move_names = _team_preview_move_names(first_member) | _team_preview_move_names(second_member)
    pair_attack_types = _team_preview_attack_types(first_member) | _team_preview_attack_types(second_member)
    score = 0.0

    if _team_preview_is_trick_room_mode(opponent_mode):
        if "fake_out_support" in pair_roles or "fake-out" in pair_move_names:
            score += 2.0
        if pair_move_names & {"taunt", "encore", "imprison"}:
            score += 2.2
        if "trick_room_setter" in pair_roles:
            score += 1.5
        if any(
            roles & PREVIEW_ATTACKER_ROLES and member.species_data.base_speed <= 70
            for roles, member in ((first_roles, first_member), (second_roles, second_member))
        ):
            score += 1.0

    if _team_preview_is_tailwind_mode(opponent_mode):
        if "trick_room_setter" in pair_roles:
            score += 1.8
        if "fake_out_support" in pair_roles or pair_move_names & {"icy-wind", "electroweb", "quash"}:
            score += 1.4
        if "wide-guard" in pair_move_names:
            score += 1.1
        if _team_preview_has_priority_pressure(first_member) or _team_preview_has_priority_pressure(second_member):
            score += 0.8

    weather_name = _team_preview_opponent_weather(opponent_mode)
    if weather_name:
        if "weather_setter" in pair_roles:
            score += 1.7
        if "wide-guard" in pair_move_names:
            score += 1.0
        if pair_attack_types & set(_team_preview_weather_punish_types(weather_name)):
            score += 1.3

    terrain_name = _team_preview_opponent_terrain(opponent_mode)
    if terrain_name:
        if "terrain_setter" in pair_roles:
            score += 1.5
        if pair_attack_types & set(_team_preview_terrain_punish_types(terrain_name)):
            score += 1.0

    return score


def _score_team_preview_opponent_member_context(
    member: TeamMember,
    roles: set[str],
    speed_tier: str,
    opponent_mode: str | None,
    lead_slot: bool,
) -> float:
    if not opponent_mode:
        return 0.0

    move_names = _team_preview_move_names(member)
    attack_types = _team_preview_attack_types(member)
    score = 0.0

    if _team_preview_is_trick_room_mode(opponent_mode):
        if "fake_out_support" in roles or "fake-out" in move_names:
            score += 1.6 if lead_slot else 0.8
        if move_names & {"taunt", "encore", "imprison"}:
            score += 1.7 if lead_slot else 0.9
        if "trick_room_setter" in roles:
            score += 1.4
        if speed_tier in {"trick_room_slow", "slow"} and roles & PREVIEW_ATTACKER_ROLES:
            score += 0.8
        if speed_tier in {"very_fast", "elite_fast"} and not roles & {"support", "pivot", "fake_out_support"}:
            score -= 0.7

    if _team_preview_is_tailwind_mode(opponent_mode):
        if "trick_room_setter" in roles:
            score += 1.3
        if "fake_out_support" in roles or move_names & {"icy-wind", "electroweb", "quash"}:
            score += 1.1 if lead_slot else 0.7
        if "wide-guard" in move_names:
            score += 1.0
        if _team_preview_has_priority_pressure(member):
            score += 0.7
        if speed_tier in {"very_fast", "elite_fast"} and roles & {"cleaner", "physical_sweeper", "special_sweeper"}:
            score += 0.5

    weather_name = _team_preview_opponent_weather(opponent_mode)
    if weather_name:
        if "weather_setter" in roles:
            score += 1.5
        if "wide-guard" in move_names:
            score += 0.8
        if attack_types & set(_team_preview_weather_punish_types(weather_name)):
            score += 1.0
        if move_names & PROTECTION_MOVES:
            score += 0.3

    terrain_name = _team_preview_opponent_terrain(opponent_mode)
    if terrain_name:
        if "terrain_setter" in roles:
            score += 1.2
        if attack_types & set(_team_preview_terrain_punish_types(terrain_name)):
            score += 0.9

    return score


def _score_team_preview_opponent_selection_context(
    member: TeamMember,
    roles: set[str],
    speed_tier: str,
    opponent_mode: str | None,
    selected: list[str],
    selected_role_sets: list[set[str]],
    member_lookup: dict[str, TeamMember],
) -> float:
    if not opponent_mode:
        return 0.0

    move_names = _team_preview_move_names(member)
    attack_types = _team_preview_attack_types(member)
    selected_move_sets = [_team_preview_move_names(member_lookup[member_name]) for member_name in selected]
    selected_attack_types = [
        _team_preview_attack_types(member_lookup[member_name])
        for member_name in selected
    ]
    score = 0.0

    if _team_preview_is_trick_room_mode(opponent_mode):
        if not any("fake_out_support" in role_set for role_set in selected_role_sets) and ("fake_out_support" in roles or "fake-out" in move_names):
            score += 1.8
        if not any(selected_move_set & {"taunt", "encore", "imprison"} for selected_move_set in selected_move_sets) and move_names & {"taunt", "encore", "imprison"}:
            score += 1.8
        if not any("trick_room_setter" in role_set for role_set in selected_role_sets) and "trick_room_setter" in roles:
            score += 1.3
        if speed_tier in {"trick_room_slow", "slow"} and roles & PREVIEW_ATTACKER_ROLES:
            score += 0.7

    if _team_preview_is_tailwind_mode(opponent_mode):
        if not any("trick_room_setter" in role_set for role_set in selected_role_sets) and "trick_room_setter" in roles:
            score += 1.6
        if not any(("fake_out_support" in role_set) for role_set in selected_role_sets) and ("fake_out_support" in roles or move_names & {"icy-wind", "electroweb", "quash"}):
            score += 1.4
        if not any("wide-guard" in selected_move_set for selected_move_set in selected_move_sets) and "wide-guard" in move_names:
            score += 1.1

    weather_name = _team_preview_opponent_weather(opponent_mode)
    if weather_name:
        weather_punish_types = set(_team_preview_weather_punish_types(weather_name))
        if not any("weather_setter" in role_set for role_set in selected_role_sets) and "weather_setter" in roles:
            score += 1.4
        if not any("wide-guard" in selected_move_set for selected_move_set in selected_move_sets) and "wide-guard" in move_names:
            score += 0.8
        if not any(selected_types & weather_punish_types for selected_types in selected_attack_types) and attack_types & weather_punish_types:
            score += 1.0

    terrain_name = _team_preview_opponent_terrain(opponent_mode)
    if terrain_name:
        terrain_punish_types = set(_team_preview_terrain_punish_types(terrain_name))
        if not any("terrain_setter" in role_set for role_set in selected_role_sets) and "terrain_setter" in roles:
            score += 1.2
        if not any(selected_types & terrain_punish_types for selected_types in selected_attack_types) and attack_types & terrain_punish_types:
            score += 0.9

    return score


def _build_team_preview_member_reasons(
    pick_four: list[str],
    lead_pair: list[str],
    back_line: list[str],
    member_lookup: dict[str, TeamMember],
    member_roles: dict[str, list[str]],
    focus: str,
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None,
) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for member_name in pick_four:
        reasons[member_name] = _describe_team_preview_member_reason(
            member_lookup[member_name],
            set(member_roles.get(member_name, [])),
            focus,
            opponent_mode,
            board_anchor,
            member_name in lead_pair,
            member_name in back_line,
        )
    return reasons


def _describe_team_preview_member_reason(
    member: TeamMember,
    roles: set[str],
    focus: str,
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None,
    in_lead: bool,
    in_back: bool,
) -> str:
    move_names = _team_preview_move_names(member)
    focus_flags = _team_preview_focus_flags(focus)
    counter_reason = _describe_team_preview_counter_reason(member, roles, opponent_mode, in_lead)
    if counter_reason:
        return counter_reason

    board_anchor_reason = _describe_team_preview_board_anchor_reason(member, roles, board_anchor, in_lead, in_back)
    if board_anchor_reason:
        return board_anchor_reason

    if in_lead:
        if focus_flags["perish"] and "perish-song" in move_names:
            return "Starts the Perish Song timer from turn one."
        if focus_flags["perish"] and ("trapper" in roles or move_names & TRAPPING_MOVES):
            return "Keeps targets pinned once the Perish Song timer starts."
        if focus_flags["psyspam"] and "terrain_setter" in roles:
            return "Claims Psychic Terrain immediately for the psyspam branch."
        if focus_flags["psyspam"] and "expanding-force" in move_names:
            return "Turns the first terrain turns into immediate Psychic pressure."
        if focus_flags["trick_room"] and "trick_room_setter" in roles:
            return "Gives the line its Trick Room button."
        if focus_flags["trick_room"] and roles & {"fake_out_support", "redirector", "bulky_support"}:
            return "Buys the Trick Room turn so the slow backline can enter cleanly."
        if focus_flags["setup"] and "screen_setter" in roles:
            return "Sets the support turns that let the main sweepers boost or trade safely."
        if focus_flags["setup"] and roles & PREVIEW_SETUP_PAYOFF_ROLES:
            return "Turns the early support turns into immediate pressure without exposing the closer too soon."
        if focus_flags["setup"] and roles & {"weather_setter", "fake_out_support", "redirector", "bulky_support", "support", "healing_support"}:
            return "Opens the setup window that the team's main win conditions want."
        if focus_flags["tailwind"] and "tailwind_setter" in roles:
            return "Gets Tailwind online immediately."
        if focus_flags["tailwind"] and roles & PREVIEW_ATTACKER_ROLES:
            return "Turns the first speed-control turns into immediate pressure."
        if focus_flags["weather"] and "weather_setter" in roles:
            return "Claims weather on the opening turn."
        if focus_flags["terrain"] and "terrain_setter" in roles:
            return "Claims terrain on the opening turn."
        if "fake_out_support" in roles:
            return "Buys the opener a safer turn with Fake Out pressure."
        if roles & PREVIEW_ATTACKER_ROLES:
            return "Makes the opening turns threatening instead of passive."

    if in_back:
        if focus_flags["perish"] and ("redirector" in roles or "support" in roles):
            return "Stays in back as the follow-up support piece once the trap line starts."
        if focus_flags["psyspam"] and ("trick_room_setter" in roles or "expanding-force" in move_names or roles & {"special_sweeper", "setup_sweeper"}):
            return "Stays in back to cash in terrain turns or reset the mode later."
        if focus_flags["trick_room"] and member.species_data.base_speed <= 70 and roles & PREVIEW_ATTACKER_ROLES:
            return "Stays in back as the slow breaker once Trick Room is active."
        if focus_flags["setup"] and roles & {"setup_sweeper"}:
            return "Stays in back as the main setup win condition once support is established."
        if focus_flags["setup"] and roles & PREVIEW_SETUP_PAYOFF_ROLES:
            return "Stays in back as the payoff piece that cashes in the support turns."
        if focus_flags["setup"] and _team_preview_is_setup_enabler(roles):
            return "Stays in back as the fallback support button if the first setup line gets disrupted."
        if roles & {"setup_sweeper", "cleaner"}:
            return "Stays in back as the main cleaner once the opener has forced trades."
        if roles & {"bulky_attacker", "bulky_support", "redirector"}:
            return "Stays in back as the stabilizing midgame piece if the opener gets messy."

    return "Rounds out the four by covering a role the opening pair should not expose too early."


def _describe_team_preview_board_anchor_reason(
    member: TeamMember,
    roles: set[str],
    board_anchor: dict[str, object] | None,
    in_lead: bool,
    in_back: bool,
) -> str | None:
    if not board_anchor:
        return None

    label = cast(str, board_anchor.get("label", ""))
    if not label:
        return None

    interaction_tags = _team_preview_board_anchor_tags(board_anchor)
    if not interaction_tags:
        return None

    move_names = _team_preview_move_names(member)
    ability_names = set(_member_context_ability_names(member))
    key_pokemon = cast(list[str], board_anchor.get("key_pokemon", []))
    anchor_text = _render_series(key_pokemon[:2]) if key_pokemon else label

    if "ability-aware counterplay" in interaction_tags:
        if "mold breaker" in ability_names and "fake-out" in move_names:
            return f"Gives the line its cleanest ability-aware answer into {label}, so {anchor_text} cannot assume the first support turn is safe."
        if move_names & {"taunt", "encore", "imprison", "trick-room"}:
            return f"Keeps the key ability or setup turn from {label} from becoming automatic."
    if "spread counterplay" in interaction_tags:
        if "wide-guard" in move_names:
            return f"Blunts the spread-pressure turns that usually let {label} snowball early."
        if in_lead and move_names & PROTECTION_MOVES:
            return f"Buys a safer first cycle against the immediate spread pressure attached to {label}."
    if "setup denial" in interaction_tags and _team_preview_has_setup_disruption(member):
        return f"Directly contests the setup turns that make {label} hard to stabilize."
    if "redirection counterplay" in interaction_tags:
        if _team_preview_has_spread_move(member):
            return f"Pressures through the support shell around {label} instead of letting its redirectors soak single-target turns."
        if move_names & {"taunt", "encore"}:
            return f"Disrupts the support shell that usually keeps {label} stable through the first exchanges."

    if in_back and roles & PREVIEW_ATTACKER_ROLES:
        return f"Stays in back as the direct punish line once {label} has been forced into a fair trade pattern."

    return None


def _describe_team_preview_counter_reason(
    member: TeamMember,
    roles: set[str],
    opponent_mode: str | None,
    in_lead: bool,
) -> str | None:
    if not opponent_mode:
        return None

    move_names = _team_preview_move_names(member)
    attack_types = _team_preview_attack_types(member)

    if _team_preview_is_trick_room_mode(opponent_mode):
        if move_names & {"taunt", "encore", "imprison"}:
            return "Directly contests opposing Trick Room setup."
        if "fake_out_support" in roles or "fake-out" in move_names:
            return "Gives the line Fake Out pressure into opposing Trick Room turns."
        if "trick_room_setter" in roles:
            return "Can reverse Trick Room if the opponent gets it up first."
        if member.species_data.base_speed <= 70 and roles & PREVIEW_ATTACKER_ROLES:
            return "Still functions cleanly even if opposing Trick Room goes up."

    if _team_preview_is_tailwind_mode(opponent_mode):
        if "trick_room_setter" in roles:
            return "Gives the team a reverse-speed punish into Tailwind mirrors."
        if "wide-guard" in move_names:
            return "Blunts common spread-pressure turns from Tailwind offense."
        if "fake_out_support" in roles or move_names & {"icy-wind", "electroweb", "quash"}:
            return "Helps keep opposing Tailwind turns from snowballing immediately."
        if _team_preview_has_priority_pressure(member):
            return "Still threatens damage even when the opposing fast mode gets first move."

    weather_name = _team_preview_opponent_weather(opponent_mode)
    if weather_name:
        if "weather_setter" in roles:
            return "Can reset weather and cut off the opponent's boosted turns."
        if "wide-guard" in move_names:
            return "Checks common spread damage from the current weather shells."
        if attack_types & set(_team_preview_weather_punish_types(weather_name)):
            return f"Pressures common {weather_name.replace('_', ' ')} pieces with direct coverage."

    terrain_name = _team_preview_opponent_terrain(opponent_mode)
    if terrain_name:
        if "terrain_setter" in roles:
            return "Can overwrite the opponent's terrain and cut off their cleanest turns."
        if attack_types & set(_team_preview_terrain_punish_types(terrain_name)):
            return f"Pressures common {terrain_name.replace('_', ' ')} terrain pieces with useful coverage."

    return None


def _summarize_team_preview_plan(
    focus: str,
    lead_pair: list[str],
    back_line: list[str],
    opponent_mode: str | None,
    board_anchor: dict[str, object] | None,
    member_lookup: dict[str, TeamMember],
    member_roles: dict[str, list[str]],
) -> str:
    if not lead_pair:
        return "No clear preview plan was inferred."
    lead_text = _render_series(lead_pair)
    back_text = _render_series(back_line) if back_line else "the remaining flex slots"
    opener = _summarize_team_preview_opener(focus, lead_pair, opponent_mode, member_lookup, member_roles)

    opener = opener[0].upper() + opener[1:]
    summary = f"{opener} Keep {back_text} in back as the cleaner or stabilizing endgame line."
    anchor_note = _summarize_team_preview_board_anchor(board_anchor)
    if anchor_note:
        summary += f" {anchor_note}"
    return summary


def _summarize_team_preview_board_anchor(board_anchor: dict[str, object] | None) -> str:
    if not board_anchor:
        return ""

    label = cast(str, board_anchor.get("label", ""))
    if not label:
        return ""

    interaction_summary = cast(dict[str, object], board_anchor.get("interaction_summary", {}))
    interaction_tags = cast(list[str], interaction_summary.get("tags", []))
    key_pokemon = cast(list[str], board_anchor.get("key_pokemon", []))
    context_reasons = cast(list[str], board_anchor.get("context_reasons", []))
    target_summary = cast(dict[str, object], board_anchor.get("target_summary", {}))

    if interaction_tags:
        anchor_pokemon = _render_series(key_pokemon[:2]) if key_pokemon else "its main anchors"
        return (
            f"This is the clearest direct plan into {label}, where {_render_series(interaction_tags[:2])} matters most around {anchor_pokemon}."
        )

    if context_reasons:
        reason_text = context_reasons[0].rstrip(".")
        if reason_text and reason_text[0].isupper():
            reason_text = reason_text[0].lower() + reason_text[1:]
        return f"This is the clearest direct plan into {label}, where {reason_text}."

    if cast(int, target_summary.get("strong_answer_targets", 0)) > 0:
        return f"This is the clearest direct plan into {label}, where the move pool already pressures several of the board's main anchors."

    return f"This is the clearest direct plan into {label}."


def _summarize_team_preview_opener(
    focus: str,
    lead_pair: list[str],
    opponent_mode: str | None,
    member_lookup: dict[str, TeamMember],
    member_roles: dict[str, list[str]],
) -> str:
    lead_text = _render_series(lead_pair)
    focus_flags = _team_preview_focus_flags(focus)
    opener_prefix = f"Into {_render_mode_label(opponent_mode)}, " if opponent_mode else ""
    lead_members = [member_lookup[member_name] for member_name in lead_pair if member_name in member_lookup]
    lead_role_sets = [set(member_roles.get(member_name, [])) for member_name in lead_pair]
    lead_roles = set().union(*lead_role_sets) if lead_role_sets else set()
    lead_move_names = set().union(*(_team_preview_move_names(member) for member in lead_members)) if lead_members else set()
    attacker_count = sum(1 for roles in lead_role_sets if roles & PREVIEW_ATTACKER_ROLES)
    support_count = sum(1 for roles in lead_role_sets if roles & PREVIEW_SUPPORT_ROLES)
    has_screens = "screen_setter" in lead_roles or bool(lead_move_names & {"reflect", "light-screen"})
    has_tailwind = "tailwind_setter" in lead_roles or "tailwind" in lead_move_names
    has_disruption = bool(lead_move_names & {"fake-out", "icy-wind", "electroweb", "quash", "taunt", "encore", "wide-guard"})
    has_redirection = "redirector" in lead_roles or bool(lead_move_names & REDIRECTION_MOVES)
    has_fake_out = "fake_out_support" in lead_roles or "fake-out" in lead_move_names

    if focus_flags["perish"]:
        return f"{opener_prefix}lead {lead_text} to start the trap or positioning sequence without exposing the whole endgame at once."
    if focus_flags["screens"]:
        if has_screens and (has_disruption or has_redirection or has_fake_out):
            return f"{opener_prefix}lead {lead_text} to stall out the first burst of pressure with screens and utility, then buy clean setup or damage turns for the backline."
        if has_screens and attacker_count >= 1:
            return f"{opener_prefix}lead {lead_text} to get screens up without giving away the board, while still forcing the opponent to respect immediate damage."
        if has_disruption or has_redirection or has_fake_out or support_count >= attacker_count:
            return f"{opener_prefix}lead {lead_text} to disrupt the first few turns and buy cleaner setup or damage windows before the real closer has to commit."
        return f"{opener_prefix}lead {lead_text} to establish screens or immediate setup support before your main closer comes in."
    if focus_flags["setup"]:
        if has_disruption or has_redirection or support_count > attacker_count:
            return f"{opener_prefix}lead {lead_text} to disrupt the first few turns and buy clean setup or damage windows for the backline."
        return f"{opener_prefix}lead {lead_text} to create the support turns your main win condition needs before you commit the closer."
    if focus_flags["trick_room"] and focus_flags["tailwind"]:
        return f"{opener_prefix}lead {lead_text} to keep both speed modes available while you read which branch preview is really asking for."
    if focus_flags["trick_room"]:
        return f"{opener_prefix}lead {lead_text} to contest the opening turn and establish Trick Room or its support turn cleanly."
    if focus_flags["tailwind"]:
        if has_tailwind and attacker_count >= 1:
            if has_disruption or has_redirection or has_fake_out:
                return f"{opener_prefix}lead {lead_text} to get Tailwind online while still contesting the opening turn with utility and early pressure."
            return f"{opener_prefix}lead {lead_text} to get the fast mode online quickly and force early tempo."
        if has_disruption or has_redirection or has_fake_out:
            return f"{opener_prefix}lead {lead_text} to disrupt the opposing fast start and buy cleaner setup or damage turns later."
        return f"{opener_prefix}lead {lead_text} to keep speed control available without overcommitting your closer on turn one."
    if focus_flags["weather"]:
        if has_disruption or has_redirection:
            return f"{opener_prefix}lead {lead_text} to slow the first exchanges, then reset or exploit weather once the board is easier to control."
        return f"{opener_prefix}lead {lead_text} to secure weather first and make the opponent respect boosted damage immediately."
    if focus_flags["terrain"]:
        if has_disruption or has_redirection:
            return f"{opener_prefix}lead {lead_text} to contest the first exchanges and create safer terrain turns for the real payoff pieces."
        return f"{opener_prefix}lead {lead_text} to claim terrain early and route the game through your strongest terrain turns."
    if has_disruption or has_redirection or has_fake_out:
        return f"{opener_prefix}lead {lead_text} as the safer utility pair to stall out early pressure before the backline has to commit."
    return f"{opener_prefix}lead {lead_text} as the most stable default pair when preview does not force a hard adaptation."


def _build_team_preview_watch_teams(
    unfavorable_matchups: list[str],
    unfavorable_modes: list[str],
) -> list[str]:
    watch_teams: list[str] = []
    for mode_name in unfavorable_modes[:3]:
        rendered = _render_team_preview_watch_team_note(mode_name, is_mode=True)
        if rendered not in watch_teams:
            watch_teams.append(rendered)
    for matchup_name in unfavorable_matchups[:2]:
        rendered = _render_team_preview_watch_team_note(matchup_name, is_mode=False)
        if rendered not in watch_teams:
            watch_teams.append(rendered)
    return watch_teams


def _build_team_preview_watch_pokemon(
    members: list[TeamMember],
    unfavorable_modes: list[str],
) -> list[str]:
    own_species_tokens = {
        species_token
        for member in members
        for species_token in _species_tokens_for_member(member)
    }
    watch_pokemon: list[str] = []
    seen_species_tokens: set[str] = set()
    for mode_name in unfavorable_modes[:3]:
        snapshot = TOURNAMENT_MODE_SNAPSHOTS.get(mode_name)
        if snapshot is None:
            continue
        ranked_species = sorted(
            snapshot.get("signature_species", {}).items(),
            key=lambda item: (-item[1], item[0]),
        )
        for species_token, _ in ranked_species:
            if species_token in own_species_tokens or species_token in seen_species_tokens:
                continue
            rendered = _render_team_preview_watch_pokemon_note(species_token, mode_name)
            if rendered not in watch_pokemon:
                watch_pokemon.append(rendered)
                seen_species_tokens.add(species_token)
            if len(watch_pokemon) >= 6:
                return watch_pokemon
    return watch_pokemon


def _render_team_preview_watch_team_note(shell_name: str, *, is_mode: bool) -> str:
    normalized_name = shell_name.strip().lower()
    rendered_name = _render_mode_label(shell_name) if is_mode else shell_name.replace("_", " ").title()
    weather_prefix = next(
        (prefix for prefix in ("rain", "sun", "sand", "snow") if normalized_name.startswith(prefix)),
        None,
    )

    if is_mode:
        if "tailroom" in normalized_name or normalized_name in {"dual_mode", "semiroom"}:
            return (
                f"{rendered_name} teams can switch between fast and slow plans midgame, so do not expose your cleaner "
                "until you know which speed button they are actually leaning on."
            )
        if weather_prefix and "tailwind" in normalized_name:
            return (
                f"{rendered_name} teams stack speed and field pressure at the same time, so one passive turn can lose "
                "both tempo and positioning at once."
            )
        if weather_prefix and "room" in normalized_name:
            return (
                f"{rendered_name} teams blend weather pressure with a slower board, so preview has to answer both the "
                "setup turn and the boosted attacker behind it."
            )
        if "tailwind" in normalized_name:
            return (
                f"{rendered_name} teams try to win the first boosted speed cycle, so plan how you will spend that turn "
                "before preview ends."
            )
        if "room" in normalized_name:
            return (
                f"{rendered_name} teams want their slow attackers moving first, so treat the setup turn and the first "
                "room turn as the real danger window."
            )
        if weather_prefix:
            return (
                f"{rendered_name} teams gain extra damage or bulk from weather turns, so count those turns carefully "
                "instead of only focusing on raw type matchups."
            )
        if normalized_name.endswith("terrain"):
            return (
                f"{rendered_name} teams get value from field turns and positioning, so identify which attacker the "
                "terrain is meant to boost or protect before you choose your four."
            )
        return (
            f"{rendered_name} teams usually pressure a very specific board state, so avoid autopiloting preview into the "
            "same four without checking how their shell actually wins."
        )

    if normalized_name == "hyper_offense":
        return (
            "Hyper Offense teams can punish passive openers immediately, so your first two turns need to trade tempo "
            "rather than just gather information."
        )
    if normalized_name == "balance":
        return (
            "Balance teams usually force repeated small trades, so preserve your control pieces until you know which "
            "exchange actually opens your win condition."
        )
    if normalized_name in {"stall", "semi_stall"}:
        return (
            f"{rendered_name} teams try to stretch the game and tax your support tools, so save your setup or cleaner "
            "route for the sequence that actually breaks through."
        )
    if normalized_name == "bulky_offense":
        return (
            "Bulky Offense teams can survive one wrong trade and hit back hard, so do not assume a small early lead is "
            "enough to snowball safely."
        )
    if normalized_name == "trick_room":
        return (
            "Trick Room teams punish teams that only function while moving first, so preview should already know which "
            "of your four can survive the slow turns."
        )
    return (
        f"{rendered_name} teams usually ask whether your default plan still works in a longer game, so make preview "
        "answer that question before you lock your four."
    )


# Curated mode-role knowledge for the meta's signature species so watchlists distinguish a Pokemon
# that *sets* a mode from one that *abuses* it from one that merely *supports* it (#5). Setter sets
# are keyed by base mode mechanic; a combined mode (e.g. rain_room) inherits every mechanic in its
# name. Anything that isn't a setter or a known support piece is, by definition of being a mode's
# signature attacker, an abuser of that mode.
_WATCH_MODE_SETTERS: dict[str, frozenset[str]] = {
    "trick_room": frozenset({"hatterene", "farigiraf"}),
    "tailwind": frozenset({"whimsicott", "aerodactyl", "talonflame", "pelipper", "tornadus"}),
    "rain": frozenset({"pelipper", "politoed"}),
    "sun": frozenset({"torkoal", "ninetales"}),
    "sand": frozenset({"tyranitar", "hippowdon"}),
    "snow": frozenset({"abomasnow", "ninetales-alola"}),
}
_WATCH_MODE_SUPPORT: frozenset[str] = frozenset(
    {
        "incineroar",
        "sinistcha",
        "whimsicott",
        "farigiraf",
        "amoonguss",
        "rillaboom",
        "grimmsnarl",
        "indeedee",
        "indeedee-f",
        "clefairy",
        "primarina",
        "sylveon",
        "florges",
        "audino",
    }
)


def _watch_mode_families(mode_name: str) -> set[str]:
    """The base mode mechanics implied by a (possibly combined) mode name."""
    families: set[str] = set()
    if "room" in mode_name:
        families.add("trick_room")
    if "tailwind" in mode_name or "tailroom" in mode_name:
        families.add("tailwind")
    for weather in ("rain", "sun", "sand", "snow"):
        if weather in mode_name:
            families.add(weather)
    return families or {mode_name}


def _watch_pokemon_role(species_token: str, mode_name: str) -> str:
    families = _watch_mode_families(mode_name)
    if any(species_token in _WATCH_MODE_SETTERS.get(family, frozenset()) for family in families):
        return "setter"
    if species_token in _WATCH_MODE_SUPPORT:
        return "support"
    return "abuser"


def _render_team_preview_watch_pokemon_note(species_token: str, mode_name: str) -> str:
    species_name = _render_species_token(species_token)
    mode_label = _render_mode_label(mode_name)
    if not mode_label:
        return species_name
    role = _watch_pokemon_role(species_token, mode_name)
    return f"{species_name} ({mode_label} {role})"


def _build_team_preview_strategy_notes(
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    team_mode_packages: list[str],
    team_win_condition_labels: list[str],
    bring_plans: list[dict[str, object]],
) -> list[str]:
    notes: list[str] = []
    role_members = _team_preview_role_members(member_roles)
    primary_plan = bring_plans[0]
    primary_leads = cast(list[str], primary_plan.get("leads", []))
    primary_back = cast(list[str], primary_plan.get("back", []))

    if primary_leads and primary_back:
        notes.append(
            f"Default to {_render_series(primary_leads)} in front with {_render_series(primary_back)} in back unless preview gives you a clear reason to pivot off that line. "
            "That opener keeps your safest first-turn tempo button in front while saving the back pair that usually closes once the board is stable."
        )

    primary_win_condition = team_win_condition_labels[0] if team_win_condition_labels else ""
    if primary_win_condition == "psyspam":
        setter_candidates = _dedupe_preserving_order(
            role_members["terrain_setter"]
            + role_members["special_sweeper"]
            + role_members["trick_room_setter"]
        )
    elif primary_win_condition == "perish_trap":
        setter_candidates = _dedupe_preserving_order(
            role_members["trapper"]
            + role_members["redirector"]
            + role_members["bulky_support"]
        )
    else:
        setter_candidates = _dedupe_preserving_order(
            role_members["tailwind_setter"]
            + role_members["trick_room_setter"]
            + role_members["screen_setter"]
            + role_members["weather_setter"]
            + role_members["terrain_setter"]
        )
    if setter_candidates:
        notes.append(
            f"Try to keep {_render_series(setter_candidates[:2])} healthy until the board is ready. Those are your cleanest buttons for claiming speed or field control, so avoid cashing them in for small early chip unless that trade immediately opens your endgame."
        )

    if team_win_condition_labels:
        if primary_win_condition == "setup_sweep":
            closers = _dedupe_preserving_order(primary_back + role_members["setup_sweeper"] + role_members["cleaner"])
            if closers:
                notes.append(
                    f"Your clearest endgame is still a setup or cleaner finish, so avoid trading {_render_series(closers[:2])} too early just to win turn two damage. If they disappear before the board is stable, the team often runs out of closing power even after a good start."
                )
        elif primary_win_condition == "screens_offense":
            screen_members = role_members["screen_setter"]
            if screen_members:
                notes.append(
                    f"Use {_render_series(screen_members[:1])} to make the first two turns safer, then hand the game to your setup or cleaner pieces rather than overextending with support. The screen turn matters most when it buys two attacks or a setup window, not when it only patches a bad lead for one exchange."
                )
        elif primary_win_condition == "perish_trap":
            trap_core = _dedupe_preserving_order(role_members["trapper"] + role_members["redirector"] + role_members["bulky_support"])
            if trap_core:
                notes.append(
                    f"Perish Trap games are usually won by keeping {_render_series(trap_core[:2])} on the board long enough to lock one sequence, not by chasing every early knockout. Most losses with this shell come from breaking your own trap sequence too early, not from missing a random knockout."
                )
        elif primary_win_condition == "psyspam":
            terrain_core = _dedupe_preserving_order(role_members["terrain_setter"] + role_members["special_sweeper"] + role_members["trick_room_setter"])
            if terrain_core:
                notes.append(
                    f"Protect the terrain turns for {_render_series(terrain_core[:2])}; once Psychic pressure is online, position to trade from advantage instead of resetting the board. That usually means preserving the terrain piece or the attack slot that actually cashes the Psychic turns into a knockout."
                )

    if len(bring_plans) > 1:
        alternate_plan = bring_plans[1]
        alternate_leads = cast(list[str], alternate_plan.get("leads", []))
        if alternate_leads:
            notes.append(
                f"If preview has strong answers to your default opener, pivot early into {_render_series(alternate_leads)} rather than forcing the same four every round. That swap is usually better than making your best cleaner defend from turn one."
            )

    if not notes:
        fallback_members = [member.pokemon_set.display_name for member in members[:2]]
        notes.append(
            f"Identify whether {_render_series(fallback_members)} or your backline is meant to win the long game before team preview ends, then bring with that route in mind. Beginners usually make this harder by choosing four good Pokemon instead of choosing the four that win the same endgame."
        )
    return notes


def _build_team_preview_counterplay_notes(
    member_roles: dict[str, list[str]],
    team_win_condition_labels: list[str],
    unfavorable_matchups: list[str],
    unfavorable_modes: list[str],
    top_defensive_weaknesses: list[str],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
) -> list[str]:
    notes: list[str] = []
    role_members = _team_preview_role_members(member_roles)

    if any("tailwind" in mode_name for mode_name in unfavorable_modes):
        if role_members["trick_room_setter"]:
            notes.append(
                f"Against opposing Tailwind shells, keep {_render_series(role_members['trick_room_setter'][:2])} available as a reverse-speed punish instead of racing them every turn. Your goal is not to outspeed them every turn; it is to make their first Tailwind cycle awkward enough that your own mode can take over."
            )
        elif role_members["speed_control"] or role_members["fake_out_support"]:
            tools = _dedupe_preserving_order(role_members["speed_control"] + role_members["fake_out_support"])
            # Only suggest Fake Out if the team actually carries it (#10).
            disruption_phrase = (
                "Fake Out, stall, or force Protects" if role_members["fake_out_support"] else "stall or force Protects"
            )
            notes.append(
                f"Against opposing Tailwind shells, preserve {_render_series(tools[:2])} so the first fast turn cycle does not force your cleaner in too early. Use those turns to {disruption_phrase} rather than offering a straight damage race."
            )
        elif utility_role_counts["protection"] >= 2:
            notes.append(
                "Against opposing Tailwind shells, trade Protect turns and positioning first instead of trying to win the first damage race outright. If you burn their first boosted turn safely, their speed advantage often expires before the real damage exchange starts."
            )

    if any("room" in mode_name for mode_name in unfavorable_modes) or "trick_room" in unfavorable_matchups:
        # Genuine setup contest (Fake Out flinches the setter, your own Trick Room flips theirs) is
        # distinct from softening the first room turn (redirection, healing). Don't conflate them.
        setup_contesters = _dedupe_preserving_order(role_members["fake_out_support"] + role_members["trick_room_setter"])
        room_softeners = _dedupe_preserving_order(role_members["redirector"] + role_members["healing_support"])
        if setup_contesters:
            note = f"Into Trick Room preview, lean on {_render_series(setup_contesters[:2])} to contest the setup turn itself"
            if room_softeners:
                note += f", and use {_render_series(room_softeners[:2])} to soften the first room turn rather than to stop the Room"
            note += ". Beginners often lose this matchup by aiming only at the sweeper; making the setup turn or first room turn low-value is usually enough."
            notes.append(note)
        elif room_softeners:
            notes.append(
                f"Into Trick Room preview, you have no direct way to deny the Room, but {_render_series(room_softeners[:2])} can soften the first room turn. Keep a bulkier or slower member that survives the room turns rather than bringing four frail fast attackers."
            )
        else:
            notes.append(
                "Into Trick Room preview, avoid bringing four frail fast attackers at once. Keep at least one bulkier or slower member that can survive the room turns, because that slot is often worth more than a fourth attacker that only functions while Room is down."
            )

    if any(mode_name.startswith(("rain", "sun", "sand", "snow")) for mode_name in unfavorable_modes):
        if role_members["weather_setter"]:
            notes.append(
                f"Against weather teams, preserve {_render_series(role_members['weather_setter'][:2])} so you can reset the field instead of fighting through every boosted turn. One well-timed weather reset often matters more than winning a single damage trade while their boost is still active."
            )
        else:
            notes.append(
                "Against weather teams, pressure the setter early and use your protection turns to shorten the window where their boosted attackers get clean swings. The point is to shrink the boosted window, not to win every exchange while weather is active."
            )

    if team_win_condition_labels and team_win_condition_labels[0] == "setup_sweep" and (
        role_members["fake_out_support"]
        or role_members["redirector"]
        or role_members["screen_setter"]
        or role_members["pivot"]
    ):
        setup_helpers = _dedupe_preserving_order(
            role_members["fake_out_support"]
            + role_members["redirector"]
            + role_members["screen_setter"]
            + role_members["pivot"]
        )
        notes.append(
            f"If opponents over-respect your setup line, use {_render_series(setup_helpers[:2])} to buy the setup turn later instead of forcing it immediately. That keeps the opponent guessing and forces them to cover both the immediate damage turn and the delayed setup turn."
        )

    if top_defensive_weaknesses:
        rendered_types = ", ".join(type_name.replace("_", " ").title() for type_name in top_defensive_weaknesses[:2])
        notes.append(
            f"If preview is built around {rendered_types} pressure, do not bring four members that all amplify that axis unless your mode advantage is overwhelming. In practice, at least one of your four should resist, pivot around, or disrupt that lane instead of simply racing it."
        )

    if not notes:
        if pokemon_role_counts["bulky_support"] + pokemon_role_counts["redirector"] >= 1:
            notes.append(
                "When the matchup looks rough, lean on your support turns first and make the opponent prove they can break through before you expose the cleaner. If they have to spend turns cracking support, you usually buy more chances to find the safer win path."
            )
        else:
            notes.append(
                "When preview looks bad, favor the line that keeps your speed-control and cleaner options alive longest instead of committing to the most explosive four. The flashiest four is often wrong if it burns your only way back into the speed war."
            )
    return notes


def _team_preview_role_members(member_roles: dict[str, list[str]]) -> dict[str, list[str]]:
    role_members = {role_name: [] for role_name in POKEMON_ROLE_ORDER}
    for member_name, roles in member_roles.items():
        for role_name in roles:
            if role_name in role_members:
                role_members[role_name].append(member_name)
    return role_members


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


def _render_species_token(species_token: str) -> str:
    if species_token.endswith("-mega-x"):
        base_name = species_token[: -len("-mega-x")]
        return f"Mega {base_name.replace('-', ' ').title()} X"
    if species_token.endswith("-mega-y"):
        base_name = species_token[: -len("-mega-y")]
        return f"Mega {base_name.replace('-', ' ').title()} Y"
    if species_token.endswith("-mega"):
        base_name = species_token[: -len("-mega")]
        return f"Mega {base_name.replace('-', ' ').title()}"
    if species_token.endswith("-male"):
        base_name = species_token[: -len("-male")]
        return f"{base_name.replace('-', ' ').title()} (M)"
    if species_token.endswith("-female"):
        base_name = species_token[: -len("-female")]
        return f"{base_name.replace('-', ' ').title()} (F)"
    if species_token.endswith("-alola"):
        base_name = species_token[: -len("-alola")]
        return f"Alolan {base_name.replace('-', ' ').title()}"
    if species_token.endswith("-hisui"):
        base_name = species_token[: -len("-hisui")]
        return f"Hisuian {base_name.replace('-', ' ').title()}"
    return species_token.replace("-", " ").title()


def summarize_utility_breakdown(utility_role_moves: dict[str, list[str]]) -> list[str]:
    return _summarize_role_breakdown(utility_role_moves, UTILITY_ROLE_ORDER)


def summarize_pokemon_role_breakdown(pokemon_role_members: dict[str, list[str]]) -> list[str]:
    return _summarize_role_breakdown(pokemon_role_members, POKEMON_ROLE_ORDER)


def summarize_team_archetype_scores(
    primary_team_archetype: str,
    team_archetype_scores: dict[str, float],
) -> list[str]:
    lines = [f"  Primary: {primary_team_archetype.replace('_', ' ').title()}"]
    for archetype in TEAM_ARCHETYPE_ORDER:
        lines.append(
            f"  {archetype.replace('_', ' ').title()}: {team_archetype_scores[archetype]}"
        )
    return lines


def summarize_matchup_profile(
    favorable_matchups: list[str],
    unfavorable_matchups: list[str],
    matchup_scores: dict[str, float],
    matchup_details: dict[str, dict[str, object]],
) -> list[str]:
    lines = [
        "  Favorable into: " + ", ".join(archetype.replace("_", " ").title() for archetype in favorable_matchups),
        "  Unfavorable into: " + ", ".join(archetype.replace("_", " ").title() for archetype in unfavorable_matchups),
    ]
    for archetype in BROAD_TEAM_ARCHETYPE_ORDER:
        lines.append(f"  Vs {archetype.replace('_', ' ').title()}: {matchup_scores[archetype]}")
        details = matchup_details.get(archetype, {})
        contextual_adjustment = details.get("contextual_adjustment")
        if isinstance(contextual_adjustment, (int, float)) and abs(float(contextual_adjustment)) >= 0.05:
            lines.append(f"    Context swing: {float(contextual_adjustment):+.2f}")
        for reason in cast(list[str], details.get("reasons", []))[:2]:
            lines.append(f"    Why: {reason}")
    return lines


def summarize_meta_mode_profile(
    team_mode_labels: list[str],
    favorable_modes: list[str],
    unfavorable_modes: list[str],
    mode_matchup_scores: dict[str, float],
) -> list[str]:
    lines = [
        "  Team mode labels: " + ", ".join(_render_mode_label(mode) for mode in team_mode_labels),
        "  Favorable into: " + ", ".join(_render_mode_label(mode) for mode in favorable_modes),
        "  Unfavorable into: " + ", ".join(_render_mode_label(mode) for mode in unfavorable_modes),
    ]
    for mode in MODE_LABEL_ORDER:
        lines.append(f"  Vs {_render_mode_label(mode)}: {mode_matchup_scores[mode]}")
    return lines


def summarize_meta_analysis(meta_analysis: dict[str, object]) -> list[str]:
    if not meta_analysis:
        return ["  None"]

    lines = [
        f"  Standing: {str(meta_analysis.get('label', 'unknown')).replace('_', ' ').title()}",
        f"  Weighted score: {meta_analysis.get('overall_score', 0.0)}",
        f"  Positive share: {meta_analysis.get('positive_weight_share', 0.0)}% of the weighted field",
        f"  Pressure share: {meta_analysis.get('negative_weight_share', 0.0)}% of the weighted field",
        "  Strongest current edges: " + ", ".join(cast(list[str], meta_analysis.get("strongest_targets", []))),
        "  Current pressure: " + ", ".join(cast(list[str], meta_analysis.get("pressured_targets", []))),
    ]

    for note in cast(list[str], meta_analysis.get("notes", [])):
        lines.append(f"  - {note}")

    for entry in cast(list[dict[str, object]], meta_analysis.get("tournament_rows", []))[:8]:
        lines.append(
            f"  {entry['label']}: meta {entry['meta_share']}%, matchup {entry['matchup_score']}, popular {entry['popularity_score']}%, results {entry['result_score']}%"
        )
        if "contextual_score" in entry:
            lines.append(f"    Context score: {cast(float, entry['contextual_score']):+.2f}")
        cores = cast(list[str], entry.get("key_cores", []))
        if cores:
            lines.append(f"    Cores: {_render_series(cores[:2])}")
        key_pokemon = cast(list[str], entry.get("key_pokemon", []))
        if key_pokemon:
            lines.append(f"    Pokemon: {_render_series(key_pokemon)}")
        for reason in cast(list[str], entry.get("context_reasons", []))[:2]:
            lines.append(f"    Why: {reason}")
    return lines


def summarize_team_difficulty(
    difficulty_label: str,
    difficulty_score: float,
    difficulty_factors: list[str],
) -> list[str]:
    lines = [
        f"  Label: {difficulty_label.replace('_', ' ').title()}",
        f"  Score: {difficulty_score}/10",
    ]
    for factor in difficulty_factors:
        lines.append(f"  - {factor}")
    return lines


def summarize_beginner_guidance(guidance_notes: list[str]) -> list[str]:
    if not guidance_notes:
        return ["  - No major beginner-facing build issues were flagged."]
    return [f"  - {note}" for note in guidance_notes]


def summarize_team_preview(team_preview: dict[str, object]) -> list[str]:
    if not team_preview:
        return ["  None"]

    bring_plans = cast(list[dict[str, object]], team_preview.get("bring_plans", []))
    watch_teams = cast(list[str], team_preview.get("watch_teams", []))
    watch_pokemon = cast(list[str], team_preview.get("watch_pokemon", []))
    strategy_notes = cast(list[str], team_preview.get("strategy_notes", []))
    counterplay_notes = cast(list[str], team_preview.get("counterplay_notes", []))

    lines: list[str] = []
    for plan in bring_plans:
        plan_label = cast(str, plan.get("label", "Plan"))
        leads = cast(list[str], plan.get("leads", []))
        back = cast(list[str], plan.get("back", []))
        pick_four = cast(list[str], plan.get("pick_four", []))
        recommended_into = cast(list[str], plan.get("recommended_into", []))
        member_reasons = cast(dict[str, str], plan.get("member_reasons", {}))
        summary = cast(str, plan.get("summary", ""))
        lines.append(
            f"  {plan_label}: lead {_render_series(leads)}; back {_render_series(back)}"
        )
        if recommended_into:
            lines.append(f"    Recommended into: {', '.join(recommended_into)}")
        if summary:
            lines.append(f"    {summary}")
        for member_name in pick_four:
            reason = member_reasons.get(member_name)
            if reason:
                lines.append(f"    {member_name}: {reason}")

    for note in watch_teams:
        lines.append(f"  Watch team: {note}")
    for note in watch_pokemon:
        lines.append(f"  Watch Pokemon: {note}")
    for note in strategy_notes:
        lines.append(f"  Strategy: {note}")
    for note in counterplay_notes:
        lines.append(f"  Counterplay: {note}")
    return lines or ["  None"]


def summarize_member_roles(member_roles: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for member_name, roles in member_roles.items():
        if not roles:
            continue
        rendered_roles = ", ".join(role.replace("_", " ").title() for role in roles)
        lines.append(f"  {member_name}: {rendered_roles}")
    return lines


def _summarize_role_breakdown(role_values: dict[str, list[str]], role_order: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for role in role_order:
        values = role_values[role]
        if not values:
            continue
        value_counts = Counter(values)
        rendered_values = ", ".join(
            f"{value} x{count}" if count > 1 else value
            for value, count in value_counts.items()
        )
        lines.append(f"  {role.replace('_', ' ').title()}: {len(values)} ({rendered_values})")
    return lines


def _is_protection_move(api_name: str, short_effect: str) -> bool:
    if api_name in PROTECTION_MOVES:
        return True
    return _contains_any(
        short_effect,
        (
            "prevents any moves from hitting the user",
            "protect itself from all attacks",
            "protects all friendly pok",
            "protects friendly pok",
            "protects all allies",
        ),
    )


def _is_screen_move(api_name: str, short_effect: str) -> bool:
    return api_name in SCREEN_MOVES or "reduces damage from" in short_effect


def _is_redirection_move(api_name: str, short_effect: str) -> bool:
    return api_name in REDIRECTION_MOVES or "redirect" in short_effect


def _is_weather_move(api_name: str, short_effect: str) -> bool:
    return api_name in WEATHER_MOVES or "changes the weather" in short_effect


def _is_terrain_move(api_name: str, short_effect: str) -> bool:
    return api_name in TERRAIN_MOVES or "terrain" in short_effect


def _is_speed_control_move(move: MoveData, short_effect: str) -> bool:
    if move.api_name in {
        "electroweb",
        "icy-wind",
        "nuzzle",
        "quash",
        "tailwind",
        "thunder-wave",
        "trick-room",
    }:
        return True
    if _guarantees_paralysis(move):
        return True
    if _guarantees_speed_change(move):
        return True

    return _contains_any(
        short_effect,
        (
            "act last",
            "move go last",
            "move last",
            "slower pok",
            "move first",
            "doubled speed",
            "speed doubled",
        ),
    )


def _is_recovery_move(move: MoveData, short_effect: str) -> bool:
    return move.healing > 0 or _contains_any(short_effect, ("heal", "restores", "regains"))


def _is_healing_support_move(move: MoveData, api_name: str, short_effect: str) -> bool:
    if api_name in HEALING_SUPPORT_MOVES:
        return True
    if move.target_name in {"user-and-allies", "users-field"} and move.healing > 0:
        return True
    return (
        "status" in short_effect
        and _contains_any(short_effect, ("party", "allies", "team", "entire"))
    )


def _is_pivoting_move(api_name: str, short_effect: str) -> bool:
    if api_name in PIVOT_MOVES:
        return True
    return _contains_any(
        short_effect,
        (
            "user immediately switches out",
            "user must switch out after attacking",
            "makes the user switch out",
            "switches with a party pok",
            "switch out after attacking",
        ),
    )


def _is_entry_hazard_move(api_name: str, short_effect: str) -> bool:
    if api_name in ENTRY_HAZARD_MOVES:
        return True
    return "switch in" in short_effect and _contains_any(short_effect, ("trap", "damage", "hurt"))


def _is_hazard_removal_move(api_name: str, short_effect: str) -> bool:
    if api_name in HAZARD_REMOVAL_MOVES:
        return True
    return _contains_any(
        short_effect,
        (
            "removes field effects",
            "removes spikes",
            "removes stealth rock",
            "clears away fog",
        ),
    )


def _is_disruption_move(api_name: str, short_effect: str) -> bool:
    if api_name in DISRUPTION_MOVES:
        return True
    return _contains_any(
        short_effect,
        (
            "can only use damaging moves",
            "forced to repeat",
            "repeat its last move",
            "disables the target",
            "prevents the target from using",
            "can no longer use the same move",
        ),
    )


def _is_item_control_move(api_name: str, short_effect: str) -> bool:
    if api_name in ITEM_CONTROL_MOVES:
        return True
    if "held item" not in short_effect and "item" not in short_effect:
        return False
    return _contains_any(short_effect, ("drop", "lose", "remove", "swap", "switch", "exchange"))


def _is_phazing_move(move: MoveData, api_name: str, short_effect: str) -> bool:
    if api_name in PHAZING_MOVES or move.category_name == "force-switch":
        return True
    return _contains_any(
        short_effect,
        (
            "forces trainers to switch",
            "dragged out",
            "switches the target out",
            "target is scared off",
        ),
    )


def _is_trapping_move(api_name: str, short_effect: str) -> bool:
    if api_name in TRAPPING_MOVES:
        return True
    return _contains_any(
        short_effect,
        (
            "traps the target",
            "cannot switch out",
            "prevent the target from escaping",
            "prevents the target from fleeing",
        ),
    )


def _is_anti_setup_move(api_name: str, short_effect: str) -> bool:
    if api_name in ANTI_SETUP_MOVES:
        return True
    return _contains_any(
        short_effect,
        (
            "resets all pokémon’s stats",
            "eliminates every stat change",
            "removes the target's stat changes",
            "steals the target's stat changes",
            "reverses all stat changes",
        ),
    )


def _guarantees_flinch(move: MoveData) -> bool:
    if move.flinch_chance <= 0:
        return False
    if move.damage_class == "status":
        return True
    return move.flinch_chance == 100 or move.effect_chance == 100


def _guarantees_ailment(move: MoveData) -> bool:
    if move.ailment_name == "none":
        return False
    if move.damage_class == "status":
        return True
    return move.ailment_chance == 100 or move.effect_chance == 100


def _guarantees_paralysis(move: MoveData) -> bool:
    return move.ailment_name == "paralysis" and _guarantees_ailment(move)


def _guarantees_speed_change(move: MoveData) -> bool:
    if not _guarantees_stat_changes(move):
        return False
    return any(stat_change.stat_name == "speed" for stat_change in move.stat_changes)


def _guarantees_positive_stat_change(move: MoveData) -> bool:
    if not _guarantees_stat_changes(move):
        return False
    return any(stat_change.change > 0 for stat_change in move.stat_changes)


def _guarantees_negative_stat_change(move: MoveData) -> bool:
    if not _guarantees_stat_changes(move):
        return False
    return any(stat_change.change < 0 for stat_change in move.stat_changes)


def _guarantees_stat_changes(move: MoveData) -> bool:
    if not move.stat_changes:
        return False
    if move.damage_class == "status":
        return True
    return move.stat_chance == 100 or move.effect_chance == 100


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _render_mode_label(mode_name: str) -> str:
    return mode_name.replace("_", " ").title()


def _species_tokens_for_member(member: TeamMember) -> set[str]:
    api_name = member.species_data.api_name.lower()
    tokens = {api_name}
    compact_parts = [part for part in api_name.split("-") if part not in {"mega", "male", "female"}]
    if compact_parts:
        tokens.add("-".join(compact_parts))
        tokens.add(compact_parts[0])
        if compact_parts[-1] not in {compact_parts[0], "hisui", "alola", "paldea"}:
            tokens.add(compact_parts[-1])
    if api_name.endswith("-rotom"):
        tokens.add("rotom")
    return tokens


def _weighted_defensive_exposure(
    defensive_profile: dict[str, dict[str, float | int]],
    top_defensive_weaknesses: list[str],
    weighted_types: dict[str, float],
) -> float:
    exposure = 0.0
    for type_name, weight in weighted_types.items():
        type_profile = defensive_profile[type_name]
        exposure += weight * (
            float(type_profile["average_multiplier"])
            - 1.0
            + 0.12 * int(type_profile["weak_members"])
            - 0.05 * int(type_profile["resistant_members"])
            - 0.08 * int(type_profile["immune_members"])
        )
        if type_name in top_defensive_weaknesses:
            exposure += 0.18 * weight
    return exposure


def _score_team_field_soundness(
    defensive_profile: dict[str, dict[str, float | int]],
    top_defensive_weaknesses: list[str],
    offensive_coverage: dict[str, int],
    pokemon_role_counts: dict[str, int],
    utility_role_counts: dict[str, int],
    contextual_matchup_profile: ContextualMatchupProfile,
) -> tuple[float, list[str]]:
    """Absolute, mode-independent measure of how field-viable a team actually is.

    The weighted mode/broad matchup scores are *mean-centered* (they describe which
    matchups are relatively best/worst for this team, summing to ~0), so on their own
    they make every team look favorable into half the field regardless of quality.
    This term restores an absolute baseline: it returns a signed offset (≈0 for a sound
    meta team, strongly negative for a structurally broken one) plus human-readable
    reasons. The offset is added uniformly to every board matchup, so the relative shell
    ranking is preserved while the overall grade reflects real soundness.

    The dominant signal is *shared* (stacked) weakness — a type that threatens most of
    the team at once, so there is no healthy member to pivot to (the hallmark of a
    mono-type build). It is reinforced by raw exposure to the common attacking field and
    one-dimensional offense, and a small floor for teams with no disruption at all.
    """

    # Shared weakness: members a type hits super-effectively beyond a 3-member "pivot"
    # floor, weighted by how common that attacking type is. A mono-type team stacks this.
    stacked_weakness = 0.0
    for type_name, threat_weight in M_A_FIELD_THREAT_TYPES.items():
        weak_members = int(defensive_profile[type_name]["weak_members"])
        stacked_weakness += threat_weight * max(0, weak_members - 3)

    # Raw exposure to the broad attacking field, penalized only above an average baseline.
    field_exposure = _weighted_defensive_exposure(
        defensive_profile, top_defensive_weaknesses, M_A_FIELD_THREAT_TYPES
    )
    exposure_excess = max(0.0, field_exposure - 2.6)

    # One-dimensional offense: few distinct attacking types is easy to wall.
    distinct_attack_types = sum(1 for count in offensive_coverage.values() if count > 0)
    narrow_offense = max(0, 7 - distinct_attack_types)

    # Floor: a team with no speed control, redirection, or priority has nothing to bend a
    # bad matchup with.
    speed_control = pokemon_role_counts["speed_control"] + utility_role_counts["speed_control"]
    disruption_tools = speed_control + pokemon_role_counts["redirector"] + contextual_matchup_profile.priority_attacks
    no_disruption = 1.0 if disruption_tools == 0 else 0.0

    penalty = (
        0.08 * stacked_weakness
        + 0.06 * exposure_excess
        + 0.035 * narrow_offense
        + 0.25 * no_disruption
    )
    penalty = min(penalty, 1.0)
    soundness = -round(penalty, 2)

    # Clauses are fragments (no trailing period) so they read cleanly when joined into a
    # series by the caller's note.
    reasons: list[str] = []
    if stacked_weakness >= 1.5:
        reasons.append(
            "multiple common attacking types hit most of the team at once, so a single well-picked "
            "attacker pressures the whole board with no healthy member to pivot into"
        )
    if exposure_excess >= 0.75:
        reasons.append("it is broadly exposed to the most common offense in the format")
    if narrow_offense >= 2:
        reasons.append("its offense is one-dimensional, so bulky answers can wall it without much risk")
    if no_disruption:
        reasons.append("it has no speed control, redirection, or priority to bend a losing matchup")
    return soundness, reasons


def _normalized_ability_name(ability: str | None) -> str:
    return (ability or "").strip().lower()


def _normalized_item_name(item: str | None) -> str:
    return (item or "").strip().lower()
