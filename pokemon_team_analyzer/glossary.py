"""Plain-language glossary and team summary.

Single source of truth for the vocabulary the analyzer emits (archetypes, modes, score
rails, jargon) plus a templated plain-language team summary. The glossary is embedded in
the analysis payload so the web UI can render tooltips without a second source of truth,
and the summary is generated server-side so it stays consistent and is unit-testable.
"""

from __future__ import annotations


def _label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()


def _join(values: list[str]) -> str:
    cleaned = [_label(value) for value in values if value]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


# term key -> {term (display), definition}. Keys match the raw labels the engine emits.
GLOSSARY: dict[str, dict[str, str]] = {
    # Broad archetypes
    "hyper_offense": {"term": "Hyper Offense", "definition": "All-out aggression — fast attackers and chip support that try to win before the opponent stabilizes."},
    "bulky_offense": {"term": "Bulky Offense", "definition": "Offense with staying power: attackers bulky enough to trade and pivot rather than fold to one hit."},
    "balance": {"term": "Balance", "definition": "A mix of offense and defense that adapts game-to-game instead of forcing a single plan."},
    "semi_stall": {"term": "Semi-Stall", "definition": "Defensively tilted — bulky support and recovery grind the opponent down, with a light offensive finish."},
    "stall": {"term": "Stall", "definition": "Maximum defense: bulk, recovery, and disruption that aim to outlast rather than out-damage."},
    "trick_room": {"term": "Trick Room", "definition": "Built around Trick Room, which reverses Speed so the slowest Pokemon move first for five turns."},
    # Modes / packages
    "tailwind": {"term": "Tailwind", "definition": "Doubles your team's Speed for a few turns — the main fast-mode speed-control tool."},
    "semiroom": {"term": "Semiroom", "definition": "A team that can play under either Tailwind or Trick Room, flexing its speed mode to the matchup."},
    "tailroom": {"term": "Tailroom", "definition": "A dual-mode team carrying both Tailwind and Trick Room so it can pick a speed mode each game."},
    "dual_mode": {"term": "Dual Mode", "definition": "Carries two distinct game plans (e.g. two megas or two speed modes) and commits based on team preview."},
    "rain": {"term": "Rain", "definition": "Sets rain to boost Water moves and Swift Swim speed while weakening Fire."},
    "sun": {"term": "Sun", "definition": "Sets harsh sunlight to boost Fire moves and Chlorophyll speed while weakening Water."},
    "sand": {"term": "Sand", "definition": "Sets a sandstorm that chips non-Rock/Ground/Steel Pokemon and powers up sand abusers."},
    "snow": {"term": "Snow", "definition": "Sets snow, which raises Ice-types' Defense and enables Slush Rush speed."},
    "electric_terrain": {"term": "Electric Terrain", "definition": "Boosts Electric moves and blocks sleep for grounded Pokemon."},
    "grassy_terrain": {"term": "Grassy Terrain", "definition": "Boosts Grass moves, heals grounded Pokemon, and softens Earthquake."},
    "misty_terrain": {"term": "Misty Terrain", "definition": "Halves Dragon damage and blocks status for grounded Pokemon."},
    "psychic_terrain": {"term": "Psychic Terrain", "definition": "Boosts Psychic moves and blocks priority against grounded Pokemon."},
    "screens_offense": {"term": "Screens Offense", "definition": "Sets Reflect/Light Screen to soak damage while setup sweepers snowball."},
    "psyspam": {"term": "Psyspam", "definition": "Spams strong Psychic spread moves, often under Psychic Terrain, to overwhelm the field."},
    "perish_trap": {"term": "Perish Trap", "definition": "Uses Perish Song plus trapping to force KOs by the song's countdown."},
    # UI concepts / jargon
    "pilot_load": {"term": "Pilot Load", "definition": "How demanding the team is to play well — higher means more reads, sequencing, and risk to manage."},
    "speed_tier": {"term": "Speed Shape", "definition": "Where the team sits on the Speed spectrum, which decides who moves first."},
    "style_shell": {"term": "Style Shell", "definition": "The team's broad offense/defense identity (hyper offense through stall)."},
    "mode_shell": {"term": "Mode Shell", "definition": "The speed/weather/terrain package the team commits to (Tailwind, Trick Room, rain, etc.)."},
    "broad_pressure": {"term": "Broad Pressure", "definition": "How the team scores against the six broad archetypes, from hyper offense to stall."},
    "package_identity": {"term": "Package Identity", "definition": "How strongly the team commits to a specific mode/weather package versus staying flexible."},
    "endgame_plan": {"term": "Endgame Plan", "definition": "The team's primary win condition — setup sweep, perish trap, screens offense, or psyspam."},
    "matchup_score": {"term": "Matchup Score", "definition": "A relative edge: positive favors you, negative favors them, and bigger magnitude means a clearer read."},
    "meta_share": {"term": "Meta Share", "definition": "Estimated share of the current tournament field this team or mode represents."},
    "impact_score": {"term": "Impact Score", "definition": "A matchup edge weighted by how common that team or mode is right now."},
    "utility_load": {"term": "Utility Load", "definition": "How many non-attacking support actions (screens, redirection, speed control, etc.) the team carries."},
}


