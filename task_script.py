import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path.cwd()))

from pokemon_team_analyzer.analyzer import analyze_team_text
from tests.test_analyzer import load_example_team, FakeMetadataProvider

# Load the specified team text
team_text = load_example_team("championsmeta_master_ball_ready_team.txt")

# Initialize the fake metadata provider
metadata_provider = FakeMetadataProvider()

# Analyze the team
analysis = analyze_team_text(team_text, metadata_provider=metadata_provider)

# Print specified values
print(f"team_mode_labels: {analysis.team_mode_labels}")
print(f"favorable_matchups: {analysis.favorable_matchups}")
print(f"unfavorable_matchups: {analysis.unfavorable_matchups}")
print(f"matchup_scores: {analysis.matchup_scores}")
print(f"pokemon_role_counts: {analysis.pokemon_role_counts}")
print(f"utility_role_counts: {analysis.utility_role_counts}")
