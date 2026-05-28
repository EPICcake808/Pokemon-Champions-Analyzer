from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .analyzer import (
    analyze_team_text,
    summarize_beginner_guidance,
    summarize_member_roles,
    summarize_matchup_profile,
    summarize_meta_analysis,
    summarize_meta_mode_profile,
    summarize_pokemon_role_breakdown,
    summarize_team_archetype_scores,
    summarize_team_difficulty,
    summarize_team_preview,
    summarize_utility_breakdown,
)
from .champions_m_a_moves import get_allowed_moves_for_species
from .data import CachedPokeApiClient
from .models import TYPE_ORDER
from .regulations import (
    DEFAULT_REGULATION_ID,
    IllegalTeamError,
    get_regulation,
    list_regulations,
    resolve_required_item_for_species,
    resolve_builder_option_source_species_name,
    resolve_regulation_species_name,
)
from .service import (
    build_regulation_catalog_payload,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.catalog_json:
        print(
            json.dumps(
                build_regulation_catalog_payload(
                    include_team_text=args.include_team_text,
                    include_rules=args.include_rules,
                ),
                indent=2,
            )
        )
        return 0

    if args.builder_species_json:
        try:
            print(json.dumps(_builder_species_options_as_dict(args.builder_species_json, args.regulation), indent=2))
        except (KeyError, LookupError) as error:
            print(json.dumps({"error": str(error)}, indent=2))
            return 2
        return 0

    if args.builder_move_json:
        try:
            print(json.dumps(_builder_move_options_as_dict(args.builder_move_json), indent=2))
        except LookupError as error:
            print(json.dumps({"error": str(error)}, indent=2))
            return 2
        return 0

    if args.team_file is None:
        parser.error("team_file is required unless --catalog-json, --builder-species-json, or --builder-move-json is used")

    team_text = Path(args.team_file).read_text(encoding="utf-8")

    try:
        analysis = analyze_team_text(team_text, regulation_id=args.regulation)
    except IllegalTeamError as error:
        if args.json:
            print(json.dumps({"error": str(error), "legality": error.legality.to_dict()}, indent=2))
            return 2

        print(render_legality_error(error.legality))
        return 2

    if args.json:
        print(json.dumps(analysis.to_dict(), indent=2))
        return 0

    print(render_text_report(analysis.to_dict()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze a Pokemon Showdown team import.")
    parser.add_argument("team_file", nargs="?", help="Path to a text file containing a Pokemon Showdown import.")
    parser.add_argument(
        "--regulation",
        default=DEFAULT_REGULATION_ID,
        choices=[regulation.id for regulation in list_regulations()],
        help="Champions regulation to validate against before analysis.",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON instead of a text report.")
    parser.add_argument(
        "--catalog-json",
        action="store_true",
        help="Emit the built-in Champions regulation catalog as JSON and exit.",
    )
    parser.add_argument(
        "--include-team-text",
        action="store_true",
        help="When used with --catalog-json, include stored tournament export text in the catalog payload.",
    )
    parser.add_argument(
        "--include-rules",
        action="store_true",
        help="When used with --catalog-json, include eligible species and allowed item lists in the catalog payload.",
    )
    parser.add_argument(
        "--builder-species-json",
        metavar="SPECIES",
        help="Emit JSON builder options for a single regulation-legal species and exit.",
    )
    parser.add_argument(
        "--builder-move-json",
        metavar="MOVE",
        help="Emit JSON builder details for a single move and exit.",
    )
    return parser


def _builder_species_options_as_dict(species_name: str, regulation_id: str) -> dict[str, object]:
    regulation = get_regulation(regulation_id)
    canonical_species = resolve_regulation_species_name(species_name, regulation_id=regulation_id)
    if canonical_species is None:
        raise KeyError(f"{species_name} is not an eligible Pokemon or legal Mega Evolution in {regulation.display_name}.")

    provider = CachedPokeApiClient()
    move_source_species = resolve_builder_option_source_species_name(canonical_species)
    species_data = provider.get_species(canonical_species)
    return {
        "species": canonical_species,
        "types": list(species_data.types),
        "abilities": list(provider.get_species_abilities(canonical_species)),
        "moves": list(get_allowed_moves_for_species(move_source_species)),
        "base_stats": {
            "hp": species_data.base_hp,
            "attack": species_data.base_attack,
            "defense": species_data.base_defense,
            "special_attack": species_data.base_special_attack,
            "special_defense": species_data.base_special_defense,
            "speed": species_data.base_speed,
        },
        "required_item": resolve_required_item_for_species(canonical_species),
    }


def _builder_move_options_as_dict(move_name: str) -> dict[str, object]:
    provider = CachedPokeApiClient()
    move = provider.get_move(move_name)
    return asdict(move)

def render_legality_error(legality: object) -> str:
    regulation_id = legality.regulation_id if hasattr(legality, "regulation_id") else legality["regulation_id"]
    issues = legality.issues if hasattr(legality, "issues") else legality["issues"]

    lines = [f"Team is illegal for regulation {regulation_id}:"]
    for issue in issues:
        message = issue.message if hasattr(issue, "message") else issue["message"]
        lines.append(f"  - {message}")
    return "\n".join(lines)


def render_text_report(analysis: dict[str, object]) -> str:
    typing_counts = analysis["typing_counts"]
    defensive_profile = analysis["defensive_profile"]
    offensive_coverage = analysis["offensive_coverage"]
    target_coverage = analysis.get("target_coverage", {})
    coverage_gaps = analysis.get("coverage_gaps", [])
    speed_profile = analysis["speed_profile"]
    speed_benchmarks = speed_profile.get("benchmarks", {})
    damage_split = analysis["damage_split"]
    utility_breakdown = analysis["utility_breakdown"]
    pokemon_role_breakdown = analysis.get("pokemon_role_breakdown", {})
    member_roles = analysis.get("member_roles", {})
    team_archetype = analysis.get("team_archetype", "unknown")
    team_archetype_scores = analysis.get("team_archetype_scores", {})
    team_package_profile = analysis.get("team_package_profile", {})
    matchup_profile = analysis.get("matchup_profile", {})
    meta_mode_profile = analysis.get("meta_mode_profile", {})
    meta_analysis = analysis.get("meta_analysis", {})
    team_difficulty = analysis.get("team_difficulty", {})
    beginner_guidance = analysis.get("beginner_guidance", {})
    team_preview = analysis.get("team_preview", {})
    top_defensive_weaknesses = analysis["top_defensive_weaknesses"]
    vector = analysis["vector"]
    utility_lines = summarize_utility_breakdown(
        {role: details["moves"] for role, details in utility_breakdown.items()}
    )
    pokemon_role_lines = summarize_pokemon_role_breakdown(
        {role: details["members"] for role, details in pokemon_role_breakdown.items()}
    ) if pokemon_role_breakdown else []
    member_role_lines = summarize_member_roles(member_roles) if member_roles else []
    team_archetype_lines = summarize_team_archetype_scores(team_archetype, team_archetype_scores) if team_archetype_scores else []
    matchup_lines = summarize_matchup_profile(
        matchup_profile.get("favorable", []),
        matchup_profile.get("unfavorable", []),
        matchup_profile.get("scores", {}),
        matchup_profile.get("details", {}),
    ) if matchup_profile else []
    meta_mode_lines = summarize_meta_mode_profile(
        meta_mode_profile.get("team_labels", []),
        meta_mode_profile.get("favorable", []),
        meta_mode_profile.get("unfavorable", []),
        meta_mode_profile.get("scores", {}),
    ) if meta_mode_profile else []
    meta_analysis_lines = summarize_meta_analysis(meta_analysis) if meta_analysis else []
    difficulty_lines = summarize_team_difficulty(
        team_difficulty.get("label", "unknown"),
        team_difficulty.get("score", 0.0),
        team_difficulty.get("factors", []),
    ) if team_difficulty else []
    beginner_guidance_lines = summarize_beginner_guidance(
        beginner_guidance.get("notes", []),
    ) if beginner_guidance else []
    team_preview_lines = summarize_team_preview(team_preview) if team_preview else []

    lines = [
        f"Team size: {analysis['team_size']}",
        "",
        "Typing counts:",
    ]
    lines.extend(_render_type_counts(typing_counts))
    lines.extend(
        [
            "",
            "Defensive profile:",
        ]
    )
    lines.extend(_render_defensive_profile(defensive_profile))
    lines.extend(
        [
            "",
            f"Most exposed types: {', '.join(top_defensive_weaknesses)}",
            "",
            "Offensive coverage:",
        ]
    )
    lines.extend(_render_type_counts(offensive_coverage))
    if target_coverage and coverage_gaps:
        lines.extend(
            [
                "",
                "Coverage gaps:",
            ]
        )
        lines.extend(_render_coverage_gaps(target_coverage, coverage_gaps))
    lines.extend(
        [
            "",
            "Speed profile:",
            f"  Average base Speed: {speed_profile['average_base_speed']}",
            f"  Team speed tier: {speed_profile['team_tier'].replace('_', ' ').title()}",
            f"  Average level-50 Speed: {speed_profile['average_battle_speed']}",
            f"  Median level-50 Speed: {speed_profile['median_battle_speed']}",
            (
                f"  Spread: {speed_profile['spread']['minimum']} to {speed_profile['spread']['maximum']} "
                f"(range {speed_profile['spread']['range']}, stdev {speed_profile['standard_deviation']})"
            ),
            (
                f"  Fastest: {speed_profile['fastest']['pokemon']} "
                f"(base {speed_profile['fastest']['base_speed']}, speed {speed_profile['fastest']['battle_speed']}, "
                f"{speed_profile['fastest']['tier'].replace('_', ' ').title()})"
            ),
            (
                f"  Slowest: {speed_profile['slowest']['pokemon']} "
                f"(base {speed_profile['slowest']['base_speed']}, speed {speed_profile['slowest']['battle_speed']}, "
                f"{speed_profile['slowest']['tier'].replace('_', ' ').title()})"
            ),
            "  Tier distribution: "
            + ", ".join(
                (
                    f"{tier.replace('_', ' ').title()} {details['count']}"
                    + (f" ({', '.join(details['members'])})" if details['members'] else "")
                )
                for tier, details in speed_profile['distribution'].items()
            ),
            "  Members:",
            *[
                (
                    f"    {member['pokemon']}: speed {member['battle_speed']} "
                    f"(base {member['base_speed']}, {member['tier'].replace('_', ' ').title()})"
                    + (
                        "; contexts "
                        + ", ".join(
                            f"{context['label']} {context['speed']}"
                            for context in member.get('speed_contexts', [])[:3]
                        )
                        if member.get("speed_contexts")
                        else ""
                    )
                )
                for member in speed_profile['members']
            ],
            *(
                [
                    "  Benchmark notes:",
                    *[f"    - {note}" for note in speed_benchmarks.get("notes", [])],
                ]
                if speed_benchmarks.get("notes")
                else []
            ),
            "",
            "Damage split:",
            f"  Physical: {damage_split['physical']}",
            f"  Special: {damage_split['special']}",
            f"  Utility: {analysis['utility_moves']}",
            "",
            "Utility profile:",
        ]
    )
    lines.extend(utility_lines or ["  None"])
    lines.extend(
        [
            "",
            "Team archetype:",
        ]
    )
    lines.extend(team_archetype_lines or ["  None"])
    lines.extend(
        [
            "",
            "Team package profile:",
        ]
    )
    lines.extend(_render_team_package_profile(team_package_profile))
    lines.extend(
        [
            "",
            "Matchup profile:",
        ]
    )
    lines.extend(matchup_lines or ["  None"])
    lines.extend(
        [
            "",
            "Meta mode profile:",
        ]
    )
    lines.extend(meta_mode_lines or ["  None"])
    lines.extend(
        [
            "",
            "Meta analysis:",
        ]
    )
    lines.extend(meta_analysis_lines or ["  None"])
    lines.extend(
        [
            "",
            "Team difficulty:",
        ]
    )
    lines.extend(difficulty_lines or ["  None"])
    lines.extend(
        [
            "",
            "Builder guidance:",
        ]
    )
    lines.extend(beginner_guidance_lines or ["  None"])
    lines.extend(
        [
            "",
            "Team preview:",
        ]
    )
    lines.extend(team_preview_lines or ["  None"])
    lines.extend(
        [
            "",
            "Pokemon role profile:",
        ]
    )
    lines.extend(pokemon_role_lines or ["  None"])
    lines.extend(
        [
            "",
            "Member roles:",
        ]
    )
    lines.extend(member_role_lines or ["  None"])
    lines.extend(
        [
            "",
            f"Vector length: {len(vector)}",
            f"Vector: {vector}",
        ]
    )
    return "\n".join(lines)


def _render_type_counts(values: dict[str, int]) -> list[str]:
    return [f"  {type_name.title()}: {values[type_name]}" for type_name in TYPE_ORDER]


def _render_defensive_profile(defensive_profile: dict[str, dict[str, float | int]]) -> list[str]:
    lines: list[str] = []
    for type_name in TYPE_ORDER:
        row = defensive_profile[type_name]
        lines.append(
            "  "
            + f"{type_name.title()}: avg {row['average_multiplier']}x, "
            + f"weak {row['weak_members']}, resist {row['resistant_members']}, immune {row['immune_members']}"
        )
    return lines


def _render_coverage_gaps(
    target_coverage: dict[str, dict[str, float | int]],
    coverage_gaps: list[str],
) -> list[str]:
    lines: list[str] = []
    for type_name in coverage_gaps:
        row = target_coverage[type_name]
        lines.append(
            "  "
            + f"{type_name.title()}: best {row['best_multiplier']}x, "
            + f"{row['super_effective_lines']} super-effective lines, "
            + f"{row['neutral_or_better_lines']} neutral-or-better lines"
        )
    return lines


def _render_team_package_profile(team_package_profile: dict[str, object]) -> list[str]:
    if not team_package_profile:
        return ["  None"]

    style = team_package_profile.get("style", {})
    modes = team_package_profile.get("modes", {})
    win_conditions = team_package_profile.get("win_conditions", {})

    style_label = style.get("label", "unknown")
    mode_labels = modes.get("labels", [])
    win_condition_labels = win_conditions.get("labels", [])

    return [
        f"  Style: {style_label.replace('_', ' ').title()}",
        "  Modes: " + (
            ", ".join(label.replace("_", " ").title() for label in mode_labels)
            if mode_labels
            else "None"
        ),
        "  Win conditions: " + (
            ", ".join(label.replace("_", " ").title() for label in win_condition_labels)
            if win_condition_labels
            else "None"
        ),
    ]
