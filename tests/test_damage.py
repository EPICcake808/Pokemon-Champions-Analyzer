import unittest

from pokemon_team_analyzer.damage import (
    Combatant,
    FieldConditions,
    compute_damage,
)
from pokemon_team_analyzer.damage_benchmarks import build_damage_matchups
from pokemon_team_analyzer.models import MoveData, SpeciesData


def _move(
    name: str,
    type_name: str,
    damage_class: str,
    power: int | None,
    *,
    target_name: str = "selected-pokemon",
) -> MoveData:
    return MoveData(
        name=name,
        api_name=name.lower().replace(" ", "-"),
        type_name=type_name,
        damage_class=damage_class,
        power=power,
        target_name=target_name,
    )


def _attacker(**overrides) -> Combatant:
    base = dict(
        species="Tester",
        types=("normal",),
        hp=150,
        attack=200,
        defense=100,
        special_attack=200,
        special_defense=100,
    )
    base.update(overrides)
    return Combatant(**base)


def _defender(**overrides) -> Combatant:
    base = dict(
        species="Dummy",
        types=("normal",),
        hp=150,
        attack=100,
        defense=100,
        special_attack=100,
        special_defense=100,
    )
    base.update(overrides)
    return Combatant(**base)


class DamageFormulaTests(unittest.TestCase):
    """Hand-verified golden numbers for the Gen 9 formula at level 50.

    Reference scenario: Attack 200 into Defense 100 with a 100-BP move yields a base
    damage of ((22 * 100 * 200) // 100) // 50 + 2 = 90, so the unmodified roll spread
    is floor(90 * (85+i)/100) = 76..90.
    """

    NEUTRAL_MOVE = _move("Test Strike", "normal", "physical", 100)

    def test_neutral_no_modifiers(self):
        # Bug-type attacker using a Normal move -> no STAB.
        result = compute_damage(_attacker(types=("bug",)), _defender(), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertEqual(result.min_damage, 76)
        self.assertEqual(result.max_damage, 90)
        self.assertEqual(len(result.rolls), 16)
        self.assertEqual(result.type_multiplier, 1.0)
        self.assertEqual(result.stab, 1.0)

    def test_stab_one_point_five(self):
        attacker = _attacker(types=("normal",))
        result = compute_damage(attacker, _defender(), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertEqual(result.stab, 1.5)
        self.assertEqual(result.min_damage, 114)
        self.assertEqual(result.max_damage, 135)

    def test_adaptability_doubles_stab(self):
        attacker = _attacker(types=("normal",), ability="Adaptability")
        result = compute_damage(attacker, _defender(), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertEqual(result.stab, 2.0)
        # base 90 -> *2.0 STAB: 76->152, 90->180
        self.assertEqual(result.min_damage, 152)
        self.assertEqual(result.max_damage, 180)

    def test_super_effective(self):
        # Fighting (no STAB here) into a normal-type defender = 2x.
        move = _move("Test Chop", "fighting", "physical", 100)
        result = compute_damage(_attacker(types=("bug",)), _defender(), move)
        assert result is not None
        self.assertEqual(result.type_multiplier, 2.0)
        self.assertEqual(result.min_damage, 152)
        self.assertEqual(result.max_damage, 180)

    def test_spread_reduction(self):
        result = compute_damage(
            _attacker(types=("bug",)),
            _defender(),
            self.NEUTRAL_MOVE,
            FieldConditions(spread=True),
        )
        assert result is not None
        # base 90 -> pokeRound(90*0.75)=67 (half rounds down) -> 56..67
        self.assertEqual(result.min_damage, 56)
        self.assertEqual(result.max_damage, 67)

    def test_life_orb_final_modifier(self):
        attacker = _attacker(types=("bug",), item="Life Orb")
        result = compute_damage(attacker, _defender(), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertEqual(result.min_damage, 99)
        self.assertEqual(result.max_damage, 117)

    def test_choice_band_boosts_physical(self):
        attacker = _attacker(types=("bug",), item="Choice Band")
        result = compute_damage(attacker, _defender(), self.NEUTRAL_MOVE)
        assert result is not None
        # Attack 200 -> *1.5 = 300, base = ((22*100*300)//100)//50+2 = 134, rolls 113..134
        self.assertEqual(result.min_damage, 113)
        self.assertEqual(result.max_damage, 134)

    def test_ability_type_immunity(self):
        move = _move("Test Quake", "ground", "physical", 100)
        result = compute_damage(_attacker(types=("bug",)), _defender(ability="Levitate"), move)
        assert result is not None
        self.assertEqual(result.max_damage, 0)
        self.assertTrue(result.summary.lower().startswith("no damage"))
        self.assertFalse(result.possible_ohko)

    def test_type_chart_immunity(self):
        # Normal into Ghost = 0x.
        result = compute_damage(_attacker(types=("bug",)), _defender(types=("ghost",)), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertEqual(result.type_multiplier, 0.0)
        self.assertEqual(result.max_damage, 0)
        self.assertEqual(set(result.rolls), {0})

    def test_status_move_returns_none(self):
        move = _move("Test Glare", "normal", "status", None)
        self.assertIsNone(compute_damage(_attacker(), _defender(), move))

    def test_ko_flags(self):
        # Defender with low HP -> guaranteed OHKO.
        result = compute_damage(_attacker(types=("bug",)), _defender(hp=70), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertTrue(result.guaranteed_ohko)
        self.assertEqual(result.summary, "Guaranteed OHKO")


class SunHeatWaveSurvivalTests(unittest.TestCase):
    """The headline example: a bulky Steel/Dragon survives a sun-boosted spread Heat Wave."""

    def test_archaludon_survives_sun_heat_wave(self):
        heat_wave = _move("Heat Wave", "fire", "special", 95, target_name="all-opponents")
        charizard_y = Combatant(
            species="Charizard-Mega-Y",
            types=("fire", "flying"),
            hp=153,
            attack=110,
            defense=130,
            special_attack=200,
            special_defense=130,
            ability="Drought",
            item=None,
        )
        archaludon = Combatant(
            species="Archaludon",
            types=("steel", "dragon"),
            hp=175,
            attack=120,
            defense=130,
            special_attack=150,
            special_defense=130,
            ability="Stamina",
            item=None,
        )
        result = compute_damage(
            charizard_y,
            archaludon,
            heat_wave,
            FieldConditions(weather="sun", spread=True),
        )
        assert result is not None
        # Fire is neutral into Steel/Dragon (2x * 0.5x = 1x).
        self.assertEqual(result.type_multiplier, 1.0)
        self.assertFalse(result.possible_ohko, "Archaludon should survive even the high roll")
        self.assertLess(result.max_percent, 100.0)
        self.assertGreater(result.min_percent, 0.0)


class _FakeProvider:
    """Knows a couple of benchmark entries; everything else raises (skipped gracefully)."""

    SPECIES = {
        "Sinistcha": SpeciesData("Sinistcha", "sinistcha", ("grass", "ghost"), 71, 60, 106, 121, 80, 70),
        "Charizard-Mega-Y": SpeciesData(
            "Charizard-Mega-Y", "charizard-mega-y", ("fire", "flying"), 78, 104, 78, 159, 115, 100
        ),
    }
    MOVES = {
        "Heat Wave": MoveData("Heat Wave", "heat-wave", "fire", "special", 95, target_name="all-opponents"),
    }

    def get_species(self, name: str) -> SpeciesData:
        if name not in self.SPECIES:
            raise LookupError(name)
        return self.SPECIES[name]

    def get_move(self, name: str) -> MoveData:
        if name not in self.MOVES:
            raise LookupError(name)
        return self.MOVES[name]


class DamageGridTests(unittest.TestCase):
    def test_grid_populates_and_skips_unresolved(self):
        member = Combatant(
            species="Dragapult",
            types=("dragon", "ghost"),
            hp=155,
            attack=150,
            defense=95,
            special_attack=150,
            special_defense=95,
        )
        moves = (
            _move("Shadow Ball", "ghost", "special", 80),
            _move("Dragon Darts", "dragon", "physical", 50),
        )
        grid = build_damage_matchups([(member, moves)], _FakeProvider())
        self.assertIn("Leftovers Sinistcha", grid["benchmark_walls"])
        self.assertIn("Sun Mega Charizard Y Heat Wave", grid["benchmark_attackers"])
        # Unresolved benchmarks (Archaludon, Garchomp, ...) are skipped, not errored.
        self.assertNotIn("Bulky Archaludon", grid["benchmark_walls"])
        self.assertTrue(grid["outgoing"])
        self.assertTrue(grid["incoming"])


if __name__ == "__main__":
    unittest.main()
