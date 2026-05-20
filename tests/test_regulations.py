from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pokemon_team_analyzer.analyzer import analyze_team_text
from pokemon_team_analyzer.cli import main as cli_main
from pokemon_team_analyzer.models import MoveData, MoveStatChange, SpeciesData
from pokemon_team_analyzer.regulations import (
    DEFAULT_REGULATION_ID,
    IllegalTeamError,
    get_regulation,
    regulation_catalog_as_dict,
    validate_team_legality_text,
)


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


LEGAL_MA_TEAM = """Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Garchomp @ Focus Sash
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Swords Dance

Rotom-Wash @ Leftovers
Ability: Levitate
- Thunderbolt
- Hydro Pump
- Will-O-Wisp
- Protect

Corviknight @ Sharp Beak
Ability: Mirror Armor
- Tailwind
- Roost
- Body Press
- U-turn

Gengar @ Gengarite
Ability: Cursed Body
- Shadow Ball
- Sludge Bomb
- Protect
- Icy Wind

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave
"""

ILLEGAL_SPECIES_TEAM = """Raging Bolt @ Leftovers
Ability: Protosynthesis
- Thunderclap
- Draco Meteor
- Calm Mind
- Protect

Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Garchomp @ Focus Sash
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Swords Dance

Rotom-Wash @ Leftovers
Ability: Levitate
- Thunderbolt
- Hydro Pump
- Will-O-Wisp
- Protect

Corviknight @ Sharp Beak
Ability: Mirror Armor
- Tailwind
- Roost
- Body Press
- U-turn

Gengar @ Gengarite
Ability: Cursed Body
- Shadow Ball
- Sludge Bomb
- Protect
- Icy Wind
"""

ILLEGAL_MEGA_TEAM = """Garchomp @ Gengarite
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Swords Dance

Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Rotom-Wash @ Leftovers
Ability: Levitate
- Thunderbolt
- Hydro Pump
- Will-O-Wisp
- Protect

Corviknight @ Sharp Beak
Ability: Mirror Armor
- Tailwind
- Roost
- Body Press
- U-turn

Gengar @ Focus Sash
Ability: Cursed Body
- Shadow Ball
- Sludge Bomb
- Protect
- Icy Wind

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave
"""

ILLEGAL_ITEM_DUPLICATE_TEAM = """Incineroar @ Assault Vest
Ability: Intimidate
- Fake Out
- Flare Blitz
- Knock Off
- Parting Shot

Garchomp @ Assault Vest
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Swords Dance

Rotom-Wash @ Leftovers
Ability: Levitate
- Thunderbolt
- Hydro Pump
- Will-O-Wisp
- Protect

Corviknight @ Sharp Beak
Ability: Mirror Armor
- Tailwind
- Roost
- Body Press
- U-turn

Gengar @ Gengarite
Ability: Cursed Body
- Shadow Ball
- Sludge Bomb
- Protect
- Icy Wind

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave
"""

ILLEGAL_MOVE_TEAM = """Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz
- Knock Off
- U-turn

Garchomp @ Focus Sash
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Swords Dance

Rotom-Wash @ Leftovers
Ability: Levitate
- Thunderbolt
- Hydro Pump
- Will-O-Wisp
- Protect

Corviknight @ Sharp Beak
Ability: Mirror Armor
- Tailwind
- Roost
- Body Press
- U-turn

Gengar @ Gengarite
Ability: Cursed Body
- Shadow Ball
- Sludge Bomb
- Protect
- Icy Wind

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave
"""

