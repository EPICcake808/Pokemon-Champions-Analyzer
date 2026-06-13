from __future__ import annotations

from collections import Counter
from pathlib import Path
import unittest

from pokemon_team_analyzer.champions_m_a_meta import MODE_LABEL_ORDER
from pokemon_team_analyzer.analyzer import (
    ContextualMatchupProfile,
    _build_snapshot_interaction_summary,
    _build_snapshot_target_matchup_summary,
    _fast_offense_counter_tools,
    _render_mode_label,
    _resolve_members,
    _screen_counter_tool_labels,
    _score_broad_contextual_matchup,
    _setup_counter_tool_labels,
    _trick_room_counter_tool_labels,
    analyze_team,
    analyze_team_text,
    classify_utility_roles,
)
from pokemon_team_analyzer.meta_snapshots import get_tournament_team_snapshots
from pokemon_team_analyzer.cli import render_text_report
from pokemon_team_analyzer.speed_benchmarks import get_speed_benchmark_catalog
from pokemon_team_analyzer.stats import compute_stat
from pokemon_team_analyzer.models import (
    BROAD_TEAM_ARCHETYPE_ORDER,
    MODE_PACKAGE_ORDER,
    MoveData,
    MoveStatChange,
    PokemonSet,
    SpeciesData,
    STYLE_PACKAGE_ORDER,
    TEAM_ARCHETYPE_ORDER,
    WIN_CONDITION_PACKAGE_ORDER,
)
from pokemon_team_analyzer.showdown import parse_showdown_team


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _make_contextual_profile(**overrides: object) -> ContextualMatchupProfile:
    """Build a neutral ContextualMatchupProfile for reason-gating tests."""

    defaults: dict[str, object] = dict(
        species_tokens=set(),
        move_counts=Counter(),
        attack_type_counts=Counter(),
        ability_counts=Counter(),
        team_mode_packages=(),
        team_win_condition_labels=(),
        fast_members=0,
        slow_members=0,
        bulky_members=0,
        frail_members=0,
        strong_attackers=0,
        weather_setters=0,
        terrain_setters=0,
        redirection=0,
        screens=0,
        protective_turns=0,
        recovery_loop=0,
        hazard_control=0,
        priority_attacks=0,
        sleep_pressure=0,
        setup_pressure=0.0,
        immediate_pressure=0.0,
        water_resistance=0,
        fire_resistance=0,
        electric_resistance=0,
        intimidate_support=0,
        priority_block_bypass=0,
        fire_exposure=0.0,
        water_exposure=0.0,
        rock_exposure=0.0,
        ground_exposure=0.0,
        flying_exposure=0.0,
        poison_exposure=0.0,
        grass_bias=0.0,
        fighting_bias=0.0,
        psychic_bias=0.0,
        weather_punish_rain=0.0,
        weather_punish_sun=0.0,
        weather_punish_sand=0.0,
        weather_punish_snow=0.0,
        tailwind_counter_tools=0.0,
        trick_room_counter_tools=0.0,
        screen_counter_tools=0.0,
        setup_counter_tools=0.0,
        progress_pressure=0.0,
        disruption_pressure=0.0,
        mindgame_pressure=0.0,
        coverage_gaps=(),
    )
    defaults.update(overrides)
    return ContextualMatchupProfile(**defaults)  # type: ignore[arg-type]


def load_example_team(file_name: str) -> str:
    return (EXAMPLES_DIR / file_name).read_text(encoding="utf-8")


SAMPLE_TEAM = """Lucario-Mega @ Lucarionite
Ability: Adaptability
Level: 50
EVs: 32 HP / 32 Def / 2 Spe
Bold Nature
- Aura Sphere
- Detect
- Calm Mind
- Dark Pulse

Sableye @ Roseli Berry
Ability: Prankster
Level: 50
EVs: 32 HP / 9 Def / 25 SpD
Sassy Nature
- Rain Dance
- Quash
- Light Screen
- Reflect

Archaludon @ Leftovers
Ability: Stamina
Level: 50
EVs: 32 HP / 1 Def / 5 SpA / 25 SpD / 3 Spe
Modest Nature
- Electro Shot
- Dragon Pulse
- Flash Cannon
- Protect

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
EVs: 31 HP / 7 Def / 28 SpD
Sassy Nature
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Basculegion (M) @ Choice Scarf
Ability: Adaptability
Level: 50
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Last Respects
- Aqua Jet
- Wave Crash
- Psychic Fangs

Aerodactyl @ Focus Sash
Ability: Unnerve
Level: 50
EVs: 32 Atk / 2 SpD / 32 Spe
Jolly Nature
- Rock Slide
- Tailwind
- Dual Wingbeat
- Wide Guard
"""

HYBRID_UTILITY_TEAM = """Sableye @ Leftovers
Ability: Prankster
- Fake Out
- Trick Room
- Quash
- Nuzzle

Aerodactyl @ Focus Sash
Ability: Pressure
- Icy Wind
- Protect
- Tailwind
- Rock Slide
"""

ROLE_TEAM = """Tyranitar @ Leftovers
Ability: Sand Stream
- Stealth Rock
- Roar
- Knock Off
- Stone Edge

Corviknight @ Rocky Helmet
Ability: Pressure
- Defog
- U-turn
- Roost
- Body Press

Grimmsnarl @ Light Clay
Ability: Prankster
- Reflect
- Light Screen
- Taunt
- Parting Shot

Amoonguss @ Sitrus Berry
Ability: Regenerator
- Rage Powder
- Spore
- Pollen Puff
- Protect

Volcarona @ Heavy-Duty Boots
Ability: Flame Body
- Quiver Dance
- Fiery Dance
- Bug Buzz
- Psychic

Tapu Koko @ Magnet
Ability: Electric Surge
- U-turn
- Thunderbolt
- Dazzling Gleam
- Taunt
"""

HYPER_OFFENSE_TEAM = """Grimmsnarl @ Light Clay
Ability: Prankster
- Reflect
- Light Screen
- Taunt
- Parting Shot

Glimmora @ Focus Sash
Ability: Toxic Debris
- Stealth Rock
- Power Gem
- Sludge Wave
- Earth Power

Garchomp @ Clear Amulet
Ability: Rough Skin
- Swords Dance
- Earthquake
- Dragon Claw
- Stone Edge

Volcarona @ Heavy-Duty Boots
Ability: Flame Body
- Quiver Dance
- Fiery Dance
- Bug Buzz
- Psychic

Dragapult @ Choice Band
Ability: Infiltrator
- Dragon Darts
- Phantom Force
- U-turn
- Fire Blast

Iron Valiant @ Booster Energy
Ability: Quark Drive
- Swords Dance
- Close Combat
- Spirit Break
- Knock Off
"""

TRICK_ROOM_TEAM = """Farigiraf @ Sitrus Berry
Ability: Armor Tail
- Trick Room
- Psychic
- Dazzling Gleam
- Protect

Torkoal @ Charcoal
Ability: Drought
- Eruption
- Heat Wave
- Earth Power
- Protect

Ursaluna @ Flame Orb
Ability: Guts
- Facade
- Earthquake
- Stone Edge
- Protect

Amoonguss @ Rocky Helmet
Ability: Regenerator
- Rage Powder
- Spore
- Pollen Puff
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
- Fake Out
- Drain Punch
- Wild Charge
- Protect

Porygon2 @ Eviolite
Ability: Download
- Trick Room
- Recover
- Ice Beam
- Psychic
"""

SUPPORT_HEAVY_CHOICE_TEAM = """Dragapult @ Choice Band
Ability: Infiltrator
- Dragon Darts
- Phantom Force
- U-turn
- Protect

Sableye @ Leftovers
Ability: Prankster
- Quash
- Light Screen
- Reflect
- Taunt

Corviknight @ Leftovers
Ability: Pressure
- Defog
- Roost
- U-turn
- Protect

Amoonguss @ Sitrus Berry
Ability: Regenerator
- Rage Powder
- Spore
- Pollen Puff
- Protect

Milotic @ Leftovers
Ability: Competitive
- Icy Wind
- Recover
- Scald
- Protect

Audino @ Leftovers
Ability: Regenerator
- Heal Pulse
- Heal Bell
- Helping Hand
- Protect
"""

LOW_SUPPORT_TOOLS_TEAM = """Garchomp @ Soft Sand
Ability: Rough Skin
- Dragon Claw
- Earthquake
- Rock Slide
- Protect

Dragapult @ Choice Band
Ability: Infiltrator
- Dragon Darts
- Phantom Force
- Fire Blast
- Protect

Iron Valiant @ Booster Energy
Ability: Quark Drive
- Close Combat
- Dazzling Gleam
- Psychic
- Protect

Scizor-Mega @ Scizorite
Ability: Technician
- Bullet Punch
- Bug Bite
- Swords Dance
- Protect

Tyranitar @ Leftovers
Ability: Sand Stream
- Stone Edge
- Knock Off
- Earthquake
- Protect

Gengar @ Focus Sash
Ability: Cursed Body
- Shadow Ball
- Sludge Bomb
- Thunderbolt
- Protect
"""

PERISH_TRAP_TEAM = """Gengar @ Gengarite
Ability: Cursed Body
- Perish Song
- Protect
- Shadow Ball
- Sludge Bomb

Politoed @ Mystic Water
Ability: Drizzle
- Perish Song
- Protect
- Icy Wind
- Whirlpool

Sableye @ Focus Sash
Ability: Prankster
- Mean Look
- Quash
- Protect
- Rain Dance

Sinistcha @ Sitrus Berry
Ability: Hospitality
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Primarina @ Leftovers
Ability: Liquid Voice
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Kingambit @ Black Glasses
Ability: Defiant
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head
"""

TAILWIND_UTILITY_TEAM = """Sneasler @ White Herb
Ability: Unburden
- Close Combat
- Dire Claw
- Fake Out
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
- Dragon Claw
- Rock Slide
- Protect
- Stomping Tantrum

Sinistcha @ Sitrus Berry
Ability: Hospitality
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Aerodactyl @ Focus Sash
Ability: Unnerve
- Rock Slide
- Protect
- Dual Wingbeat
- Tailwind

Scizor-Mega @ Scizorite
Ability: Technician
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance

Milotic @ Leftovers
Ability: Competitive
- Scald
- Protect
- Icy Wind
- Recover
"""

SUN_TAILWIND_TEAM = """Whimsicott @ Focus Sash
Ability: Prankster
- Tailwind
- Moonblast
- Encore
- Protect

Torkoal @ Charcoal
Ability: Drought
- Eruption
- Heat Wave
- Earth Power
- Protect

Volcarona @ Heavy-Duty Boots
Ability: Flame Body
- Quiver Dance
- Fiery Dance
- Bug Buzz
- Protect

Garchomp @ Clear Amulet
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Stone Edge
- Protect

Arcanine-Hisui @ Sitrus Berry
Ability: Intimidate
- Flare Blitz
- Extreme Speed
- Rock Slide
- Protect

Kingambit @ Black Glasses
Ability: Defiant
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Protect
"""

PSYSPAM_TEAM = """Indeedee-F @ Psychic Seed
Ability: Psychic Surge
- Psychic
- Dazzling Gleam
- Protect
- Aura Sphere

Hatterene @ Life Orb
Ability: Magic Bounce
- Expanding Force
- Dazzling Gleam
- Trick Room
- Protect

Farigiraf @ Sitrus Berry
Ability: Armor Tail
- Trick Room
- Psychic
- Dazzling Gleam
- Protect

Iron Hands @ Assault Vest
Ability: Quark Drive
- Fake Out
- Drain Punch
- Wild Charge
- Protect

Sinistcha @ Sitrus Berry
Ability: Hospitality
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Kingambit @ Black Glasses
Ability: Defiant
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Protect
"""

SNOW_TAILWIND_TEAM = """Alolan Ninetales @ Light Clay
Ability: Snow Warning
- Aurora Veil
- Blizzard
- Freeze-Dry
- Protect

Aerodactyl @ Focus Sash
Ability: Unnerve
- Tailwind
- Rock Slide
- Dual Wingbeat
- Protect

Garchomp @ Clear Amulet
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Stone Edge
- Protect

Scizor-Mega @ Scizorite
Ability: Technician
- Bullet Punch
- Bug Bite
- Swords Dance
- Protect

Milotic @ Leftovers
Ability: Competitive
- Scald
- Icy Wind
- Recover
- Protect

Kingambit @ Black Glasses
Ability: Defiant
- Kowtow Cleave
- Iron Head
- Sucker Punch
- Protect
"""


