import sys
import os

# Add current directory to sys.path to allow imports
sys.path.append(os.getcwd())

from pokemon_team_analyzer.champions_m_a_data import ELIGIBLE_SPECIES
from pokemon_team_analyzer.champions_m_a_moves import get_allowed_moves_for_species

search_keywords = ["Tapu", "Indeedee", "Ninetales", "Torkoal", "Tyranitar", "Farigiraf", "Kingambit", "Primarina", "Venusaur", "Scizor", "Amoonguss", "Sinistcha", "Corviknight", "Glastrier"]
exact_species = ["Tapu Bulu", "Tapu Fini", "Indeedee (Female)", "Ninetales (Alolan Form)", "Torkoal", "Tyranitar", "Farigiraf", "Kingambit", "Primarina", "Venusaur", "Amoonguss", "Sinistcha", "Corviknight"]

print("1) Eligible species containing keywords:")
matched_species = [s for s in ELIGIBLE_SPECIES if any(kw in s for kw in search_keywords)]
print(", ".join(sorted(matched_species)))

print("\n2) Allowed moves for specific species:")
for name in exact_species:
    if name in ELIGIBLE_SPECIES:
        moves = get_allowed_moves_for_species(name)
        print(f"{name}: {', '.join(moves)}")
    else:
        # Check if the name exists under a slightly different form just in case
        pass

