import sys
from pokemon_team_analyzer.analyzer import analyze_team_text
from tests.test_analyzer import FakeMetadataProvider

ORIGINAL_MEGA_SCIZOR = """Sneasler @ White Herb
Ability: Unburden
Level: 50
- Close Combat
- Dire Claw
- Fake Out
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
Level: 50
- Dragon Claw
- Rock Slide
- Protect
- Stomping Tantrum

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Aerodactyl @ Focus Sash
Ability: Unnerve
Level: 50
- Rock Slide
- Protect
- Dual Wingbeat
- Tailwind

Scizor-Mega @ Scizorite
Ability: Technician
Level: 50
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance

Milotic @ Leftovers
Ability: Competitive
Level: 50
- Scald
- Protect
- Icy Wind
- Recover
"""

BALANCE_VARIANT_A = '''Sneasler @ White Herb
Ability: Unburden
Level: 50
- Close Combat
- Dire Claw
- Fake Out
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
Level: 50
- Dragon Claw
- Rock Slide
- Protect
- Stomping Tantrum

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Aerodactyl @ Focus Sash
Ability: Unnerve
Level: 50
- Rock Slide
- Protect
- Dual Wingbeat
- Tailwind

Scizor-Mega @ Scizorite
Ability: Technician
Level: 50
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance

Milotic @ Leftovers
Ability: Competitive
Level: 50
- Scald
- Protect
- Icy Wind
- Recover
'''

BALANCE_VARIANT_B = '''Sneasler @ White Herb
Ability: Unburden
Level: 50
- Close Combat
- Dire Claw
- Fake Out
- Protect

Garchomp @ Soft Sand
Ability: Rough Skin
Level: 50
- Dragon Claw
- Rock Slide
- Protect
- Stomping Tantrum

Sinistcha @ Mental Herb
Ability: Hospitality
Level: 50
- Matcha Gotcha
- Rage Powder
- Trick Room
- Life Dew

Aerodactyl @ Focus Sash
Ability: Unnerve
Level: 50
- Rock Slide
- Protect
- Dual Wingbeat
- Tailwind

Scizor-Mega @ Scizorite
Ability: Technician
Level: 50
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
- Hyper Voice
- Moonblast
- Calm Mind
- Protect
'''

BALANCE_VARIANT_C = '''Gardevoir-Mega @ Gardevoirite
Ability: Pixilate
Level: 50
- Hyper Voice
- Psychic
- Trick Room
- Protect

Primarina @ Leftovers
Ability: Liquid Voice
Level: 50
- Hyper Voice
- Moonblast
- Calm Mind
- Protect

Whimsicott @ Focus Sash
Ability: Prankster
Level: 50
- Tailwind
- Moonblast
- Encore
- Protect

Sinistcha @ Sitrus Berry
Ability: Hospitality
Level: 50
- Matcha Gotcha
- Rage Powder
- Life Dew
- Protect

Arcanine-Hisui @ Charcoal
Ability: Intimidate
Level: 50
- Rock Slide
- Flare Blitz
- Extreme Speed
- Protect

Kingambit @ Black Glasses
Ability: Defiant
Level: 50
- Kowtow Cleave
- Protect
- Sucker Punch
- Iron Head
'''

TEAMS = {
    "ORIGINAL": ORIGINAL_MEGA_SCIZOR,
    "BALANCE_VARIANT_A": BALANCE_VARIANT_A,
    "BALANCE_VARIANT_B": BALANCE_VARIANT_B,
    "BALANCE_VARIANT_C": BALANCE_VARIANT_C
}

metadata_provider = FakeMetadataProvider()

print(f"{'Team':<20} | {'Archetype':<15} | {'Top 4 Scores':<45} | {'Modes'}")
print("-" * 120)

for name, team_text in TEAMS.items():
    analysis = analyze_team_text(team_text, metadata_provider)
    
    archetype = analysis.team_archetype
    sorted_scores = sorted(analysis.team_archetype_scores.items(), key=lambda x: x[1], reverse=True)[:4]
    scores_str = ", ".join([f"{k}: {v:.2f}" for k, v in sorted_scores])
    modes_str = ", ".join(analysis.team_mode_labels)
    
    print(f"{name:<20} | {archetype:<15} | {scores_str:<45} | {modes_str}")
