from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .champions_m_a_data import (
    ALLOWED_HELD_ITEMS,
    ALLOWED_MEGA_EVOLUTIONS,
    ELIGIBLE_SPECIES,
    MEGA_STONE_TO_BASE_SPECIES,
)
from .champions_m_a_moves import get_allowed_moves_for_species
from .data import MetadataProvider, normalize_showdown_name
from .models import PokemonSet, TeamAnalysis
from .showdown import parse_showdown_team


DEFAULT_REGULATION_ID = "champions_regulation_m_a"

SHOWDOWN_SPECIES_ALIASES = {
    "arcanine-hisui": "arcanine (hisuian form)",
    "avalugg-hisui": "avalugg (hisuian form)",
    "basculegion (f)": "basculegion (female)",
    "basculegion (m)": "basculegion (male)",
    "basculegion-f": "basculegion (female)",
    "basculegion-female": "basculegion (female)",
    "basculegion-m": "basculegion (male)",
    "basculegion-male": "basculegion (male)",
    "decidueye-hisui": "decidueye (hisuian form)",
    "goodra-hisui": "goodra (hisuian form)",
    "gourgeist": "gourgeist (medium variety)",
    "gourgeist-average": "gourgeist (medium variety)",
    "gourgeist-large": "gourgeist (large variety)",
    "gourgeist-small": "gourgeist (small variety)",
    "gourgeist-super": "gourgeist (jumbo variety)",
    "lycanroc": "lycanroc (midday form)",
    "lycanroc-dusk": "lycanroc (dusk form)",
    "lycanroc-midday": "lycanroc (midday form)",
    "lycanroc-midnight": "lycanroc (midnight form)",
    "maushold-family-of-three": "maushold",
    "maushold-family-of-four": "maushold",
    "meowstic-f": "meowstic (female)",
    "meowstic-m": "meowstic (male)",
    "morpeko-hangry": "morpeko",
    "ninetales-alola": "ninetales (alolan form)",
    "palafin-hero": "palafin",
    "raichu-alola": "raichu (alolan form)",
    "rotom": "rotom (rotom)",
    "rotom-fan": "rotom (fan rotom)",
    "rotom-frost": "rotom (frost rotom)",
    "rotom-heat": "rotom (heat rotom)",
    "rotom-mow": "rotom (mow rotom)",
    "rotom-wash": "rotom (wash rotom)",
    "samurott-hisui": "samurott (hisuian form)",
    "slowbro-galar": "slowbro (galarian form)",
    "slowking-galar": "slowking (galarian form)",
    "stunfisk-galar": "stunfisk (galarian form)",
    "tauros-paldea-aqua": "tauros (paldean form (aqua breed))",
    "tauros-paldea-blaze": "tauros (paldean form (blaze breed))",
    "tauros-paldea-combat": "tauros (paldean form (combat breed))",
    "typhlosion-hisui": "typhlosion (hisuian form)",
    "zoroark-hisui": "zoroark (hisuian form)",
}

REGIONAL_FORM_SYNONYMS = {
    "alolan": ("alolan", "alola"),
    "galarian": ("galarian", "galar"),
    "hisuian": ("hisuian", "hisui"),
}


def _build_generated_species_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}

    regional_form_pattern = re.compile(r"^(?P<base>.+) \((?P<form>Alolan|Galarian|Hisuian) Form\)$", re.IGNORECASE)
    paldean_form_pattern = re.compile(
        r"^(?P<base>.+) \(Paldean Form \((?P<breed>Combat Breed|Blaze Breed|Aqua Breed)\)\)$",
        re.IGNORECASE,
    )

    for species_name in ELIGIBLE_SPECIES:
        canonical_name = species_name.lower()

        regional_match = regional_form_pattern.match(species_name)
        if regional_match is not None:
            base_name = regional_match.group("base")
            form_name = regional_match.group("form").lower()
            for synonym in REGIONAL_FORM_SYNONYMS[form_name]:
                aliases[normalize_showdown_name(f"{synonym} {base_name}", convert_gender_suffix=True)] = canonical_name
                aliases[normalize_showdown_name(f"{base_name} {synonym}", convert_gender_suffix=True)] = canonical_name
            continue

        paldean_match = paldean_form_pattern.match(species_name)
        if paldean_match is not None:
            base_name = paldean_match.group("base")
            breed_name = paldean_match.group("breed")
            breed_variants = {breed_name, breed_name.removesuffix(" Breed")}
            for region_name in ("paldean", "paldea"):
                for breed_variant in breed_variants:
                    aliases[normalize_showdown_name(f"{region_name} {base_name} {breed_variant}", convert_gender_suffix=True)] = canonical_name
                    aliases[normalize_showdown_name(f"{base_name} {region_name} {breed_variant}", convert_gender_suffix=True)] = canonical_name

    return aliases


