from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from pokemon_team_analyzer.champions_m_a_tournament_meta import (
    TOURNAMENT_META_AS_OF,
    TOURNAMENT_TEAM_SNAPSHOTS,
)
from pokemon_team_analyzer.meta_snapshots import (
    BUILT_IN_META_SNAPSHOT_SOURCE_LABEL,
    build_built_in_meta_snapshot_feed,
    clear_runtime_meta_snapshot_cache,
    get_runtime_common_meta_pokemon,
    get_tournament_meta_provenance,
    get_tournament_team_snapshots,
)
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

    def test_built_in_meta_snapshot_feed_uses_current_curated_board(self) -> None:
        payload = build_built_in_meta_snapshot_feed()

        self.assertEqual(payload["version"], 1)
        self.assertIn("generatedAt", payload)
        regulations = payload["regulations"]
        self.assertEqual(len(regulations), 1)

        document = regulations[0]
        self.assertEqual(document["regulationId"], DEFAULT_REGULATION_ID)
        self.assertEqual(document["sourceLabel"], BUILT_IN_META_SNAPSHOT_SOURCE_LABEL)
        self.assertEqual(document["tournamentTeamSnapshots"][0]["slug"], TOURNAMENT_TEAM_SNAPSHOTS[0]["slug"])
        self.assertIsInstance(document["tournamentTeamSnapshots"][0]["modes"], list)


class MetaProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_runtime_meta_snapshot_cache()

    def tearDown(self) -> None:
        clear_runtime_meta_snapshot_cache()

    def test_built_in_provenance_carries_as_of_and_sources(self) -> None:
        provenance = get_tournament_meta_provenance(DEFAULT_REGULATION_ID)
        self.assertEqual(provenance["as_of"], TOURNAMENT_META_AS_OF)
        self.assertFalse(provenance["is_live"])
        self.assertTrue(provenance["methodology"])
        sources = provenance["sources"]
        self.assertTrue(sources)
        self.assertTrue(all(source.get("url", "").startswith("http") for source in sources))

    def test_live_snapshot_provenance_uses_published_updated_at(self) -> None:
        runtime_payload = {
            "regulationId": DEFAULT_REGULATION_ID,
            "updatedAt": "2026-06-10T12:00:00Z",
            "sourceLabel": "Live published meta snapshot",
            "tournamentTeamSnapshots": [
                {
                    "slug": "live-shell",
                    "label": "Live Shell",
                    "source": "Live source",
                    "result_label": "recent top cut",
                    "field_relevance": 0.9,
                    "popularity_weight": 0.8,
                    "result_weight": 0.85,
                    "modes": ["tailwind"],
                    "mode_weights": {"tailwind": 1.0},
                    "broad_mix": {"hyper_offense": 1.0},
                    "key_pokemon": ["dragapult"],
                    "key_cores": ["Dragapult core"],
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
                return_value=_DummyHttpResponse(runtime_payload),
            ):
                get_tournament_team_snapshots(DEFAULT_REGULATION_ID)
                provenance = get_tournament_meta_provenance(DEFAULT_REGULATION_ID)

        self.assertEqual(provenance["as_of"], "2026-06-10T12:00:00Z")
        self.assertTrue(provenance["is_live"])
        # A feed without commonMetaPokemon is live but not usage-based.
        self.assertFalse(provenance["usage_based"])


def _usage_feed_payload() -> dict[str, object]:
    return {
        "regulationId": DEFAULT_REGULATION_ID,
        "updatedAt": "2026-06-12T09:00:00Z",
        "sourceLabel": "Automated multi-source board",
        "commonMetaPokemon": [
            {
                "species": "Incineroar",
                "metaShare": 41.2,
                "whyUsed": "Safest glue piece.",
                "whatItDoes": "Fake Out, Intimidate, pivot.",
                "featuredTeams": ["Incineroar Sinistcha Trick Room"],
                "usagePercent": 41.2,
                "teamCount": 73,
                "sampleSize": 177,
            },
            {
                "species": "Basculegion",
                "metaShare": 37.6,
                "whyUsed": "Rain cleaner.",
                "whatItDoes": "Wave Crash, Last Respects.",
                "featuredTeams": ["Basculegion Garchomp Tailwind"],
            },
        ],
        "tournamentTeamSnapshots": [
            {
                "slug": "live-shell",
                "label": "Live Shell",
                "source": "Limitless tournament results",
                "result_label": "tournament winner",
                "field_relevance": 0.9,
                "popularity_weight": 0.8,
                "result_weight": 0.85,
                "modes": ["rain"],
                "mode_weights": {"rain": 1.0},
                "broad_mix": {"bulky_offense": 1.0},
                "key_pokemon": ["basculegion", "archaludon"],
                "key_cores": ["Basculegion + Archaludon"],
            }
        ],
        "provenance": {
            "sampleSize": 177,
            "authoritativeSource": {
                "name": "Limitless",
                "url": "https://play.limitlesstcg.com/tournaments/completed?game=VGC",
            },
            "sources": [
                {"name": "Pikalytics", "url": "https://www.pikalytics.com/", "available": True},
                {"name": "Pokemon Zone", "url": "https://www.pokemon-zone.com/champions/", "available": False},
            ],
        },
    }


class RuntimeUsageMetaTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_runtime_meta_snapshot_cache()

    def tearDown(self) -> None:
        clear_runtime_meta_snapshot_cache()

    def _with_feed(self, fn):
        with patch.dict(
            os.environ,
            {"POKEMON_ANALYZER_META_SNAPSHOT_URL": "https://example.com/api/meta-snapshot"},
            clear=False,
        ):
            with patch(
                "pokemon_team_analyzer.meta_snapshots.urlopen",
                return_value=_DummyHttpResponse(_usage_feed_payload()),
            ):
                return fn()

    def test_runtime_common_meta_pokemon_normalized_to_row_shape(self) -> None:
        rows = self._with_feed(lambda: get_runtime_common_meta_pokemon(DEFAULT_REGULATION_ID))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["species"], "Incineroar")
        self.assertEqual(rows[0]["meta_share"], 41.2)
        self.assertEqual(rows[0]["why_used"], "Safest glue piece.")
        self.assertEqual(rows[0]["featured_teams"], ["Incineroar Sinistcha Trick Room"])
        # camelCase feed keys must not leak into the analyzer row shape.
        self.assertNotIn("metaShare", rows[0])

    def test_provenance_is_usage_based_with_sample_size_and_sources(self) -> None:
        def run():
            get_tournament_team_snapshots(DEFAULT_REGULATION_ID)
            return get_tournament_meta_provenance(DEFAULT_REGULATION_ID)

        provenance = self._with_feed(run)
        self.assertTrue(provenance["usage_based"])
        self.assertEqual(provenance["sample_size"], 177)
        self.assertTrue(provenance["is_live"])
        self.assertIn("usage", provenance["methodology"].lower())
        labels = [source["label"] for source in provenance["sources"]]
        self.assertIn("Limitless", labels)
        # Unavailable sources are marked so the UI does not imply they were used.
        self.assertTrue(any("unavailable" in label.lower() for label in labels))

    def test_analyzer_common_meta_pokemon_prefers_real_usage(self) -> None:
        from pokemon_team_analyzer.analyzer import _build_common_meta_pokemon

        rows = self._with_feed(lambda: _build_common_meta_pokemon(DEFAULT_REGULATION_ID))
        self.assertEqual([row["species"] for row in rows], ["Incineroar", "Basculegion"])
        self.assertEqual(rows[0]["meta_share"], 41.2)

    def test_analyzer_falls_back_to_board_share_without_feed(self) -> None:
        from pokemon_team_analyzer.analyzer import _build_common_meta_pokemon

        # No POKEMON_ANALYZER_META_SNAPSHOT_URL -> derive board share from curated shells.
        rows = _build_common_meta_pokemon(DEFAULT_REGULATION_ID)
        self.assertTrue(rows)
        self.assertIn("meta_share", rows[0])


if __name__ == "__main__":
    unittest.main()