from __future__ import annotations

from dataclasses import asdict

from .analyzer import analyze_team_text, _normalized_member_stats
from .champions_m_a_moves import get_allowed_moves_for_species
from .damage import (
    FieldConditions,
    combatant_from_stats,
    compute_damage,
)
from .data import CachedPokeApiClient, MetadataProvider
from .models import MoveData, PokemonSet, SpeciesData, TeamMember
from .preview import analyze_preview
from .slot_doctor import analyze_slots
from .regulations import (
    DEFAULT_REGULATION_ID,
    IllegalTeamError,
    get_regulation,
    regulation_catalog_as_dict,
    resolve_required_item_for_species,
    resolve_builder_option_source_species_name,
    resolve_regulation_species_name,
)


_SPREAD_TARGET_NAMES = {"all-opponents", "all-other-pokemon", "entire-field"}


def build_regulation_catalog_payload(*, include_team_text: bool = False, include_rules: bool = False) -> dict[str, object]:
    return {
        "default_regulation_id": DEFAULT_REGULATION_ID,
        "regulations": regulation_catalog_as_dict(
            include_team_text=include_team_text,
            include_rules=include_rules,
        ),
    }


def build_builder_species_options_payload(species_name: str, regulation_id: str = DEFAULT_REGULATION_ID) -> dict[str, object]:
    regulation = get_regulation(regulation_id)
    canonical_species = resolve_regulation_species_name(species_name, regulation_id=regulation_id)
    if canonical_species is None:
        raise KeyError(f"{species_name} is not an eligible Pokemon or legal Mega Evolution in {regulation.display_name}.")

    provider = CachedPokeApiClient()
    move_source_species = resolve_builder_option_source_species_name(canonical_species)
    species_data = provider.get_species(canonical_species)
    return {
        "species": canonical_species,
        "types": list(species_data.types),
        "abilities": list(provider.get_species_abilities(canonical_species)),
        "moves": list(get_allowed_moves_for_species(move_source_species)),
        "base_stats": {
            "hp": species_data.base_hp,
            "attack": species_data.base_attack,
            "defense": species_data.base_defense,
            "special_attack": species_data.base_special_attack,
            "special_defense": species_data.base_special_defense,
            "speed": species_data.base_speed,
        },
        "required_item": resolve_required_item_for_species(canonical_species),
    }


def build_builder_move_payload(move_name: str) -> dict[str, object]:
    provider = CachedPokeApiClient()
    return asdict(provider.get_move(move_name))


def _resolve_damage_side(
    side: dict[str, object],
    provider: MetadataProvider,
    regulation_id: str,
) -> tuple[SpeciesData, dict[str, int], MoveData | None]:
    raw_species = str(side.get("species") or "").strip()
    if not raw_species:
        raise KeyError("A species is required for both attacker and defender.")
    canonical = resolve_regulation_species_name(raw_species, regulation_id=regulation_id) or raw_species
    species = provider.get_species(canonical)
    evs = {str(k): int(v) for k, v in (side.get("evs") or {}).items()}
    pokemon_set = PokemonSet(
        species=canonical,
        moves=[],
        item=side.get("item") or None,
        ability=side.get("ability") or None,
        nature=side.get("nature") or None,
        evs=evs,
    )
    stats = _normalized_member_stats(TeamMember(pokemon_set=pokemon_set, species_data=species, move_data=()))
    move = None
    move_name = side.get("move")
    if move_name:
        move = provider.get_move(str(move_name))
    return species, stats, move


def build_damage_payload(payload: dict[str, object]) -> dict[str, object]:
    """Interactive single-hit damage calculation for the /api/damage endpoint."""

    regulation_id = str(payload.get("regulationId") or DEFAULT_REGULATION_ID)
    attacker_side = dict(payload.get("attacker") or {})
    defender_side = dict(payload.get("defender") or {})
    field_input = dict(payload.get("field") or {})

    provider = CachedPokeApiClient()
    attacker_species, attacker_stats, move = _resolve_damage_side(attacker_side, provider, regulation_id)
    defender_species, defender_stats, _ = _resolve_damage_side(defender_side, provider, regulation_id)

    if move is None:
        raise LookupError("Select an attacking move to calculate damage.")

    attacker = combatant_from_stats(
        attacker_species,
        attacker_stats,
        ability=attacker_side.get("ability") or None,
        item=attacker_side.get("item") or None,
    )
    defender = combatant_from_stats(
        defender_species,
        defender_stats,
        ability=defender_side.get("ability") or None,
        item=defender_side.get("item") or None,
    )

    spread = field_input.get("spread")
    if spread is None:
        spread = move.target_name in _SPREAD_TARGET_NAMES
    conditions = FieldConditions(
        weather=field_input.get("weather") or None,
        spread=bool(spread),
        crit=bool(field_input.get("crit", False)),
        attacker_atk_stage=int(field_input.get("attackerAtkStage", 0) or 0),
        defender_def_stage=int(field_input.get("defenderDefStage", 0) or 0),
        attacker_burned=bool(field_input.get("attackerBurned", False)),
        reflect=bool(field_input.get("reflect", False)),
        light_screen=bool(field_input.get("lightScreen", False)),
    )

    result = compute_damage(attacker, defender, move, conditions)
    return {
        "ok": True,
        "attacker": {"species": attacker.species, "types": list(attacker.types), "stats": attacker_stats},
        "defender": {"species": defender.species, "types": list(defender.types), "stats": defender_stats},
        "move": {"name": move.name, "type": move.type_name, "category": move.damage_class, "power": move.power},
        "result": asdict(result) if result is not None else None,
    }


def build_preview_payload(
    my_team_text: str,
    opponent_team_text: str,
    regulation_id: str = DEFAULT_REGULATION_ID,
) -> dict[str, object]:
    """Preview-trainer recommendation for the /api/preview endpoint."""
    return analyze_preview(my_team_text, opponent_team_text, regulation_id=regulation_id)


def build_slot_doctor_payload(team_text: str, regulation_id: str = DEFAULT_REGULATION_ID) -> dict[str, object]:
    """Slot-doctor diagnosis + M-A-legal fixes for the /api/slot-doctor endpoint."""
    return analyze_slots(team_text, regulation_id=regulation_id)


def build_analysis_route_payload(team_text: str, regulation_id: str = DEFAULT_REGULATION_ID) -> tuple[dict[str, object], int]:
    try:
        analysis = analyze_team_text(team_text, regulation_id=regulation_id)
    except IllegalTeamError as error:
        return {
            "ok": False,
            "message": str(error),
            "legality": error.legality.to_dict(),
        }, 400

    return {
        "ok": True,
        "analysis": analysis.to_dict(),
    }, 200