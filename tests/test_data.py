from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pokemon_team_analyzer.data import CachedPokeApiClient


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


if __name__ == "__main__":
    unittest.main()