MOCK_ALLOWED_MOVES_BY_SPECIES = {
    "Abomasnow": ("blizzard", "giga-drain", "ice-shard", "protect"),
    "Aerodactyl": ("dual-wingbeat", "protect", "rock-slide", "tailwind", "wide-guard"),
    "Audino": ("heal-pulse", "helping-hand", "misty-terrain", "protect"),
    "Arcanine (Hisuian Form)": ("extreme-speed", "flare-blitz", "protect", "rock-slide"),
    "Charizard": ("air-slash", "heat-wave", "protect", "solar-beam"),
    "Corviknight": ("body-press", "protect", "roost", "tailwind", "u-turn"),
    "Farigiraf": ("dazzling-gleam", "helping-hand", "protect", "psychic", "trick-room"),
    "Florges": ("helping-hand", "misty-terrain", "moonblast", "protect"),
    "Garchomp": ("dragon-claw", "earthquake", "protect", "rock-slide", "stomping-tantrum", "swords-dance"),
    "Gengar": ("icy-wind", "perish-song", "protect", "shadow-ball", "sludge-bomb"),
    "Glimmora": ("earth-power", "power-gem", "sludge-wave", "stealth-rock"),
    "Hippowdon": ("protect", "sandstorm", "stomping-tantrum", "yawn"),
    "Hydrapple": ("dragon-pulse", "earth-power", "giga-drain", "grassy-terrain"),
    "Incineroar": ("fake-out", "flare-blitz", "knock-off", "parting-shot"),
    "Kingambit": ("iron-head", "kowtow-cleave", "protect", "sucker-punch"),
    "Milotic": ("icy-wind", "protect", "recover", "scald"),
    "Ninetales (Alolan Form)": ("aurora-veil", "blizzard", "freeze-dry", "protect"),
    "Politoed": ("icy-wind", "perish-song", "protect", "whirlpool"),
    "Primarina": ("calm-mind", "hyper-voice", "misty-terrain", "moonblast", "protect"),
    "Rhyperior": ("protect", "rock-slide", "stomping-tantrum", "swords-dance"),
    "Roserade": ("giga-drain", "grassy-terrain", "sleep-powder", "sludge-bomb"),
    "Rotom (Wash Rotom)": ("hydro-pump", "protect", "thunderbolt", "will-o-wisp"),
    "Sableye": ("mean-look", "protect", "quash", "rain-dance", "reflect", "sunny-day"),
    "Scizor": ("bug-bite", "bullet-punch", "protect", "swords-dance", "u-turn"),
    "Sinistcha": ("grassy-terrain", "life-dew", "matcha-gotcha", "protect", "rage-powder", "strength-sap", "trick-room"),
    "Sneasler": ("close-combat", "dire-claw", "fake-out", "protect"),
    "Tinkaton": ("fake-out", "gigaton-hammer", "play-rough", "thunder-wave"),
    "Torkoal": ("earth-power", "eruption", "heat-wave", "protect"),
    "Torterra": ("grassy-terrain", "protect", "stomping-tantrum", "wood-hammer"),
    "Tyranitar": ("knock-off", "protect", "rock-slide", "roar", "stealth-rock", "stone-edge"),
    "Venusaur": ("giga-drain", "growth", "protect", "sludge-bomb"),
}


def fake_get_allowed_moves_for_species(species_name: str) -> tuple[str, ...]:
    return MOCK_ALLOWED_MOVES_BY_SPECIES[species_name]


