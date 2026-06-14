from __future__ import annotations

from pathlib import Path
import re
import unittest

from pokemon_team_analyzer.analyzer import analyze_team_text
from pokemon_team_analyzer.showdown import parse_showdown_team
from pokemon_team_analyzer.regulations import DEFAULT_REGULATION_ID, IllegalTeamError


ROOT = Path(__file__).resolve().parent.parent


class ExampleTeamTests(unittest.TestCase):
    def test_example_team_evs_follow_champions_scale(self) -> None:
        example_paths = sorted((ROOT / "examples").glob("*.txt")) + sorted((ROOT / "web/examples").glob("*.txt"))

        for path in example_paths:
            with self.subTest(example=str(path.relative_to(ROOT))):
                for pokemon_set in parse_showdown_team(path.read_text(encoding="utf-8")):
                    self.assertLessEqual(sum(pokemon_set.evs.values()), 66)
                    self.assertTrue(all(value <= 32 for value in pokemon_set.evs.values()))

        source_text = (ROOT / "web/src/lib/example-teams.ts").read_text(encoding="utf-8")
        for match in re.finditer(r"EVs:\s*([^`\n]+)", source_text):
            values = [int(value) for value in re.findall(r"(\d+)\s+(?:HP|Atk|Def|SpA|SpD|Spe)", match.group(1))]
            with self.subTest(example_team_line=match.group(0)):
                self.assertLessEqual(sum(values), 66)
                self.assertTrue(all(value <= 32 for value in values))

    def test_all_example_team_files_are_legal(self) -> None:
        example_paths = sorted((ROOT / "examples").glob("*.txt")) + sorted((ROOT / "web/examples").glob("*.txt"))

        for path in example_paths:
            with self.subTest(example=str(path.relative_to(ROOT))):
                try:
                    analyze_team_text(path.read_text(encoding="utf-8"), regulation_id=DEFAULT_REGULATION_ID)
                except IllegalTeamError as error:
                    issues = [issue.message for issue in error.legality.issues]
                    self.fail(f"{path.name} is illegal: {issues}")

    def test_mono_type_team_is_graded_down_for_stacked_weakness(self) -> None:
        # A mono-grass team shares its weaknesses across the whole roster (one well-picked
        # attacker pressures everything), so the absolute soundness penalty should pull it
        # into the negative band rather than letting mean-centered matchup scores grade it
        # favorably.
        grass = analyze_team_text(
            (ROOT / "examples" / "realistic_grassy_terrain_team.txt").read_text(encoding="utf-8"),
            regulation_id=DEFAULT_REGULATION_ID,
        )
        meta = grass.meta_analysis
        self.assertLess(meta["overall_score"], 0.0)
        self.assertIn(meta["label"], {"shaky", "pressured"})
        self.assertGreater(meta["negative_weight_share"], meta["positive_weight_share"])

        # A structurally sound meta team keeps a healthy grade (penalty ~0).
        sand = analyze_team_text(
            (ROOT / "examples" / "realistic_sand_team.txt").read_text(encoding="utf-8"),
            regulation_id=DEFAULT_REGULATION_ID,
        )
        self.assertIn(sand.meta_analysis["label"], {"solid", "strong"})

    def test_niche_example_teams_hit_their_intended_archetypes(self) -> None:
        expected_archetypes = {
            "realistic_grassy_terrain_team.txt": "grassy_terrain",
            "realistic_misty_terrain_team.txt": "misty_terrain",
            "realistic_sand_room_team.txt": "sand_room",
            "realistic_sun_tailroom_team.txt": "sun_tailroom",
        }

        for file_name, expected_archetype in expected_archetypes.items():
            path = ROOT / "examples" / file_name
            with self.subTest(example=file_name):
                analysis = analyze_team_text(path.read_text(encoding="utf-8"), regulation_id=DEFAULT_REGULATION_ID)
                self.assertEqual(analysis.team_archetype, expected_archetype)


if __name__ == "__main__":
    unittest.main()