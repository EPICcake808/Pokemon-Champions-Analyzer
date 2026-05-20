import sys
import os

# Add the project root to sys.path
sys.path.append('/Users/iohari/Documents/GitHub/Pokemon-Champions-Analyzer')

from pokemon_team_analyzer.analyzer import analyze_team_text
from tests.test_analyzer import FakeMetadataProvider

file_path = '/Users/iohari/Documents/GitHub/Pokemon-Champions-Analyzer/examples/championsmeta_master_ball_ready_team.txt'
with open(file_path, 'r') as f:
    team_text = f.read()

metadata_provider = FakeMetadataProvider()
analysis = analyze_team_text(team_text, metadata_provider)

print(f"team_mode_labels: {analysis.team_mode_labels}")
print(f"team_mode_scores: {analysis.team_mode_scores}")
print(f"favorable_modes: {analysis.favorable_modes}")
print(f"unfavorable_modes: {analysis.unfavorable_modes}")
