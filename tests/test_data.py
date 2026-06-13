from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pokemon_team_analyzer.data import CachedPokeApiClient, _deserialize_species_data


class StubbedPokeApiClient(CachedPokeApiClient):
    def __init__(self, cache_path: Path, responses: dict[str, dict[str, object]]) -> None:
        self._responses = responses
        super().__init__(cache_path=cache_path)

    def _fetch_json(self, path: str) -> dict[str, object]:
        return self._responses[path]


class CachedMoveRefreshTests(unittest.TestCase):
    def test_get_move_refreshes_incomplete_cached_stat_change_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "pokeapi_cache.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "pokemon": {},
                        "move": {
                            "calm-mind": {
                                "name": "Calm Mind",
                                "api_name": "calm-mind",
                                "type_name": "psychic",
                                "damage_class": "status",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            client = StubbedPokeApiClient(
                cache_path=cache_path,
                responses={
                    "move/calm-mind": {
                        "name": "calm-mind",
                        "type": {"name": "psychic"},
                        "damage_class": {"name": "status"},
                        "effect_entries": [
                            {
                                "language": {"name": "en"},
                                "short_effect": "Raises the user's Sp. Atk and Sp. Def by 1.",
                            }
                        ],
                        "effect_chance": None,
                        "meta": {
                            "category": {"name": "net-good-stats"},
                            "ailment": {"name": "none"},
                            "ailment_chance": 0,
                            "flinch_chance": 0,
                            "healing": 0,
                            "stat_chance": 0,
                        },
                        "stat_changes": [
                            {"stat": {"name": "special-attack"}, "change": 1},
                            {"stat": {"name": "special-defense"}, "change": 1},
                        ],
                        "priority": 0,
                        "target": {"name": "user"},
                    }
                },
            )

            move = client.get_move("Calm Mind")

            self.assertEqual(move.api_name, "calm-mind")
            self.assertEqual(move.target_name, "user")
            self.assertEqual(move.short_effect, "Raises the user's Sp. Atk and Sp. Def by 1.")
            self.assertEqual(len(move.stat_changes), 2)

            refreshed_cache = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertIn("target_name", refreshed_cache["move"]["calm-mind"])
            self.assertIn("stat_changes", refreshed_cache["move"]["calm-mind"])

    def test_get_move_refreshes_incomplete_cached_healing_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "pokeapi_cache.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "pokemon": {},
                        "move": {
                            "life-dew": {
                                "name": "Life Dew",
                                "api_name": "life-dew",
                                "type_name": "water",
                                "damage_class": "status",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            client = StubbedPokeApiClient(
                cache_path=cache_path,
                responses={
                    "move/life-dew": {
                        "name": "life-dew",
                        "type": {"name": "water"},
                        "damage_class": {"name": "status"},
                        "effect_entries": [
                            {
                                "language": {"name": "en"},
                                "short_effect": "The user and its allies restore 25% of their max HP.",
                            }
                        ],
                        "effect_chance": None,
                        "meta": {
                            "category": {"name": "heal"},
                            "ailment": {"name": "none"},
                            "ailment_chance": 0,
                            "flinch_chance": 0,
                            "healing": 25,
                            "stat_chance": 0,
                        },
                        "stat_changes": [],
                        "priority": 0,
                        "target": {"name": "user-and-allies"},
                    }
                },
            )

            move = client.get_move("Life Dew")

            self.assertEqual(move.api_name, "life-dew")
            self.assertEqual(move.healing, 25)
            self.assertEqual(move.target_name, "user-and-allies")
            self.assertIn("restore 25%", move.short_effect)

            refreshed_cache = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(refreshed_cache["move"]["life-dew"]["healing"], 25)
            self.assertEqual(refreshed_cache["move"]["life-dew"]["target_name"], "user-and-allies")

    def test_get_move_handles_null_meta_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "pokeapi_cache.json"
            cache_path.write_text(json.dumps({"pokemon": {}, "move": {}}), encoding="utf-8")
            client = StubbedPokeApiClient(
                cache_path=cache_path,
                responses={
                    "move/electro-shot": {
                        "name": "electro-shot",
                        "type": {"name": "electric"},
                        "damage_class": {"name": "special"},
                        "effect_entries": [
                            {
                                "language": {"name": "en"},
                                "short_effect": "Charges on the first turn and attacks on the second.",
                            }
                        ],
                        "effect_chance": None,
                        "meta": None,
                        "stat_changes": [],
                        "priority": 0,
                        "target": {"name": "selected-pokemon"},
                    }
                },
            )

            move = client.get_move("Electro Shot")

            self.assertEqual(move.api_name, "electro-shot")
            self.assertEqual(move.category_name, "unknown")
            self.assertEqual(move.ailment_name, "none")
            self.assertEqual(move.healing, 0)
            self.assertEqual(move.target_name, "selected-pokemon")

    def test_get_move_falls_back_to_flavor_text_when_effect_entries_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "pokeapi_cache.json"
            cache_path.write_text(json.dumps({"pokemon": {}, "move": {}}), encoding="utf-8")
            client = StubbedPokeApiClient(
                cache_path=cache_path,
                responses={
                    "move/electro-shot": {
                        "name": "electro-shot",
                        "type": {"name": "electric"},
                        "damage_class": {"name": "special"},
                        "effect_entries": [],
                        "flavor_text_entries": [
                            {
                                "language": {"name": "en"},
                                "version_group": {"name": "scarlet-violet"},
                                "flavor_text": (
                                    "The user gathers electricity on the first turn, boosting its Sp. Atk stat, "
                                    "then fires a high-voltage shot on the next turn. The shot will be fired immediately in rain."
                                ),
                            }
                        ],
                        "effect_chance": None,
                        "meta": None,
                        "stat_changes": [{"stat": {"name": "special-attack"}, "change": 1}],
                        "priority": 0,
                        "target": {"name": "selected-pokemon"},
                        "power": 130,
                        "accuracy": 100,
                        "pp": 10,
                    }
                },
            )

            move = client.get_move("Electro Shot")

            self.assertIn("first turn", move.short_effect)
            self.assertIn("immediately in rain", move.short_effect)
            self.assertEqual(move.power, 130)
            self.assertEqual(move.target_name, "selected-pokemon")

    def test_get_move_refreshes_cached_blank_short_effect_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "pokeapi_cache.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "pokemon": {},
                        "move": {
                            "electro-shot": {
                                "name": "Electro Shot",
                                "api_name": "electro-shot",
                                "type_name": "electric",
                                "damage_class": "special",
                                "power": 130,
                                "accuracy": 100,
                                "pp": 10,
                                "short_effect": "",
                                "effect_chance": None,
                                "category_name": "unknown",
                                "ailment_name": "none",
                                "ailment_chance": 0,
                                "flinch_chance": 0,
                                "healing": 0,
                                "stat_chance": 0,
                                "stat_changes": [],
                                "priority": 0,
                                "target_name": "selected-pokemon",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            client = StubbedPokeApiClient(
                cache_path=cache_path,
                responses={
                    "move/electro-shot": {
                        "name": "electro-shot",
                        "type": {"name": "electric"},
                        "damage_class": {"name": "special"},
                        "effect_entries": [],
                        "flavor_text_entries": [
                            {
                                "language": {"name": "en"},
                                "version_group": {"name": "scarlet-violet"},
                                "flavor_text": "Charges on the first turn and fires immediately in rain.",
                            }
                        ],
                        "effect_chance": None,
                        "meta": None,
                        "stat_changes": [],
                        "priority": 0,
                        "target": {"name": "selected-pokemon"},
                        "power": 130,
                        "accuracy": 100,
                        "pp": 10,
                    }
                },
            )

            move = client.get_move("Electro Shot")

            self.assertEqual(move.short_effect, "Charges on the first turn and fires immediately in rain.")
            refreshed_cache = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(
                refreshed_cache["move"]["electro-shot"]["short_effect"],
                "Charges on the first turn and fires immediately in rain.",
            )


class ChampionsStatOverrideTests(unittest.TestCase):
    def test_rebalanced_species_use_champions_stats_not_mainline(self) -> None:
        # PokeAPI serves mainline stats; the analyzer must serve Champions values.
        mainline_alakazam = {
            "name": "Alakazam",
            "api_name": "alakazam",
            "types": ("psychic",),
            "base_hp": 55,
            "base_attack": 50,
            "base_defense": 45,
            "base_special_attack": 135,
            "base_special_defense": 95,
            "base_speed": 120,
        }
        species = _deserialize_species_data(mainline_alakazam)
        # Champions: 175 Special Attack, 150 Speed (Serebii Champions dex).
        self.assertEqual(species.base_special_attack, 175)
        self.assertEqual(species.base_speed, 150)
        # Untouched stats keep their PokeAPI values.
        self.assertEqual(species.base_hp, 55)
        self.assertEqual(species.base_defense, 45)

    def test_non_rebalanced_species_keep_pokeapi_stats(self) -> None:
        mainline_garchomp = {
            "name": "Garchomp",
            "api_name": "garchomp",
            "types": ("dragon", "ground"),
            "base_hp": 108,
            "base_attack": 130,
            "base_defense": 95,
            "base_special_attack": 80,
            "base_special_defense": 85,
            "base_speed": 102,
        }
        species = _deserialize_species_data(mainline_garchomp)
        self.assertEqual(species.base_speed, 102)
        self.assertEqual(species.base_attack, 130)


if __name__ == "__main__":
    unittest.main()