from __future__ import annotations

from dataclasses import dataclass, field

from .champions_m_a_meta import MODE_LABEL_ORDER
from .glossary import GLOSSARY


TYPE_ORDER = (
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)

UTILITY_ROLE_ORDER = (
    "protection",
    "screen",
    "redirection",
    "weather",
    "terrain",
    "speed_control",
    "recovery",
    "healing_support",
    "pivoting",
    "entry_hazard",
    "hazard_removal",
    "disruption",
    "item_control",
    "phazing",
    "trapping",
    "anti_setup",
    "flinch_control",
    "status_infliction",
    "stat_boost",
    "stat_drop",
    "other_utility",
)

POKEMON_ROLE_ORDER = (
    "physical_sweeper",
    "special_sweeper",
    "setup_sweeper",
    "cleaner",
    "bulky_attacker",
    "pivot",
    "bulky_pivot",
    "bulky_support",
    "support",
    "fake_out_support",
    "tailwind_setter",
    "trick_room_setter",
    "hazard_setter",
    "hazard_control",
    "screen_setter",
    "weather_setter",
    "terrain_setter",
    "speed_control",
    "healing_support",
    "trapper",
    "redirector",
)

BROAD_TEAM_ARCHETYPE_ORDER = (
    "hyper_offense",
    "bulky_offense",
    "balance",
    "semi_stall",
    "stall",
    "trick_room",
)

STYLE_PACKAGE_ORDER = (
    "hyper_offense",
    "bulky_offense",
    "balance",
    "semi_stall",
    "stall",
)

MODE_PACKAGE_ORDER = (
    "tailwind",
    "trick_room",
    "semiroom",
    "tailroom",
    "dual_mode",
    "rain",
    "sun",
    "sand",
    "snow",
    "electric_terrain",
    "grassy_terrain",
    "misty_terrain",
    "psychic_terrain",
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
)

WIN_CONDITION_PACKAGE_ORDER = (
    "perish_trap",
    "screens_offense",
    "setup_sweep",
    "psyspam",
)

TEAM_ARCHETYPE_ORDER = (
    *BROAD_TEAM_ARCHETYPE_ORDER,
    "rain",
    "sun",
    "sand",
    "snow",
    "electric_terrain",
    "grassy_terrain",
    "misty_terrain",
    "psychic_terrain",
    "tailwind",
    "semiroom",
    "rain_tailwind",
    "sun_tailwind",
    "sand_tailwind",
    "snow_tailwind",
    "rain_room",
    "sun_room",
    "sand_room",
    "snow_room",
    "tailroom",
    "rain_tailroom",
    "sun_tailroom",
    "screens_offense",
    "psyspam",
    "dual_mode",
    "perish_trap",
)

SPEED_TIER_ORDER = (
    "trick_room_slow",
    "slow",
    "midrange",
    "fast",
    "very_fast",
    "elite_fast",
)

# Per-section confidence in the analysis (#16). Surfaced so heuristic outputs are not read as precise
# predictions: high-confidence sections rest on directly checked facts, low-confidence ones are
# heuristic inferences. ``ANALYSIS_CONFIDENCE`` maps each analysis section to a tier in
# ``CONFIDENCE_TIERS``; the web renders the tier as a caveat badge.
CONFIDENCE_TIERS: dict[str, str] = {
    "high": "Based on directly checked facts — legality and the team's actual moves, items, and stats.",
    "medium": "A heuristic read of archetype and mode from team composition.",
    "low": "A heuristic matchup estimate — directional, not a win-rate prediction.",
    "very_low": "Low-sample or unknown custom sets — treat as a rough signal only.",
}
ANALYSIS_CONFIDENCE: dict[str, str] = {
    "legality": "high",
    "roles": "high",
    "speed": "high",
    "coverage": "high",
    "archetype": "medium",
    "modes": "medium",
    "matchup": "low",
    "meta_board": "low",
}


@dataclass(frozen=True)
class PokemonSet:
    species: str
    moves: list[str]
    item: str | None = None
    ability: str | None = None
    level: int | None = None
    nature: str | None = None
    evs: dict[str, int] = field(default_factory=dict)
    nickname: str | None = None

    @property
    def display_name(self) -> str:
        return self.nickname or self.species


@dataclass(frozen=True)
class SpeciesData:
    name: str
    api_name: str
    types: tuple[str, ...]
    base_hp: int
    base_attack: int
    base_defense: int
    base_special_attack: int
    base_special_defense: int
    base_speed: int


@dataclass(frozen=True)
class MoveStatChange:
    stat_name: str
    change: int


