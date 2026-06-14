import unittest

from pokemon_team_analyzer.champions_m_a_data import ELIGIBLE_SPECIES
from pokemon_team_analyzer.champions_m_a_moves import get_allowed_moves_for_species
from pokemon_team_analyzer.regulations import resolve_builder_option_source_species_name
from pokemon_team_analyzer.slot_doctor import analyze_slots

# A fast, disruption-less squad: should flag Trick Room (with a legal move-swap) and setup.
FAST_TEAM = """Dragapult @ Choice Specs
Ability: Clear Body
Nature: Timid
EVs: 32 SpA / 32 Spe
- Shadow Ball
- Draco Meteor
- Flamethrower
- Thunderbolt

Garchomp @ Life Orb
Ability: Rough Skin
Nature: Jolly
EVs: 32 Atk / 32 Spe
- Earthquake
- Dragon Claw
- Stone Edge
- Stomping Tantrum

Greninja @ Mystic Water
Ability: Torrent
Nature: Timid
EVs: 32 SpA / 32 Spe
- Hydro Pump
- Ice Beam
- Dark Pulse
- Grass Knot
"""

_ELIGIBLE = set(ELIGIBLE_SPECIES)


class SlotDoctorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = analyze_slots(FAST_TEAM, regulation_id=None)

    def test_structure_and_cap(self):
        self.assertTrue(self.result["ok"])
        self.assertLessEqual(len(self.result["gaps"]), 3)
        self.assertEqual(len(self.result["team"]), 3)

    def test_detects_trick_room_with_legal_move_swap(self):
        tr_gap = next((gap for gap in self.result["gaps"] if gap["id"] == "trick_room"), None)
        self.assertIsNotNone(tr_gap, "fast disruption-less team should fold to Trick Room")
        self.assertTrue(tr_gap["move_swaps"], "expected at least one concrete move swap")
        # Every suggested swap must be a real legal move for that member.
        team_species = {"Dragapult", "Garchomp", "Greninja"}
        for swap in tr_gap["move_swaps"]:
            self.assertIn(swap["member"], team_species)
            source = resolve_builder_option_source_species_name(swap["member"])
            legal = {move.lower() for move in get_allowed_moves_for_species(source)}
            self.assertIn(swap["move"].lower(), legal)

    def test_all_replacements_are_legal_species(self):
        for gap in self.result["gaps"]:
            for replacement in gap["replacements"]:
                species = replacement["species"]
                if species is not None:
                    self.assertIn(species, _ELIGIBLE)

    def test_empty_team_raises(self):
        with self.assertRaises(ValueError):
            analyze_slots("", regulation_id=None)


if __name__ == "__main__":
    unittest.main()
