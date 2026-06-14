import unittest
from pathlib import Path

from pokemon_team_analyzer.analyzer import _speed_coverage_share, analyze_team_text

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


class SpeedCoverageShareTests(unittest.TestCase):
    META = [(200, 10.0), (150, 20.0), (100, 5.0)]  # (assumed_speed, meta_share)
    TOTAL = 35.0

    def test_faster_wins_counts_slower_meta(self):
        # Speed 160 beats the 150 and 100 entries (25 share) -> 25/35.
        self.assertEqual(_speed_coverage_share(self.META, 160, self.TOTAL, faster_wins=True), round(100 * 25 / 35, 1))

    def test_trick_room_counts_faster_meta(self):
        # Under TR, speed 160 "beats" the faster 200 entry (10 share) -> 10/35.
        self.assertEqual(_speed_coverage_share(self.META, 160, self.TOTAL, faster_wins=False), round(100 * 10 / 35, 1))

    def test_tie_splits_half(self):
        # Exact tie with the 150 entry: half of 20 share counts on each side.
        self.assertEqual(_speed_coverage_share([(150, 20.0)], 150, 20.0, faster_wins=True), 50.0)


class SpeedCoverageIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        team = (EXAMPLES_DIR / "realistic_hyper_offense_team.txt").read_text()
        cls.coverage = analyze_team_text(team).speed_coverage

    def test_available_and_per_member(self):
        self.assertTrue(self.coverage["available"])
        self.assertGreater(self.coverage["sample_species"], 0)
        self.assertEqual(len(self.coverage["members"]), 6)

    def test_invariants(self):
        for member in self.coverage["members"]:
            for key in ("natural_pct", "tailwind_pct", "trick_room_pct"):
                self.assertGreaterEqual(member[key], 0.0)
                self.assertLessEqual(member[key], 100.0)
            # +0 and Trick Room coverage partition the field (ties split evenly).
            self.assertAlmostEqual(member["natural_pct"] + member["trick_room_pct"], 100.0, delta=0.3)
            # Tailwind only ever doubles your speed, so it cannot be worse than +0.
            self.assertGreaterEqual(member["tailwind_pct"], member["natural_pct"] - 0.2)


if __name__ == "__main__":
    unittest.main()