@dataclass(frozen=True)
class MoveData:
    name: str
    api_name: str
    type_name: str
    damage_class: str
    power: int | None = None
    accuracy: int | None = None
    pp: int = 0
    short_effect: str = ""
    effect_chance: int | None = None
    category_name: str = "unknown"
    ailment_name: str = "none"
    ailment_chance: int = 0
    flinch_chance: int = 0
    healing: int = 0
    stat_chance: int = 0
    stat_changes: tuple[MoveStatChange, ...] = ()
    priority: int = 0
    target_name: str = "unknown"


@dataclass(frozen=True)
class TeamMember:
    pokemon_set: PokemonSet
    species_data: SpeciesData
    move_data: tuple[MoveData, ...]


@dataclass(frozen=True)
class TeamAnalysis:
    regulation_id: str | None
    team_size: int
    typing_counts: dict[str, int]
    defensive_profile: dict[str, dict[str, float | int]]
    offensive_coverage: dict[str, int]
    target_coverage: dict[str, dict[str, float | int]]
    coverage_gaps: list[str]
    coverage_quality: list[dict[str, object]]
    average_base_speed: float
    average_battle_speed: float
    median_battle_speed: float
    speed_standard_deviation: float
    team_speed_tier: str
    fastest_pokemon: tuple[str, int]
    slowest_pokemon: tuple[str, int]
    fastest_battle_speed_pokemon: tuple[str, int]
    slowest_battle_speed_pokemon: tuple[str, int]
    member_base_speeds: dict[str, int]
    member_battle_speeds: dict[str, int]
    member_stats: dict[str, dict[str, int]]
    member_speed_tiers: dict[str, str]
    speed_tier_counts: dict[str, int]
    speed_tier_members: dict[str, list[str]]
    speed_benchmark_catalog: dict[str, str] | None
    speed_benchmark_notes: list[str]
    speed_benchmark_groups: dict[str, dict[str, object]]
    member_speed_benchmark_tags: dict[str, list[dict[str, object]]]
    member_speed_contexts: dict[str, list[dict[str, object]]]
    damage_split: dict[str, int]
    damage_matchups: dict[str, object]
    speed_coverage: dict[str, object]
    plain_summary: list[str]
    utility_moves: int
    utility_role_counts: dict[str, int]
    utility_role_moves: dict[str, list[str]]
    pokemon_role_counts: dict[str, int]
    pokemon_role_members: dict[str, list[str]]
    member_roles: dict[str, list[str]]
    primary_team_archetype: str
    team_archetype_scores: dict[str, float]
    primary_team_style: str
    team_style_scores: dict[str, float]
    team_mode_packages: list[str]
    team_mode_package_scores: dict[str, float]
    team_win_condition_labels: list[str]
    team_win_condition_scores: dict[str, float]
    matchup_scores: dict[str, float]
    matchup_details: dict[str, dict[str, object]]
    favorable_matchups: list[str]
    unfavorable_matchups: list[str]
    team_mode_scores: dict[str, float]
    team_mode_labels: list[str]
    mode_matchup_scores: dict[str, float]
    favorable_modes: list[str]
    unfavorable_modes: list[str]
    team_difficulty_label: str
    team_difficulty_score: float
    team_difficulty_factors: list[str]
    beginner_guidance_notes: list[str]
    team_preview_plans: list[dict[str, object]]
    team_preview_watch_teams: list[str]
    team_preview_watch_pokemon: list[str]
    team_preview_strategy_notes: list[str]
    team_preview_counterplay_notes: list[str]
    meta_analysis: dict[str, object]
    top_defensive_weaknesses: list[str]
    vector_labels: list[str]
    vector: list[float]

    @property
    def team_archetype(self) -> str:
        return self.primary_team_archetype

    def to_dict(self) -> dict[str, object]:
        return {
            "regulation_id": self.regulation_id,
            "confidence": ANALYSIS_CONFIDENCE,
            "confidence_tiers": CONFIDENCE_TIERS,
            "team_size": self.team_size,
            "typing_counts": self.typing_counts,
            "defensive_profile": self.defensive_profile,
            "top_defensive_weaknesses": self.top_defensive_weaknesses,
            "offensive_coverage": self.offensive_coverage,
            "target_coverage": self.target_coverage,
            "coverage_gaps": self.coverage_gaps,
            "coverage_quality": self.coverage_quality,
            "speed_profile": {
                "average_base_speed": self.average_base_speed,
                "average_battle_speed": self.average_battle_speed,
                "median_battle_speed": self.median_battle_speed,
                "standard_deviation": self.speed_standard_deviation,
                "team_tier": self.team_speed_tier,
                "normalized_level": 50,
                "fastest": {
                    "pokemon": self.fastest_battle_speed_pokemon[0],
                    "base_speed": self.member_base_speeds[self.fastest_battle_speed_pokemon[0]],
                    "battle_speed": self.fastest_battle_speed_pokemon[1],
                    "tier": self.member_speed_tiers[self.fastest_battle_speed_pokemon[0]],
                },
                "slowest": {
                    "pokemon": self.slowest_battle_speed_pokemon[0],
                    "base_speed": self.member_base_speeds[self.slowest_battle_speed_pokemon[0]],
                    "battle_speed": self.slowest_battle_speed_pokemon[1],
                    "tier": self.member_speed_tiers[self.slowest_battle_speed_pokemon[0]],
                },
                "base_speed_extremes": {
                    "fastest": {
                        "pokemon": self.fastest_pokemon[0],
                        "base_speed": self.fastest_pokemon[1],
                    },
                    "slowest": {
                        "pokemon": self.slowest_pokemon[0],
                        "base_speed": self.slowest_pokemon[1],
                    },
                },
                "spread": {
                    "minimum": self.slowest_battle_speed_pokemon[1],
                    "maximum": self.fastest_battle_speed_pokemon[1],
                    "range": self.fastest_battle_speed_pokemon[1] - self.slowest_battle_speed_pokemon[1],
                },
                "distribution": {
                    tier: {
                        "count": self.speed_tier_counts[tier],
                        "members": self.speed_tier_members[tier],
                    }
                    for tier in SPEED_TIER_ORDER
                },
                "benchmarks": {
                    "catalog": self.speed_benchmark_catalog,
                    "notes": self.speed_benchmark_notes,
                    "groups": self.speed_benchmark_groups,
                },
                "coverage": self.speed_coverage,
                "members": [
                    {
                        "pokemon": member_name,
                        "base_speed": self.member_base_speeds[member_name],
                        "battle_speed": self.member_battle_speeds[member_name],
                        "stats": self.member_stats[member_name],
                        "tier": self.member_speed_tiers[member_name],
                        "speed_contexts": self.member_speed_contexts[member_name],
                        "benchmark_tags": self.member_speed_benchmark_tags[member_name],
                    }
                    for member_name, _ in sorted(
                        self.member_battle_speeds.items(),
                        key=lambda item: (item[1], item[0]),
                        reverse=True,
                    )
                ],
            },
            "damage_split": self.damage_split,
            "damage_matchups": self.damage_matchups,
            "utility_moves": self.utility_moves,
            "utility_breakdown": {
                role: {
                    "count": self.utility_role_counts[role],
                    "moves": self.utility_role_moves[role],
                }
                for role in UTILITY_ROLE_ORDER
            },
            "pokemon_role_breakdown": {
                role: {
                    "count": self.pokemon_role_counts[role],
                    "members": self.pokemon_role_members[role],
                }
                for role in POKEMON_ROLE_ORDER
            },
            "member_roles": self.member_roles,
            "team_archetype": self.primary_team_archetype,
            "team_archetype_scores": self.team_archetype_scores,
            "team_package_profile": {
                "style": {
                    "label": self.primary_team_style,
                    "scores": {
                        style: self.team_style_scores[style]
                        for style in STYLE_PACKAGE_ORDER
                    },
                },
                "modes": {
                    "labels": self.team_mode_packages,
                    "scores": {
                        mode: self.team_mode_package_scores[mode]
                        for mode in MODE_PACKAGE_ORDER
                    },
                },
                "win_conditions": {
                    "labels": self.team_win_condition_labels,
                    "scores": {
                        package: self.team_win_condition_scores[package]
                        for package in WIN_CONDITION_PACKAGE_ORDER
                    },
                },
            },
            "matchup_profile": {
                "scores": self.matchup_scores,
                "details": self.matchup_details,
                "favorable": self.favorable_matchups,
                "unfavorable": self.unfavorable_matchups,
            },
            "meta_mode_profile": {
                "team_scores": {
                    mode: self.team_mode_scores[mode]
                    for mode in MODE_LABEL_ORDER
                },
                "team_labels": self.team_mode_labels,
                "scores": {
                    mode: self.mode_matchup_scores[mode]
                    for mode in MODE_LABEL_ORDER
                },
                "favorable": self.favorable_modes,
                "unfavorable": self.unfavorable_modes,
            },
            "team_difficulty": {
                "label": self.team_difficulty_label,
                "score": self.team_difficulty_score,
                "factors": self.team_difficulty_factors,
            },
            "beginner_guidance": {
                "notes": self.beginner_guidance_notes,
            },
            "team_preview": {
                "bring_plans": self.team_preview_plans,
                "watch_teams": self.team_preview_watch_teams,
                "watch_pokemon": self.team_preview_watch_pokemon,
                "strategy_notes": self.team_preview_strategy_notes,
                "counterplay_notes": self.team_preview_counterplay_notes,
            },
            "meta_analysis": self.meta_analysis,
            "plain_summary": self.plain_summary,
            "glossary": GLOSSARY,
            "vector_labels": self.vector_labels,
            "vector": self.vector,
        }