GENERATED_SPECIES_ALIASES = _build_generated_species_aliases()

MEGA_STONE_TO_MEGA_NAME = {
    "abomasite": "mega abomasnow",
    "absolite": "mega absol",
    "aerodactylite": "mega aerodactyl",
    "aggronite": "mega aggron",
    "alakazite": "mega alakazam",
    "altarianite": "mega altaria",
    "ampharosite": "mega ampharos",
    "audinite": "mega audino",
    "banettite": "mega banette",
    "beedrillite": "mega beedrill",
    "blastoisinite": "mega blastoise",
    "cameruptite": "mega camerupt",
    "chandelurite": "mega chandelure",
    "charizardite x": "mega charizard x",
    "charizardite y": "mega charizard y",
    "chesnaughtite": "mega chesnaught",
    "chimechite": "mega chimecho",
    "clefablite": "mega clefable",
    "crabominite": "mega crabominable",
    "delphoxite": "mega delphox",
    "dragoninite": "mega dragonite",
    "drampanite": "mega drampa",
    "emboarite": "mega emboar",
    "excadrite": "mega excadrill",
    "feraligite": "mega feraligatr",
    "floettite": "mega floette",
    "froslassite": "mega froslass",
    "galladite": "mega gallade",
    "garchompite": "mega garchomp",
    "gardevoirite": "mega gardevoir",
    "gengarite": "mega gengar",
    "glalitite": "mega glalie",
    "glimmoranite": "mega glimmora",
    "golurkite": "mega golurk",
    "greninjite": "mega greninja",
    "gyaradosite": "mega gyarados",
    "hawluchanite": "mega hawlucha",
    "heracronite": "mega heracross",
    "houndoominite": "mega houndoom",
    "kangaskhanite": "mega kangaskhan",
    "lopunnite": "mega lopunny",
    "lucarionite": "mega lucario",
    "manectite": "mega manectric",
    "medichamite": "mega medicham",
    "meganiumite": "mega meganium",
    "meowsticite": "mega meowstic",
    "pidgeotite": "mega pidgeot",
    "pinsirite": "mega pinsir",
    "sablenite": "mega sableye",
    "scizorite": "mega scizor",
    "scovillainite": "mega scovillain",
    "sharpedonite": "mega sharpedo",
    "skarmorite": "mega skarmory",
    "slowbronite": "mega slowbro",
    "starminite": "mega starmie",
    "steelixite": "mega steelix",
    "tyranitarite": "mega tyranitar",
    "venusaurite": "mega venusaur",
    "victreebelite": "mega victreebel",
}


def _normalized_item_name(item: str | None) -> str:
    return (item or "").strip().lower()


def _normalized_species_name(species_name: str) -> str:
    lowered = species_name.strip().lower()
    if lowered in SHOWDOWN_SPECIES_ALIASES:
        return SHOWDOWN_SPECIES_ALIASES[lowered]
    normalized = normalize_showdown_name(species_name, convert_gender_suffix=True)
    if normalized in SHOWDOWN_SPECIES_ALIASES:
        return SHOWDOWN_SPECIES_ALIASES[normalized]
    if normalized in GENERATED_SPECIES_ALIASES:
        return GENERATED_SPECIES_ALIASES[normalized]
    return lowered


