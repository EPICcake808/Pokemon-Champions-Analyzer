from __future__ import annotations

import re

from .models import PokemonSet


FORM_DESCRIPTOR_PATTERN = re.compile(
    r"^(?:M|F|Male|Female|Rotom|[A-Za-z-]+ Form|[A-Za-z-]+ Variety|[A-Za-z-]+ Rotom|Paldean Form \((?:Combat|Blaze|Aqua) Breed\)|(?:Combat|Blaze|Aqua) Breed)$"
)


def parse_showdown_team(team_text: str) -> list[PokemonSet]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", team_text.strip()) if block.strip()]
    team: list[PokemonSet] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        species_text, item = _parse_header(lines[0])
        nickname, species = _parse_species(species_text)
        ability = None
        level = None
        nature = None
        evs: dict[str, int] = {}
        moves: list[str] = []

        for line in lines[1:]:
            if line.startswith("Ability: "):
                ability = line.removeprefix("Ability: ").strip() or None
            elif line.startswith("Level: "):
                level = int(line.removeprefix("Level: ").strip())
            elif line.startswith("EVs: "):
                evs = _parse_evs(line.removeprefix("EVs: "))
            elif line.startswith("IVs: "):
                continue
            elif line.endswith(" Nature"):
                nature = line[: -len(" Nature")].strip() or None
            elif line.startswith("- "):
                moves.append(line[2:].strip())

        if not moves:
            raise ValueError(f"Pokemon set for '{species}' does not contain any moves.")

        team.append(
            PokemonSet(
                species=species,
                moves=moves,
                item=item,
                ability=ability,
                level=level,
                nature=nature,
                evs=evs,
                nickname=nickname,
            )
        )

    if not team:
        raise ValueError("No Pokemon sets were found in the Showdown import text.")

    return team


def _parse_header(header: str) -> tuple[str, str | None]:
    if " @ " not in header:
        return header.strip(), None
    species_text, item = header.split(" @ ", 1)
    return species_text.strip(), item.strip() or None


def _parse_species(species_text: str) -> tuple[str | None, str]:
    stripped = species_text.strip()
    if stripped.endswith(" (M)") or stripped.endswith(" (F)"):
        return None, stripped

    split = _split_nickname_and_species(stripped)
    if split is not None:
        nickname, species = split
        if not _looks_like_form_descriptor(species):
            return nickname, species

    return None, stripped


def _split_nickname_and_species(species_text: str) -> tuple[str, str] | None:
    if not species_text.endswith(")"):
        return None

    depth = 0
    for index in range(len(species_text) - 1, -1, -1):
        character = species_text[index]
        if character == ")":
            depth += 1
        elif character == "(":
            depth -= 1
            if depth == 0:
                if index == 0 or species_text[index - 1] != " ":
                    return None
                nickname = species_text[: index - 1].strip()
                species = species_text[index + 1 : -1].strip()
                if not nickname or not species:
                    return None
                return nickname, species

    return None


def _looks_like_form_descriptor(species_text: str) -> bool:
    return FORM_DESCRIPTOR_PATTERN.fullmatch(species_text.strip()) is not None


def _parse_evs(ev_text: str) -> dict[str, int]:
    evs: dict[str, int] = {}
    for part in ev_text.split("/"):
        cleaned = part.strip()
        if not cleaned:
            continue
        amount_text, stat = cleaned.split(" ", 1)
        evs[stat.strip()] = int(amount_text)
    return evs
