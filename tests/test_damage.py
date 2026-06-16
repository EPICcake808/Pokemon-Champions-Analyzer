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

    def test_type_boost_item_matches_move_type(self):
        # Soft Sand gives a legal 1.2x base-power boost to Ground moves.
        move = _move("Test Quake", "ground", "physical", 100)
        attacker = _attacker(types=("bug",), item="Soft Sand")
        result = compute_damage(attacker, _defender(), move)
        assert result is not None
        # base power 100 -> 120; base = ((22*120*200)//100)//50+2 = 107, rolls 90..107.
        self.assertEqual(result.min_damage, 90)
        self.assertEqual(result.max_damage, 107)
        # A modeled item must not be reported back as unmodeled.
        self.assertEqual(result.unmodeled, ())

    def test_type_boost_item_ignores_other_types(self):
        # Soft Sand does nothing for a non-Ground move, but is still recognised.
        attacker = _attacker(types=("bug",), item="Soft Sand")
        result = compute_damage(attacker, _defender(), self.NEUTRAL_MOVE)
        assert result is not None
        self.assertEqual(result.min_damage, 76)
        self.assertEqual(result.max_damage, 90)
        self.assertEqual(result.unmodeled, ())

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


class SandSnowDefensiveBoostTests(unittest.TestCase):
    """Sand gives Rock defenders 1.5x SpDef; snow gives Ice defenders 1.5x Def (Gen 9)."""

    # Psychic is neutral on Rock; Normal is neutral on Ice -- keeps type_eff at 1.0 with no STAB.
    SPECIAL_MOVE = _move("Test Beam", "psychic", "special", 100)
    PHYSICAL_MOVE = _move("Test Strike", "normal", "physical", 100)

    def test_sand_boosts_rock_special_defense(self):
        rock = _defender(types=("rock",))
        baseline = compute_damage(_attacker(), rock, self.SPECIAL_MOVE)
        sand = compute_damage(_attacker(), rock, self.SPECIAL_MOVE, FieldConditions(weather="sand"))
        assert baseline is not None and sand is not None
        # SpDef 100 -> 150, so base drops from 90 (76..90) to 60 (51..60).
        self.assertEqual((baseline.min_damage, baseline.max_damage), (76, 90))
        self.assertEqual((sand.min_damage, sand.max_damage), (51, 60))

    def test_sand_does_not_boost_physical_or_non_rock(self):
        # Sand only touches SpDef, so a physical hit is unchanged...
        rock_physical = compute_damage(
            _attacker(types=("bug",)), _defender(types=("rock",)), self.PHYSICAL_MOVE,
            FieldConditions(weather="sand"),
        )
        baseline_physical = compute_damage(
            _attacker(types=("bug",)), _defender(types=("rock",)), self.PHYSICAL_MOVE,
        )
        assert rock_physical is not None and baseline_physical is not None
        self.assertEqual(rock_physical.max_damage, baseline_physical.max_damage)
        # ...and a non-Rock special target gets nothing either.
        non_rock = compute_damage(
            _attacker(), _defender(types=("normal",)), self.SPECIAL_MOVE,
            FieldConditions(weather="sand"),
        )
        assert non_rock is not None
        self.assertEqual(non_rock.max_damage, 90)

    def test_snow_boosts_ice_defense(self):
        ice = _defender(types=("ice",))
        baseline = compute_damage(_attacker(types=("bug",)), ice, self.PHYSICAL_MOVE)
        snow = compute_damage(
            _attacker(types=("bug",)), ice, self.PHYSICAL_MOVE, FieldConditions(weather="snow"),
        )
        assert baseline is not None and snow is not None
        # Def 100 -> 150, so base drops from 90 (76..90) to 60 (51..60).
        self.assertEqual((baseline.min_damage, baseline.max_damage), (76, 90))
        self.assertEqual((snow.min_damage, snow.max_damage), (51, 60))

    def test_snow_does_not_boost_special_or_non_ice(self):
        ice_special = compute_damage(
            _attacker(), _defender(types=("ice",)), self.SPECIAL_MOVE,
            FieldConditions(weather="snow"),
        )
        assert ice_special is not None
        self.assertEqual(ice_special.max_damage, 90)


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


class AssumptionDisclosureTests(unittest.TestCase):
    """Variable-power and field-dependent rolls must disclose their assumptions (#11)."""

    def test_variable_power_move_discloses_assumption(self):
        last_respects = _move("Last Respects", "ghost", "physical", 50)
        result = compute_damage(_attacker(types=("ghost",)), _defender(), last_respects)
        assert result is not None
        self.assertTrue(
            any("Last Respects" in note and "50 BP" in note for note in result.assumptions),
            msg=f"expected a Last Respects BP assumption, got {result.assumptions}",
        )

    def test_field_conditions_are_disclosed(self):
        move = _move("Test Strike", "normal", "physical", 100)
        field = FieldConditions(spread=True, crit=True, attacker_burned=True)
        result = compute_damage(_attacker(types=("bug",)), _defender(), move, field)
        assert result is not None
        joined = " ".join(result.assumptions)
        self.assertIn("Spread move", joined)
        self.assertIn("Critical hit", joined)
        self.assertIn("burned", joined)

    def test_exact_move_has_no_spurious_assumptions(self):
        move = _move("Test Strike", "normal", "physical", 100)
        result = compute_damage(_attacker(types=("bug",)), _defender(), move)
        assert result is not None
        self.assertEqual(result.assumptions, ())

    def test_light_screen_reduces_special_and_is_disclosed(self):
        move = _move("Test Beam", "normal", "special", 100)
        plain = compute_damage(_attacker(types=("bug",)), _defender(), move)
        screened = compute_damage(
            _attacker(types=("bug",)), _defender(), move, FieldConditions(light_screen=True)
        )
        assert plain is not None and screened is not None
        self.assertLess(screened.max_damage, plain.max_damage)
        self.assertTrue(any("Light Screen" in note for note in screened.assumptions))


if __name__ == "__main__":
    unittest.main()
