from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from pokemon_team_analyzer.meta_ingest import build, discover, reconcile, schema, usage
from pokemon_team_analyzer.meta_ingest.sources import SourceUsage
from pokemon_team_analyzer.meta_ingest.sources import limitless, limitlessvgc, pikalytics, pokemon_zone
from pokemon_team_analyzer.meta_ingest.sources.limitless import Roster, Tournament

_FIXTURES = Path(__file__).parent / "fixtures"
_TOURNAMENTS = json.loads((_FIXTURES / "limitless_tournaments.json").read_text())
_STANDINGS = json.loads((_FIXTURES / "limitless_standings.json").read_text())
_PIKALYTICS_HTML = (_FIXTURES / "pikalytics_leaderboard.html").read_text()
_LVGC_LISTING_HTML = (_FIXTURES / "limitlessvgc_listing.html").read_text()
_LVGC_STANDINGS_HTML = (_FIXTURES / "limitlessvgc_standings.html").read_text()

# A fixed "now" so the date-window filter in list_tournaments is deterministic.
_NOW = datetime(2026, 6, 13, tzinfo=UTC)


def _fake_get_json(url, **_kwargs):
    if "/tournaments?" in url:
        # Single page of results; an empty page stops pagination.
        return _TOURNAMENTS if "page=1" in url else []
    if "/standings" in url:
        return _STANDINGS
    raise AssertionError(f"unexpected URL {url}")


def _make_roster(tokens, placing, tournament=None):
    tournament = tournament or Tournament(id="t1", name="Event", date="2026-06-12T00:00:00Z", format="M-A", players=20)
    decklist = [{"id": t, "name": t, "item": "", "ability": "", "attacks": ["Protect", "Tackle"]} for t in tokens]
    return Roster(
        tournament=tournament,
        player="p",
        placing=placing,
        record_text="1-0-0",
        species_tokens=tuple(tokens),
        showdown_text="",
        decklist=decklist,
    )


class SpeciesTokenTests(unittest.TestCase):
    def test_mega_resolution_from_item(self):
        self.assertEqual(limitless.species_token({"id": "lucario", "name": "Lucario", "item": "Lucarionite"}), "lucario-mega")
        self.assertEqual(limitless.species_token({"id": "charizard", "name": "Charizard", "item": "Charizardite Y"}), "charizard-mega-y")
        self.assertEqual(limitless.species_token({"id": "charizard", "name": "Charizard", "item": "Charizardite X"}), "charizard-mega-x")
        self.assertEqual(limitless.species_token({"id": "gyarados", "name": "Gyarados", "item": "Gyaradosite"}), "gyarados-mega")

    def test_special_floette_mega_matches_catalog(self):
        token = limitless.species_token({"id": "floette-eternal", "name": "Eternal Flower Floette", "item": "Floettite"})
        self.assertEqual(token, "floette-mega")

    def test_non_mega_and_forms_passthrough(self):
        self.assertEqual(limitless.species_token({"id": "basculegion", "name": "Basculegion", "item": "Choice Scarf"}), "basculegion")
        self.assertEqual(limitless.species_token({"id": "arcanine-hisui", "name": "Hisuian Arcanine", "item": "Focus Sash"}), "arcanine-hisui")

    def test_held_non_matching_stone_does_not_mega_tag(self):
        # A Pokémon that is not the stone's species keeps its base token.
        self.assertEqual(limitless.species_token({"id": "garchomp", "name": "Garchomp", "item": "Lucarionite"}), "garchomp")

    def test_render_showdown_text_includes_item_ability_moves(self):
        text = limitless.render_showdown_text(_STANDINGS[0]["decklist"])
        self.assertIn("Pelipper @ Focus Sash", text)
        self.assertIn("Ability: Drizzle", text)
        self.assertIn("- Tailwind", text)


