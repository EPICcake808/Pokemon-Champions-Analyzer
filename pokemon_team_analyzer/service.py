from __future__ import annotations

from dataclasses import asdict

from .analyzer import analyze_team_text
from .champions_m_a_moves import get_allowed_moves_for_species
from .data import CachedPokeApiClient
from .regulations import (
    DEFAULT_REGULATION_ID,
    IllegalTeamError,
    get_regulation,
    regulation_catalog_as_dict,
    resolve_builder_option_source_species_name,
    resolve_regulation_species_name,
)


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
    return {
        "species": canonical_species,
        "abilities": list(provider.get_species_abilities(canonical_species)),
        "moves": list(get_allowed_moves_for_species(move_source_species)),
    }


def build_builder_move_payload(move_name: str) -> dict[str, object]:
    provider = CachedPokeApiClient()
    return asdict(provider.get_move(move_name))


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