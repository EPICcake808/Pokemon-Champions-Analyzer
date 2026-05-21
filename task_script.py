import sys
import os
import json

# Ensure the package is in the search path
sys.path.append(os.path.abspath('.'))

try:
    from tests.test_analyzer import analyze_team_text, SAMPLE_TEAM, FakeMetadataProvider
except ImportError:
    # Fallback
    from pokemon_team_analyzer.analyzer import analyze_team_text
    from tests.test_analyzer import SAMPLE_TEAM, FakeMetadataProvider

def run():
    analysis = analyze_team_text(SAMPLE_TEAM, metadata_provider=FakeMetadataProvider(), regulation_id=None)
    
    # Map the requested fields from the analysis object
    # Some fields (like natural_statuses) are expected but not in TeamAnalysis.
    # We'll check the speed_benchmark_groups or tags to find related info if possible.
    
    result = {
        "average_battle_speed": getattr(analysis, "average_battle_speed", None),
        "median_battle_speed": getattr(analysis, "median_battle_speed", None),
        "speed_standard_deviation": getattr(analysis, "speed_standard_deviation", None),
        "fastest_battle_speed_pokemon": getattr(analysis, "fastest_battle_speed_pokemon", None),
        "slowest_battle_speed_pokemon": getattr(analysis, "slowest_battle_speed_pokemon", None),
        "member_battle_speeds": getattr(analysis, "member_battle_speeds", None),
        "natural_statuses": None,
        "tailwind_statuses": None,
        "choice_scarf_statuses": None,
        "trick_room_statuses": None,
        "aerodactyl_tags": None,
        "basculegion_tags": None,
        "speed_tier_counts": getattr(analysis, "speed_tier_counts", None),
        "lucario_defense": None,
        "basculegion_speed": None,
        "speed_benchmark_notes": getattr(analysis, "speed_benchmark_notes", None)
    }
    
    # Try to populate tags/statuses if they exist in benchmark groups or member tags
    # Based on the SAMPLE_TEAM provided in tests/test_analyzer.py
    groups = getattr(analysis, "speed_benchmark_groups", {})
    if groups:
        result["natural_statuses"] = groups.get("natural", {}).get("statuses")
        result["tailwind_statuses"] = groups.get("tailwind", {}).get("statuses")
        result["choice_scarf_statuses"] = groups.get("choice_scarf", {}).get("statuses")
        result["trick_room_statuses"] = groups.get("trick_room", {}).get("statuses")
        
    member_tags = getattr(analysis, "member_speed_benchmark_tags", {})
    if member_tags:
        result["aerodactyl_tags"] = member_tags.get("Aerodactyl")
        result["basculegion_tags"] = member_tags.get("Basculegion (M)")
    
    # basculegion_speed and lucario_defense might be part of individual member analysis if available
    # For now, let's keep them as null or try to infer.
    # Looking at the requirement, these specific names might be custom from the test suite's perspective.
    
    print(json.dumps(result))

if __name__ == "__main__":
    run()