class LimitlessListingTests(unittest.TestCase):
    def test_list_filters_by_format_size_and_window(self):
        with patch.object(limitless, "get_json", _fake_get_json):
            tournaments = limitless.list_tournaments(since_days=30, min_players=8, now=_NOW)
        ids = [t.id for t in tournaments]
        self.assertEqual(ids, ["aaa111", "bbb222"])  # M-A, >=8 players, within window
        # ccc333 (wrong format), ddd444 (too small), eee555 (out of window) excluded.

    def test_fetch_rosters_parses_tokens_and_skips_empty_decklists(self):
        tournament = Tournament(id="aaa111", name="CROWN", date="2026-06-12T16:20:00Z", format="M-A", players=47)
        with patch.object(limitless, "get_json", _fake_get_json):
            rosters = limitless.fetch_rosters(tournament)
        self.assertEqual(len(rosters), 2)  # the empty-decklist entry is skipped
        self.assertIn("charizard-mega-y", rosters[0].species_tokens)
        self.assertIn("basculegion", rosters[0].species_tokens)
        self.assertEqual(rosters[0].placing, 1)

    def test_collect_rosters_aggregates_window(self):
        with patch.object(limitless, "get_json", _fake_get_json):
            rosters, tournaments, warnings = limitless.collect_rosters(since_days=30, min_players=8, now=_NOW)
        self.assertEqual(len(tournaments), 2)
        self.assertEqual(len(rosters), 4)  # 2 rosters per tournament
        self.assertEqual(warnings, [])


class UsageTests(unittest.TestCase):
    def test_raw_usage_is_share_of_teams(self):
        rosters = [
            _make_roster(["incineroar", "basculegion", "kingambit", "sinistcha"], placing=1),
            _make_roster(["incineroar", "garchomp", "whimsicott", "sneasler"], placing=8),
            _make_roster(["incineroar", "basculegion", "torkoal", "venusaur"], placing=20),
        ]
        report = usage.compute_usage(rosters, tournament_count=2, since_days=30)
        by_token = {entry.token: entry for entry in report.entries}
        self.assertEqual(report.sample_size, 3)
        self.assertEqual(by_token["incineroar"].team_count, 3)
        self.assertEqual(by_token["incineroar"].raw_usage_pct, 100.0)
        self.assertAlmostEqual(by_token["basculegion"].raw_usage_pct, 66.7, places=1)
        self.assertEqual(report.entries[0].token, "incineroar")  # sorted by weighted desc

    def test_base_species_collapse_unifies_mega_and_floette(self):
        self.assertEqual(usage.base_species_token("charizard-mega-y"), "charizard")
        self.assertEqual(usage.base_species_token("gengar-mega"), "gengar")
        # platform floette-mega and official floette-eternal must collapse to one token
        self.assertEqual(usage.base_species_token("floette-mega"), "floette-eternal")
        self.assertEqual(usage.base_species_token("floette-eternal"), "floette-eternal")
        # a mega-token roster and a base-token roster count as the same species
        report = usage.compute_usage(
            [
                _make_roster(["charizard-mega-y", "garchomp", "whimsicott", "sneasler"], 1),
                _make_roster(["charizard", "incineroar", "kingambit", "sinistcha"], 2),
            ],
            tournament_count=1,
            since_days=30,
        )
        by_token = {e.token: e for e in report.entries}
        self.assertEqual(by_token["charizard"].team_count, 2)
        self.assertNotIn("charizard-mega-y", by_token)

    def test_official_tier_outweighs_larger_online_event(self):
        official = Tournament(id="o1", name="Regional X", date="2026-06-01T00:00:00Z",
                              format="M-A", players=300, tier="regional", source="limitlessvgc")
        online_big = Tournament(id="g1", name="Big Online", date="2026-06-10T00:00:00Z",
                                format="M-A", players=6000, tier="online", source="limitless")
        self.assertGreater(usage.tier_weight(official), usage.tier_weight(online_big))
        # A species seen only at the regional outranks one seen only at the bigger online event.
        report = usage.compute_usage(
            [
                _make_roster(["kingambit", "garchomp", "incineroar", "sinistcha"], 1, tournament=official),
                _make_roster(["whimsicott", "torkoal", "venusaur", "aerodactyl"], 1, tournament=online_big),
            ],
            tournament_count=2,
            since_days=30,
        )
        by_token = {e.token: e for e in report.entries}
        self.assertGreater(by_token["kingambit"].weighted_usage_pct, by_token["whimsicott"].weighted_usage_pct)
        self.assertEqual(report.official_count, 1)
        # The top entry is a species from the heavily-weighted regional team.
        self.assertIn(report.entries[0].token, {"kingambit", "garchomp", "incineroar", "sinistcha"})


