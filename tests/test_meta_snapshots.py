from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from pokemon_team_analyzer.champions_m_a_tournament_meta import TOURNAMENT_TEAM_SNAPSHOTS
from pokemon_team_analyzer.meta_snapshots import clear_runtime_meta_snapshot_cache, get_tournament_team_snapshots
from pokemon_team_analyzer.regulations import DEFAULT_REGULATION_ID


class _DummyHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_DummyHttpResponse":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> bool:
        return False


class RuntimeMetaSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_runtime_meta_snapshot_cache()

    def tearDown(self) -> None:
        clear_runtime_meta_snapshot_cache()

    def test_runtime_meta_snapshot_fetch_overrides_built_in_board(self) -> None:
        payload = {
            "regulationId": DEFAULT_REGULATION_ID,
            "sourceLabel": "Automated daily board",
            "tournamentTeamSnapshots": [
                {
                    "slug": "runtime-shell",
                    "label": "Runtime Shell",
                    "source": "External feed",
                    "result_label": "daily refresh",
                    "field_relevance": 0.95,
                    "popularity_weight": 0.8,
                    "result_weight": 0.9,
                    "modes": ["tailwind"],
                    "mode_weights": {"tailwind": 1.0},
                    "broad_mix": {"hyper_offense": 0.7, "bulky_offense": 0.3},
                    "key_pokemon": ["whimsicott", "garchomp", "kingambit"],
                    "key_cores": ["Whimsicott + Garchomp"],
                }
            ],
        }

        with patch.dict(
            os.environ,
            {"POKEMON_ANALYZER_META_SNAPSHOT_URL": "https://example.com/api/meta-snapshot"},
            clear=False,
        ):
            with patch(
                "pokemon_team_analyzer.meta_snapshots.urlopen",
                return_value=_DummyHttpResponse(payload),
            ) as mocked_urlopen:
                snapshots = get_tournament_team_snapshots(DEFAULT_REGULATION_ID)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["slug"], "runtime-shell")
        self.assertEqual(snapshots[0]["modes"], ("tailwind",))
        self.assertEqual(snapshots[0]["key_pokemon"], ("whimsicott", "garchomp", "kingambit"))
        request = mocked_urlopen.call_args.args[0]
        self.assertIn(f"regulationId={DEFAULT_REGULATION_ID}", request.full_url)

    def test_runtime_meta_snapshot_failure_falls_back_to_built_in_board(self) -> None:
        with patch.dict(
            os.environ,
            {"POKEMON_ANALYZER_META_SNAPSHOT_URL": "https://example.com/api/meta-snapshot"},
            clear=False,
        ):
            with patch(
                "pokemon_team_analyzer.meta_snapshots.urlopen",
                side_effect=OSError("unreachable"),
            ):
                snapshots = get_tournament_team_snapshots(DEFAULT_REGULATION_ID)

        self.assertEqual(snapshots, TOURNAMENT_TEAM_SNAPSHOTS)


if __name__ == "__main__":
    unittest.main()