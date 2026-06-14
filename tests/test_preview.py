import unittest
from pathlib import Path

from pokemon_team_analyzer.preview import analyze_preview

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


class PreviewTrainerTests(unittest.TestCase):
    """Integration coverage using bundled example teams (resolved via the cached provider)."""

    @classmethod
    def setUpClass(cls):
        cls.mine = (EXAMPLES_DIR / "realistic_hyper_offense_team.txt").read_text()
        cls.opponent = (EXAMPLES_DIR / "realistic_trick_room_team.txt").read_text()
        cls.result = analyze_preview(cls.mine, cls.opponent)

    def test_recommends_four_and_a_lead(self):
        bring = self.result["recommended_bring"]
        self.assertEqual(len(bring["members"]), 4)
        self.assertEqual(len(bring["lead"]), 2)
        # Lead must be drawn from the recommended four.
        self.assertTrue(set(bring["lead"]).issubset(set(bring["members"])))

    def test_reasons_and_matchups_present(self):
        self.assertTrue(self.result["recommended_bring"]["reasons"])
        # One matchup record per resolved member of my team.
        self.assertEqual(len(self.result["matchups"]), 6)
        for record in self.result["matchups"]:
            self.assertEqual(record["opponent_count"], len(self.result["opponent"]))
            self.assertIn("ko_targets", record)
            self.assertIn("threatened_by", record)

    def test_detects_opponent_trick_room(self):
        self.assertTrue(self.result["opponent_has_trick_room"])
        self.assertTrue(
            any("Trick Room" in reason for reason in self.result["recommended_bring"]["reasons"])
        )

    def test_empty_team_raises(self):
        with self.assertRaises(ValueError):
            analyze_preview("", self.opponent)


if __name__ == "__main__":
    unittest.main()