def _canonical_mega_name(species_name: str) -> str | None:
    stripped = species_name.strip()
    lowered = stripped.lower()
    if lowered.startswith("mega "):
        return stripped.lower()
    if "-mega-" in lowered:
        base_name, suffix = re.split(r"-mega-", stripped, maxsplit=1, flags=re.IGNORECASE)
        return f"Mega {base_name.strip()} {suffix.strip().upper()}".lower()
    if lowered.endswith("-mega"):
        return f"Mega {stripped[:-5].strip()}".lower()
    return None


def _base_species_from_mega_species(species_name: str) -> str | None:
    stripped = species_name.strip()
    lowered = stripped.lower()
    if lowered.startswith("mega "):
        base_name = stripped[5:].strip()
        if base_name.lower().endswith(" x") or base_name.lower().endswith(" y"):
            return base_name[:-2].strip()
        return base_name
    if "-mega-" in lowered:
        return re.split(r"-mega-", stripped, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    if lowered.endswith("-mega"):
        return stripped[:-5].strip()
    return None


OFFICIAL_SPECIES_BY_KEY = {
    _normalized_species_name(species_name): species_name
    for species_name in ELIGIBLE_SPECIES
}
OFFICIAL_ITEM_BY_KEY = {
    _normalized_item_name(item_name): item_name
    for item_name in ALLOWED_HELD_ITEMS
}
OFFICIAL_MEGA_BY_KEY = {
    mega_name.lower(): mega_name
    for mega_name in ALLOWED_MEGA_EVOLUTIONS
}
MEGA_STONE_TO_BASE_KEYS = {
    _normalized_item_name(stone_name): tuple(_normalized_species_name(species_name) for species_name in species_names)
    for stone_name, species_names in MEGA_STONE_TO_BASE_SPECIES.items()
}
MEGA_TO_BASE_KEYS = {
    mega_name: MEGA_STONE_TO_BASE_KEYS[stone_name]
    for stone_name, mega_name in MEGA_STONE_TO_MEGA_NAME.items()
}
MEGA_TO_REQUIRED_ITEM_KEYS = {
    mega_name: stone_name
    for stone_name, mega_name in MEGA_STONE_TO_MEGA_NAME.items()
}


@dataclass(frozen=True)
class TeamLegalityIssue:
    code: str
    message: str
    member_name: str | None = None
    team_slot: int | None = None
    value: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "member_name": self.member_name,
            "team_slot": self.team_slot,
            "value": self.value,
        }