class DiscoverModeInferenceTests(unittest.TestCase):
    def test_rain_from_drizzle_ability(self):
        modes, _ = discover.infer_modes(_STANDINGS[0]["decklist"])
        self.assertIn("rain", modes[0] + " " + " ".join(modes))

    def test_trick_room_and_tailwind_compose(self):
        decklist = [
            {"ability": "Hospitality", "attacks": ["Trick Room", "Matcha Gotcha"]},
            {"ability": "Prankster", "attacks": ["Tailwind", "Moonblast"]},
        ]
        modes, scores = discover.infer_modes(decklist)
        self.assertEqual(modes[0], "tailroom")
        self.assertIn("trick_room", scores)
        self.assertIn("tailwind", scores)

    def test_always_returns_a_mode(self):
        modes, _ = discover.infer_modes([{"ability": "", "attacks": ["Tackle"]}])
        self.assertEqual(modes, ["dual_mode"])

    def test_two_megas_flag_dual_mode_without_displacing_primary(self):
        # Reg M-A allows one mega per battle, so two mega stones = a functional dual-mode
        # team; dual_mode rides along as a secondary while the real primary mode stays.
        decklist = [
            {"ability": "", "attacks": ["Tailwind", "Protect"]},
            {"ability": "", "attacks": ["Earthquake"]},
        ]
        modes, scores = discover.infer_modes(decklist, mega_count=2)
        self.assertEqual(modes[0], "tailwind")
        self.assertIn("dual_mode", scores)
        # A single mega is not a dual-mode tell.
        _, single = discover.infer_modes(decklist, mega_count=1)
        self.assertNotIn("dual_mode", single)


class DiscoverClusteringTests(unittest.TestCase):
    def test_similar_teams_cluster_into_valid_snapshot(self):
        tour = Tournament(id="aaa111", name="CROWN", date="2026-06-12T16:20:00Z", format="M-A", players=47)
        # Two near-identical rain shells (5/6 species shared) should merge.
        base = ["pelipper", "archaludon", "basculegion", "incineroar", "sinistcha"]
        rosters = [
            Roster(tour, "a", 1, "8-0-0", tuple(base + ["charizard-mega-y"]),
                   "", [{"ability": "Drizzle", "attacks": ["Tailwind"]}] + [{"ability": "", "attacks": ["Surf"]}] * 5),
            Roster(tour, "b", 2, "7-1-0", tuple(base + ["lucario-mega"]),
                   "", [{"ability": "Drizzle", "attacks": ["Tailwind"]}] + [{"ability": "", "attacks": ["Surf"]}] * 5),
        ]
        result = discover.discover_shells(rosters)
        self.assertEqual(result.clusters_formed, 1)
        snapshot = result.snapshots[0]
        # Required schema fields present and internally consistent.
        self.assertGreaterEqual(len(snapshot["key_cores"]), 1)
        self.assertTrue(set(snapshot["modes"]) <= set(snapshot["mode_weights"]))
        self.assertIn("basculegion", snapshot["key_pokemon"])
        self.assertEqual(snapshot["result_label"], "winner")  # grassroots winner
        self.assertFalse(snapshot["is_official"])

    def test_dual_mega_team_anchors_each_mega_in_its_own_core(self):
        tour = Tournament(id="dm1", name="CROWN", date="2026-06-12T16:20:00Z", format="M-A", players=47)
        species = ("charizard-mega-y", "floette-mega", "garchomp", "basculegion", "kingambit", "whimsicott")
        decklist = (
            [{"ability": "", "item": "Charizardite Y", "attacks": ["Heat Wave"]},
             {"ability": "", "item": "Floettite", "attacks": ["Moonblast"]}]
            + [{"ability": "", "attacks": ["Tailwind"]}]
            + [{"ability": "", "attacks": ["Surf"]}] * 3
        )
        rosters = [Roster(tour, "a", 1, "8-0-0", species, "", decklist)]
        snapshot = discover.discover_shells(rosters).snapshots[0]
        # The two-mega team is surfaced as dual_mode (tailwind stays the primary label).
        self.assertIn("dual_mode", snapshot["modes"])
        # Each mega anchors its own core instead of one mega being buried behind supports.
        mega_anchored = [core for core in snapshot["key_cores"] if core.split(" + ")[0].startswith("Mega ")]
        self.assertGreaterEqual(len(mega_anchored), 2)

    def test_official_top_cut_team_outranks_grassroots_and_is_labeled(self):
        regional = Tournament(id="r1", name="Regional Indianapolis, IN", date="2026-05-30T00:00:00Z",
                              format="m-a", players=1013, tier="regional", source="limitlessvgc")
        online = Tournament(id="o1", name="Friday Online", date="2026-06-10T00:00:00Z",
                            format="M-A", players=20, tier="online", source="limitless")

        def decklist(species):
            return [{"id": s, "name": s, "item": "", "ability": "", "attacks": ["Protect", "Moonblast"]} for s in species]

        official_shell = ("kingambit", "garchomp", "charizard", "incineroar", "sinistcha", "whimsicott")
        online_shell = ("torkoal", "venusaur", "aerodactyl", "hatterene", "kommo-o", "sableye")
        rosters = [
            Roster(regional, "champ", 1, "", official_shell, "x", decklist(official_shell)),
            Roster(online, "rando", 30, "", online_shell, "x", decklist(online_shell)),
        ]
        result = discover.discover_shells(rosters)
        top = result.snapshots[0]
        # The Regional-winning team is the top shell and is labeled as an official result.
        self.assertTrue(top["is_official"])
        self.assertIn("Regional", str(top["result_label"]))
        self.assertIn("kingambit", top["key_pokemon"])
        self.assertGreater(top["field_relevance"], result.snapshots[-1]["field_relevance"])