class FakeMetadataProvider:
    def __init__(self) -> None:
        self.species = {
            "Lucario-Mega": SpeciesData("Lucario-Mega", "lucario-mega", ("fighting", "steel"), 70, 145, 88, 140, 70, 112),
            "Mega Lucario": SpeciesData("Mega Lucario", "lucario-mega", ("fighting", "steel"), 70, 145, 88, 140, 70, 112),
            "Sableye": SpeciesData("Sableye", "sableye", ("dark", "ghost"), 50, 75, 75, 65, 65, 50),
            "Pelipper": SpeciesData("Pelipper", "pelipper", ("water", "flying"), 60, 50, 100, 95, 70, 65),
            "Archaludon": SpeciesData("Archaludon", "archaludon", ("steel", "dragon"), 90, 105, 130, 125, 65, 85),
            "Sinistcha": SpeciesData("Sinistcha", "sinistcha", ("grass", "ghost"), 71, 60, 106, 121, 80, 70),
            "Basculegion (M)": SpeciesData("Basculegion (M)", "basculegion-male", ("water", "ghost"), 120, 112, 65, 80, 75, 78),
            "Aerodactyl": SpeciesData("Aerodactyl", "aerodactyl", ("rock", "flying"), 80, 105, 65, 60, 75, 130),
            "Tyranitar": SpeciesData("Tyranitar", "tyranitar", ("rock", "dark"), 100, 134, 110, 95, 100, 61),
            "Corviknight": SpeciesData("Corviknight", "corviknight", ("flying", "steel"), 98, 87, 105, 53, 85, 67),
            "Grimmsnarl": SpeciesData("Grimmsnarl", "grimmsnarl", ("dark", "fairy"), 95, 120, 65, 95, 75, 60),
            "Amoonguss": SpeciesData("Amoonguss", "amoonguss", ("grass", "poison"), 114, 85, 70, 85, 80, 30),
            "Volcarona": SpeciesData("Volcarona", "volcarona", ("bug", "fire"), 85, 60, 65, 135, 105, 100),
            "Tapu Koko": SpeciesData("Tapu Koko", "tapu-koko", ("electric", "fairy"), 70, 115, 85, 95, 75, 130),
            "Indeedee-F": SpeciesData("Indeedee-F", "indeedee-f", ("psychic", "normal"), 70, 55, 65, 95, 105, 85),
            "Hatterene": SpeciesData("Hatterene", "hatterene", ("psychic", "fairy"), 57, 90, 95, 136, 103, 29),
            "Alolan Ninetales": SpeciesData("Alolan Ninetales", "ninetales-alola", ("ice", "fairy"), 73, 67, 75, 81, 100, 109),
            "Glimmora": SpeciesData("Glimmora", "glimmora", ("rock", "poison"), 83, 55, 90, 130, 81, 86),
            "Garchomp": SpeciesData("Garchomp", "garchomp", ("dragon", "ground"), 108, 130, 95, 80, 85, 102),
            "Dragapult": SpeciesData("Dragapult", "dragapult", ("dragon", "ghost"), 88, 120, 75, 100, 75, 142),
            "Iron Valiant": SpeciesData("Iron Valiant", "iron-valiant", ("fairy", "fighting"), 74, 130, 90, 120, 60, 116),
            "Farigiraf": SpeciesData("Farigiraf", "farigiraf", ("normal", "psychic"), 120, 90, 70, 110, 70, 60),
            "Torkoal": SpeciesData("Torkoal", "torkoal", ("fire",), 70, 85, 140, 85, 70, 20),
            "Ursaluna": SpeciesData("Ursaluna", "ursaluna", ("ground", "normal"), 130, 140, 105, 45, 80, 50),
            "Iron Hands": SpeciesData("Iron Hands", "iron-hands", ("fighting", "electric"), 154, 140, 108, 50, 68, 50),
            "Porygon2": SpeciesData("Porygon2", "porygon2", ("normal",), 85, 80, 90, 105, 95, 60),
            "Sneasler": SpeciesData("Sneasler", "sneasler", ("fighting", "poison"), 80, 130, 60, 40, 80, 120),
            "Gardevoir-Mega": SpeciesData("Gardevoir-Mega", "gardevoir-mega", ("psychic", "fairy"), 68, 85, 65, 165, 135, 100),
            "Primarina": SpeciesData("Primarina", "primarina", ("water", "fairy"), 80, 74, 74, 126, 116, 60),
            "Whimsicott": SpeciesData("Whimsicott", "whimsicott", ("grass", "fairy"), 60, 67, 85, 77, 75, 116),
            "Arcanine-Hisui": SpeciesData("Arcanine-Hisui", "arcanine-hisui", ("fire", "rock"), 95, 115, 80, 95, 80, 90),
            "Kingambit": SpeciesData("Kingambit", "kingambit", ("dark", "steel"), 100, 135, 120, 60, 85, 50),
            "Scizor-Mega": SpeciesData("Scizor-Mega", "scizor-mega", ("bug", "steel"), 70, 150, 140, 65, 100, 75),
            "Scizor": SpeciesData("Scizor", "scizor", ("bug", "steel"), 70, 130, 100, 55, 80, 65),
            "Milotic": SpeciesData("Milotic", "milotic", ("water",), 95, 60, 79, 100, 125, 81),
            "Gengar": SpeciesData("Gengar", "gengar", ("ghost", "poison"), 60, 65, 60, 130, 75, 110),
            "Mega Gengar": SpeciesData("Mega Gengar", "gengar-mega", ("ghost", "poison"), 60, 65, 80, 170, 95, 130),
            "Gengar-Mega": SpeciesData("Gengar-Mega", "gengar-mega", ("ghost", "poison"), 60, 65, 80, 170, 95, 130),
            "Incineroar": SpeciesData("Incineroar", "incineroar", ("fire", "dark"), 95, 115, 90, 80, 90, 60),
            "Politoed": SpeciesData("Politoed", "politoed", ("water",), 90, 75, 75, 90, 100, 70),
            "Hydrapple": SpeciesData("Hydrapple", "hydrapple", ("grass", "dragon"), 106, 80, 110, 120, 80, 44),
            "Venusaur": SpeciesData("Venusaur", "venusaur", ("grass", "poison"), 80, 82, 83, 100, 100, 80),
            "Torterra": SpeciesData("Torterra", "torterra", ("grass", "ground"), 95, 109, 105, 75, 85, 56),
            "Roserade": SpeciesData("Roserade", "roserade", ("grass", "poison"), 60, 70, 65, 125, 105, 90),
            "Audino": SpeciesData("Audino", "audino", ("normal",), 103, 60, 86, 60, 86, 50),
            "Florges": SpeciesData("Florges", "florges", ("fairy",), 78, 65, 68, 112, 154, 75),
            "Hippowdon": SpeciesData("Hippowdon", "hippowdon", ("ground",), 108, 112, 118, 68, 72, 47),
            "Rhyperior": SpeciesData("Rhyperior", "rhyperior", ("ground", "rock"), 115, 140, 130, 55, 55, 40),
            "Charizard": SpeciesData("Charizard", "charizard", ("fire", "flying"), 78, 84, 78, 109, 85, 100),
            "Mega Charizard Y": SpeciesData("Mega Charizard Y", "charizard-mega-y", ("fire", "flying"), 78, 104, 78, 159, 115, 100),
            "Charizard-Mega-Y": SpeciesData("Charizard-Mega-Y", "charizard-mega-y", ("fire", "flying"), 78, 104, 78, 159, 115, 100),
            "Ninetales-Alola": SpeciesData("Ninetales-Alola", "ninetales-alola", ("ice", "fairy"), 73, 67, 75, 81, 100, 109),
            "Abomasnow": SpeciesData("Abomasnow", "abomasnow", ("grass", "ice"), 90, 92, 75, 92, 85, 60),
        }
        self.moves = {
            "Aura Sphere": MoveData("Aura Sphere", "aura-sphere", "fighting", "special"),
            "Detect": MoveData(
                "Detect",
                "detect",
                "fighting",
                "status",
                short_effect="Prevents any moves from hitting the user this turn.",
                priority=4,
                target_name="user",
            ),
            "Calm Mind": MoveData(
                "Calm Mind",
                "calm-mind",
                "psychic",
                "status",
                stat_changes=(
                    MoveStatChange("special-attack", 1),
                    MoveStatChange("special-defense", 1),
                ),
            ),
            "Dark Pulse": MoveData("Dark Pulse", "dark-pulse", "dark", "special"),
            "Rain Dance": MoveData(
                "Rain Dance",
                "rain-dance",
                "water",
                "status",
                short_effect="Changes the weather to rain for five turns.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Quash": MoveData(
                "Quash",
                "quash",
                "dark",
                "status",
                short_effect="Makes the target act last this turn.",
                target_name="selected-pokemon",
            ),
            "Light Screen": MoveData(
                "Light Screen",
                "light-screen",
                "psychic",
                "status",
                short_effect="Reduces damage from special attacks by 50% for five turns.",
                category_name="field-effect",
                target_name="users-field",
            ),
            "Reflect": MoveData(
                "Reflect",
                "reflect",
                "psychic",
                "status",
                short_effect="Reduces damage from physical attacks by 50% for five turns.",
                category_name="field-effect",
                target_name="users-field",
            ),
            "Electro Shot": MoveData("Electro Shot", "electro-shot", "electric", "special"),
            "Dragon Pulse": MoveData("Dragon Pulse", "dragon-pulse", "dragon", "special"),
            "Flash Cannon": MoveData("Flash Cannon", "flash-cannon", "steel", "special"),
            "Protect": MoveData(
                "Protect",
                "protect",
                "normal",
                "status",
                short_effect="Prevents any moves from hitting the user this turn.",
                priority=4,
                target_name="user",
            ),
            "Matcha Gotcha": MoveData("Matcha Gotcha", "matcha-gotcha", "grass", "special"),
            "Rage Powder": MoveData(
                "Rage Powder",
                "rage-powder",
                "bug",
                "status",
                short_effect="Redirects the target's single-target effects to the user for this turn.",
                priority=2,
                target_name="user",
            ),
            "Life Dew": MoveData(
                "Life Dew",
                "life-dew",
                "water",
                "status",
                short_effect="Restores HP to the user and its allies.",
                healing=25,
                target_name="users-field",
            ),
            "Last Respects": MoveData("Last Respects", "last-respects", "ghost", "physical"),
            "Aqua Jet": MoveData("Aqua Jet", "aqua-jet", "water", "physical"),
            "Wave Crash": MoveData("Wave Crash", "wave-crash", "water", "physical"),
            "Psychic Fangs": MoveData("Psychic Fangs", "psychic-fangs", "psychic", "physical"),
            "Rock Slide": MoveData("Rock Slide", "rock-slide", "rock", "physical"),
            "Tailwind": MoveData(
                "Tailwind",
                "tailwind",
                "flying",
                "status",
                short_effect="For three turns, friendly Pokemon have doubled Speed.",
                category_name="field-effect",
                target_name="users-field",
            ),
            "Dual Wingbeat": MoveData("Dual Wingbeat", "dual-wingbeat", "flying", "physical"),
            "Wide Guard": MoveData(
                "Wide Guard",
                "wide-guard",
                "rock",
                "status",
                short_effect="Protects all friendly Pokemon from damaging moves that target multiple Pokemon this turn.",
                priority=3,
                target_name="users-field",
            ),
            "Fake Out": MoveData(
                "Fake Out",
                "fake-out",
                "normal",
                "physical",
                short_effect="Causes the target to flinch.",
                effect_chance=100,
                flinch_chance=100,
                priority=3,
                target_name="selected-pokemon",
            ),
            "Trick Room": MoveData(
                "Trick Room",
                "trick-room",
                "psychic",
                "status",
                short_effect="For five turns, slower Pokemon move first.",
                priority=-7,
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Nuzzle": MoveData(
                "Nuzzle",
                "nuzzle",
                "electric",
                "physical",
                short_effect="Has a chance to paralyze the target.",
                effect_chance=100,
                ailment_name="paralysis",
                ailment_chance=100,
                category_name="damage-ailment",
                target_name="selected-pokemon",
            ),
            "Icy Wind": MoveData(
                "Icy Wind",
                "icy-wind",
                "ice",
                "special",
                short_effect="Has a chance to lower the target's Speed by one stage.",
                effect_chance=100,
                category_name="damage-lower",
                stat_chance=100,
                stat_changes=(MoveStatChange("speed", -1),),
                target_name="all-opponents",
            ),
            "Stealth Rock": MoveData(
                "Stealth Rock",
                "stealth-rock",
                "rock",
                "status",
                short_effect="Causes damage when opposing Pokemon switch in.",
                category_name="field-effect",
                target_name="opponents-field",
            ),
            "Roar": MoveData(
                "Roar",
                "roar",
                "normal",
                "status",
                short_effect="Immediately ends wild battles. Forces trainers to switch Pokemon.",
                category_name="force-switch",
                priority=-6,
                target_name="selected-pokemon",
            ),
            "Knock Off": MoveData(
                "Knock Off",
                "knock-off",
                "dark",
                "physical",
                short_effect="Target drops its held item.",
                target_name="selected-pokemon",
            ),
            "Stone Edge": MoveData("Stone Edge", "stone-edge", "rock", "physical"),
            "Defog": MoveData(
                "Defog",
                "defog",
                "flying",
                "status",
                short_effect="Lowers the target's evasion by one stage. Removes field effects from the enemy field.",
                category_name="unique",
                stat_changes=(MoveStatChange("evasion", -1),),
                target_name="selected-pokemon",
            ),
            "U-turn": MoveData(
                "U-turn",
                "u-turn",
                "bug",
                "physical",
                short_effect="User must switch out after attacking.",
                target_name="selected-pokemon",
            ),
            "Roost": MoveData(
                "Roost",
                "roost",
                "flying",
                "status",
                short_effect="Heals the user for half its max HP.",
                healing=50,
                target_name="user",
            ),
            "Body Press": MoveData("Body Press", "body-press", "fighting", "physical"),
            "Taunt": MoveData(
                "Taunt",
                "taunt",
                "dark",
                "status",
                short_effect="For the next few turns, the target can only use damaging moves.",
                target_name="selected-pokemon",
            ),
            "Parting Shot": MoveData(
                "Parting Shot",
                "parting-shot",
                "dark",
                "status",
                short_effect="Lowers all targets' Attack and Special Attack by one stage. Makes the user switch out.",
                effect_chance=100,
                category_name="net-good-stats",
                stat_chance=100,
                stat_changes=(
                    MoveStatChange("attack", -1),
                    MoveStatChange("special-attack", -1),
                ),
                target_name="selected-pokemon",
            ),
            "Spore": MoveData(
                "Spore",
                "spore",
                "grass",
                "status",
                short_effect="Puts the target to sleep.",
                ailment_name="sleep",
                ailment_chance=100,
                target_name="selected-pokemon",
            ),
            "Pollen Puff": MoveData(
                "Pollen Puff",
                "pollen-puff",
                "bug",
                "special",
                short_effect="Damages the target, or heals the target for half its max HP.",
                target_name="selected-pokemon",
            ),
            "Quiver Dance": MoveData(
                "Quiver Dance",
                "quiver-dance",
                "bug",
                "status",
                stat_changes=(
                    MoveStatChange("special-attack", 1),
                    MoveStatChange("special-defense", 1),
                    MoveStatChange("speed", 1),
                ),
                target_name="user",
            ),
            "Fiery Dance": MoveData("Fiery Dance", "fiery-dance", "fire", "special"),
            "Bug Buzz": MoveData("Bug Buzz", "bug-buzz", "bug", "special"),
            "Psychic": MoveData("Psychic", "psychic", "psychic", "special"),
            "Thunderbolt": MoveData("Thunderbolt", "thunderbolt", "electric", "special"),
            "Dazzling Gleam": MoveData("Dazzling Gleam", "dazzling-gleam", "fairy", "special"),
            "Electric Terrain": MoveData(
                "Electric Terrain",
                "electric-terrain",
                "electric",
                "status",
                short_effect="For five turns, prevents all Pokemon on the ground from sleeping and strengthens their Electric moves.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Psychic Terrain": MoveData(
                "Psychic Terrain",
                "psychic-terrain",
                "psychic",
                "status",
                short_effect="For five turns, grounded Pokemon cannot be hit by priority moves and Psychic moves are strengthened.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Expanding Force": MoveData("Expanding Force", "expanding-force", "psychic", "special"),
            "Aurora Veil": MoveData(
                "Aurora Veil",
                "aurora-veil",
                "ice",
                "status",
                short_effect="Reduces damage from physical and special moves for five turns.",
                category_name="field-effect",
                target_name="users-field",
            ),
            "Blizzard": MoveData("Blizzard", "blizzard", "ice", "special"),
            "Freeze-Dry": MoveData("Freeze-Dry", "freeze-dry", "ice", "special"),
            "Haze": MoveData(
                "Haze",
                "haze",
                "ice",
                "status",
                short_effect="Resets all Pokemon's stats, accuracy, and evasion.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Spirit Shackle": MoveData(
                "Spirit Shackle",
                "spirit-shackle",
                "ghost",
                "physical",
                short_effect="Traps the target.",
                target_name="selected-pokemon",
            ),
            "Heal Bell": MoveData(
                "Heal Bell",
                "heal-bell",
                "normal",
                "status",
                short_effect="Cures the entire party of major status effects.",
                target_name="user-and-allies",
            ),
            "Giga Drain": MoveData("Giga Drain", "giga-drain", "grass", "special"),
            "Grassy Terrain": MoveData(
                "Grassy Terrain",
                "grassy-terrain",
                "grass",
                "status",
                short_effect="For five turns, grounded Pokemon recover HP and Grass moves are strengthened.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Strength Sap": MoveData(
                "Strength Sap",
                "strength-sap",
                "grass",
                "status",
                short_effect="Lowers the target's Attack and restores the user's HP.",
                healing=50,
                stat_changes=(MoveStatChange("attack", -1),),
                target_name="selected-pokemon",
            ),
            "Growth": MoveData(
                "Growth",
                "growth",
                "normal",
                "status",
                stat_changes=(
                    MoveStatChange("attack", 1),
                    MoveStatChange("special-attack", 1),
                ),
                target_name="user",
            ),
            "Wood Hammer": MoveData("Wood Hammer", "wood-hammer", "grass", "physical"),
            "Sleep Powder": MoveData(
                "Sleep Powder",
                "sleep-powder",
                "grass",
                "status",
                short_effect="Puts the target to sleep.",
                ailment_name="sleep",
                ailment_chance=100,
                target_name="selected-pokemon",
            ),
            "Misty Terrain": MoveData(
                "Misty Terrain",
                "misty-terrain",
                "fairy",
                "status",
                short_effect="For five turns, grounded Pokemon are protected from major status effects and Dragon moves are weakened.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Helping Hand": MoveData(
                "Helping Hand",
                "helping-hand",
                "normal",
                "status",
                short_effect="Boosts an ally's move this turn.",
                priority=5,
                target_name="ally",
            ),
            "Heal Pulse": MoveData(
                "Heal Pulse",
                "heal-pulse",
                "psychic",
                "status",
                short_effect="Restores half of the target's max HP.",
                healing=50,
                target_name="selected-pokemon",
            ),
            "Sandstorm": MoveData(
                "Sandstorm",
                "sandstorm",
                "rock",
                "status",
                short_effect="Changes the weather to a sandstorm for five turns.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Yawn": MoveData(
                "Yawn",
                "yawn",
                "normal",
                "status",
                short_effect="Causes the target to fall asleep next turn.",
                ailment_name="sleep",
                ailment_chance=100,
                target_name="selected-pokemon",
            ),
            "Ice Shard": MoveData("Ice Shard", "ice-shard", "ice", "physical", priority=1),
            "Sunny Day": MoveData(
                "Sunny Day",
                "sunny-day",
                "fire",
                "status",
                short_effect="Changes the weather to harsh sunlight for five turns.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Air Slash": MoveData("Air Slash", "air-slash", "flying", "special"),
            "Solar Beam": MoveData("Solar Beam", "solar-beam", "grass", "special"),
            "Power Gem": MoveData("Power Gem", "power-gem", "rock", "special"),
            "Sludge Wave": MoveData("Sludge Wave", "sludge-wave", "poison", "special"),
            "Earth Power": MoveData("Earth Power", "earth-power", "ground", "special"),
            "Swords Dance": MoveData(
                "Swords Dance",
                "swords-dance",
                "normal",
                "status",
                stat_changes=(MoveStatChange("attack", 2),),
                target_name="user",
            ),
            "Earthquake": MoveData("Earthquake", "earthquake", "ground", "physical"),
            "Dragon Claw": MoveData("Dragon Claw", "dragon-claw", "dragon", "physical"),
            "Dragon Darts": MoveData("Dragon Darts", "dragon-darts", "dragon", "physical"),
            "Phantom Force": MoveData("Phantom Force", "phantom-force", "ghost", "physical"),
            "Fire Blast": MoveData("Fire Blast", "fire-blast", "fire", "special"),
            "Close Combat": MoveData("Close Combat", "close-combat", "fighting", "physical"),
            "Dire Claw": MoveData("Dire Claw", "dire-claw", "poison", "physical"),
            "Spirit Break": MoveData("Spirit Break", "spirit-break", "fairy", "physical"),
            "Eruption": MoveData("Eruption", "eruption", "fire", "special"),
            "Heat Wave": MoveData("Heat Wave", "heat-wave", "fire", "special"),
            "Facade": MoveData("Facade", "facade", "normal", "physical"),
            "Drain Punch": MoveData("Drain Punch", "drain-punch", "fighting", "physical"),
            "Wild Charge": MoveData("Wild Charge", "wild-charge", "electric", "physical"),
            "Recover": MoveData(
                "Recover",
                "recover",
                "normal",
                "status",
                short_effect="Heals the user for half its max HP.",
                healing=50,
                target_name="user",
            ),
            "Ice Beam": MoveData("Ice Beam", "ice-beam", "ice", "special"),
            "Hyper Voice": MoveData("Hyper Voice", "hyper-voice", "normal", "special"),
            "Moonblast": MoveData("Moonblast", "moonblast", "fairy", "special"),
            "Encore": MoveData(
                "Encore",
                "encore",
                "normal",
                "status",
                short_effect="Forces the target to repeat its last move for 3 turns.",
                target_name="selected-pokemon",
            ),
            "Flare Blitz": MoveData("Flare Blitz", "flare-blitz", "fire", "physical"),
            "Extreme Speed": MoveData("Extreme Speed", "extreme-speed", "normal", "physical", priority=2),
            "Kowtow Cleave": MoveData("Kowtow Cleave", "kowtow-cleave", "dark", "physical"),
            "Iron Head": MoveData("Iron Head", "iron-head", "steel", "physical"),
            "Sucker Punch": MoveData("Sucker Punch", "sucker-punch", "dark", "physical", priority=1),
            "Stomping Tantrum": MoveData("Stomping Tantrum", "stomping-tantrum", "ground", "physical"),
            "Bullet Punch": MoveData("Bullet Punch", "bullet-punch", "steel", "physical", priority=1),
            "Bug Bite": MoveData("Bug Bite", "bug-bite", "bug", "physical"),
            "Scald": MoveData("Scald", "scald", "water", "special"),
            "Hurricane": MoveData("Hurricane", "hurricane", "flying", "special"),
            "Shadow Ball": MoveData("Shadow Ball", "shadow-ball", "ghost", "special"),
            "Sludge Bomb": MoveData("Sludge Bomb", "sludge-bomb", "poison", "special"),
            "Perish Song": MoveData(
                "Perish Song",
                "perish-song",
                "normal",
                "status",
                short_effect="All active Pokemon faint in three turns.",
                category_name="whole-field-effect",
                target_name="entire-field",
            ),
            "Mean Look": MoveData(
                "Mean Look",
                "mean-look",
                "normal",
                "status",
                short_effect="Prevents the target from fleeing or switching out.",
                target_name="selected-pokemon",
            ),
            "Whirlpool": MoveData(
                "Whirlpool",
                "whirlpool",
                "water",
                "special",
                short_effect="Traps the target for several turns.",
                target_name="selected-pokemon",
            ),
        }

    def get_species(self, species_name: str) -> SpeciesData:
        return self.species[species_name]

    def get_move(self, move_name: str) -> MoveData:
        return self.moves[move_name]


class AnalyzerTests(unittest.TestCase):
    def test_compute_stat_applies_nature_after_stat_points(self) -> None:
        # HP and neutral non-HP stats add a flat +1 per Stat Point.
        self.assertEqual(compute_stat(70, 0, is_hp=True), 145)
        self.assertEqual(compute_stat(70, 1, is_hp=True), 146)
        self.assertEqual(compute_stat(112, 0), 132)
        self.assertEqual(compute_stat(112, 2), 134)

        # The nature multiplier is applied AFTER the Stat Points are added (the game's
        # order), not before. With the old (incorrect) order Aerodactyl came out at 197.
        self.assertEqual(compute_stat(88, 32, nature=1), 154)

        # Golden maxima cross-checked against Serebii's Champions dex / worked examples.
        self.assertEqual(compute_stat(130, 32, nature=1), 200)  # Jolly Aerodactyl max Speed
        self.assertEqual(compute_stat(142, 32, nature=1), 213)  # Timid Dragapult max Speed
        self.assertEqual(compute_stat(116, 32, nature=1), 184)  # Timid Whimsicott max Speed
        self.assertEqual(compute_stat(120, 32, nature=1), 189)  # Jolly Sneasler max Speed
        self.assertEqual(compute_stat(102, 32, nature=1), 169)  # Jolly Garchomp max Speed
        self.assertEqual(compute_stat(142, 16, nature=1), 195)  # Timid Dragapult, 16 SP

    def test_speed_benchmarks_are_generated_from_compute_stat(self) -> None:
        catalog = get_speed_benchmark_catalog("champions_regulation_m_a")
        assert catalog is not None
        targets = {
            benchmark.slug: benchmark.target_speed
            for group in catalog.groups
            for benchmark in group.benchmarks
        }
        # Each benchmark must equal compute_stat() run on its declared set, so the
        # benchmark layer can never drift from the analyzer's own speed math.
        self.assertEqual(targets["jolly_garchomp"], compute_stat(102, 32, nature=1))
        self.assertEqual(targets["jolly_garchomp"], 169)
        self.assertEqual(targets["timid_whimsicott"], 184)
        self.assertEqual(targets["jolly_sneasler"], 189)
        self.assertEqual(targets["timid_dragapult"], 213)
        self.assertEqual(targets["choice_scarf_basculegion"], 214)
        self.assertEqual(targets["tailwind_garchomp"], compute_stat(102, 32, nature=1) * 2)

    def test_parser_reads_six_sets(self) -> None:
        team = parse_showdown_team(SAMPLE_TEAM)
        self.assertEqual(len(team), 6)
        self.assertEqual(team[4].species, "Basculegion (M)")
        self.assertEqual(team[0].moves[0], "Aura Sphere")

    def test_parser_reads_realistic_showdown_exports(self) -> None:
        team = parse_showdown_team(load_example_team("realistic_trick_room_team.txt"))

        self.assertEqual(len(team), 6)
        self.assertEqual(team[0].species, "Farigiraf")
        self.assertEqual(team[0].level, 50)
        self.assertEqual(team[0].evs, {"HP": 32, "Def": 15, "SpA": 19})
        self.assertEqual(team[-1].species, "Arcanine-Hisui")
        self.assertEqual(team[-1].item, "White Herb")
        self.assertEqual(team[-1].nature, "Adamant")

    def test_parser_preserves_canonical_parenthesized_form_species(self) -> None:
        team = parse_showdown_team(
            """Zoroark (Hisuian Form) @ Focus Sash
Ability: Illusion
- Hyper Voice
- Shadow Ball
- Protect
- Bitter Malice

Tauros (Paldean Form (Aqua Breed)) @ Mystic Water
Ability: Intimidate
- Wave Crash
- Close Combat
- Protect
- Aqua Jet
"""
        )

        self.assertEqual(team[0].species, "Zoroark (Hisuian Form)")
        self.assertIsNone(team[0].nickname)
        self.assertEqual(team[1].species, "Tauros (Paldean Form (Aqua Breed))")
        self.assertIsNone(team[1].nickname)

    def test_parser_supports_nicknamed_parenthesized_form_species(self) -> None:
        team = parse_showdown_team(
            """Fox Ghost (Zoroark (Hisuian Form)) @ Focus Sash
Ability: Illusion
- Hyper Voice
- Shadow Ball
- Protect
- Bitter Malice
"""
        )

        self.assertEqual(team[0].nickname, "Fox Ghost")
        self.assertEqual(team[0].species, "Zoroark (Hisuian Form)")

    def test_analysis_builds_expected_summary_and_vector(self) -> None:
        analysis = analyze_team_text(SAMPLE_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)
        self.assertEqual(analysis.team_size, 6)
        self.assertEqual(analysis.typing_counts["ghost"], 3)
        self.assertEqual(analysis.typing_counts["steel"], 2)
        self.assertEqual(analysis.offensive_coverage["water"], 2)
        self.assertEqual(analysis.offensive_coverage["fighting"], 1)
        self.assertEqual(analysis.average_base_speed, 87.5)
        self.assertAlmostEqual(analysis.average_battle_speed, 121.5, places=2)
        self.assertAlmostEqual(analysis.median_battle_speed, 121.0, places=2)
        self.assertAlmostEqual(analysis.speed_standard_deviation, 44.77, places=2)
        self.assertEqual(analysis.team_speed_tier, "mixed")
        self.assertEqual(analysis.fastest_pokemon, ("Aerodactyl", 130))
        self.assertEqual(analysis.slowest_pokemon, ("Sableye", 50))
        self.assertEqual(analysis.fastest_battle_speed_pokemon, ("Aerodactyl", 200))
        self.assertEqual(analysis.slowest_battle_speed_pokemon, ("Sableye", 63))
        self.assertEqual(analysis.member_battle_speeds["Lucario-Mega"], 134)
        self.assertEqual(analysis.member_battle_speeds["Sinistcha"], 81)
        self.assertEqual(analysis.member_speed_tiers["Sableye"], "trick_room_slow")
        self.assertEqual(analysis.member_speed_tiers["Aerodactyl"], "elite_fast")

        self.assertEqual(
            analysis.speed_benchmark_catalog,
            {
                "regulation_id": "champions_regulation_m_a",
                "display_name": "Pokemon Champions Regulation M-A Speed Benchmarks",
                "notes": (
                    "Computed from declared Regulation M-A reference sets (perfect IVs, 32 Stat Points "
                    "in the relevant stat, level 50) using the shared Champions stat formula. These are "
                    "exact max/min speed lines for common shells, not exhaustive usage stats."
                ),
            },
        )
        natural_statuses = {
            benchmark["slug"]: benchmark["status"]
            for benchmark in analysis.speed_benchmark_groups["natural"]["benchmarks"]
        }
        tailwind_statuses = {
            benchmark["slug"]: benchmark["status"]
            for benchmark in analysis.speed_benchmark_groups["tailwind"]["benchmarks"]
        }
        choice_scarf_statuses = {
            benchmark["slug"]: benchmark["status"]
            for benchmark in analysis.speed_benchmark_groups["choice_scarf"]["benchmarks"]
        }
        trick_room_statuses = {
            benchmark["slug"]: benchmark["status"]
            for benchmark in analysis.speed_benchmark_groups["trick_room"]["benchmarks"]
        }
        # With the corrected formula, max-invested Aerodactyl (200) now correctly outruns
        # base-102 Garchomp (169), base-116 Whimsicott (184), and base-120 Sneasler (189).
        self.assertEqual(natural_statuses["jolly_garchomp"], "outspeed")
        self.assertEqual(natural_statuses["timid_whimsicott"], "outspeed")
        self.assertEqual(natural_statuses["jolly_sneasler"], "outspeed")
        self.assertEqual(natural_statuses["timid_dragapult"], "miss")
        self.assertEqual(tailwind_statuses["tailwind_garchomp"], "outspeed")
        self.assertEqual(tailwind_statuses["tailwind_sneasler"], "outspeed")
        self.assertEqual(choice_scarf_statuses["choice_scarf_basculegion"], "tie")
        self.assertEqual(trick_room_statuses["min_speed_torkoal"], "miss")
        self.assertEqual(
            [tag["benchmark_slug"] for tag in analysis.member_speed_benchmark_tags["Aerodactyl"]],
            ["jolly_garchomp", "timid_whimsicott", "jolly_sneasler", "tailwind_garchomp", "tailwind_sneasler"],
        )
        self.assertEqual(
            [
                (tag["benchmark_slug"], tag["status"])
                for tag in analysis.member_speed_benchmark_tags["Basculegion (M)"]
            ],
            [("choice_scarf_basculegion", "tie")],
        )
        self.assertGreaterEqual(len(analysis.speed_benchmark_notes), 6)
        self.assertTrue(any(note.startswith("Team speed shape:") for note in analysis.speed_benchmark_notes))
        self.assertTrue(any("fastest unboosted line at 200" in note for note in analysis.speed_benchmark_notes))
        self.assertTrue(any("outruns Max-Speed Jolly Sneasler (189)" in note for note in analysis.speed_benchmark_notes))
        self.assertTrue(any("Tailwind line at 400" in note for note in analysis.speed_benchmark_notes))
        self.assertTrue(any("ties Max-Speed Choice Scarf Jolly Basculegion (214)" in note for note in analysis.speed_benchmark_notes))
        self.assertIn(
            "Trick Room underspeed: the team has no Trick Room setter, so it cannot create its own slower-first mode.",
            analysis.speed_benchmark_notes,
        )
        self.assertTrue(any(note.startswith("Benchmark depth:") for note in analysis.speed_benchmark_notes))
        self.assertTrue(any("Tailwind + Choice Scarf" in note for note in analysis.speed_benchmark_notes))
        self.assertEqual(
            analysis.speed_tier_counts,
            {
                "trick_room_slow": 1,
                "slow": 1,
                "midrange": 1,
                "fast": 2,
                "very_fast": 0,
                "elite_fast": 1,
            },
        )
        self.assertEqual(analysis.speed_tier_members["trick_room_slow"], ["Sableye"])
        self.assertEqual(analysis.damage_split, {"physical": 6, "special": 6})
        self.assertEqual(analysis.utility_moves, 12)
        self.assertEqual(analysis.utility_role_counts["protection"], 4)
        self.assertEqual(analysis.utility_role_counts["screen"], 2)
        self.assertEqual(analysis.utility_role_counts["weather"], 1)
        self.assertEqual(analysis.utility_role_counts["speed_control"], 2)
        self.assertEqual(analysis.utility_role_counts["redirection"], 1)
        self.assertEqual(analysis.utility_role_counts["recovery"], 1)
        self.assertEqual(analysis.utility_role_counts["healing_support"], 1)
        self.assertEqual(analysis.target_coverage["electric"]["best_multiplier"], 1.0)
        self.assertEqual(analysis.target_coverage["electric"]["super_effective_lines"], 0)
        self.assertEqual(analysis.utility_role_counts["stat_boost"], 1)
        self.assertEqual(len(analysis.vector), 133)
        self.assertEqual(analysis.vector_labels[0], "typing_normal")
        self.assertEqual(analysis.vector_labels[-1], "team_archetype_perish_trap")
        self.assertEqual(set(analysis.mode_matchup_scores), set(MODE_LABEL_ORDER))
        self.assertEqual(set(analysis.team_style_scores), set(STYLE_PACKAGE_ORDER))
        self.assertEqual(set(analysis.team_mode_package_scores), set(MODE_PACKAGE_ORDER))
        self.assertEqual(set(analysis.team_win_condition_scores), set(WIN_CONDITION_PACKAGE_ORDER))
        self.assertTrue(analysis.team_mode_labels)
        self.assertTrue(analysis.team_mode_packages)
        self.assertEqual(analysis.member_stats["Lucario-Mega"]["defense"], 154)
        self.assertEqual(analysis.member_stats["Basculegion (M)"]["speed"], 143)
        self.assertEqual(
            {context["slug"] for context in analysis.member_speed_contexts["Basculegion (M)"]},
            {"choice_scarf", "tailwind", "tailwind_choice_scarf"},
        )
        self.assertEqual(analysis.primary_team_style, "hyper_offense")
        analysis_dict = analysis.to_dict()
        self.assertIn("team_package_profile", analysis_dict)
        self.assertEqual(analysis_dict["team_package_profile"]["style"]["label"], analysis.primary_team_style)
        self.assertIn("special_sweeper", analysis.member_roles["Lucario-Mega"])
        self.assertIn("support", analysis.member_roles["Sableye"])
        self.assertIn("physical_sweeper", analysis.member_roles["Basculegion (M)"])
        self.assertIn("cleaner", analysis.member_roles["Basculegion (M)"])
        self.assertIn("bulky_attacker", analysis.member_roles["Basculegion (M)"])
        self.assertNotIn("speed_control", analysis.member_roles["Basculegion (M)"])
        self.assertAlmostEqual(analysis.defensive_profile["ghost"]["average_multiplier"], 1.3333, places=4)

    def test_analysis_counts_damaging_utility_moves_and_role_overlap(self) -> None:
        analysis = analyze_team_text(HYBRID_UTILITY_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        self.assertEqual(analysis.utility_moves, 7)
        self.assertEqual(analysis.damage_split, {"physical": 3, "special": 1})
        self.assertEqual(analysis.offensive_coverage["normal"], 1)
        self.assertEqual(analysis.offensive_coverage["electric"], 1)
        self.assertEqual(analysis.offensive_coverage["ice"], 1)
        self.assertEqual(analysis.utility_role_counts["protection"], 1)
        self.assertEqual(analysis.utility_role_counts["speed_control"], 5)
        self.assertEqual(analysis.utility_role_counts["flinch_control"], 1)
        self.assertEqual(analysis.utility_role_counts["status_infliction"], 1)
        self.assertEqual(analysis.utility_role_counts["stat_drop"], 1)
        self.assertEqual(analysis.utility_role_moves["speed_control"], ["Trick Room", "Quash", "Nuzzle", "Icy Wind", "Tailwind"])

    def test_classify_expanded_utility_roles(self) -> None:
        provider = FakeMetadataProvider()
        expected_roles = {
            "Stealth Rock": {"entry_hazard"},
            "Defog": {"hazard_removal"},
            "U-turn": {"pivoting"},
            "Knock Off": {"item_control"},
            "Taunt": {"disruption"},
            "Haze": {"anti_setup"},
            "Roar": {"phazing"},
            "Spirit Shackle": {"trapping"},
            "Heal Bell": {"healing_support"},
            "Electric Terrain": {"terrain"},
            "Parting Shot": {"pivoting", "stat_drop"},
        }

        for move_name, expected in expected_roles.items():
            with self.subTest(move=move_name):
                roles = set(classify_utility_roles(provider.get_move(move_name)))
                self.assertTrue(expected.issubset(roles))

    def test_analysis_infers_competitive_pokemon_roles(self) -> None:
        analysis = analyze_team_text(ROLE_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        self.assertEqual(analysis.utility_role_counts["entry_hazard"], 1)
        self.assertEqual(analysis.utility_role_counts["hazard_removal"], 1)
        self.assertEqual(analysis.utility_role_counts["pivoting"], 3)
        self.assertEqual(analysis.utility_role_counts["disruption"], 2)
        self.assertEqual(analysis.utility_role_counts["item_control"], 1)
        self.assertEqual(analysis.utility_role_counts["phazing"], 1)
        self.assertEqual(analysis.utility_role_counts["healing_support"], 1)

        self.assertIn("hazard_setter", analysis.member_roles["Tyranitar"])
        self.assertIn("weather_setter", analysis.member_roles["Tyranitar"])
        self.assertIn("bulky_attacker", analysis.member_roles["Tyranitar"])
        self.assertIn("hazard_control", analysis.member_roles["Corviknight"])
        self.assertIn("bulky_pivot", analysis.member_roles["Corviknight"])
        self.assertIn("bulky_support", analysis.member_roles["Corviknight"])
        self.assertIn("screen_setter", analysis.member_roles["Grimmsnarl"])
        self.assertIn("support", analysis.member_roles["Grimmsnarl"])
        self.assertIn("redirector", analysis.member_roles["Amoonguss"])
        self.assertIn("healing_support", analysis.member_roles["Amoonguss"])
        self.assertIn("bulky_pivot", analysis.member_roles["Amoonguss"])
        self.assertIn("setup_sweeper", analysis.member_roles["Volcarona"])
        self.assertIn("special_sweeper", analysis.member_roles["Volcarona"])
        self.assertIn("pivot", analysis.member_roles["Tapu Koko"])
        self.assertIn("terrain_setter", analysis.member_roles["Tapu Koko"])
        self.assertEqual(analysis.team_archetype, "balance")
        self.assertEqual(analysis.target_coverage["ground"]["best_multiplier"], 1.0)
        self.assertEqual(analysis.target_coverage["ground"]["super_effective_lines"], 0)

        self.assertEqual(analysis.pokemon_role_counts["hazard_setter"], 1)
        self.assertEqual(analysis.pokemon_role_counts["hazard_control"], 1)
        self.assertEqual(analysis.pokemon_role_counts["screen_setter"], 1)
        self.assertEqual(analysis.pokemon_role_counts["weather_setter"], 1)
        self.assertEqual(analysis.pokemon_role_counts["terrain_setter"], 1)
        self.assertEqual(analysis.pokemon_role_counts["setup_sweeper"], 1)
        self.assertEqual(analysis.pokemon_role_counts["redirector"], 1)
        self.assertGreater(analysis.team_archetype_scores["sand"], 0)
        self.assertGreater(analysis.team_archetype_scores["electric_terrain"], 0)
        self.assertIn("sand", analysis.team_mode_packages)
        self.assertIn("electric_terrain", analysis.team_mode_packages)

    def test_analysis_infers_team_archetypes(self) -> None:
        provider = FakeMetadataProvider()
        expected_archetypes = {
            ROLE_TEAM: "balance",
            HYPER_OFFENSE_TEAM: "hyper_offense",
            TRICK_ROOM_TEAM: "trick_room",
            SUN_TAILWIND_TEAM: "sun_tailwind",
            PERISH_TRAP_TEAM: "perish_trap",
        }

        for team_text, expected_archetype in expected_archetypes.items():
            with self.subTest(archetype=expected_archetype):
                analysis = analyze_team_text(team_text, metadata_provider=provider, regulation_id=None)
                self.assertEqual(analysis.team_archetype, expected_archetype)
                self.assertGreaterEqual(
                    analysis.team_archetype_scores[expected_archetype],
                    max(analysis.team_archetype_scores.values()),
                )

        hyper_offense_analysis = analyze_team_text(HYPER_OFFENSE_TEAM, metadata_provider=provider, regulation_id=None)
        trick_room_analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=provider, regulation_id=None)

        self.assertGreater(hyper_offense_analysis.team_archetype_scores["screens_offense"], 0)
        self.assertGreater(trick_room_analysis.team_archetype_scores["sun_room"], 0)
        self.assertIn("screens_offense", hyper_offense_analysis.team_win_condition_labels)
        self.assertIn("setup_sweep", hyper_offense_analysis.team_win_condition_labels)
        self.assertIn("sun_room", trick_room_analysis.team_mode_packages)

    def test_screens_offense_requires_actual_screen_support(self) -> None:
        class ComplaintMetadataProvider:
            def __init__(self) -> None:
                self.species = {
                    "Palafin": SpeciesData("Palafin", "palafin", ("water",), 100, 70, 72, 53, 62, 100),
                    "Kleavor": SpeciesData("Kleavor", "kleavor", ("bug", "rock"), 70, 135, 95, 45, 70, 85),
                    "Tinkaton": SpeciesData("Tinkaton", "tinkaton", ("fairy", "steel"), 85, 75, 77, 70, 105, 94),
                    "Mega Manectric": SpeciesData("Mega Manectric", "manectric-mega", ("electric",), 70, 75, 80, 135, 80, 135),
                    "Pelipper": SpeciesData("Pelipper", "pelipper", ("water", "flying"), 60, 50, 100, 95, 70, 65),
                    "Archaludon": SpeciesData("Archaludon", "archaludon", ("steel", "dragon"), 90, 105, 130, 125, 65, 85),
                }
                self.moves = {
                    "Jet Punch": MoveData("Jet Punch", "jet-punch", "water", "physical", priority=1),
                    "Wave Crash": MoveData("Wave Crash", "wave-crash", "water", "physical"),
                    "Flip Turn": MoveData("Flip Turn", "flip-turn", "water", "physical"),
                    "Protect": MoveData("Protect", "protect", "normal", "status", priority=4, target_name="user"),
                    "Stone Axe": MoveData("Stone Axe", "stone-axe", "rock", "physical"),
                    "X-Scissor": MoveData("X-Scissor", "x-scissor", "bug", "physical"),
                    "Close Combat": MoveData("Close Combat", "close-combat", "fighting", "physical"),
                    "U-turn": MoveData("U-turn", "u-turn", "bug", "physical"),
                    "Fake Out": MoveData(
                        "Fake Out",
                        "fake-out",
                        "normal",
                        "physical",
                        effect_chance=100,
                        flinch_chance=100,
                        priority=3,
                        target_name="selected-pokemon",
                    ),
                    "Gigaton Hammer": MoveData("Gigaton Hammer", "gigaton-hammer", "steel", "physical"),
                    "Play Rough": MoveData("Play Rough", "play-rough", "fairy", "physical"),
                    "Thunder Wave": MoveData("Thunder Wave", "thunder-wave", "electric", "status"),
                    "Thunderbolt": MoveData("Thunderbolt", "thunderbolt", "electric", "special"),
                    "Volt Switch": MoveData("Volt Switch", "volt-switch", "electric", "special"),
                    "Snarl": MoveData("Snarl", "snarl", "dark", "special"),
                    "Tailwind": MoveData(
                        "Tailwind",
                        "tailwind",
                        "flying",
                        "status",
                        category_name="field-effect",
                        target_name="users-field",
                    ),
                    "Hydro Pump": MoveData("Hydro Pump", "hydro-pump", "water", "special"),
                    "Hurricane": MoveData("Hurricane", "hurricane", "flying", "special"),
                    "Electro Shot": MoveData("Electro Shot", "electro-shot", "electric", "special"),
                    "Draco Meteor": MoveData("Draco Meteor", "draco-meteor", "dragon", "special"),
                    "Flash Cannon": MoveData("Flash Cannon", "flash-cannon", "steel", "special"),
                }

            def get_species(self, species_name: str) -> SpeciesData:
                return self.species[species_name]

            def get_move(self, move_name: str) -> MoveData:
                return self.moves[move_name]

        team = [
            PokemonSet("Palafin", ["Jet Punch", "Wave Crash", "Flip Turn", "Protect"], item="Mystic Water", ability="Zero to Hero", nature="Adamant", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Kleavor", ["Stone Axe", "X-Scissor", "Close Combat", "U-turn"], item="Choice Scarf", ability="Sharpness", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Tinkaton", ["Fake Out", "Gigaton Hammer", "Play Rough", "Thunder Wave"], item="Mental Herb", ability="Mold Breaker", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Mega Manectric", ["Thunderbolt", "Volt Switch", "Snarl", "Protect"], item="Manectite", ability="Intimidate", nature="Timid", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Pelipper", ["Tailwind", "Hydro Pump", "Hurricane", "Protect"], item="Focus Sash", ability="Drizzle", nature="Modest", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Archaludon", ["Electro Shot", "Draco Meteor", "Flash Cannon", "Protect"], item="Leftovers", ability="Stamina", nature="Modest", evs={"SpA": 66, "Spe": 66}),
        ]

        analysis = analyze_team(team, metadata_provider=ComplaintMetadataProvider(), regulation_id=None)

        self.assertEqual(analysis.pokemon_role_counts["screen_setter"], 0)
        self.assertEqual(analysis.utility_role_counts["screen"], 0)
        self.assertLessEqual(analysis.team_archetype_scores["screens_offense"], 0.0)
        self.assertNotIn("screens_offense", analysis.team_win_condition_labels)

    def test_lightning_rod_and_mold_breaker_context_reduce_overstated_electric_and_room_flags(self) -> None:
        class ComplaintContextProvider:
            def __init__(self) -> None:
                self.species = {
                    "Palafin": SpeciesData("Palafin", "palafin", ("water",), 100, 70, 72, 53, 62, 100),
                    "Kleavor": SpeciesData("Kleavor", "kleavor", ("bug", "rock"), 70, 135, 95, 45, 70, 85),
                    "Tinkaton": SpeciesData("Tinkaton", "tinkaton", ("fairy", "steel"), 85, 75, 77, 70, 105, 94),
                    "Manectric": SpeciesData("Manectric", "manectric", ("electric",), 70, 75, 60, 105, 60, 105),
                    "Mega Manectric": SpeciesData("Mega Manectric", "manectric-mega", ("electric",), 70, 75, 80, 135, 80, 135),
                    "Pelipper": SpeciesData("Pelipper", "pelipper", ("water", "flying"), 60, 50, 100, 95, 70, 65),
                    "Archaludon": SpeciesData("Archaludon", "archaludon", ("steel", "dragon"), 90, 105, 130, 125, 65, 85),
                }
                self.moves = {
                    "Jet Punch": MoveData("Jet Punch", "jet-punch", "water", "physical", priority=1),
                    "Wave Crash": MoveData("Wave Crash", "wave-crash", "water", "physical"),
                    "Flip Turn": MoveData("Flip Turn", "flip-turn", "water", "physical"),
                    "Protect": MoveData("Protect", "protect", "normal", "status", priority=4, target_name="user"),
                    "Stone Axe": MoveData("Stone Axe", "stone-axe", "rock", "physical"),
                    "X-Scissor": MoveData("X-Scissor", "x-scissor", "bug", "physical"),
                    "Close Combat": MoveData("Close Combat", "close-combat", "fighting", "physical"),
                    "U-turn": MoveData("U-turn", "u-turn", "bug", "physical"),
                    "Fake Out": MoveData(
                        "Fake Out",
                        "fake-out",
                        "normal",
                        "physical",
                        effect_chance=100,
                        flinch_chance=100,
                        priority=3,
                        target_name="selected-pokemon",
                    ),
                    "Gigaton Hammer": MoveData("Gigaton Hammer", "gigaton-hammer", "steel", "physical"),
                    "Play Rough": MoveData("Play Rough", "play-rough", "fairy", "physical"),
                    "Thunder Wave": MoveData("Thunder Wave", "thunder-wave", "electric", "status"),
                    "Thunderbolt": MoveData("Thunderbolt", "thunderbolt", "electric", "special"),
                    "Volt Switch": MoveData("Volt Switch", "volt-switch", "electric", "special"),
                    "Snarl": MoveData("Snarl", "snarl", "dark", "special"),
                    "Tailwind": MoveData(
                        "Tailwind",
                        "tailwind",
                        "flying",
                        "status",
                        category_name="field-effect",
                        target_name="users-field",
                    ),
                    "Hydro Pump": MoveData("Hydro Pump", "hydro-pump", "water", "special"),
                    "Hurricane": MoveData("Hurricane", "hurricane", "flying", "special"),
                    "Electro Shot": MoveData("Electro Shot", "electro-shot", "electric", "special"),
                    "Draco Meteor": MoveData("Draco Meteor", "draco-meteor", "dragon", "special"),
                    "Flash Cannon": MoveData("Flash Cannon", "flash-cannon", "steel", "special"),
                }

            def get_species(self, species_name: str) -> SpeciesData:
                return self.species[species_name]

            def get_move(self, move_name: str) -> MoveData:
                return self.moves[move_name]

        team = [
            PokemonSet("Palafin", ["Jet Punch", "Wave Crash", "Flip Turn", "Protect"], item="Mystic Water", ability="Zero to Hero", nature="Adamant", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Kleavor", ["Stone Axe", "X-Scissor", "Close Combat", "U-turn"], item="Choice Scarf", ability="Sharpness", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Tinkaton", ["Fake Out", "Gigaton Hammer", "Play Rough", "Thunder Wave"], item="Mental Herb", ability="Mold Breaker", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Manectric", ["Thunderbolt", "Volt Switch", "Snarl", "Protect"], item="Manectite", ability="Lightning Rod", nature="Timid", evs={"SpA": 32, "Spe": 66}),
            PokemonSet("Pelipper", ["Tailwind", "Hydro Pump", "Hurricane", "Protect"], item="Focus Sash", ability="Drizzle", nature="Modest", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Archaludon", ["Electro Shot", "Draco Meteor", "Flash Cannon", "Protect"], item="Leftovers", ability="Stamina", nature="Modest", evs={"SpA": 66, "Spe": 66}),
        ]

        analysis = analyze_team(team, metadata_provider=ComplaintContextProvider(), regulation_id=None)

        self.assertEqual(analysis.defensive_profile["electric"]["immune_members"], 1)
        self.assertLess(float(analysis.defensive_profile["electric"]["average_multiplier"]), 1.0)
        self.assertNotIn("electric", analysis.top_defensive_weaknesses)

        trick_room_reasons = analysis.matchup_details["trick_room"]["reasons"]
        self.assertTrue(any("Mold Breaker Fake Out" in reason for reason in trick_room_reasons))

        farigiraf_row = next(
            row for row in analysis.meta_analysis["tournament_rows"] if row["label"] == "Farigiraf Torkoal Room"
        )
        self.assertTrue(any("Armor Tail" in reason for reason in farigiraf_row["context_reasons"]))

    def test_snapshot_target_summary_rewards_real_dual_type_answer_lines(self) -> None:
        class SnapshotContextProvider:
            def __init__(self) -> None:
                self.species = {
                    "Palafin": SpeciesData("Palafin", "palafin", ("water",), 100, 70, 72, 53, 62, 100),
                    "Kleavor": SpeciesData("Kleavor", "kleavor", ("bug", "rock"), 70, 135, 95, 45, 70, 85),
                    "Tinkaton": SpeciesData("Tinkaton", "tinkaton", ("fairy", "steel"), 85, 75, 77, 70, 105, 94),
                    "Mega Manectric": SpeciesData("Mega Manectric", "manectric-mega", ("electric",), 70, 75, 80, 135, 80, 135),
                    "Pelipper": SpeciesData("Pelipper", "pelipper", ("water", "flying"), 60, 50, 100, 95, 70, 65),
                    "Archaludon": SpeciesData("Archaludon", "archaludon", ("steel", "dragon"), 90, 105, 130, 125, 65, 85),
                    "Sinistcha": SpeciesData("Sinistcha", "sinistcha", ("grass", "ghost"), 71, 60, 106, 121, 80, 70),
                    "Incineroar": SpeciesData("Incineroar", "incineroar", ("fire", "dark"), 95, 115, 90, 80, 90, 60),
                    "Scizor": SpeciesData("Scizor", "scizor", ("bug", "steel"), 70, 130, 100, 55, 80, 65),
                }
                self.moves = {
                    "Jet Punch": MoveData("Jet Punch", "jet-punch", "water", "physical", priority=1),
                    "Wave Crash": MoveData("Wave Crash", "wave-crash", "water", "physical"),
                    "Flip Turn": MoveData("Flip Turn", "flip-turn", "water", "physical"),
                    "Protect": MoveData("Protect", "protect", "normal", "status", priority=4, target_name="user"),
                    "Stone Axe": MoveData("Stone Axe", "stone-axe", "rock", "physical"),
                    "X-Scissor": MoveData("X-Scissor", "x-scissor", "bug", "physical"),
                    "Close Combat": MoveData("Close Combat", "close-combat", "fighting", "physical"),
                    "U-turn": MoveData("U-turn", "u-turn", "bug", "physical"),
                    "Fake Out": MoveData(
                        "Fake Out",
                        "fake-out",
                        "normal",
                        "physical",
                        effect_chance=100,
                        flinch_chance=100,
                        priority=3,
                        target_name="selected-pokemon",
                    ),
                    "Gigaton Hammer": MoveData("Gigaton Hammer", "gigaton-hammer", "steel", "physical"),
                    "Play Rough": MoveData("Play Rough", "play-rough", "fairy", "physical"),
                    "Thunder Wave": MoveData("Thunder Wave", "thunder-wave", "electric", "status"),
                    "Thunderbolt": MoveData("Thunderbolt", "thunderbolt", "electric", "special"),
                    "Volt Switch": MoveData("Volt Switch", "volt-switch", "electric", "special"),
                    "Snarl": MoveData("Snarl", "snarl", "dark", "special"),
                    "Tailwind": MoveData(
                        "Tailwind",
                        "tailwind",
                        "flying",
                        "status",
                        category_name="field-effect",
                        target_name="users-field",
                    ),
                    "Hydro Pump": MoveData("Hydro Pump", "hydro-pump", "water", "special"),
                    "Hurricane": MoveData("Hurricane", "hurricane", "flying", "special"),
                    "Electro Shot": MoveData("Electro Shot", "electro-shot", "electric", "special"),
                    "Draco Meteor": MoveData("Draco Meteor", "draco-meteor", "dragon", "special"),
                    "Flash Cannon": MoveData("Flash Cannon", "flash-cannon", "steel", "special"),
                }

            def get_species(self, species_name: str) -> SpeciesData:
                return self.species[species_name]

            def get_move(self, move_name: str) -> MoveData:
                return self.moves[move_name]

        provider = SnapshotContextProvider()
        answer_team = [
            PokemonSet("Palafin", ["Jet Punch", "Wave Crash", "Flip Turn", "Protect"], item="Mystic Water", ability="Zero to Hero", nature="Adamant", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Kleavor", ["Stone Axe", "X-Scissor", "Close Combat", "U-turn"], item="Choice Scarf", ability="Sharpness", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Tinkaton", ["Fake Out", "Gigaton Hammer", "Play Rough", "Thunder Wave"], item="Mental Herb", ability="Mold Breaker", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Manectric", ["Thunderbolt", "Volt Switch", "Snarl", "Protect"], item="Manectite", ability="Lightning Rod", nature="Timid", evs={"SpA": 32, "Spe": 66}),
            PokemonSet("Pelipper", ["Tailwind", "Hydro Pump", "Hurricane", "Protect"], item="Focus Sash", ability="Drizzle", nature="Modest", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Archaludon", ["Electro Shot", "Draco Meteor", "Flash Cannon", "Protect"], item="Leftovers", ability="Stamina", nature="Modest", evs={"SpA": 66, "Spe": 66}),
        ]
        neutral_team = [
            PokemonSet("Palafin", ["Jet Punch", "Wave Crash", "Flip Turn", "Protect"], item="Mystic Water", ability="Zero to Hero", nature="Adamant", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Kleavor", ["Stone Axe", "X-Scissor", "Protect", "U-turn"], item="Choice Scarf", ability="Sharpness", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Tinkaton", ["Fake Out", "Gigaton Hammer", "Protect", "Thunder Wave"], item="Mental Herb", ability="Mold Breaker", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Manectric", ["Thunderbolt", "Snarl", "Protect", "Protect"], item="Manectite", ability="Lightning Rod", nature="Timid", evs={"SpA": 32, "Spe": 66}),
            PokemonSet("Pelipper", ["Tailwind", "Hydro Pump", "Protect", "Protect"], item="Focus Sash", ability="Drizzle", nature="Modest", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Archaludon", ["Electro Shot", "Draco Meteor", "Flash Cannon", "Protect"], item="Leftovers", ability="Stamina", nature="Modest", evs={"SpA": 66, "Spe": 66}),
        ]

        answer_members = _resolve_members(answer_team, provider, regulation_id=None)
        neutral_members = _resolve_members(neutral_team, provider, regulation_id=None)
        snapshot = next(
            entry for entry in get_tournament_team_snapshots(None) if entry["label"] == "Rain Archaludon"
        )

        answer_summary = _build_snapshot_target_matchup_summary(snapshot, answer_members, provider, regulation_id=None)
        neutral_summary = _build_snapshot_target_matchup_summary(snapshot, neutral_members, provider, regulation_id=None)

        self.assertGreater(answer_summary.resolved_targets, 0)
        self.assertEqual(answer_summary.resolved_targets, neutral_summary.resolved_targets)
        self.assertGreater(answer_summary.average_offensive_pressure, neutral_summary.average_offensive_pressure)
        self.assertGreater(answer_summary.strong_answer_targets, neutral_summary.strong_answer_targets)

    def test_analysis_covers_terrain_and_snow_shells(self) -> None:
        provider = FakeMetadataProvider()
        psyspam_analysis = analyze_team_text(PSYSPAM_TEAM, metadata_provider=provider, regulation_id=None)
        snow_analysis = analyze_team_text(SNOW_TAILWIND_TEAM, metadata_provider=provider, regulation_id=None)

        self.assertGreater(psyspam_analysis.team_archetype_scores["psychic_terrain"], 0)
        self.assertGreater(psyspam_analysis.team_archetype_scores["psyspam"], 0)
        self.assertIn("psychic_terrain", psyspam_analysis.team_mode_packages)
        self.assertIn("psyspam", psyspam_analysis.team_win_condition_labels)

        self.assertGreater(snow_analysis.team_archetype_scores["snow"], 0)
        self.assertGreater(snow_analysis.team_archetype_scores["snow_tailwind"], 0)
        self.assertIn("snow", snow_analysis.team_mode_packages)
        self.assertIn("snow_tailwind", snow_analysis.team_mode_packages)

    def test_realistic_example_teams_infer_expected_roles_and_archetypes(self) -> None:
        provider = FakeMetadataProvider()
        example_expectations = {
            "realistic_sand_team.txt": {
                "archetype": "sand_tailwind",
                "member_roles": {
                    "Tyranitar": {"bulky_attacker", "support", "hazard_setter", "weather_setter"},
                    "Corviknight": {"bulky_support", "bulky_pivot", "support", "speed_control", "tailwind_setter"},
                    "Sinistcha": {"support", "healing_support", "redirector"},
                },
            },
            "realistic_hyper_offense_team.txt": {
                "archetype": "hyper_offense",
                "member_roles": {
                    "Glimmora": {"special_sweeper", "hazard_setter"},
                    "Garchomp": {"physical_sweeper"},
                    "Whimsicott": {"speed_control", "tailwind_setter"},
                },
            },
            "realistic_trick_room_team.txt": {
                "archetype": "trick_room",
                "member_roles": {
                    "Farigiraf": {"bulky_attacker", "speed_control", "trick_room_setter"},
                    "Sinistcha": {"support", "speed_control", "trick_room_setter", "healing_support", "redirector"},
                    "Arcanine-Hisui": {"bulky_pivot"},
                },
            },
            "realistic_perish_trap_team.txt": {
                "archetype": "perish_trap",
                "member_roles": {
                    "Politoed": {"weather_setter", "speed_control", "trapper"},
                    "Sableye": {"weather_setter", "speed_control", "trapper", "support"},
                    "Sinistcha": {"support", "healing_support", "redirector"},
                },
            },
        }

        for file_name, expectation in example_expectations.items():
            with self.subTest(example=file_name):
                analysis = analyze_team_text(load_example_team(file_name), metadata_provider=provider, regulation_id=None)
                self.assertEqual(analysis.team_archetype, expectation["archetype"])
                self.assertGreaterEqual(
                    analysis.team_archetype_scores[expectation["archetype"]],
                    max(analysis.team_archetype_scores.values()),
                )
                for member_name, expected_roles in expectation["member_roles"].items():
                    with self.subTest(example=file_name, member=member_name):
                        self.assertTrue(expected_roles.issubset(set(analysis.member_roles[member_name])))

    def test_curated_mode_shell_examples_cover_remaining_archetypes(self) -> None:
        provider = FakeMetadataProvider()
        example_expectations = {
            "realistic_grassy_terrain_team.txt": "grassy_terrain",
            "realistic_misty_terrain_team.txt": "misty_terrain",
            "realistic_sand_room_team.txt": "sand_room",
            "realistic_snow_room_team.txt": "snow_room",
            "realistic_sun_tailroom_team.txt": "sun_tailroom",
        }

        for file_name, expected_archetype in example_expectations.items():
            with self.subTest(example=file_name):
                analysis = analyze_team_text(load_example_team(file_name), metadata_provider=provider, regulation_id=None)
                self.assertEqual(analysis.team_archetype, expected_archetype)
                self.assertGreaterEqual(
                    analysis.team_archetype_scores[expected_archetype],
                    max(analysis.team_archetype_scores.values()),
                )
                self.assertIn(expected_archetype, analysis.team_mode_packages)

    def test_team_package_style_tracks_supportive_proactive_shells(self) -> None:
        provider = FakeMetadataProvider()
        example_expectations = {
            "realistic_sand_team.txt": "balance",
            "championsmeta_mega_scizor_team.txt": "balance",
        }

        for file_name, expected_style in example_expectations.items():
            with self.subTest(example=file_name):
                analysis = analyze_team_text(load_example_team(file_name), metadata_provider=provider, regulation_id=None)
                self.assertEqual(analysis.primary_team_style, expected_style)

    def test_sample_teams_auto_upgrade_mega_stone_holders_to_mega_species(self) -> None:
        provider = FakeMetadataProvider()
        hyper_offense_analysis = analyze_team_text(
            load_example_team("realistic_hyper_offense_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )
        perish_analysis = analyze_team_text(
            load_example_team("realistic_perish_trap_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )

        self.assertIn("Mega Charizard Y", hyper_offense_analysis.member_roles)
        self.assertNotIn("Charizard", hyper_offense_analysis.member_roles)
        self.assertIn("Mega Gengar", perish_analysis.member_roles)
        self.assertNotIn("Gengar", perish_analysis.member_roles)

    def test_incoherent_example_does_not_claim_perish_trap_without_trap(self) -> None:
        provider = FakeMetadataProvider()
        real_perish_analysis = analyze_team_text(
            load_example_team("realistic_perish_trap_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )
        incoherent_analysis = analyze_team_text(
            load_example_team("incoherent_stress_test_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )

        self.assertIn("perish_trap", real_perish_analysis.team_win_condition_labels)
        self.assertNotIn("perish_trap", incoherent_analysis.team_win_condition_labels)
        self.assertLess(incoherent_analysis.team_archetype_scores["perish_trap"], 2.0)
        self.assertNotEqual(incoherent_analysis.primary_team_style, "hyper_offense")
        self.assertLess(incoherent_analysis.matchup_scores["hyper_offense"], 3.0)
        self.assertLess(incoherent_analysis.matchup_scores["trick_room"], 2.5)

    def test_speed_benchmarks_include_trick_room_and_member_tags(self) -> None:
        analysis = analyze_team_text(
            load_example_team("realistic_trick_room_team.txt"),
            metadata_provider=FakeMetadataProvider(),
            regulation_id=None,
        )

        trick_room_statuses = {
            benchmark["slug"]: benchmark["status"]
            for benchmark in analysis.speed_benchmark_groups["trick_room"]["benchmarks"]
        }
        self.assertEqual(trick_room_statuses["min_speed_torkoal"], "tie")
        self.assertEqual(trick_room_statuses["min_speed_amoonguss"], "underspeed")
        self.assertEqual(trick_room_statuses["min_speed_sinistcha"], "tie")
        self.assertTrue(
            any(
                "slowest Trick Room-ready line at 36" in note
                for note in analysis.speed_benchmark_notes
            )
        )
        self.assertEqual(
            [tag["benchmark_slug"] for tag in analysis.member_speed_benchmark_tags["Torkoal"]],
            [
                "min_speed_torkoal",
                "min_speed_amoonguss",
                "min_speed_kingambit",
                "min_speed_farigiraf",
                "min_speed_sinistcha",
            ],
        )
        self.assertEqual(
            [tag["benchmark_slug"] for tag in analysis.member_speed_benchmark_tags["Farigiraf"]],
            ["min_speed_sinistcha"],
        )
        analysis_dict = analysis.to_dict()
        member_payloads = {
            member["pokemon"]: member
            for member in analysis_dict["speed_profile"]["members"]
        }
        self.assertIn("benchmark_tags", member_payloads["Torkoal"])
        self.assertIn("stats", member_payloads["Torkoal"])
        self.assertIn("speed_contexts", member_payloads["Torkoal"])
        self.assertEqual(
            [tag["benchmark_slug"] for tag in member_payloads["Kingambit"]["benchmark_tags"]],
            ["min_speed_farigiraf", "min_speed_sinistcha"],
        )

    def test_speed_contexts_include_ability_based_boosts(self) -> None:
        analysis = analyze_team_text(
            load_example_team("championsmeta_mega_scizor_team.txt"),
            metadata_provider=FakeMetadataProvider(),
            regulation_id=None,
        )

        sneasler_contexts = {
            context["slug"]: context["speed"]
            for context in analysis.member_speed_contexts["Sneasler"]
        }
        self.assertEqual(sneasler_contexts["unburden"], 344)
        self.assertEqual(sneasler_contexts["tailwind_unburden"], 688)

    def test_analysis_predicts_matchups_and_team_difficulty(self) -> None:
        provider = FakeMetadataProvider()
        balance_analysis = analyze_team_text(ROLE_TEAM, metadata_provider=provider, regulation_id=None)
        hyper_offense_analysis = analyze_team_text(HYPER_OFFENSE_TEAM, metadata_provider=provider, regulation_id=None)
        trick_room_analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=provider, regulation_id=None)

        for analysis in (balance_analysis, hyper_offense_analysis, trick_room_analysis):
            self.assertEqual(set(analysis.matchup_scores), set(BROAD_TEAM_ARCHETYPE_ORDER))
            self.assertEqual(set(analysis.team_archetype_scores), set(TEAM_ARCHETYPE_ORDER))
            self.assertEqual(set(analysis.team_style_scores), set(STYLE_PACKAGE_ORDER))
            self.assertEqual(set(analysis.team_mode_package_scores), set(MODE_PACKAGE_ORDER))
            self.assertEqual(set(analysis.team_win_condition_scores), set(WIN_CONDITION_PACKAGE_ORDER))
            self.assertEqual(set(analysis.mode_matchup_scores), set(MODE_LABEL_ORDER))
            self.assertTrue(analysis.favorable_matchups)
            self.assertTrue(analysis.unfavorable_matchups)
            self.assertTrue(analysis.team_mode_labels)
            self.assertTrue(analysis.team_mode_packages)
            self.assertTrue(analysis.favorable_modes)
            self.assertTrue(analysis.unfavorable_modes)
            self.assertGreaterEqual(analysis.team_difficulty_score, 1.0)
            self.assertLessEqual(analysis.team_difficulty_score, 10.0)
            self.assertIn(analysis.team_difficulty_label, {"low", "moderate", "high", "very_high"})
            self.assertTrue(analysis.team_difficulty_factors)
            self.assertTrue(analysis.beginner_guidance_notes)

        self.assertIn("stall", hyper_offense_analysis.favorable_matchups)
        self.assertIn("trick_room", hyper_offense_analysis.unfavorable_matchups)
        self.assertIn("hyper_offense", balance_analysis.favorable_matchups)
        self.assertEqual(hyper_offense_analysis.primary_team_style, "hyper_offense")
        self.assertEqual(balance_analysis.primary_team_style, "balance")
        self.assertEqual(trick_room_analysis.primary_team_style, "bulky_offense")
        self.assertEqual(balance_analysis.team_difficulty_label, "moderate")
        self.assertEqual(trick_room_analysis.team_difficulty_label, "high")
        self.assertGreater(trick_room_analysis.team_difficulty_score, balance_analysis.team_difficulty_score)

    def test_matchup_profile_tracks_real_champions_m_a_team_plans(self) -> None:
        provider = FakeMetadataProvider()
        master_ball_analysis = analyze_team_text(
            load_example_team("championsmeta_master_ball_ready_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )
        mega_scizor_analysis = analyze_team_text(
            load_example_team("championsmeta_mega_scizor_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )

        self.assertGreater(master_ball_analysis.matchup_scores["hyper_offense"], 0)
        self.assertGreater(master_ball_analysis.matchup_scores["bulky_offense"], 0)
        self.assertTrue(any("rain" in mode for mode in master_ball_analysis.team_mode_labels))
        self.assertIn("hyper_offense", mega_scizor_analysis.favorable_matchups)
        self.assertGreater(
            mega_scizor_analysis.matchup_scores["trick_room"],
            0,
        )
        self.assertTrue(any("tailwind" in mode for mode in mega_scizor_analysis.team_mode_labels))
        self.assertNotIn("trick_room", mega_scizor_analysis.unfavorable_matchups)

    def test_tournament_mode_layer_covers_current_mode_shell_examples(self) -> None:
        provider = FakeMetadataProvider()
        expected_mode_labels = {
            "realistic_grassy_terrain_team.txt": "grassy_terrain",
            "realistic_misty_terrain_team.txt": "misty_terrain",
            "realistic_sand_room_team.txt": "sand_room",
            "realistic_snow_room_team.txt": "snow_room",
            "realistic_sun_tailroom_team.txt": "sun_tailroom",
        }

        for file_name, expected_label in expected_mode_labels.items():
            with self.subTest(example=file_name):
                analysis = analyze_team_text(load_example_team(file_name), metadata_provider=provider, regulation_id=None)
                self.assertIn(expected_label, analysis.team_mode_labels)
                self.assertGreater(
                    analysis.team_mode_scores[expected_label],
                    0,
                )

    def test_item_and_ability_signals_refine_roles(self) -> None:
        provider = FakeMetadataProvider()
        sample_analysis = analyze_team_text(SAMPLE_TEAM, metadata_provider=provider, regulation_id=None)
        trick_room_analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=provider, regulation_id=None)
        mega_scizor_analysis = analyze_team_text(
            load_example_team("championsmeta_mega_scizor_team.txt"),
            metadata_provider=provider,
            regulation_id=None,
        )

        self.assertIn("physical_sweeper", sample_analysis.member_roles["Basculegion (M)"])
        self.assertIn("cleaner", sample_analysis.member_roles["Basculegion (M)"])
        self.assertIn("bulky_attacker", sample_analysis.member_roles["Basculegion (M)"])
        self.assertNotIn("speed_control", sample_analysis.member_roles["Basculegion (M)"])
        self.assertIn("bulky_support", trick_room_analysis.member_roles["Porygon2"])
        self.assertIn("bulky_attacker", trick_room_analysis.member_roles["Iron Hands"])
        self.assertIn("bulky_pivot", trick_room_analysis.member_roles["Amoonguss"])
        self.assertIn("physical_sweeper", mega_scizor_analysis.member_roles["Sneasler"])
        self.assertIn("cleaner", mega_scizor_analysis.member_roles["Sneasler"])
        self.assertIn("fake_out_support", mega_scizor_analysis.member_roles["Sneasler"])
        self.assertNotIn("support", mega_scizor_analysis.member_roles["Sneasler"])

    def test_beginner_guidance_flags_building_issues(self) -> None:
        provider = FakeMetadataProvider()
        support_heavy_analysis = analyze_team_text(
            SUPPORT_HEAVY_CHOICE_TEAM,
            metadata_provider=provider,
            regulation_id=None,
        )
        low_support_analysis = analyze_team_text(
            LOW_SUPPORT_TOOLS_TEAM,
            metadata_provider=provider,
            regulation_id=None,
        )

        support_heavy_notes = "\n".join(support_heavy_analysis.beginner_guidance_notes)
        self.assertIn("Dragapult is holding Choice Band but also has Protect", support_heavy_notes)
        self.assertIn("very support-heavy", support_heavy_notes)
        self.assertIn("most dedicated support slots are", support_heavy_notes)
        self.assertIn("Sableye", support_heavy_notes)
        self.assertIn("Corviknight", support_heavy_notes)
        self.assertIn("Audino", support_heavy_notes)
        self.assertEqual(
            support_heavy_analysis.to_dict()["beginner_guidance"]["notes"],
            support_heavy_analysis.beginner_guidance_notes,
        )

        low_support_notes = "\n".join(low_support_analysis.beginner_guidance_notes)
        self.assertIn("no dedicated speed-control move", low_support_notes)
        self.assertIn("no Fake Out, redirection, screens, or pivoting move", low_support_notes)
        self.assertIn("no clear anti-setup button", low_support_notes)
        self.assertIn("only has one real speed-mode button", low_support_notes)
        self.assertIn("wants setup turns, but it has very few tools", low_support_notes)

    def test_live_board_context_flows_into_benchmark_and_team_notes(self) -> None:
        analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        benchmark_notes = "\n".join(analysis.speed_benchmark_notes)
        difficulty_notes = "\n".join(analysis.team_difficulty_factors)
        guidance_notes = "\n".join(analysis.beginner_guidance_notes)

        self.assertIn("live board", benchmark_notes)
        self.assertIn("teams", benchmark_notes)
        self.assertNotIn("Farigiraf Torkoal Room", benchmark_notes)
        self.assertIn("teams", difficulty_notes)
        self.assertIn("Start your matchup reps into teams", guidance_notes)
        self.assertNotIn("Mega Venusaur Kommo-o", difficulty_notes)
        self.assertNotIn("Mega Venusaur Kommo-o", guidance_notes)
        self.assertNotIn("Rain Archaludon", guidance_notes)

    def test_team_preview_builds_default_plans_and_watchlists(self) -> None:
        analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        self.assertTrue(analysis.team_preview_plans)
        self.assertTrue(analysis.team_preview_watch_teams)
        self.assertTrue(analysis.team_preview_watch_pokemon)
        self.assertTrue(analysis.team_preview_strategy_notes)
        self.assertTrue(analysis.team_preview_counterplay_notes)
        self.assertTrue(any(" so " in note for note in analysis.team_preview_watch_teams))
        self.assertTrue(any("(" in note and ")" in note for note in analysis.team_preview_watch_pokemon))
        self.assertTrue(any("That opener keeps" in note for note in analysis.team_preview_strategy_notes))
        self.assertTrue(any("In practice" in note for note in analysis.team_preview_counterplay_notes))

        primary_plan = analysis.team_preview_plans[0]
        self.assertIn("Room", primary_plan["label"])
        self.assertEqual(len(primary_plan["leads"]), 2)
        self.assertEqual(len(primary_plan["back"]), 2)
        self.assertEqual(len(primary_plan["pick_four"]), 4)
        self.assertIn("Lead", primary_plan["summary"])
        self.assertEqual(set(primary_plan["member_reasons"]), set(primary_plan["pick_four"]))
        self.assertTrue(all(primary_plan["member_reasons"].values()))
        self.assertEqual(len(analysis.team_preview_plans), 1 + len(MODE_LABEL_ORDER))
        self.assertTrue(all(plan["recommended_into"] for plan in analysis.team_preview_plans[1:]))
        self.assertTrue(all(plan["label"].startswith("Into ") or "mirror plan" in plan["label"] for plan in analysis.team_preview_plans[1:]))
        anchored_plans = [plan for plan in analysis.team_preview_plans[1:] if len(plan["recommended_into"]) > 1]
        self.assertTrue(anchored_plans)
        self.assertTrue(all(plan["recommended_into"][1] in plan["summary"] for plan in anchored_plans))
        self.assertTrue(any(plan["recommended_into"][1] in " ".join(plan["member_reasons"].values()) for plan in anchored_plans))
        plan_signatures = {
            (tuple(sorted(plan["leads"])), tuple(sorted(plan["pick_four"])), tuple(plan["recommended_into"]))
            for plan in analysis.team_preview_plans
        }
        self.assertEqual(len(plan_signatures), len(analysis.team_preview_plans))
        self.assertTrue(
            any(
                tuple(sorted(plan["leads"])) != tuple(sorted(primary_plan["leads"]))
                or tuple(sorted(plan["pick_four"])) != tuple(sorted(primary_plan["pick_four"]))
                for plan in analysis.team_preview_plans[1:]
            )
        )
        primary_pick_four = set(primary_plan["pick_four"])
        self.assertTrue(
            any(
                len(primary_pick_four & set(plan["pick_four"])) <= 2
                for plan in analysis.team_preview_plans[1:]
            )
        )

        preview_payload = analysis.to_dict()["team_preview"]
        self.assertEqual(preview_payload["bring_plans"], analysis.team_preview_plans)
        self.assertEqual(preview_payload["watch_teams"], analysis.team_preview_watch_teams)
        self.assertEqual(preview_payload["watch_pokemon"], analysis.team_preview_watch_pokemon)

        covered_team_types = {plan["recommended_into"][0] for plan in analysis.team_preview_plans[1:]}
        self.assertEqual(
            covered_team_types,
            {_render_mode_label(mode_name) for mode_name in MODE_LABEL_ORDER},
        )

    def test_meta_analysis_reports_weighted_field_position(self) -> None:
        analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        self.assertIn(analysis.meta_analysis["label"], {"dominant", "strong", "solid", "fragile"})
        self.assertTrue(analysis.meta_analysis["strongest_modes"])
        self.assertTrue(analysis.meta_analysis["pressured_modes"])
        self.assertTrue(analysis.meta_analysis["strongest_targets"])
        self.assertTrue(analysis.meta_analysis["pressured_targets"])
        self.assertTrue(analysis.meta_analysis["weighted_matchups"])
        self.assertTrue(analysis.meta_analysis["tournament_rows"])
        self.assertTrue(analysis.meta_analysis["common_pokemon"])
        self.assertTrue(analysis.meta_analysis["notes"])
        self.assertGreater(analysis.meta_analysis["positive_weight_share"], 0)
        self.assertIn("Farigiraf Torkoal Room", analysis.meta_analysis["strongest_targets"])

        top_weighted_matchup = analysis.meta_analysis["weighted_matchups"][0]
        self.assertEqual(
            set(top_weighted_matchup),
            {
                "mode",
                "tournament_weight",
                "meta_share",
                "matchup_score",
                "impact_score",
                "identity_score",
                "standing",
            },
        )

        top_tournament_row = analysis.meta_analysis["tournament_rows"][0]
        self.assertEqual(
            set(top_tournament_row),
            {
                "slug",
                "label",
                "source",
                "result_label",
                "modes",
                "key_cores",
                "key_pokemon",
                "popularity_score",
                "result_score",
                "meta_weight",
                "meta_share",
                "contextual_score",
                "context_reasons",
                "target_summary",
                "interaction_summary",
                "matchup_score",
                "impact_score",
                "standing",
            },
        )
        self.assertTrue(top_tournament_row["key_cores"])
        self.assertTrue(top_tournament_row["key_pokemon"])
        self.assertTrue(top_tournament_row["context_reasons"])
        self.assertGreaterEqual(top_tournament_row["target_summary"]["resolved_targets"], 1)

        matchup_details = analysis.to_dict()["matchup_profile"]["details"]
        self.assertIn("trick_room", matchup_details)
        self.assertIsInstance(matchup_details["trick_room"]["contextual_adjustment"], float)
        self.assertTrue(matchup_details["trick_room"]["reasons"])

        top_common_pokemon = analysis.meta_analysis["common_pokemon"][0]
        self.assertEqual(
            set(top_common_pokemon),
            {"species", "meta_share", "why_used", "what_it_does", "featured_teams"},
        )
        self.assertTrue(top_common_pokemon["featured_teams"])

        common_meta_species = [entry["species"] for entry in analysis.meta_analysis["common_pokemon"]]
        self.assertIn("Sinistcha", common_meta_species)
        self.assertIn("Whimsicott", common_meta_species)

        sinistcha_entry = next(
            entry for entry in analysis.meta_analysis["common_pokemon"] if entry["species"] == "Sinistcha"
        )
        self.assertGreater(sinistcha_entry["meta_share"], 50)
        self.assertIn("healing", sinistcha_entry["why_used"].lower())
        self.assertIn("rage powder", sinistcha_entry["what_it_does"].lower())

        tournament_labels = {row["label"] for row in analysis.meta_analysis["tournament_rows"]}
        self.assertEqual(len(analysis.meta_analysis["tournament_rows"]), 8)
        self.assertIn("Venusaur Charizard Sun", tournament_labels)
        self.assertIn("Whimsicott Glimmora", tournament_labels)
        self.assertIn("Mega Venusaur Kommo-o", tournament_labels)
        self.assertIn("Vivillon Mega Blastoise", tournament_labels)
        self.assertIn("Sableye Archaludon Screens", tournament_labels)
        self.assertIn("Sand Garchomp Balance", tournament_labels)
        self.assertNotIn("Mega Gardevoir Tailroom", tournament_labels)
        self.assertNotIn("Mega Scizor Balance", tournament_labels)
        self.assertNotIn("Hydrapple Grassy Balance", tournament_labels)

        tournament_key_pokemon = {
            row["label"]: row["key_pokemon"] for row in analysis.meta_analysis["tournament_rows"]
        }
        self.assertGreaterEqual(len(tournament_key_pokemon["Venusaur Charizard Sun"]), 5)
        self.assertGreaterEqual(len(tournament_key_pokemon["Whimsicott Glimmora"]), 5)
        self.assertGreaterEqual(len(tournament_key_pokemon["Mega Venusaur Kommo-o"]), 5)
        self.assertGreaterEqual(len(tournament_key_pokemon["Vivillon Mega Blastoise"]), 5)
        self.assertGreaterEqual(len(tournament_key_pokemon["Sableye Archaludon Screens"]), 5)
        self.assertIn("Torkoal", tournament_key_pokemon["Venusaur Charizard Sun"])
        self.assertIn("Kingambit", tournament_key_pokemon["Whimsicott Glimmora"])
        self.assertIn("Incineroar", tournament_key_pokemon["Mega Venusaur Kommo-o"])
        self.assertIn("Pelipper", tournament_key_pokemon["Sableye Archaludon Screens"])
        self.assertIn("Whimsicott", tournament_key_pokemon["Vivillon Mega Blastoise"])

        payload = analysis.to_dict()["meta_analysis"]
        self.assertEqual(payload, analysis.meta_analysis)

    def test_snapshot_interaction_summary_credits_armor_tail_counterplay(self) -> None:
        class InteractionProvider:
            def __init__(self) -> None:
                self.species = {
                    "Tinkaton": SpeciesData("Tinkaton", "tinkaton", ("fairy", "steel"), 85, 75, 77, 70, 105, 94),
                    "Mega Manectric": SpeciesData("Mega Manectric", "manectric-mega", ("electric",), 70, 75, 80, 135, 80, 135),
                    "Pelipper": SpeciesData("Pelipper", "pelipper", ("water", "flying"), 60, 50, 100, 95, 70, 65),
                    "Archaludon": SpeciesData("Archaludon", "archaludon", ("steel", "dragon"), 90, 105, 130, 125, 65, 85),
                    "Farigiraf": SpeciesData("Farigiraf", "farigiraf", ("normal", "psychic"), 120, 90, 70, 110, 70, 60),
                }
                self.moves = {
                    "Fake Out": MoveData(
                        "Fake Out",
                        "fake-out",
                        "normal",
                        "physical",
                        effect_chance=100,
                        flinch_chance=100,
                        priority=3,
                        target_name="selected-pokemon",
                    ),
                    "Gigaton Hammer": MoveData("Gigaton Hammer", "gigaton-hammer", "steel", "physical"),
                    "Play Rough": MoveData("Play Rough", "play-rough", "fairy", "physical"),
                    "Thunder Wave": MoveData("Thunder Wave", "thunder-wave", "electric", "status"),
                    "Thunderbolt": MoveData("Thunderbolt", "thunderbolt", "electric", "special"),
                    "Volt Switch": MoveData("Volt Switch", "volt-switch", "electric", "special"),
                    "Snarl": MoveData("Snarl", "snarl", "dark", "special"),
                    "Protect": MoveData("Protect", "protect", "normal", "status", priority=4, target_name="user"),
                    "Tailwind": MoveData(
                        "Tailwind",
                        "tailwind",
                        "flying",
                        "status",
                        category_name="field-effect",
                        target_name="users-field",
                    ),
                    "Hydro Pump": MoveData("Hydro Pump", "hydro-pump", "water", "special"),
                    "Hurricane": MoveData("Hurricane", "hurricane", "flying", "special"),
                    "Electro Shot": MoveData("Electro Shot", "electro-shot", "electric", "special"),
                    "Draco Meteor": MoveData("Draco Meteor", "draco-meteor", "dragon", "special"),
                    "Flash Cannon": MoveData("Flash Cannon", "flash-cannon", "steel", "special"),
                }

            def get_species(self, species_name: str) -> SpeciesData:
                return self.species[species_name]

            def get_move(self, move_name: str) -> MoveData:
                return self.moves[move_name]

        provider = InteractionProvider()
        answer_team = [
            PokemonSet("Tinkaton", ["Fake Out", "Gigaton Hammer", "Play Rough", "Thunder Wave"], item="Mental Herb", ability="Mold Breaker", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Manectric", ["Thunderbolt", "Volt Switch", "Snarl", "Protect"], item="Manectite", ability="Lightning Rod", nature="Timid", evs={"SpA": 32, "Spe": 66}),
            PokemonSet("Pelipper", ["Tailwind", "Hydro Pump", "Hurricane", "Protect"], item="Focus Sash", ability="Drizzle", nature="Modest", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Archaludon", ["Electro Shot", "Draco Meteor", "Flash Cannon", "Protect"], item="Leftovers", ability="Stamina", nature="Modest", evs={"SpA": 66, "Spe": 66}),
        ]
        neutral_team = [
            PokemonSet("Tinkaton", ["Fake Out", "Gigaton Hammer", "Play Rough", "Thunder Wave"], item="Mental Herb", ability="Own Tempo", nature="Jolly", evs={"Atk": 66, "Spe": 66}),
            PokemonSet("Manectric", ["Thunderbolt", "Volt Switch", "Snarl", "Protect"], item="Manectite", ability="Lightning Rod", nature="Timid", evs={"SpA": 32, "Spe": 66}),
            PokemonSet("Pelipper", ["Tailwind", "Hydro Pump", "Hurricane", "Protect"], item="Focus Sash", ability="Drizzle", nature="Modest", evs={"SpA": 66, "Spe": 66}),
            PokemonSet("Archaludon", ["Electro Shot", "Draco Meteor", "Flash Cannon", "Protect"], item="Leftovers", ability="Stamina", nature="Modest", evs={"SpA": 66, "Spe": 66}),
        ]

        answer_members = _resolve_members(answer_team, provider, regulation_id=None)
        neutral_members = _resolve_members(neutral_team, provider, regulation_id=None)
        snapshot = next(
            entry for entry in get_tournament_team_snapshots(None) if entry["label"] == "Farigiraf Torkoal Room"
        )

        answer_summary = _build_snapshot_interaction_summary(snapshot, answer_members, provider, regulation_id=None)
        neutral_summary = _build_snapshot_interaction_summary(snapshot, neutral_members, provider, regulation_id=None)

        self.assertGreater(answer_summary.ability_clause_targets, 0)
        self.assertGreater(answer_summary.ability_clause_answers, neutral_summary.ability_clause_answers)
        self.assertIn("ability-aware counterplay", answer_summary.tags)

    def test_contextual_meta_analysis_respects_grassy_shell_pressure_points(self) -> None:
        analysis = analyze_team_text(
            load_example_team("realistic_grassy_terrain_team.txt"),
            metadata_provider=FakeMetadataProvider(),
            regulation_id=None,
        )

        tournament_rows = {
            row["label"]: row
            for row in analysis.meta_analysis["tournament_rows"]
        }

        self.assertGreater(
            tournament_rows["Rain Archaludon"]["matchup_score"],
            tournament_rows["Venusaur Charizard Sun"]["matchup_score"],
        )
        self.assertGreater(
            tournament_rows["Rain Archaludon"]["matchup_score"],
            tournament_rows["Mega Venusaur Kommo-o"]["matchup_score"],
        )
        self.assertLess(tournament_rows["Venusaur Charizard Sun"]["matchup_score"], 0.15)
        self.assertLess(tournament_rows["Mega Venusaur Kommo-o"]["matchup_score"], 0.15)
        self.assertTrue(tournament_rows["Venusaur Charizard Sun"]["context_reasons"])
        self.assertTrue(tournament_rows["Mega Venusaur Kommo-o"]["context_reasons"])
        self.assertTrue(
            any(
                label in {"Venusaur Charizard Sun", "Whimsicott Glimmora", "Mega Venusaur Kommo-o"}
                for label in analysis.meta_analysis["pressured_targets"]
            )
        )

    def test_team_preview_prefers_real_trick_room_and_specialized_win_condition_cores(self) -> None:
        provider = FakeMetadataProvider()
        trick_room_analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=provider, regulation_id=None)
        perish_analysis = analyze_team_text(PERISH_TRAP_TEAM, metadata_provider=provider, regulation_id=None)
        psyspam_analysis = analyze_team_text(PSYSPAM_TEAM, metadata_provider=provider, regulation_id=None)

        trick_room_plan = trick_room_analysis.team_preview_plans[0]
        trick_room_lead_roles = [
            set(trick_room_analysis.member_roles[member_name])
            for member_name in trick_room_plan["leads"]
        ]
        self.assertIn("Trick Room", trick_room_plan["label"])
        self.assertEqual(
            sum(1 for roles in trick_room_lead_roles if "trick_room_setter" in roles),
            1,
        )
        self.assertTrue(
            any(
                roles & {"fake_out_support", "redirector", "bulky_support"}
                for roles in trick_room_lead_roles
            )
        )

        perish_plan = perish_analysis.team_preview_plans[0]
        self.assertIn("Perish Trap", perish_plan["label"])
        self.assertIn("Mega Gengar", perish_plan["pick_four"])
        self.assertIn("Politoed", perish_plan["pick_four"])
        self.assertTrue(
            {"Sableye", "Sinistcha"} & set(perish_plan["pick_four"])
        )

        psyspam_plan = psyspam_analysis.team_preview_plans[0]
        self.assertIn("Psyspam", psyspam_plan["label"])
        self.assertIn("Indeedee-F", psyspam_plan["leads"])
        self.assertIn("Hatterene", psyspam_plan["pick_four"])
        self.assertTrue(
            any("Indeedee-F and Hatterene" in note for note in psyspam_analysis.team_preview_strategy_notes)
        )

    def test_team_preview_defaults_to_setup_support_core_for_setup_shells(self) -> None:
        analysis = analyze_team_text(SAMPLE_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        primary_plan = analysis.team_preview_plans[0]
        non_primary_summaries = [plan["summary"].lower() for plan in analysis.team_preview_plans[1:]]

        self.assertTrue(
            "Screens Offense" in primary_plan["label"] or "Setup Sweep" in primary_plan["label"]
        )
        self.assertIn("Sableye", primary_plan["leads"])
        self.assertTrue(
            {"Sableye", "Archaludon", "Lucario-Mega"}.issubset(set(primary_plan["pick_four"]))
        )
        self.assertTrue(
            any(
                "setup" in reason.lower() or "support" in reason.lower() or "screen" in reason.lower()
                for reason in primary_plan["member_reasons"].values()
            )
        )
        self.assertTrue(
            any(
                "disrupt" in summary or "stall out" in summary or "buy clean" in summary
                for summary in non_primary_summaries
            )
        )

    def test_team_preview_tailwind_summaries_keep_tailwind_language_with_utility_leads(self) -> None:
        analysis = analyze_team_text(TAILWIND_UTILITY_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)

        primary_plan = analysis.team_preview_plans[0]
        summary = primary_plan["summary"].lower()

        self.assertIn("Tailwind", primary_plan["label"])
        self.assertIn("Aerodactyl", primary_plan["leads"])
        self.assertIn("Gets Tailwind online immediately.", primary_plan["member_reasons"]["Aerodactyl"])
        self.assertTrue("tailwind online" in summary or "fast mode" in summary)
        self.assertNotIn("disrupt the opposing fast start", summary)

    def test_text_report_includes_utility_role_breakdown(self) -> None:
        analysis = analyze_team_text(ROLE_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)
        report = render_text_report(analysis.to_dict())

        self.assertIn("Speed profile:", report)
        self.assertIn("Benchmark notes:", report)
        self.assertIn("Team speed tier:", report)
        self.assertIn("Tier distribution:", report)
        self.assertIn("Members:", report)
        self.assertIn("Utility profile:", report)
        self.assertIn("Team archetype:", report)
        self.assertIn("Matchup profile:", report)
        self.assertIn("Meta mode profile:", report)
        self.assertIn("Meta analysis:", report)
        self.assertIn("Team difficulty:", report)
        self.assertIn("Team preview:", report)
        self.assertIn("Pokemon role profile:", report)
        self.assertIn("Member roles:", report)
        self.assertIn("Coverage gaps:", report)
        self.assertIn("Primary: Balance", report)
        self.assertIn("Favorable into:", report)
        self.assertIn("Team mode labels:", report)
        self.assertIn("Label:", report)
        self.assertIn("Builder guidance:", report)
        self.assertIn("Watch team:", report)
        self.assertIn("Ground: best 1.0x, 0 super-effective lines, 9 neutral-or-better lines", report)
        self.assertIn("Hazard Removal: 1 (Defog)", report)
        self.assertIn("Setup Sweeper: 1 (Volcarona)", report)
        self.assertIn("Tapu Koko: Cleaner, Pivot, Terrain Setter", report)

    def test_text_report_includes_meta_preview_context(self) -> None:
        analysis = analyze_team_text(TRICK_ROOM_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)
        report = render_text_report(analysis.to_dict())

        self.assertIn("Meta analysis:", report)
        self.assertIn("Standing:", report)
        self.assertIn("Weighted score:", report)
        self.assertIn("Farigiraf Torkoal Room", report)
        self.assertIn("Venusaur Charizard Sun", report)
        self.assertIn("Whimsicott Glimmora", report)
        self.assertIn("Mega Venusaur Kommo-o", report)
        self.assertIn("Vivillon Mega Blastoise", report)
        self.assertIn("Sableye Archaludon Screens", report)
        self.assertIn("Sand Garchomp Balance", report)
        self.assertNotIn("Mega Gardevoir Tailroom", report)
        self.assertNotIn("Mega Scizor Balance", report)
        self.assertNotIn("Hydrapple Grassy Balance", report)
        self.assertIn("Cores:", report)
        self.assertIn("Pokemon:", report)
        self.assertIn(
            "Pokemon: Pelipper, Archaludon, Basculegion, Sinistcha, Incineroar, and Scizor",
            report,
        )
        self.assertIn(
            "Pokemon: Mega Venusaur, Kommo O, Torkoal, Whimsicott, Sinistcha, and Incineroar",
            report,
        )
        self.assertIn("Recommended into:", report)
        self.assertIn("Into Rain", report)
        self.assertIn("Pressures common rain pieces with direct coverage.", report)


class MatchupReasonGatingTests(unittest.TestCase):
    """The phrase-bank bug: matchup reasons must not cite tools the team lacks."""

    NAMED_MOVE_TOOLS = ("Encore", "Fake Out", "Taunt", "Wide Guard", "Imprison")

    def test_fast_offense_tools_do_not_invent_encore_or_fake_out(self) -> None:
        # A Tailwind/anti-offense bonus driven only by priority must NOT name Encore/Fake Out.
        priority_only = _make_contextual_profile(priority_attacks=2)
        tools = _fast_offense_counter_tools(priority_only, include_protect=False)
        self.assertEqual(tools, ["priority"])
        self.assertNotIn("Encore", tools)
        self.assertNotIn("Fake Out", tools)
        # When the moves are actually on the team, they are named.
        with_moves = _make_contextual_profile(move_counts=Counter({"encore": 1, "fake-out": 1}))
        self.assertEqual(_fast_offense_counter_tools(with_moves, include_protect=False), ["Encore", "Fake Out"])

    def test_screen_tools_only_claim_item_control_when_present(self) -> None:
        no_item_control = _make_contextual_profile(strong_attackers=3)
        self.assertNotIn("item control", _screen_counter_tool_labels(no_item_control))
        with_knock_off = _make_contextual_profile(move_counts=Counter({"knock-off": 1}))
        self.assertIn("item control", _screen_counter_tool_labels(with_knock_off))

    def test_trick_room_and_setup_tools_gate_on_real_moves(self) -> None:
        intimidate_only = _make_contextual_profile(intimidate_support=1)
        tr_tools = _trick_room_counter_tool_labels(intimidate_only)
        self.assertEqual(tr_tools, ["Intimidate"])
        self.assertNotIn("Encore", tr_tools)
        self.assertNotIn("Taunt", tr_tools)

        priority_only = _make_contextual_profile(priority_attacks=1)
        setup_tools = _setup_counter_tool_labels(priority_only)
        self.assertEqual(setup_tools, ["priority"])
        self.assertNotIn("Encore", setup_tools)

    def test_broad_matchup_reasons_never_name_absent_moves(self) -> None:
        # Every counter bonus is maxed, but the bonuses come from priority alone and the
        # team runs NONE of the named disruption moves. No reason may invent them.
        profile = _make_contextual_profile(
            move_counts=Counter(),
            tailwind_counter_tools=3.0,
            trick_room_counter_tools=3.0,
            screen_counter_tools=3.0,
            setup_counter_tools=3.0,
            priority_attacks=2,
            bulky_members=2,
            slow_members=2,
            recovery_loop=2,
        )
        for archetype in ("hyper_offense", "bulky_offense", "balance", "semi_stall", "stall", "trick_room"):
            _, reasons = _score_broad_contextual_matchup(archetype, profile)
            for reason in reasons:
                for tool in self.NAMED_MOVE_TOOLS:
                    self.assertNotIn(
                        tool,
                        reason,
                        msg=f"{archetype} reason invented absent tool {tool!r}: {reason!r}",
                    )

        # Sanity: when the team actually runs Encore, the Trick Room reason names it.
        with_encore = _make_contextual_profile(
            move_counts=Counter({"encore": 1}),
            trick_room_counter_tools=3.0,
        )
        _, reasons = _score_broad_contextual_matchup("trick_room", with_encore)
        self.assertTrue(any("Encore" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()
