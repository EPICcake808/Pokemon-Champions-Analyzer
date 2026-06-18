from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pokemon_team_analyzer.analyzer import analyze_team_text
from pokemon_team_analyzer.champions_m_a_moves import get_allowed_moves_for_species
from pokemon_team_analyzer.cli import main as cli_main
from pokemon_team_analyzer.data import pokemon_name_candidates
from pokemon_team_analyzer.models import MoveData, MoveStatChange, PokemonSet, SpeciesData
from pokemon_team_analyzer.regulations import (
    CATALOG_DEFAULT_REGULATION_ID,
    DEFAULT_REGULATION_ID,
    IllegalTeamError,
    M_B_REGULATION_ID,
    get_regulation,
    regulation_catalog_as_dict,
    resolve_regulation_pokemon_set,
    resolve_regulation_species_name,
    validate_team_legality,
    validate_team_legality_text,
)
from pokemon_team_analyzer.showdown import parse_showdown_team


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

LEGAL_BARE_BASCULEGION_TEAM = """Incineroar @ Sitrus Berry
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

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave

Basculegion @ Mystic Water
Ability: Adaptability
- Wave Crash
- Last Respects
- Aqua Jet
- Protect
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

ILLEGAL_SPECIES_DUPLICATE_TEAM = """Incineroar @ Sitrus Berry
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

Garchomp @ Soft Sand
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Rock Slide

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

ILLEGAL_FORM_SPECIES_DUPLICATE_TEAM = """Ninetales @ Charcoal
Ability: Flash Fire
- Heat Wave
- Protect
- Will-O-Wisp
- Extrasensory

Ninetales (Alolan Form) @ Light Ball
Ability: Snow Warning
- Blizzard
- Protect
- Aurora Veil
- Freeze-Dry

Garchomp @ Soft Sand
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Rock Slide

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

ILLEGAL_MEGA_SPECIES_DUPLICATE_TEAM = """Charizard @ Charizardite Y
Ability: Blaze
- Heat Wave
- Air Slash
- Protect
- Solar Beam

Mega Charizard X @ Charizardite X
Ability: Tough Claws
- Heat Wave
- Air Slash
- Protect
- Solar Beam

Incineroar @ Sitrus Berry
Ability: Intimidate
- Fake Out
- Flare Blitz
- Parting Shot
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
- Earthquake
- Dragon Claw
- Protect
- Rock Slide