class ReconcileTests(unittest.TestCase):
    def _usage_report(self):
        rosters = [
            _make_roster(["basculegion", "kingambit", "incineroar", "garchomp"], 1),
            _make_roster(["basculegion", "froslass-mega", "incineroar", "sneasler"], 2),
        ]
        return usage.compute_usage(rosters, tournament_count=1, since_days=30)

    def test_flags_token_absent_from_secondary_and_degrades(self):
        report_usage = self._usage_report()
        pika = SourceUsage("Pikalytics", "u", True, {"basculegion": 51.5, "kingambit": 40.7, "incineroar": 25.9, "garchomp": 40.5})
        zone = SourceUsage("Pokémon Zone", "z", False, note="HTTP 403")
        result = reconcile.reconcile(report_usage, [pika, zone])
        self.assertGreater(result.top10_overlap, 0.5)
        # froslass-mega collapses to base "froslass", which is in our top-10 but absent
        # from Pikalytics -> flagged.
        flagged = {c.token for c in result.comparisons if c.flags}
        self.assertIn("froslass", flagged)
        # Unavailable source recorded, run still proceeds.
        self.assertTrue(any(not s["available"] for s in result.sources))

    def test_secondary_mega_tokens_base_normalized_for_comparison(self):
        report_usage = self._usage_report()
        # Pikalytics reports charizard-mega-y; our usage would carry base "charizard".
        # The comparison must base-normalize so they line up (not double-flag).
        pika = SourceUsage("Pikalytics", "u", True, {"basculegion": 51.5, "charizard-mega-y": 31.8})
        result = reconcile.reconcile(report_usage, [pika])
        base_map = reconcile._base_normalized_token_pct(pika)
        self.assertIn("charizard", base_map)
        self.assertNotIn("charizard-mega-y", base_map)

    def test_no_secondary_sources_is_handled(self):
        result = reconcile.reconcile(self._usage_report(), [])
        self.assertEqual(result.top10_overlap, 0.0)
        self.assertTrue(any("solely" in line for line in result.summary))


class PikalyticsParseTests(unittest.TestCase):
    def test_parses_leaderboard_rows_to_tokens(self):
        token_pct = pikalytics.parse_usage_html(_PIKALYTICS_HTML)
        self.assertEqual(token_pct["basculegion"], 51.5)
        self.assertEqual(token_pct["charizard-mega-y"], 31.81)
        self.assertEqual(len(token_pct), 4)

    def test_fetch_unavailable_on_empty_markup(self):
        with patch.object(pikalytics, "get_text", lambda *a, **k: "<html></html>"):
            result = pikalytics.fetch_usage()
        self.assertFalse(result.available)

    def test_pokemon_zone_degrades_on_403(self):
        from pokemon_team_analyzer.meta_ingest.http import HttpError

        def boom(*_a, **_k):
            raise HttpError("u", 403, "HTTP 403 Forbidden")

        with patch.object(pokemon_zone, "get_text", boom):
            result = pokemon_zone.fetch_usage()
        self.assertFalse(result.available)
        self.assertIn("403", result.note)


