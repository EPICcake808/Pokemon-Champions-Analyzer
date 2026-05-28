from __future__ import annotations

from collections import Counter
from itertools import combinations
from statistics import median, pstdev
from typing import Iterable, cast

from .champions_m_a_meta import MODE_LABEL_ORDER, TOURNAMENT_MODE_SNAPSHOTS
from .data import CachedPokeApiClient, MetadataProvider
from .meta_snapshots import get_tournament_team_snapshots
from .models import (
    BROAD_TEAM_ARCHETYPE_ORDER,
    MODE_PACKAGE_ORDER,
    MoveData,
    POKEMON_ROLE_ORDER,
    SPEED_TIER_ORDER,
    STYLE_PACKAGE_ORDER,
    TEAM_ARCHETYPE_ORDER,
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
from .speed_benchmarks import SpeedBenchmarkGroup, RegulationSpeedBenchmarkCatalog, get_speed_benchmark_catalog


TYPE_EFFECTIVENESS = {
    "normal": {"rock": 0.5, "ghost": 0.0, "steel": 0.5},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0},
    "water": {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5},
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5},
    "poison": {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0.0, "fairy": 2.0},
    "ground": {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0},
    "flying": {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0, "steel": 0.5},
    "ghost": {"normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5},
    "dragon": {"dragon": 2.0, "steel": 0.5, "fairy": 0.0},
    "dark": {"fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, "steel": 0.5, "fairy": 2.0},
    "fairy": {"fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5},
}

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
PREVIEW_PRIMARY_WIN_CONDITIONS = {"perish_trap", "psyspam"}
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
CHAMPIONS_FIXED_IV = 31
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

    for attack_type in TYPE_ORDER:
        multipliers = []
        weak_members = 0
        resistant_members = 0
        immune_members = 0

        for member in members:
            multiplier = defensive_multiplier(member.species_data.types, attack_type)
            multipliers.append(multiplier)
            if multiplier == 0.0:
                immune_members += 1
            elif multiplier > 1.0:
                weak_members += 1
            elif multiplier < 1.0:
                resistant_members += 1

        defensive_profile[attack_type] = {
            "average_multiplier": round(sum(multipliers) / len(multipliers), 4),
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
    matchup_scores, favorable_matchups, unfavorable_matchups = infer_matchup_profile(
        members,
        classified_members,
        pokemon_role_counts,
        utility_role_counts,
        offensive_coverage,
        defensive_profile,
        top_defensive_weaknesses,
        team_archetype_scores,
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
    meta_analysis = infer_meta_analysis(
        team_mode_scores,
        team_mode_labels,
        mode_matchup_scores,
        matchup_scores,
        favorable_modes,
        unfavorable_modes,
        regulation_id=regulation_id,
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

    return TeamAnalysis(
        regulation_id=regulation_id,
        team_size=len(members),
        typing_counts=typing_counts,
        defensive_profile=defensive_profile,
        offensive_coverage=offensive_coverage,
        target_coverage=target_coverage,
        coverage_gaps=coverage_gaps,
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


def defensive_multiplier(defending_types: tuple[str, ...], attack_type: str) -> float:
    multiplier = 1.0
    matchups = TYPE_EFFECTIVENESS[attack_type]
    for defending_type in defending_types:
        multiplier *= matchups.get(defending_type, 1.0)
    return multiplier


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


def _normalized_battle_speed(member: TeamMember) -> int:
    return _normalized_member_stats(member)["speed"]


def _normalized_member_stats(member: TeamMember) -> dict[str, int]:
    level = 50
    return {
        "hp": _normalized_hp_stat(member.species_data.base_hp, member.pokemon_set.evs.get("HP", 0), level=level),
        "attack": _normalized_non_hp_stat(
            member.species_data.base_attack,
            member.pokemon_set.evs.get("Atk", 0),
            level=level,
            nature_multiplier=_nature_multiplier(member.pokemon_set.nature, "attack"),
        ),
        "defense": _normalized_non_hp_stat(
            member.species_data.base_defense,
            member.pokemon_set.evs.get("Def", 0),
            level=level,
            nature_multiplier=_nature_multiplier(member.pokemon_set.nature, "defense"),
        ),
        "special_attack": _normalized_non_hp_stat(
            member.species_data.base_special_attack,
            member.pokemon_set.evs.get("SpA", 0),
            level=level,
            nature_multiplier=_nature_multiplier(member.pokemon_set.nature, "special_attack"),
        ),
        "special_defense": _normalized_non_hp_stat(
            member.species_data.base_special_defense,
            member.pokemon_set.evs.get("SpD", 0),
            level=level,
            nature_multiplier=_nature_multiplier(member.pokemon_set.nature, "special_defense"),
        ),
        "speed": _normalized_non_hp_stat(
            member.species_data.base_speed,
            member.pokemon_set.evs.get("Spe", 0),
            level=level,
            nature_multiplier=_nature_multiplier(member.pokemon_set.nature, "speed"),
        ),
    }


def _normalized_hp_stat(base_stat: int, ev: int, *, level: int) -> int:
    base_component = ((2 * base_stat + CHAMPIONS_FIXED_IV) * level) // 100
    return base_component + level + 10 + ev


def _normalized_non_hp_stat(base_stat: int, ev: int, *, level: int, nature_multiplier: float) -> int:
    base_component = ((2 * base_stat + CHAMPIONS_FIXED_IV) * level) // 100
    return int((base_component + 5) * nature_multiplier) + ev


def _nature_multiplier(nature: str | None, stat_name: str) -> float:
    normalized_nature = (nature or "").strip().lower()
    if normalized_nature not in NATURE_MODIFIERS:
        return 1.0
    boosted_stat, lowered_stat = NATURE_MODIFIERS[normalized_nature]
    if stat_name == boosted_stat:
        return 1.1
    if stat_name == lowered_stat:
        return 0.9
    return 1.0


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
    item_name = _normalized_item_name(member.pokemon_set.item)
    weather_from_ability = ability_name in WEATHER_SETTER_ABILITIES
    terrain_from_ability = ability_name in TERRAIN_SETTER_ABILITIES
    has_regenerator = ability_name == "regenerator"
    has_choice_power_item = item_name in CHOICE_POWER_ITEMS
    has_choice_scarf = item_name == "choice scarf"
    has_assault_vest = item_name == "assault vest"
    has_light_clay = item_name == "light clay"
    has_defensive_item = item_name in DEFENSIVE_ITEMS
    has_recovery_item = item_name in RECOVERY_ITEMS
    has_eviolite = item_name == "eviolite"
    has_pivot_ability = ability_name in PIVOT_ABILITIES
    has_support_ability = ability_name in SUPPORT_ABILITIES
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
    if (
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
        ability_name = _normalized_ability_name(member.pokemon_set.ability)
        if ability_name:
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
        scores["screens_offense"] -= 6.0
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
) -> tuple[dict[str, float], list[str], list[str]]:
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

    average_score = sum(raw_scores.values()) / len(raw_scores)
    matchup_scores = {
        archetype: round(raw_scores[archetype] - average_score, 2)
        for archetype in BROAD_TEAM_ARCHETYPE_ORDER
    }
    favorable_ranked = sorted(matchup_scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    unfavorable_ranked = sorted(matchup_scores.items(), key=lambda item: (item[1], item[0]))
    favorable_matchups = [archetype for archetype, score in favorable_ranked if score > 0][:2]
    unfavorable_matchups = [archetype for archetype, score in unfavorable_ranked if score < 0][:2]

    if not favorable_matchups:
        favorable_matchups = [favorable_ranked[0][0]]
    if not unfavorable_matchups:
        unfavorable_matchups = [unfavorable_ranked[0][0]]

    return matchup_scores, favorable_matchups, unfavorable_matchups


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
        ability_name = _normalized_ability_name(member.pokemon_set.ability)
        if ability_name:
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


def infer_meta_analysis(
    team_mode_scores: dict[str, float],
    team_mode_labels: list[str],
    mode_matchup_scores: dict[str, float],
    broad_matchup_scores: dict[str, float],
    favorable_modes: list[str],
    unfavorable_modes: list[str],
    regulation_id: str | None = DEFAULT_REGULATION_ID,
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
        mode_matchup_scores,
        broad_matchup_scores,
        regulation_id=regulation_id,
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
            f"Weighted against current Regulation M-A tournament-result teams, this team grades as "
            f"{meta_label.replace('_', ' ')} at {overall_score}, with {positive_weight_share}% of the tracked board "
            f"scoring favorable and {negative_weight_share}% scoring pressured."
        )
    ]
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
        "notes": notes,
    }


def _build_tournament_meta_rows(
    mode_matchup_scores: dict[str, float],
    broad_matchup_scores: dict[str, float],
    regulation_id: str | None = DEFAULT_REGULATION_ID,
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
        matchup_score = round(0.72 * mode_score + 0.28 * broad_score, 2)
        rows.append(
            {
                "slug": snapshot["slug"],
                "label": snapshot["label"],
                "source": snapshot["source"],
                "result_label": snapshot["result_label"],
                "modes": [_render_mode_label(mode_name) for mode_name in cast(tuple[str, ...], snapshot["modes"])],
                "key_cores": list(cast(tuple[str, ...], snapshot["key_cores"])),
                "key_pokemon": [
                    _render_species_token(species_token)
                    for species_token in cast(tuple[str, ...], snapshot["key_pokemon"])
                ],
                "popularity_score": round(100 * cast(float, snapshot["popularity_weight"]), 1),
                "result_score": round(100 * cast(float, snapshot["result_weight"]), 1),
                "meta_weight": round(meta_weight, 4),
                "meta_share": round(100 * meta_weight / total_weight, 1),
                "matchup_score": matchup_score,
                "impact_score": round(meta_weight * matchup_score, 2),
                "standing": _classify_meta_matchup_standing(matchup_score),
            }
        )

    return sorted(
        rows,
        key=lambda row: (-cast(float, row["meta_share"]), -abs(cast(float, row["impact_score"])), cast(str, row["label"])),
    )


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
    if overall_score >= 0.6:
        return "strong"
    if overall_score >= 0.2:
        return "solid"
    if overall_score > -0.2:
        return "even"
    if overall_score > -0.6:
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
        lead_pair, pick_four = _select_team_preview_plan(
            members,
            member_roles,
            member_battle_speeds,
            member_speed_tiers,
            focus,
            opponent_mode,
            bring_plans,
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
        )
        bring_plans.append(
            {
                "label": _render_team_preview_plan_label(focus, index, opponent_mode),
                "summary": _summarize_team_preview_plan(focus, lead_pair, back_line, opponent_mode),
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
                "summary": _summarize_team_preview_plan("safe_default", fallback_leads, fallback_back, None),
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
        descriptors.append(
            {
                "focus": primary_focus,
                "opponent_mode": opponent_mode,
                "recommended_into": [_render_mode_label(opponent_mode)],
            }
        )
    return descriptors


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
    )
    fallback_pick_four = _select_team_preview_pick_four(
        members,
        member_roles,
        member_battle_speeds,
        member_speed_tiers,
        focus,
        fallback_leads,
        opponent_mode,
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


def _score_team_preview_pair(
    pair: tuple[str, str],
    members: list[TeamMember],
    member_roles: dict[str, list[str]],
    member_battle_speeds: dict[str, int],
    member_speed_tiers: dict[str, str],
    focus: str,
    opponent_mode: str | None,
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
    focus_flags = _team_preview_focus_flags(focus)
    move_names = _team_preview_move_names(member)

    if selected_attackers < 2 and roles & PREVIEW_ATTACKER_ROLES:
        score += 1.3
    if selected_supports == 0 and roles & PREVIEW_SUPPORT_ROLES:
        score += 1.2
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
) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for member_name in pick_four:
        reasons[member_name] = _describe_team_preview_member_reason(
            member_lookup[member_name],
            set(member_roles.get(member_name, [])),
            focus,
            opponent_mode,
            member_name in lead_pair,
            member_name in back_line,
        )
    return reasons


def _describe_team_preview_member_reason(
    member: TeamMember,
    roles: set[str],
    focus: str,
    opponent_mode: str | None,
    in_lead: bool,
    in_back: bool,
) -> str:
    move_names = _team_preview_move_names(member)
    focus_flags = _team_preview_focus_flags(focus)
    counter_reason = _describe_team_preview_counter_reason(member, roles, opponent_mode, in_lead)
    if counter_reason:
        return counter_reason

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
        if roles & {"setup_sweeper", "cleaner"}:
            return "Stays in back as the main cleaner once the opener has forced trades."
        if roles & {"bulky_attacker", "bulky_support", "redirector"}:
            return "Stays in back as the stabilizing midgame piece if the opener gets messy."

    return "Rounds out the four by covering a role the opening pair should not expose too early."


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


def _summarize_team_preview_plan(focus: str, lead_pair: list[str], back_line: list[str], opponent_mode: str | None) -> str:
    if not lead_pair:
        return "No clear preview plan was inferred."
    lead_text = _render_series(lead_pair)
    back_text = _render_series(back_line) if back_line else "the remaining flex slots"
    focus_flags = _team_preview_focus_flags(focus)
    opener_prefix = f"Into {_render_mode_label(opponent_mode)}, " if opponent_mode else ""

    if focus_flags["perish"]:
        opener = f"{opener_prefix}lead {lead_text} to start the trap or positioning sequence without exposing the whole endgame at once."
    elif focus_flags["screens"]:
        opener = f"{opener_prefix}lead {lead_text} to establish screens or immediate setup support before your main closer comes in."
    elif focus_flags["trick_room"] and focus_flags["tailwind"]:
        opener = f"{opener_prefix}lead {lead_text} to keep both speed modes available while you read which branch preview is really asking for."
    elif focus_flags["trick_room"]:
        opener = f"{opener_prefix}lead {lead_text} to contest the opening turn and establish Trick Room or its support turn cleanly."
    elif focus_flags["tailwind"]:
        opener = f"{opener_prefix}lead {lead_text} to get the fast mode online quickly and force early tempo."
    elif focus_flags["weather"]:
        opener = f"{opener_prefix}lead {lead_text} to secure weather first and make the opponent respect boosted damage immediately."
    elif focus_flags["terrain"]:
        opener = f"{opener_prefix}lead {lead_text} to claim terrain early and route the game through your strongest terrain turns."
    else:
        opener = f"{opener_prefix}lead {lead_text} as the most stable default pair when preview does not force a hard adaptation."

    opener = opener[0].upper() + opener[1:]
    return f"{opener} Keep {back_text} in back as the cleaner or stabilizing endgame line."


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


def _render_team_preview_watch_pokemon_note(species_token: str, mode_name: str) -> str:
    species_name = _render_species_token(species_token)
    mode_label = _render_mode_label(mode_name)
    return f"{species_name} ({mode_label})" if mode_label else species_name


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
            notes.append(
                f"Against opposing Tailwind shells, preserve {_render_series(tools[:2])} so the first fast turn cycle does not force your cleaner in too early. Use those turns to stall, Fake Out, or force Protects rather than offering a straight damage race."
            )
        elif utility_role_counts["protection"] >= 2:
            notes.append(
                "Against opposing Tailwind shells, trade Protect turns and positioning first instead of trying to win the first damage race outright. If you burn their first boosted turn safely, their speed advantage often expires before the real damage exchange starts."
            )

    if any("room" in mode_name for mode_name in unfavorable_modes) or "trick_room" in unfavorable_matchups:
        setup_contesters = _dedupe_preserving_order(role_members["fake_out_support"] + role_members["trick_room_setter"] + role_members["redirector"])
        if setup_contesters:
            notes.append(
                f"Into Trick Room preview, lean on {_render_series(setup_contesters[:2])} to either contest the setup turn or make the first room turn low-impact. Beginners often lose this matchup by aiming only at the sweeper; making the setup turn or first room turn low-value is usually enough."
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
) -> list[str]:
    lines = [
        "  Favorable into: " + ", ".join(archetype.replace("_", " ").title() for archetype in favorable_matchups),
        "  Unfavorable into: " + ", ".join(archetype.replace("_", " ").title() for archetype in unfavorable_matchups),
    ]
    for archetype in BROAD_TEAM_ARCHETYPE_ORDER:
        lines.append(f"  Vs {archetype.replace('_', ' ').title()}: {matchup_scores[archetype]}")
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
        cores = cast(list[str], entry.get("key_cores", []))
        if cores:
            lines.append(f"    Cores: {_render_series(cores[:2])}")
        key_pokemon = cast(list[str], entry.get("key_pokemon", []))
        if key_pokemon:
            lines.append(f"    Pokemon: {_render_series(key_pokemon)}")
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


def _normalized_ability_name(ability: str | None) -> str:
    return (ability or "").strip().lower()


def _normalized_item_name(item: str | None) -> str:
    return (item or "").strip().lower()