class ChampionsMetadataProvider:
    def __init__(self) -> None:
        self.species = {
            "Corviknight": SpeciesData("Corviknight", "corviknight", ("flying", "steel"), 98, 87, 105, 53, 85, 67),
            "Garchomp": SpeciesData("Garchomp", "garchomp", ("dragon", "ground"), 108, 130, 95, 80, 85, 102),
            "Gengar": SpeciesData("Gengar", "gengar", ("ghost", "poison"), 60, 65, 60, 130, 75, 110),
            "Incineroar": SpeciesData("Incineroar", "incineroar", ("fire", "dark"), 95, 115, 90, 80, 90, 60),
            "Rotom-Wash": SpeciesData("Rotom-Wash", "rotom-wash", ("electric", "water"), 50, 65, 107, 105, 107, 86),
            "Tinkaton": SpeciesData("Tinkaton", "tinkaton", ("fairy", "steel"), 85, 75, 77, 70, 105, 94),
        }
        self.moves = {
            "Body Press": MoveData("Body Press", "body-press", "fighting", "physical"),
            "Dragon Claw": MoveData("Dragon Claw", "dragon-claw", "dragon", "physical"),
            "Earthquake": MoveData("Earthquake", "earthquake", "ground", "physical"),
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
            "Flare Blitz": MoveData("Flare Blitz", "flare-blitz", "fire", "physical"),
            "Gigaton Hammer": MoveData("Gigaton Hammer", "gigaton-hammer", "steel", "physical"),
            "Hydro Pump": MoveData("Hydro Pump", "hydro-pump", "water", "special"),
            "Icy Wind": MoveData(
                "Icy Wind",
                "icy-wind",
                "ice",
                "special",
                short_effect="Lowers the target's Speed by one stage.",
                effect_chance=100,
                category_name="damage-lower",
                stat_chance=100,
                stat_changes=(MoveStatChange("speed", -1),),
                target_name="all-opponents",
            ),
            "Knock Off": MoveData(
                "Knock Off",
                "knock-off",
                "dark",
                "physical",
                short_effect="Target drops its held item.",
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
            "Play Rough": MoveData("Play Rough", "play-rough", "fairy", "physical"),
            "Protect": MoveData(
                "Protect",
                "protect",
                "normal",
                "status",
                short_effect="Prevents any moves from hitting the user this turn.",
                priority=4,
                target_name="user",
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
            "Shadow Ball": MoveData("Shadow Ball", "shadow-ball", "ghost", "special"),
            "Sludge Bomb": MoveData("Sludge Bomb", "sludge-bomb", "poison", "special"),
            "Swords Dance": MoveData(
                "Swords Dance",
                "swords-dance",
                "normal",
                "status",
                stat_changes=(MoveStatChange("attack", 2),),
                target_name="user",
            ),
            "Tailwind": MoveData(
                "Tailwind",
                "tailwind",
                "flying",
                "status",
                short_effect="For three turns, friendly Pokemon have doubled Speed.",
                category_name="field-effect",
                target_name="users-field",
            ),
            "Thunder Wave": MoveData(
                "Thunder Wave",
                "thunder-wave",
                "electric",
                "status",
                short_effect="Paralyzes the target.",
                ailment_name="paralysis",
                ailment_chance=100,
                target_name="selected-pokemon",
            ),
            "Thunderbolt": MoveData("Thunderbolt", "thunderbolt", "electric", "special"),
            "U-turn": MoveData(
                "U-turn",
                "u-turn",
                "bug",
                "physical",
                short_effect="User must switch out after attacking.",
                target_name="selected-pokemon",
            ),
            "Will-O-Wisp": MoveData(
                "Will-O-Wisp",
                "will-o-wisp",
                "fire",
                "status",
                short_effect="Burns the target.",
                ailment_name="burn",
                ailment_chance=100,
                target_name="selected-pokemon",
            ),
        }

    def get_species(self, species_name: str) -> SpeciesData:
        return self.species[species_name]

    def get_move(self, move_name: str) -> MoveData:
        return self.moves[move_name]


class ExplodingMetadataProvider:
    def get_species(self, species_name: str) -> SpeciesData:
        raise AssertionError(f"metadata lookup should not happen for illegal teams: {species_name}")

    def get_move(self, move_name: str) -> MoveData:
        raise AssertionError(f"move lookup should not happen for illegal teams: {move_name}")


class RegulationTests(unittest.TestCase):
    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_regulation_catalog_is_web_serializable(self, _mock_get_allowed_moves: object) -> None:
        payload = regulation_catalog_as_dict(include_team_text=False)
        rendered = json.dumps(payload)

        self.assertEqual(len(payload), 1)
        self.assertIn(DEFAULT_REGULATION_ID, rendered)
        self.assertIn("official", rendered)
        self.assertIn("eligible_pokemon_count", rendered)
        self.assertNotIn("team_text", rendered)

    def test_cli_can_emit_regulation_catalog_json_without_team_file(self) -> None:
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["--catalog-json"])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["default_regulation_id"], DEFAULT_REGULATION_ID)
        self.assertEqual(payload["regulations"][0]["id"], DEFAULT_REGULATION_ID)
        self.assertIn("display_name", payload["regulations"][0])

    @patch("pokemon_team_analyzer.cli.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    @patch("pokemon_team_analyzer.cli.CachedPokeApiClient")
    def test_cli_builder_species_accepts_legal_mega_form(
        self,
        mock_provider_factory: object,
        _mock_get_allowed_moves: object,
    ) -> None:
        mock_provider = mock_provider_factory.return_value
        mock_provider.get_species_abilities.return_value = ("technician",)
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["--builder-species-json", "Mega Scizor", "--regulation", DEFAULT_REGULATION_ID])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["species"], "Mega Scizor")
        self.assertEqual(payload["abilities"], ["technician"])
        self.assertIn("bullet-punch", payload["moves"])

    def test_regulation_m_a_metadata_tracks_official_sources(self) -> None:
        regulation = get_regulation(DEFAULT_REGULATION_ID)

        self.assertEqual(regulation.display_name, "Pokemon Champions Regulation M-A")
        self.assertTrue(regulation.is_official_champions_regulation)
        self.assertEqual(regulation.source_ruleset_name, "Pokemon Champions Regulation Set M-A")
        self.assertEqual(regulation.source_ruleset_url, "https://news.pokemon-home.com/en/page/751.html")
        self.assertGreater(len(regulation.eligible_species), 200)
        self.assertGreater(len(regulation.allowed_held_items), 100)
        self.assertEqual(len(regulation.allowed_mega_evolutions), 59)
        self.assertEqual(len(regulation.teams), 0)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_accepts_legal_m_a_team(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(LEGAL_MA_TEAM)

        self.assertTrue(legality.is_legal)
        self.assertEqual(legality.issues, ())

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_rejects_illegal_species_and_duplicate_items(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(ILLEGAL_SPECIES_TEAM)
        issue_codes = {issue.code for issue in legality.issues}

        self.assertFalse(legality.is_legal)
        self.assertIn("illegal_species", issue_codes)
        self.assertIn("duplicate_item", issue_codes)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_rejects_wrong_mega_stone_holder(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(ILLEGAL_MEGA_TEAM)
        issue_codes = {issue.code for issue in legality.issues}

        self.assertFalse(legality.is_legal)
        self.assertIn("illegal_mega_stone_holder", issue_codes)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_handles_duplicate_illegal_items(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(ILLEGAL_ITEM_DUPLICATE_TEAM)
        issue_codes = {issue.code for issue in legality.issues}

        self.assertFalse(legality.is_legal)
        self.assertIn("illegal_item", issue_codes)
        self.assertIn("duplicate_item", issue_codes)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_rejects_champions_illegal_move(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(ILLEGAL_MOVE_TEAM)
        issue_codes = {issue.code for issue in legality.issues}

        self.assertFalse(legality.is_legal)
        self.assertIn("illegal_move", issue_codes)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_analysis_rejects_illegal_team_before_metadata_lookup(self, _mock_get_allowed_moves: object) -> None:
        with self.assertRaises(IllegalTeamError) as raised:
            analyze_team_text(ILLEGAL_SPECIES_TEAM, metadata_provider=ExplodingMetadataProvider())

        self.assertIn("illegal_species", {issue.code for issue in raised.exception.legality.issues})

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_analysis_rejects_illegal_move_before_metadata_lookup(self, _mock_get_allowed_moves: object) -> None:
        with self.assertRaises(IllegalTeamError) as raised:
            analyze_team_text(ILLEGAL_MOVE_TEAM, metadata_provider=ExplodingMetadataProvider())

        self.assertIn("illegal_move", {issue.code for issue in raised.exception.legality.issues})

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_analysis_accepts_legal_m_a_team(self, _mock_get_allowed_moves: object) -> None:
        analysis = analyze_team_text(LEGAL_MA_TEAM, metadata_provider=ChampionsMetadataProvider())

        self.assertEqual(analysis.team_size, 6)
        self.assertIn(analysis.team_archetype, analysis.team_archetype_scores)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_curated_example_teams_are_legal_for_regulation_m_a(self, _mock_get_allowed_moves: object) -> None:
        for file_name in (
            "realistic_sand_team.txt",
            "realistic_hyper_offense_team.txt",
            "realistic_trick_room_team.txt",
            "realistic_perish_trap_team.txt",
            "realistic_grassy_terrain_team.txt",
            "realistic_misty_terrain_team.txt",
            "realistic_sand_room_team.txt",
            "realistic_snow_room_team.txt",
            "realistic_sun_tailroom_team.txt",
        ):
            with self.subTest(example=file_name):
                legality = validate_team_legality_text((EXAMPLES_DIR / file_name).read_text(encoding="utf-8"))
                self.assertTrue(legality.is_legal, msg=f"{file_name}: {[issue.message for issue in legality.issues]}")


if __name__ == "__main__":
    unittest.main()