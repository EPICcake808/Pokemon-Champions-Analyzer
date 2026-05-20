from pokemon_team_analyzer import analyze_team_text, validate_team_legality_text
from tests.test_analyzer import FakeMetadataProvider

team_text = """Tyranitar @ Hard Stone
Ability: Sand Stream
Level: 50
- Stealth Rock
- Roar
- Knock Off
- Stone Edge

Corviknight @ Sharp Beak
Ability: Pressure
Level: 50
- Tailwind
- U-turn
- Roost
- Body Press

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

Milotic @ Leftovers
Ability: Competitive
Level: 50
- Scald
- Protect
- Icy Wind
- Recover

Scizor-Mega @ Scizorite
Ability: Technician
Level: 50
- Bullet Punch
- Protect
- Bug Bite
- Swords Dance"""

metadata_provider = FakeMetadataProvider()

# Legality
legality = validate_team_legality_text(team_text)
print(f"Legality: {legality}")

# Analysis
analysis = analyze_team_text(team_text, metadata_provider=metadata_provider)

print(f"Archetype: {analysis.archetype}")

# Top 4 archetype scores
# Assuming analysis.archetype_scores is a dict or similar
sorted_scores = sorted(analysis.archetype_scores.items(), key=lambda x: x[1], reverse=True)
print("Top 4 Archetype Scores:")
for name, score in sorted_scores[:4]:
    print(f"  {name}: {score:.4f}")

print(f"Team Mode Labels: {analysis.team_mode_labels}")