_ARCHETYPE_PLAN = {
    "hyper_offense": "Apply pressure immediately and close before the opponent sets up.",
    "bulky_offense": "Trade efficiently and grind a midgame lead with your bulkier attackers.",
    "balance": "Read the preview, then commit to the line the matchup rewards.",
    "semi_stall": "Stabilize early, deny progress, and let chip and recovery win the long game.",
    "stall": "Outlast the opponent — preserve your walls and never take an avoidable hit.",
    "trick_room": "Set Trick Room safely and snowball while your slow attackers move first.",
}


def build_plain_language_summary(
    *,
    archetype: str,
    style: str,
    mode_labels: list[str],
    win_condition_labels: list[str],
    speed_tier: str,
    favorable_matchups: list[str],
    unfavorable_matchups: list[str],
    unfavorable_modes: list[str],
    top_defensive_weaknesses: list[str],
    difficulty_label: str,
    difficulty_score: float,
) -> list[str]:
    """Generate a few plain-language sentences describing the team."""
    sentences: list[str] = []

    archetype_def = GLOSSARY.get(archetype, {}).get("definition", "")
    archetype_plain = archetype_def[0].lower() + archetype_def[1:] if archetype_def else ""
    opener = f"In plain terms, this is a {_label(archetype)} team"
    if archetype_plain:
        opener += f" — {archetype_plain}"
    sentences.append(opener if opener.endswith(".") else opener + ".")

    mode_clause = ""
    primary_mode = next((mode for mode in mode_labels if mode and mode != "dual_mode"), "")
    if primary_mode:
        mode_clause = f", leaning on a {_label(primary_mode)} mode"
    sentences.append(f"It plays as a {_label(speed_tier).lower()}-speed team{mode_clause}.")

    strengths = favorable_matchups[:3]
    if strengths:
        sentences.append(f"It matches up well into {_join(strengths)}.")

    liabilities = (unfavorable_matchups[:2] + unfavorable_modes[:1])[:3]
    weakness_bits: list[str] = []
    if liabilities:
        weakness_bits.append(f"struggles against {_join(liabilities)}")
    if top_defensive_weaknesses:
        weakness_bits.append(f"is defensively soft to {_join(top_defensive_weaknesses[:2])}")
    if weakness_bits:
        sentences.append("It " + " and ".join(weakness_bits) + ".")

    plan = _ARCHETYPE_PLAN.get(archetype)
    difficulty_sentence = f"Pilot load is {_label(difficulty_label).lower()} ({difficulty_score:.1f}/10)"
    if plan:
        difficulty_sentence += f"; the game plan is to {plan[0].lower() + plan[1:]}"
    sentences.append(difficulty_sentence if difficulty_sentence.endswith(".") else difficulty_sentence + ".")

    return sentences