@dataclass(frozen=True)
class TeamLegalityResult:
    regulation_id: str
    is_legal: bool
    issues: tuple[TeamLegalityIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "regulation_id": self.regulation_id,
            "is_legal": self.is_legal,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class IllegalTeamError(ValueError):
    def __init__(self, legality: TeamLegalityResult) -> None:
        self.legality = legality
        lines = [f"Team is illegal for regulation '{legality.regulation_id}'."]
        lines.extend(f"- {issue.message}" for issue in legality.issues)
        super().__init__("\n".join(lines))


@dataclass(frozen=True)
class TournamentTeamEntry:
    slug: str
    regulation_id: str
    player_name: str
    placement: str
    event_name: str
    event_date: str
    source_archive_url: str
    source_event_url: str
    export_url: str
    team_text: str

    def to_dict(self, include_team_text: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "slug": self.slug,
            "regulation_id": self.regulation_id,
            "player_name": self.player_name,
            "placement": self.placement,
            "event_name": self.event_name,
            "event_date": self.event_date,
            "source_archive_url": self.source_archive_url,
            "source_event_url": self.source_event_url,
            "export_url": self.export_url,
        }
        if include_team_text:
            payload["team_text"] = self.team_text
        return payload


@dataclass(frozen=True)
class RegulationEntry:
    id: str
    display_name: str
    battle_type: str
    team_size: int
    source_ruleset_name: str
    source_ruleset_url: str
    source_eligible_pokemon_url: str
    source_held_items_url: str
    champions_status: str
    is_official_champions_regulation: bool
    notes: str
    eligible_species: tuple[str, ...]
    allowed_held_items: tuple[str, ...]
    allowed_mega_evolutions: tuple[str, ...]
    duplicate_held_items_disallowed: bool
    teams: tuple[TournamentTeamEntry, ...] = ()

    def to_dict(
        self,
        include_teams: bool = True,
        include_team_text: bool = False,
        include_rules: bool = False,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "display_name": self.display_name,
            "battle_type": self.battle_type,
            "team_size": self.team_size,
            "source_ruleset_name": self.source_ruleset_name,
            "source_ruleset_url": self.source_ruleset_url,
            "source_eligible_pokemon_url": self.source_eligible_pokemon_url,
            "source_held_items_url": self.source_held_items_url,
            "champions_status": self.champions_status,
            "is_official_champions_regulation": self.is_official_champions_regulation,
            "notes": self.notes,
            "eligible_pokemon_count": len(self.eligible_species),
            "allowed_held_item_count": len(self.allowed_held_items),
            "allowed_mega_evolution_count": len(self.allowed_mega_evolutions),
            "duplicate_held_items_disallowed": self.duplicate_held_items_disallowed,
            "team_count": len(self.teams),
        }
        if include_rules:
            payload["eligible_species"] = list(self.eligible_species)
            payload["allowed_held_items"] = list(self.allowed_held_items)
            payload["allowed_mega_evolutions"] = list(self.allowed_mega_evolutions)
            payload["required_items_by_mega_species"] = {
                OFFICIAL_MEGA_BY_KEY[mega_name]: OFFICIAL_ITEM_BY_KEY[required_item_key]
                for mega_name, required_item_key in sorted(MEGA_TO_REQUIRED_ITEM_KEYS.items())
                if mega_name in OFFICIAL_MEGA_BY_KEY
                and required_item_key in OFFICIAL_ITEM_BY_KEY
                and OFFICIAL_MEGA_BY_KEY[mega_name] in self.allowed_mega_evolutions
            }
        if include_teams:
            payload["teams"] = [team.to_dict(include_team_text=include_team_text) for team in self.teams]
        return payload


_BUILTIN_REGULATIONS = (
    RegulationEntry(
        id=DEFAULT_REGULATION_ID,
        display_name="Pokemon Champions Regulation M-A",
        battle_type="double",
        team_size=6,
        source_ruleset_name="Pokemon Champions Regulation Set M-A",
        source_ruleset_url="https://news.pokemon-home.com/en/page/751.html",
        source_eligible_pokemon_url="https://web-view.app.pokemonchampions.jp/battle/pages/events/rs177501629259kmzbny/en/pokemon.html",
        source_held_items_url="https://www.serebii.net/pokemonchampions/items.shtml",
        champions_status="official",
        is_official_champions_regulation=True,
        notes=(
            "Current official Pokemon Champions regulation. Teams must use only the official M-A eligible Pokemon, "
            "must use only allowed held items, and may not duplicate held items. Mega Evolution is allowed once per "
            "battle for the listed Mega Evolutions when the matching Mega Stone is held."
        ),
        eligible_species=ELIGIBLE_SPECIES,
        allowed_held_items=ALLOWED_HELD_ITEMS,
        allowed_mega_evolutions=ALLOWED_MEGA_EVOLUTIONS,
        duplicate_held_items_disallowed=True,
    ),
)

_REGULATION_BY_ID = {regulation.id: regulation for regulation in _BUILTIN_REGULATIONS}


def list_regulations() -> tuple[RegulationEntry, ...]:
    return _BUILTIN_REGULATIONS


def get_regulation(regulation_id: str) -> RegulationEntry:
    try:
        return _REGULATION_BY_ID[regulation_id]
    except KeyError as error:
        available = ", ".join(regulation.id for regulation in _BUILTIN_REGULATIONS)
        raise KeyError(f"Unknown regulation '{regulation_id}'. Available regulations: {available}") from error


def resolve_regulation_species_name(
    species_name: str,
    regulation_id: str = DEFAULT_REGULATION_ID,
) -> str | None:
    regulation = get_regulation(regulation_id)
    canonical_mega_name = _canonical_mega_name(species_name)
    if canonical_mega_name is not None:
        mega_species_by_key = {
            mega_species_name.lower(): mega_species_name
            for mega_species_name in regulation.allowed_mega_evolutions
        }
        resolved_mega_species = mega_species_by_key.get(canonical_mega_name)
        if resolved_mega_species is not None:
            return resolved_mega_species

    normalized_species = _normalized_species_name(species_name)
    species_by_key = {
        _normalized_species_name(eligible_species_name): eligible_species_name
        for eligible_species_name in regulation.eligible_species
    }
    return species_by_key.get(normalized_species)


def resolve_builder_option_source_species_name(species_name: str) -> str:
    return _base_species_from_mega_species(species_name) or species_name


def resolve_required_item_for_species(species_name: str) -> str | None:
    canonical_mega_name = _canonical_mega_name(species_name)
    if canonical_mega_name is None:
        return None

    required_item_key = MEGA_TO_REQUIRED_ITEM_KEYS.get(canonical_mega_name)
    if required_item_key is None:
        return None

    return OFFICIAL_ITEM_BY_KEY.get(required_item_key, required_item_key)


def regulation_catalog_as_dict(
    include_team_text: bool = False,
    include_rules: bool = False,
) -> list[dict[str, object]]:
    return [
        regulation.to_dict(
            include_teams=True,
            include_team_text=include_team_text,
            include_rules=include_rules,
        )
        for regulation in _BUILTIN_REGULATIONS
    ]


def validate_team_legality(
    team: Iterable[PokemonSet],
    regulation_id: str = DEFAULT_REGULATION_ID,
) -> TeamLegalityResult:
    regulation = get_regulation(regulation_id)
    team_sets = list(team)
    issues: list[TeamLegalityIssue] = []
    allowed_moves_cache: dict[str, frozenset[str]] = {}
    seen_items: dict[str, str] = {}

    if len(team_sets) != regulation.team_size:
        issues.append(
            TeamLegalityIssue(
                code="invalid_team_size",
                message=(
                    f"{regulation.display_name} requires exactly {regulation.team_size} Pokemon, "
                    f"but this team has {len(team_sets)}."
                ),
                value=str(len(team_sets)),
            )
        )

    for index, pokemon_set in enumerate(team_sets, start=1):
        member_name = pokemon_set.display_name
        normalized_species = _normalized_species_name(pokemon_set.species)
        normalized_item = _normalized_item_name(pokemon_set.item)
        declared_mega = _canonical_mega_name(pokemon_set.species)
        base_from_mega = _base_species_from_mega_species(pokemon_set.species)
        move_validation_species_name: str | None = None

        if declared_mega is not None:
            if declared_mega not in OFFICIAL_MEGA_BY_KEY:
                issues.append(
                    TeamLegalityIssue(
                        code="illegal_mega_species",
                        message=f"{pokemon_set.species} is not an allowed Mega Evolution in {regulation.display_name}.",
                        member_name=member_name,
                        team_slot=index,
                        value=pokemon_set.species,
                    )
                )
            if base_from_mega is not None and _normalized_species_name(base_from_mega) not in OFFICIAL_SPECIES_BY_KEY:
                issues.append(
                    TeamLegalityIssue(
                        code="illegal_species",
                        message=f"{base_from_mega} is not an eligible Pokemon in {regulation.display_name}.",
                        member_name=member_name,
                        team_slot=index,
                        value=base_from_mega,
                    )
                )
            elif base_from_mega is not None:
                move_validation_species_name = OFFICIAL_SPECIES_BY_KEY[_normalized_species_name(base_from_mega)]
        elif normalized_species not in OFFICIAL_SPECIES_BY_KEY:
            issues.append(
                TeamLegalityIssue(
                    code="illegal_species",
                    message=f"{pokemon_set.species} is not an eligible Pokemon in {regulation.display_name}.",
                    member_name=member_name,
                    team_slot=index,
                    value=pokemon_set.species,
                )
            )
        else:
            move_validation_species_name = OFFICIAL_SPECIES_BY_KEY[normalized_species]

        if normalized_item and normalized_item not in OFFICIAL_ITEM_BY_KEY:
            issues.append(
                TeamLegalityIssue(
                    code="illegal_item",
                    message=f"{pokemon_set.item} is not an allowed held item in {regulation.display_name}.",
                    member_name=member_name,
                    team_slot=index,
                    value=pokemon_set.item,
                )
            )

        if normalized_item in MEGA_STONE_TO_BASE_KEYS:
            allowed_base_species = set(MEGA_STONE_TO_BASE_KEYS[normalized_item])
            species_key_for_stone = _normalized_species_name(base_from_mega or pokemon_set.species)
            if species_key_for_stone not in allowed_base_species:
                readable_species = ", ".join(OFFICIAL_SPECIES_BY_KEY[species_key] for species_key in sorted(allowed_base_species))
                issues.append(
                    TeamLegalityIssue(
                        code="illegal_mega_stone_holder",
                        message=f"{pokemon_set.item} can only be held by {readable_species} in {regulation.display_name}.",
                        member_name=member_name,
                        team_slot=index,
                        value=pokemon_set.item,
                    )
                )
            expected_mega = MEGA_STONE_TO_MEGA_NAME[normalized_item]
            if declared_mega is not None and declared_mega != expected_mega:
                issues.append(
                    TeamLegalityIssue(
                        code="mismatched_mega_species",
                        message=(
                            f"{pokemon_set.species} does not match {pokemon_set.item}; the matching Mega Evolution is "
                            f"{OFFICIAL_MEGA_BY_KEY[expected_mega]}."
                        ),
                        member_name=member_name,
                        team_slot=index,
                        value=pokemon_set.species,
                    )
                )
        elif declared_mega is not None:
            issues.append(
                TeamLegalityIssue(
                    code="missing_mega_stone",
                    message=f"{pokemon_set.species} must hold its matching Mega Stone in {regulation.display_name}.",
                    member_name=member_name,
                    team_slot=index,
                    value=pokemon_set.item,
                )
            )

        if move_validation_species_name is not None:
            allowed_moves = allowed_moves_cache.get(move_validation_species_name)
            if allowed_moves is None:
                allowed_moves = frozenset(get_allowed_moves_for_species(move_validation_species_name))
                allowed_moves_cache[move_validation_species_name] = allowed_moves

            for move_name in pokemon_set.moves:
                if normalize_showdown_name(move_name) not in allowed_moves:
                    issues.append(
                        TeamLegalityIssue(
                            code="illegal_move",
                            message=(
                                f"{move_name} is not in {move_validation_species_name}'s Champions move list for "
                                f"{regulation.display_name}."
                            ),
                            member_name=member_name,
                            team_slot=index,
                            value=move_name,
                        )
                    )

        if normalized_item and regulation.duplicate_held_items_disallowed:
            previous_holder = seen_items.get(normalized_item)
            item_display_name = OFFICIAL_ITEM_BY_KEY.get(normalized_item, pokemon_set.item)
            if previous_holder is not None:
                issues.append(
                    TeamLegalityIssue(
                        code="duplicate_item",
                        message=(
                            f"{item_display_name} appears on both {previous_holder} and {member_name}, "
                            f"but duplicate held items are not allowed in {regulation.display_name}."
                        ),
                        member_name=member_name,
                        team_slot=index,
                        value=item_display_name,
                    )
                )
            else:
                seen_items[normalized_item] = member_name

    return TeamLegalityResult(
        regulation_id=regulation.id,
        is_legal=not issues,
        issues=tuple(issues),
    )


def validate_team_legality_text(
    team_text: str,
    regulation_id: str = DEFAULT_REGULATION_ID,
) -> TeamLegalityResult:
    return validate_team_legality(parse_showdown_team(team_text), regulation_id=regulation_id)


def analyze_tournament_team(
    team_entry: TournamentTeamEntry,
    metadata_provider: MetadataProvider | None = None,
) -> TeamAnalysis:
    from .analyzer import analyze_team_text

    return analyze_team_text(
        team_entry.team_text,
        metadata_provider=metadata_provider,
        regulation_id=team_entry.regulation_id,
    )