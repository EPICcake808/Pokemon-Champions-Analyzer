import sys
import os

# Add the current directory to sys.path to allow imports from tests
sys.path.append(os.getcwd())

from tests.test_analyzer import analyze_team_text, FakeMetadataProvider, SAMPLE_TEAM, TRICK_ROOM_TEAM, SUN_TAILWIND_TEAM, PERISH_TRAP_TEAM, PSYSPAM_TEAM

def run_analysis(name, text):
    print(f"--- Analysis for: {name} ---")
    analysis = analyze_team_text(text, metadata_provider=FakeMetadataProvider(), regulation_id=None)
    
    print(f"Primary Team Style: {analysis.primary_team_style}")
    print(f"Team Mode Packages: {analysis.team_mode_packages}")
    print(f"Team Win Condition Labels: {analysis.team_win_condition_labels}")
    print(f"Favorable Modes: {analysis.matchup_coverage.favorable_modes if analysis.matchup_coverage else None}")
    print(f"Unfavorable Modes: {analysis.matchup_coverage.unfavorable_modes if analysis.matchup_coverage else None}")
    
    print("\nTeam Preview Block:")
    # Assuming team_preview is a dictionary and its values are TeamPreview objects or dicts
    preview = analysis.team_preview
    if isinstance(preview, dict):
        for plan_name, plan in preview.items():
            print(f"  Plan: {plan_name}")
            if hasattr(plan, 'leads'):
                print(f"    Leads: {plan.leads}")
                print(f"    Back: {plan.back}")
                print(f"    Pick Four: {plan.pick_four}")
                print(f"    Strategy: {plan.strategy}")
                print(f"    Counterplay: {plan.counterplay}")
                print(f"    Watchlist: {plan.watchlist}")
            else:
                # If it's a dict
                print(f"    Leads: {plan.get('leads')}")
                print(f"    Back: {plan.get('back')}")
                print(f"    Pick Four: {plan.get('pick_four')}")
                print(f"    Strategy: {plan.get('strategy')}")
                print(f"    Counterplay: {plan.get('counterplay')}")
                print(f"    Watchlist: {plan.get('watchlist')}")
    print("\n")

teams = [
    ("SAMPLE_TEAM", SAMPLE_TEAM),
    ("TRICK_ROOM_TEAM", TRICK_ROOM_TEAM),
    ("SUN_TAILWIND_TEAM", SUN_TAILWIND_TEAM),
    ("PERISH_TRAP_TEAM", PERISH_TRAP_TEAM),
    ("PSYSPAM_TEAM", PSYSPAM_TEAM),
]

example_files = [
    ("examples/championsmeta_master_ball_ready_team.txt", "examples/championsmeta_master_ball_ready_team.txt"),
    ("examples/championsmeta_mega_scizor_team.txt", "examples/championsmeta_mega_scizor_team.txt")
]

for name, text in teams:
    run_analysis(name, text)

for name, filepath in example_files:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            text = f.read()
            run_analysis(name, text)
    else:
        print(f"File not found: {filepath}")

