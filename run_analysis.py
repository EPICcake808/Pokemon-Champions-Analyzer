import os
import sys

# Ensure the package is in the search path
sys.path.append(os.path.abspath('.'))

from tests.test_analyzer import SAMPLE_TEAM, FakeMetadataProvider
from pokemon_team_analyzer.analyzer import analyze_team_text

def load_example_team(filename):
    with open(os.path.join('tests', 'teams', filename), 'r') as f:
        return f.read()

def run_analysis():
    provider = FakeMetadataProvider()
    analysis = analyze_team_text(SAMPLE_TEAM, metadata_provider=provider, regulation_id=None)
    
    fields = [
        "average_battle_speed", "median_battle_speed", "speed_standard_deviation",
        "fastest_battle_speed_pokemon", "slowest_battle_speed_pokemon",
        "member_battle_speeds", "member_stats", "speed_tier_counts",
        "speed_benchmark_notes"
    ]
    
    for field in fields:
        print(f"--- {field} ---")
        print(getattr(analysis, field))
        print()

    print("--- speed_benchmark_groups statuses ---")
    for group_key, group_data in analysis.speed_benchmark_groups.items():
        print(f"Group: {group_key} ({group_data['label']})")
        for benchmark in group_data.get('benchmarks', []):
             print(f"  {benchmark['label']}: {benchmark['status']}")

    print("\n--- Aerodactyl/Basculegion benchmark tags ---")
    # Using member_speed_benchmark_tags as seen in the grep
    for pkmn in ["Aerodactyl", "Basculegion (M)"]:
        tags = analysis.member_speed_benchmark_tags.get(pkmn, [])
        print(f"{pkmn}: {tags}")

    print("\n--- Sneasler Contexts ---")
    try:
        # Based on test_speed_contexts_include_ability_based_boosts
        team_text = load_example_team("championsmeta_master_ball_ready_team.txt")
        analysis_sneasler = analyze_team_text(team_text, metadata_provider=provider, regulation_id=None)
        if "Sneasler" in analysis_sneasler.member_speed_contexts:
             contexts = {
                 context["slug"]: context["speed"]
                 for context in analysis_sneasler.member_speed_contexts["Sneasler"]
             }
             print(contexts)
        else:
             print("Sneasler not found in member_speed_contexts")
    except Exception as e:
        print(f"Error getting Sneasler contexts: {e}")

run_analysis()