class SchemaValidationTests(unittest.TestCase):
    def _valid_snapshot(self):
        return {
            "slug": "live-x", "label": "X", "source": "s", "result_label": "top-8 finish",
            "field_relevance": 1.0, "popularity_weight": 0.8, "result_weight": 0.7,
            "modes": ["rain"], "mode_weights": {"rain": 1.0}, "broad_mix": {"balance": 1.0},
            "key_pokemon": ["basculegion"], "key_cores": ["A + B"],
        }

    def _valid_feed(self):
        return {
            "version": 1, "generatedAt": "2026-06-13T00:00:00Z",
            "regulations": [{
                "regulationId": "champions_regulation_m_a", "updatedAt": "2026-06-13T00:00:00Z",
                "notes": [], "commonMetaPokemon": [], "tournamentTeamSnapshots": [self._valid_snapshot()],
            }],
        }

    def test_valid_feed_passes(self):
        schema.validate_feed(self._valid_feed())  # must not raise

    def test_mode_missing_from_mode_weights_fails(self):
        feed = self._valid_feed()
        feed["regulations"][0]["tournamentTeamSnapshots"][0]["modes"] = ["rain", "sun"]
        with self.assertRaises(schema.FeedValidationError):
            schema.validate_feed(feed)

    def test_offset_datetime_rejected_like_zod(self):
        feed = self._valid_feed()
        feed["generatedAt"] = "2026-06-13T00:00:00+00:00"  # Zod requires trailing Z
        with self.assertRaises(schema.FeedValidationError):
            schema.validate_feed(feed)

    def test_meta_share_out_of_range_fails(self):
        feed = self._valid_feed()
        feed["regulations"][0]["commonMetaPokemon"] = [{
            "species": "Basculegion", "metaShare": 150.0, "whyUsed": "x", "whatItDoes": "y", "featuredTeams": [],
        }]
        with self.assertRaises(schema.FeedValidationError):
            schema.validate_feed(feed)


class BuildFeedTests(unittest.TestCase):
    def test_build_feed_end_to_end_with_mocked_sources(self):
        tournament = Tournament(id="aaa111", name="CROWN", date="2026-06-12T16:20:00Z", format="M-A", players=47)
        rosters: list[Roster] = []
        with patch.object(limitless, "get_json", _fake_get_json):
            rosters = limitless.fetch_rosters(tournament) * 3  # inflate the sample a little

        def fake_collect(**_kwargs):
            return rosters, [tournament], []

        # One official event so the weighted path + official_count are exercised offline.
        official_tour = Tournament(id="999", name="Regional Z", date="2026-06-01T00:00:00Z",
                                   format="m-a", players=400, tier="regional", source="limitlessvgc")
        official_rosters = [
            Roster(official_tour, "champ", 1, "", ("kingambit", "garchomp", "incineroar", "sinistcha"), "", []),
            Roster(official_tour, "second", 2, "", ("basculegion", "garchomp", "whimsicott", "sneasler"), "", []),
        ]

        pika = SourceUsage("Pikalytics", "u", True, {"basculegion": 51.5, "incineroar": 25.9})
        zone = SourceUsage("Pokémon Zone", "z", False, note="HTTP 403")

        with patch.object(build.limitless, "collect_rosters", fake_collect), \
             patch.object(build.limitlessvgc, "collect_official_rosters",
                          lambda **_k: (official_rosters, [official_tour], [])), \
             patch.object(build.pikalytics, "fetch_usage", lambda **_k: pika), \
             patch.object(build.pokemon_zone, "fetch_usage", lambda **_k: zone):
            result = build.build_feed(since_days=30, min_players=8)

        # Feed validates against the Python mirror of the web contract.
        schema.validate_feed(result.feed)
        document = result.feed["regulations"][0]
        self.assertTrue(document["tournamentTeamSnapshots"])
        self.assertTrue(document["commonMetaPokemon"])
        # Headline metaShare is the weighted usage; raw share is retained separately.
        top = document["commonMetaPokemon"][0]
        self.assertEqual(top["metaShare"], top["weightedUsagePercent"])
        self.assertEqual(top["sampleSize"], result.usage.sample_size)
        # The official event was counted and recorded in provenance.
        self.assertEqual(result.usage.official_count, 1)
        self.assertEqual(document["provenance"]["officialEventCount"], 1)
        self.assertTrue(document["provenance"]["officialEvents"])