Corviknight @ Sharp Beak
Ability: Mirror Armor
- Tailwind
- Roost
- Body Press
- U-turn

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
    "Eternal Flower Floette": ("light-of-ruin", "moonblast", "protect"),
    "Farigiraf": ("dazzling-gleam", "helping-hand", "protect", "psychic", "trick-room"),
    "Florges": ("helping-hand", "misty-terrain", "moonblast", "protect"),
    "Garchomp": ("dragon-claw", "earthquake", "protect", "rock-slide", "stomping-tantrum", "swords-dance"),
    "Gengar": ("icy-wind", "perish-song", "protect", "shadow-ball", "sludge-bomb"),
    "Glimmora": ("earth-power", "power-gem", "sludge-wave", "stealth-rock"),
    "Hippowdon": ("protect", "sandstorm", "stomping-tantrum", "yawn"),
    "Hydrapple": ("dragon-pulse", "earth-power", "giga-drain", "grassy-terrain"),
    "Incineroar": ("fake-out", "flare-blitz", "knock-off", "parting-shot", "protect"),
    "Kingambit": ("iron-head", "kowtow-cleave", "protect", "sucker-punch"),
    "Milotic": ("icy-wind", "protect", "recover", "scald"),
    "Ninetales": ("extrasensory", "heat-wave", "protect", "will-o-wisp"),
    "Ninetales (Alolan Form)": ("aurora-veil", "blizzard", "freeze-dry", "protect"),
    "Basculegion (Male)": ("aqua-jet", "last-respects", "protect", "psychic-fangs", "wave-crash"),
    "Politoed": ("icy-wind", "perish-song", "protect", "whirlpool"),
    "Primarina": ("calm-mind", "hyper-voice", "misty-terrain", "moonblast", "protect"),
    "Rhyperior": ("protect", "rock-slide", "stomping-tantrum", "swords-dance"),
    "Roserade": ("giga-drain", "grassy-terrain", "protect", "sleep-powder", "sludge-bomb"),
    "Rotom (Wash Rotom)": ("hydro-pump", "protect", "thunderbolt", "will-o-wisp"),
    "Sableye": ("mean-look", "protect", "quash", "rain-dance", "reflect", "sunny-day"),
    "Scizor": ("bug-bite", "bullet-punch", "protect", "swords-dance", "u-turn"),
    "Sinistcha": ("grassy-terrain", "life-dew", "matcha-gotcha", "protect", "rage-powder", "strength-sap", "trick-room"),
    "Sneasler": ("close-combat", "dire-claw", "fake-out", "protect"),
    "Tinkaton": ("fake-out", "gigaton-hammer", "play-rough", "thunder-wave"),
    "Torkoal": ("earth-power", "eruption", "heat-wave", "protect"),
    "Torterra": ("grassy-terrain", "protect", "stomping-tantrum", "swords-dance", "wood-hammer"),
    "Tyranitar": ("knock-off", "protect", "rock-slide", "roar", "stealth-rock", "stone-edge"),
    "Venusaur": ("giga-drain", "growth", "protect", "sludge-bomb"),
    "Whimsicott": ("encore", "misty-terrain", "moonblast", "protect", "tailwind"),
    "Zoroark (Hisuian Form)": ("bitter-malice", "hyper-voice", "protect", "shadow-ball"),
}


def fake_get_allowed_moves_for_species(species_name: str) -> tuple[str, ...]:
    return MOCK_ALLOWED_MOVES_BY_SPECIES[species_name]


