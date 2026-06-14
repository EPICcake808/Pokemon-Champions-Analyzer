import unittest

from pokemon_team_analyzer.glossary import GLOSSARY, build_plain_language_summary


class GlossaryTests(unittest.TestCase):
    def test_core_terms_present(self):
        for key in ("hyper_offense", "trick_room", "semiroom", "tailroom", "pilot_load", "matchup_score"):
            self.assertIn(key, GLOSSARY)
            self.assertTrue(GLOSSARY[key]["term"])
            self.assertTrue(GLOSSARY[key]["definition"])


class PlainSummaryTests(unittest.TestCase):
    def _summary(self, **overrides):
        base = dict(
            archetype="hyper_offense",
            style="hyper_offense",
            mode_labels=["tailwind"],
            win_condition_labels=["setup_sweep"],
            speed_tier="fast",
            favorable_matchups=["stall", "semi_stall"],
            unfavorable_matchups=["balance"],
            unfavorable_modes=["trick_room"],
            top_defensive_weaknesses=["ice"],
            difficulty_label="moderate",
            difficulty_score=6.2,
        )
        base.update(overrides)
        return build_plain_language_summary(**base)

    def test_summary_mentions_archetype_and_difficulty(self):
        sentences = self._summary()
        self.assertGreaterEqual(len(sentences), 4)
        joined = " ".join(sentences)
        self.assertIn("Hyper Offense", joined)
        self.assertIn("6.2/10", joined)
        # Every sentence ends cleanly.
        for sentence in sentences:
            self.assertTrue(sentence.endswith("."))

    def test_summary_handles_no_strengths_or_weaknesses(self):
        sentences = self._summary(
            favorable_matchups=[],
            unfavorable_matchups=[],
            unfavorable_modes=[],
            top_defensive_weaknesses=[],
        )
        self.assertTrue(sentences)
        self.assertIn("Hyper Offense", " ".join(sentences))


if __name__ == "__main__":
    unittest.main()