class LimitlessVgcOfficialSourceTests(unittest.TestCase):
    def test_classify_tier(self):
        self.assertEqual(limitlessvgc.classify_tier("Regional Indianapolis, IN"), "regional")
        self.assertEqual(limitlessvgc.classify_tier("Special Event Turin"), "special_event")
        self.assertEqual(limitlessvgc.classify_tier("EUIC 2026, London"), "international")
        self.assertEqual(limitlessvgc.classify_tier("World Championships 2026"), "worlds")
        self.assertEqual(limitlessvgc.classify_tier("Players Cup IV"), "players_cup")

    def test_parse_listing_filters_format_and_window(self):
        tournaments = limitlessvgc.parse_listing(_LVGC_LISTING_HTML, since_days=60, now=_NOW)
        ids = sorted(t.id for t in tournaments)
        # Only the two in-window M-A events; the 'l'-format and out-of-window rows drop.
        self.assertEqual(ids, ["434", "435"])
        by_id = {t.id: t for t in tournaments}
        self.assertEqual(by_id["434"].tier, "regional")
        self.assertEqual(by_id["434"].players, 1013)
        self.assertEqual(by_id["435"].tier, "special_event")
        self.assertEqual(by_id["435"].source, "limitlessvgc")
        self.assertEqual(by_id["435"].url, "https://limitlessvgc.com/tournaments/435")

    def test_parse_standings_extracts_placement_and_base_species(self):
        tour = Tournament(id="435", name="Special Event Turin", date="2026-06-06",
                          format="m-a", players=940, tier="special_event", source="limitlessvgc")
        rosters = limitlessvgc.parse_standings(tour, _LVGC_STANDINGS_HTML)
        self.assertEqual(len(rosters), 2)
        self.assertEqual(rosters[0].placing, 1)
        self.assertIn("floette-eternal", rosters[0].species_tokens)
        self.assertIn("gengar", rosters[0].species_tokens)  # base species (no mega in official data)
        self.assertEqual(rosters[0].showdown_text, "")  # usage-only, no decklist for discovery

    def test_collect_official_rosters_degrades_when_listing_unavailable(self):
        from pokemon_team_analyzer.meta_ingest.http import HttpError

        def boom(*_a, **_k):
            raise HttpError("u", 503, "down")

        with patch.object(limitlessvgc, "get_text", boom):
            rosters, tournaments, warnings = limitlessvgc.collect_official_rosters(since_days=60)
        self.assertEqual(rosters, [])
        self.assertTrue(warnings)


class PublishTests(unittest.TestCase):
    def test_publish_feed_posts_with_bearer_auth(self):
        from pokemon_team_analyzer.meta_ingest import publish as publish_mod
        from pokemon_team_analyzer.meta_ingest.http import HttpResponse

        captured = {}

        def fake_post_json(url, payload, *, headers=None, **_kwargs):
            captured["url"] = url
            captured["payload"] = payload
            captured["headers"] = headers or {}
            return HttpResponse(url=url, status=200, body='{"count": 1, "published": []}')

        with patch.object(publish_mod, "post_json", fake_post_json):
            result = publish_mod.publish_feed({"version": 1}, "https://app.example/api/meta-snapshot/publish", secret="s3cret")

        self.assertEqual(result["count"], 1)
        self.assertEqual(captured["url"], "https://app.example/api/meta-snapshot/publish")
        self.assertEqual(captured["payload"], {"version": 1})
        self.assertEqual(captured["headers"]["Authorization"], "Bearer s3cret")

    def test_publish_feed_requires_a_secret(self):
        from pokemon_team_analyzer.meta_ingest import publish as publish_mod

        with patch.dict("os.environ", {"META_SNAPSHOT_REFRESH_SECRET": "", "CRON_SECRET": ""}, clear=False):
            with self.assertRaises(ValueError):
                publish_mod.publish_feed({"version": 1}, "https://app.example/publish", secret="")

    def test_resolve_publish_secret_precedence(self):
        from pokemon_team_analyzer.meta_ingest import publish as publish_mod

        with patch.dict("os.environ", {"META_SNAPSHOT_REFRESH_SECRET": "primary", "CRON_SECRET": "fallback"}, clear=False):
            self.assertEqual(publish_mod.resolve_publish_secret(), "primary")
        with patch.dict("os.environ", {"META_SNAPSHOT_REFRESH_SECRET": "", "CRON_SECRET": "fallback"}, clear=False):
            self.assertEqual(publish_mod.resolve_publish_secret(), "fallback")

    def test_publish_feed_raises_on_error_status(self):
        from pokemon_team_analyzer.meta_ingest import publish as publish_mod
        from pokemon_team_analyzer.meta_ingest.http import HttpError, HttpResponse

        def fake_post_json(url, payload, *, headers=None, **_kwargs):
            return HttpResponse(url=url, status=401, body="unauthorized")

        with patch.object(publish_mod, "post_json", fake_post_json):
            with self.assertRaises(HttpError):
                publish_mod.publish_feed({"version": 1}, "https://app.example/publish", secret="x")


if __name__ == "__main__":
    unittest.main()