class ChampionsMetadataProvider:
    def __init__(self) -> None:
        self.species = {
            "Corviknight": SpeciesData("Corviknight", "corviknight", ("flying", "steel"), 98, 87, 105, 53, 85, 67),
            "Garchomp": SpeciesData("Garchomp", "garchomp", ("dragon", "ground"), 108, 130, 95, 80, 85, 102),
            "Gengar": SpeciesData("Gengar", "gengar", ("ghost", "poison"), 60, 65, 60, 130, 75, 110),
            "Mega Gengar": SpeciesData("Mega Gengar", "gengar-mega", ("ghost", "poison"), 60, 65, 80, 170, 95, 130),
            "Incineroar": SpeciesData("Incineroar", "incineroar", ("fire", "dark"), 95, 115, 90, 80, 90, 60),
            "Tinkaton": SpeciesData("Tinkaton", "tinkaton", ("fairy", "steel"), 85, 75, 77, 70, 105, 94),
            "Rotom (Wash Rotom)": SpeciesData(
                "Rotom (Wash Rotom)",
                "rotom-wash",
                ("electric", "water"),
                50,
                65,
                107,
                105,
                107,
                86,
            ),
            "Zoroark (Hisuian Form)": SpeciesData(
                "Zoroark (Hisuian Form)",
                "zoroark-hisui",
                ("normal", "ghost"),
                55,
                100,
                60,
                125,
                60,
                110,
            ),
        }
        self.moves = {
            "Bitter Malice": MoveData(
                "Bitter Malice",
                "bitter-malice",
                "ghost",
                "special",
                short_effect="May lower the target's Attack.",
                effect_chance=100,
                category_name="damage-lower",
                stat_chance=100,
                stat_changes=(MoveStatChange("attack", -1),),
                target_name="selected-pokemon",
            ),
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
            "Hyper Voice": MoveData("Hyper Voice", "hyper-voice", "normal", "special"),
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
            "Shadow Ball": MoveData("Shadow Ball", "shadow-ball", "ghost", "special"),
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

        regulation_ids = [regulation["id"] for regulation in payload]
        self.assertIn(DEFAULT_REGULATION_ID, regulation_ids)
        self.assertIn(M_B_REGULATION_ID, regulation_ids)
        self.assertIn("official", rendered)
        self.assertIn("eligible_pokemon_count", rendered)
        self.assertNotIn("team_text", rendered)

    def test_cli_can_emit_regulation_catalog_json_without_team_file(self) -> None:
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["--catalog-json"])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        # The UI loads the catalog default (M-B), while the engine fallback stays M-A.
        self.assertEqual(payload["default_regulation_id"], CATALOG_DEFAULT_REGULATION_ID)
        catalog_ids = [regulation["id"] for regulation in payload["regulations"]]
        self.assertIn(DEFAULT_REGULATION_ID, catalog_ids)
        self.assertIn(M_B_REGULATION_ID, catalog_ids)
        self.assertIn("display_name", payload["regulations"][0])

    def test_regulation_m_b_is_a_superset_of_m_a(self) -> None:
        m_a = get_regulation(DEFAULT_REGULATION_ID)
        m_b = get_regulation(M_B_REGULATION_ID)

        self.assertTrue(set(m_a.eligible_species).issubset(m_b.eligible_species))
        self.assertTrue(set(m_a.allowed_held_items).issubset(m_b.allowed_held_items))
        self.assertTrue(set(m_a.allowed_mega_evolutions).issubset(m_b.allowed_mega_evolutions))
        # M-B adds exactly its delta: 22 species, 16 megas, 15 items + 16 new mega stones.
        self.assertEqual(len(m_b.eligible_species) - len(m_a.eligible_species), 22)
        self.assertEqual(len(m_b.allowed_mega_evolutions) - len(m_a.allowed_mega_evolutions), 16)
        self.assertEqual(len(m_b.allowed_held_items) - len(m_a.allowed_held_items), 15 + 16)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=lambda name: ())
    def test_new_m_b_species_legal_in_m_b_only(self, _mock_moves: object) -> None:
        # Gholdengo is eligible in M-B but not M-A.
        team = [
            PokemonSet(species="Gholdengo", moves=[]),
            PokemonSet(species="Incineroar", moves=[]),
            PokemonSet(species="Garchomp", moves=[]),
            PokemonSet(species="Rotom-Wash", moves=[]),
            PokemonSet(species="Tinkaton", moves=[]),
            PokemonSet(species="Kingambit", moves=[]),
        ]

        m_a = validate_team_legality(team, regulation_id=DEFAULT_REGULATION_ID)
        self.assertFalse(m_a.is_legal)
        self.assertTrue(
            any(issue.code == "illegal_species" and issue.value == "Gholdengo" for issue in m_a.issues)
        )

        m_b = validate_team_legality(team, regulation_id=M_B_REGULATION_ID)
        self.assertTrue(m_b.is_legal, msg=[issue.message for issue in m_b.issues])

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=lambda name: ())
    def test_new_m_b_mega_and_stone_legal_in_m_b_only(self, _mock_moves: object) -> None:
        # Mega Staraptor + its verified Champions-original stone is legal only in M-B.
        team = [
            PokemonSet(species="Mega Staraptor", item="Staraptite", moves=[]),
            PokemonSet(species="Garchomp", moves=[]),
            PokemonSet(species="Rotom-Wash", moves=[]),
            PokemonSet(species="Tinkaton", moves=[]),
            PokemonSet(species="Kingambit", moves=[]),
            PokemonSet(species="Incineroar", moves=[]),
        ]

        m_a = validate_team_legality(team, regulation_id=DEFAULT_REGULATION_ID)
        self.assertFalse(m_a.is_legal)
        m_a_codes = {issue.code for issue in m_a.issues}
        self.assertIn("illegal_mega_species", m_a_codes)
        self.assertIn("illegal_item", m_a_codes)

        m_b = validate_team_legality(team, regulation_id=M_B_REGULATION_ID)
        self.assertTrue(m_b.is_legal, msg=[issue.message for issue in m_b.issues])

    @patch("pokemon_team_analyzer.cli.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    @patch("pokemon_team_analyzer.cli.CachedPokeApiClient")
    def test_cli_builder_species_accepts_legal_mega_form(
        self,
        mock_provider_factory: object,
        _mock_get_allowed_moves: object,
    ) -> None:
        mock_provider = mock_provider_factory.return_value
        mock_provider.get_species.return_value = SpeciesData(
            "Mega Scizor",
            "scizor-mega",
            ("bug", "steel"),
            70,
            150,
            140,
            65,
            100,
            75,
        )
        mock_provider.get_species_abilities.return_value = ("technician",)
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["--builder-species-json", "Mega Scizor", "--regulation", DEFAULT_REGULATION_ID])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["species"], "Mega Scizor")
        self.assertEqual(payload["types"], ["bug", "steel"])
        self.assertEqual(payload["abilities"], ["technician"])
        self.assertIn("bullet-punch", payload["moves"])
        self.assertEqual(payload["required_item"], "Scizorite")
        self.assertEqual(payload["base_stats"]["attack"], 150)

    @patch("pokemon_team_analyzer.cli.CachedPokeApiClient")
    def test_cli_builder_species_keeps_mega_specific_stats_for_custom_mega(
        self,
        mock_provider_factory: object,
    ) -> None:
        mock_provider = mock_provider_factory.return_value
        mock_provider.get_species.return_value = SpeciesData(
            "Mega Chimecho",
            "mega-chimecho",
            ("psychic",),
            75,
            50,
            110,
            135,
            120,
            65,
        )
        mock_provider.get_species_abilities.return_value = ("levitate",)
        stdout = StringIO()

        with patch(
            "pokemon_team_analyzer.cli.get_allowed_moves_for_species",
            side_effect=lambda species_name: ("heal-bell", "protect") if species_name == "Chimecho" else (),
        ):
            with redirect_stdout(stdout):
                exit_code = cli_main(["--builder-species-json", "Mega Chimecho", "--regulation", DEFAULT_REGULATION_ID])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["species"], "Mega Chimecho")
        self.assertEqual(payload["types"], ["psychic"])
        self.assertEqual(payload["base_stats"]["defense"], 110)
        self.assertEqual(payload["base_stats"]["special_attack"], 135)
        mock_provider.get_species.assert_called_once_with("Mega Chimecho")

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

    def test_pokeapi_name_candidates_cover_legal_forms(self) -> None:
        self.assertEqual(pokemon_name_candidates("Raichu (Alolan Form)")[0], "raichu-alola")
        self.assertEqual(pokemon_name_candidates("Arcanine (Hisuian Form)")[0], "arcanine-hisui")
        self.assertEqual(pokemon_name_candidates("Rotom (Heat Rotom)")[0], "rotom-heat")
        self.assertEqual(pokemon_name_candidates("Gourgeist (Jumbo Variety)")[0], "gourgeist-super")
        self.assertEqual(pokemon_name_candidates("Lycanroc (Dusk Form)")[0], "lycanroc-dusk")
        self.assertEqual(pokemon_name_candidates("Aegislash")[0], "aegislash-shield")
        self.assertEqual(pokemon_name_candidates("Meowstic (Female)")[0], "meowstic-female")
        self.assertEqual(pokemon_name_candidates("Maushold")[0], "maushold-family-of-four")
        self.assertEqual(pokemon_name_candidates("Palafin")[0], "palafin-zero")
        self.assertEqual(pokemon_name_candidates("Eternal Flower Floette")[0], "floette-eternal")
        self.assertEqual(
            pokemon_name_candidates("Tauros (Paldean Form (Combat Breed))")[0],
            "tauros-paldea-combat-breed",
        )

    def test_regulation_species_resolution_accepts_common_regional_aliases(self) -> None:
        self.assertEqual(resolve_regulation_species_name("Hisuian Zoroark"), "Zoroark (Hisuian Form)")
        self.assertEqual(resolve_regulation_species_name("Alolan Raichu"), "Raichu (Alolan Form)")
        self.assertEqual(resolve_regulation_species_name("Galarian Slowbro"), "Slowbro (Galarian Form)")
        self.assertEqual(resolve_regulation_species_name("Paldean Tauros Aqua"), "Tauros (Paldean Form (Aqua Breed))")
        self.assertEqual(resolve_regulation_species_name("Floette"), "Eternal Flower Floette")
        self.assertEqual(resolve_regulation_species_name("Floette-Eternal"), "Eternal Flower Floette")
        self.assertEqual(resolve_regulation_species_name("Mega Floette"), "Mega Eternal Flower Floette")

    def test_regulation_species_resolution_handles_gender_suffix_aliases(self) -> None:
        self.assertEqual(resolve_regulation_species_name("Tinkaton (F)"), "Tinkaton")
        self.assertEqual(resolve_regulation_species_name("Tinkaton (M)"), "Tinkaton")
        self.assertEqual(resolve_regulation_species_name("Meowstic (F)"), "Meowstic (Female)")
        self.assertEqual(resolve_regulation_species_name("Meowstic (M)"), "Meowstic (Male)")

    def test_regulation_species_resolution_accepts_palafin_hero_form_aliases(self) -> None:
        self.assertEqual(resolve_regulation_species_name("Palafin Hero"), "Palafin")
        self.assertEqual(resolve_regulation_species_name("Palafin (Hero Form)"), "Palafin")

    def test_regulation_species_resolution_accepts_gender_suffixed_mega_aliases(self) -> None:
        self.assertEqual(resolve_regulation_species_name("Manectric-Mega (M)"), "Mega Manectric")
        self.assertEqual(resolve_regulation_species_name("Mega Manectric (F)"), "Mega Manectric")

    def test_regulation_pokemon_set_upgrades_gender_suffixed_mega_species(self) -> None:
        team = parse_showdown_team(
            """Gardevoir (F) @ Gardevoirite
Ability: Trace
- Hyper Voice
- Protect
- Psychic
- Mystical Fire
"""
        )

        resolved_member = resolve_regulation_pokemon_set(team[0], regulation_id=DEFAULT_REGULATION_ID)

        self.assertEqual(resolved_member.species, "Mega Gardevoir")

    def test_validate_team_legality_accepts_gender_suffixed_mega_species_names(self) -> None:
        legality = validate_team_legality_text(
            """Manectric-Mega (M) @ Manectite
Ability: Intimidate
- Thunderbolt
- Protect
- Snarl
- Volt Switch
"""
        )

        issue_codes = [issue.code for issue in legality.issues]
        self.assertEqual(issue_codes, ["invalid_team_size"])

    def test_eternal_flower_floette_keeps_its_champions_move_pool(self) -> None:
        self.assertIn("light-of-ruin", get_allowed_moves_for_species("Eternal Flower Floette"))

    @patch("pokemon_team_analyzer.cli.CachedPokeApiClient")
    def test_cli_builder_species_canonicalizes_floette_to_eternal_flower_form(
        self,
        mock_provider_factory: object,
    ) -> None:
        mock_provider = mock_provider_factory.return_value
        mock_provider.get_species.return_value = SpeciesData(
            "Eternal Flower Floette",
            "floette-eternal",
            ("fairy",),
            74,
            65,
            67,
            125,
            128,
            92,
        )
        mock_provider.get_species_abilities.return_value = ("flower-veil", "symbiosis")
        stdout = StringIO()

        with patch(
            "pokemon_team_analyzer.cli.get_allowed_moves_for_species",
            side_effect=fake_get_allowed_moves_for_species,
        ):
            with redirect_stdout(stdout):
                exit_code = cli_main(["--builder-species-json", "Floette", "--regulation", DEFAULT_REGULATION_ID])

        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["species"], "Eternal Flower Floette")
        self.assertIn("light-of-ruin", payload["moves"])
        self.assertEqual(payload["base_stats"]["special_attack"], 125)
        mock_provider.get_species.assert_called_once_with("Eternal Flower Floette")

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_analysis_canonicalizes_common_regional_aliases_before_metadata_lookup(self, _mock_get_allowed_moves: object) -> None:
        alias_team = """Hisuian Zoroark @ Spell Tag
Ability: Illusion
- Hyper Voice
- Shadow Ball
- Protect
- Bitter Malice

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

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave
"""

        analysis = analyze_team_text(alias_team, metadata_provider=ChampionsMetadataProvider())

        self.assertEqual(analysis.team_size, 6)
        self.assertIn(analysis.team_archetype, analysis.team_archetype_scores)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_analysis_under_regulation_without_curated_speed_benchmarks_degrades(self, _mock_get_allowed_moves: object) -> None:
        # M-B has no curated speed benchmark catalog yet. Analysis must degrade gracefully
        # (every member still appears in the speed profile) rather than KeyError in to_dict.
        team = """Hisuian Zoroark @ Spell Tag
Ability: Illusion
- Hyper Voice
- Shadow Ball
- Protect
- Bitter Malice

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

Tinkaton @ Mental Herb
Ability: Mold Breaker
- Fake Out
- Gigaton Hammer
- Play Rough
- Thunder Wave
"""

        analysis = analyze_team_text(
            team,
            metadata_provider=ChampionsMetadataProvider(),
            regulation_id=M_B_REGULATION_ID,
        )
        payload = analysis.to_dict()

        self.assertEqual(payload["regulation_id"], M_B_REGULATION_ID)
        self.assertEqual(len(payload["speed_profile"]["members"]), 6)
        for member in payload["speed_profile"]["members"]:
            self.assertIn("benchmark_tags", member)

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_accepts_legal_m_a_team(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(LEGAL_MA_TEAM)

        self.assertTrue(legality.is_legal)
        self.assertEqual(legality.issues, ())

    def test_regulation_species_resolution_defaults_bare_gender_forms_to_male(self) -> None:
        self.assertEqual(resolve_regulation_species_name("Basculegion"), "Basculegion (Male)")
        self.assertEqual(resolve_regulation_species_name("Meowstic"), "Meowstic (Male)")

    @patch("pokemon_team_analyzer.regulations.get_allowed_moves_for_species", side_effect=fake_get_allowed_moves_for_species)
    def test_validate_team_legality_accepts_bare_basculegion(self, _mock_get_allowed_moves: object) -> None:
        legality = validate_team_legality_text(LEGAL_BARE_BASCULEGION_TEAM)

        self.assertTrue(legality.is_legal, msg=[issue.message for issue in legality.issues])
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
    def test_validate_team_legality_rejects_duplicate_species_clause(self, _mock_get_allowed_moves: object) -> None:
        exact_duplicate_legality = validate_team_legality_text(ILLEGAL_SPECIES_DUPLICATE_TEAM)
        form_duplicate_legality = validate_team_legality_text(ILLEGAL_FORM_SPECIES_DUPLICATE_TEAM)
        mega_duplicate_legality = validate_team_legality_text(ILLEGAL_MEGA_SPECIES_DUPLICATE_TEAM)

        self.assertFalse(exact_duplicate_legality.is_legal)
        self.assertIn("duplicate_species", {issue.code for issue in exact_duplicate_legality.issues})
        self.assertFalse(form_duplicate_legality.is_legal)
        self.assertIn("duplicate_species", {issue.code for issue in form_duplicate_legality.issues})
        self.assertFalse(mega_duplicate_legality.is_legal)
        self.assertIn("duplicate_species", {issue.code for issue in mega_duplicate_legality.issues})

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
    def test_analysis_rejects_duplicate_species_before_metadata_lookup(self, _mock_get_allowed_moves: object) -> None:
        with self.assertRaises(IllegalTeamError) as raised:
            analyze_team_text(ILLEGAL_FORM_SPECIES_DUPLICATE_TEAM, metadata_provider=ExplodingMetadataProvider())

        self.assertIn("duplicate_species", {issue.code for issue in raised.exception.legality.issues})

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