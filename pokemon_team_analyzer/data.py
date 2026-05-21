from __future__ import annotations

import json
import re
import ssl
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi

from .cache_paths import resolve_cache_path
from .models import MoveData, MoveStatChange, SpeciesData


API_BASE = "https://pokeapi.co/api/v2"
DEFAULT_CACHE_PATH = resolve_cache_path("pokeapi_cache.json")

SPECIES_ALIAS_OVERRIDES = {
    "aegislash": "aegislash-shield",
    "arcanine-hisuian-form": "arcanine-hisui",
    "avalugg-hisuian-form": "avalugg-hisui",
    "basculegion-female": "basculegion-female",
    "basculegion-male": "basculegion-male",
    "decidueye-hisuian-form": "decidueye-hisui",
    "farfetchd": "farfetchd",
    "goodra-hisuian-form": "goodra-hisui",
    "gourgeist-jumbo-variety": "gourgeist-super",
    "gourgeist-large-variety": "gourgeist-large",
    "gourgeist-medium-variety": "gourgeist-average",
    "gourgeist-small-variety": "gourgeist-small",
    "lycanroc-dusk-form": "lycanroc-dusk",
    "lycanroc-midday-form": "lycanroc-midday",
    "lycanroc-midnight-form": "lycanroc-midnight",
    "maushold": "maushold-family-of-four",
    "meowstic-female": "meowstic-female",
    "meowstic-male": "meowstic-male",
    "mimikyu": "mimikyu-disguised",
    "morpeko": "morpeko-full-belly",
        "palafin": "palafin-zero",
    "sirfetchd": "sirfetchd",
    "mr-mime": "mr-mime",
    "mr-rime": "mr-rime",
    "mime-jr": "mime-jr",
    "ninetales-alolan-form": "ninetales-alola",
    "nidoran-female": "nidoran-f",
    "nidoran-male": "nidoran-m",
    "raichu-alolan-form": "raichu-alola",
    "rotom-fan-rotom": "rotom-fan",
    "rotom-frost-rotom": "rotom-frost",
    "rotom-heat-rotom": "rotom-heat",
    "rotom-mow-rotom": "rotom-mow",
    "rotom-rotom": "rotom",
    "rotom-wash-rotom": "rotom-wash",
    "samurott-hisuian-form": "samurott-hisui",
    "slowbro-galarian-form": "slowbro-galar",
    "slowking-galarian-form": "slowking-galar",
    "stunfisk-galarian-form": "stunfisk-galar",
    "tauros-paldean-form-aqua-breed": "tauros-paldea-aqua-breed",
    "tauros-paldean-form-blaze-breed": "tauros-paldea-blaze-breed",
    "tauros-paldean-form-combat-breed": "tauros-paldea-combat-breed",
    "typhlosion-hisuian-form": "typhlosion-hisui",
    "type-null": "type-null",
    "zoroark-hisuian-form": "zoroark-hisui",
}


class MetadataProvider(Protocol):
    def get_species(self, species_name: str) -> SpeciesData:
        ...

    def get_move(self, move_name: str) -> MoveData:
        ...


class CachedPokeApiClient:
    def __init__(self, cache_path: Path | None = None, timeout_seconds: float = 10.0) -> None:
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self.timeout_seconds = timeout_seconds
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        self._cache = self._load_cache()

    def get_species(self, species_name: str) -> SpeciesData:
        cache_key = normalize_showdown_name(species_name, convert_gender_suffix=True)
        cached = self._cache["pokemon"].get(cache_key)
        if cached and _cached_species_has_full_stats(cached):
            return _deserialize_species_data(cached)

        payload = self._resolve_species_payload(species_name)
        trimmed = _trimmed_species_payload(species_name, payload)
        self._cache["pokemon"][cache_key] = trimmed
        self._save_cache()
        return _deserialize_species_data(trimmed)

    def get_species_abilities(self, species_name: str) -> tuple[str, ...]:
        cache_key = normalize_showdown_name(species_name, convert_gender_suffix=True)
        cached = self._cache["pokemon"].get(cache_key)
        cached_abilities = _cached_species_abilities(cached)
        if cached_abilities is not None:
            return cached_abilities

        payload = self._resolve_species_payload(species_name)
        trimmed = _trimmed_species_payload(species_name, payload)
        self._cache["pokemon"][cache_key] = trimmed
        self._save_cache()
        return tuple(str(ability_name) for ability_name in trimmed.get("abilities", ()))

    def get_move(self, move_name: str) -> MoveData:
        cache_key = normalize_showdown_name(move_name)
        cached = self._cache["move"].get(cache_key)
        if cached and _cached_move_has_full_metadata(cached):
            return _deserialize_move_data(cached)

        for candidate in move_name_candidates(move_name):
            try:
                payload = self._fetch_json(f"move/{quote(candidate)}")
            except HTTPError as error:
                if error.code == 404:
                    continue
                raise
            meta = payload.get("meta") or {}
            trimmed = {
                "name": move_name,
                "api_name": payload["name"],
                "type_name": payload["type"]["name"],
                "damage_class": payload["damage_class"]["name"],
                "power": payload.get("power"),
                "accuracy": payload.get("accuracy"),
                "pp": payload.get("pp", 0),
                "short_effect": _extract_english_short_effect(payload),
                "effect_chance": payload["effect_chance"],
                "category_name": meta.get("category", {}).get("name", "unknown"),
                "ailment_name": meta.get("ailment", {}).get("name", "none"),
                "ailment_chance": meta.get("ailment_chance", 0),
                "flinch_chance": meta.get("flinch_chance", 0),
                "healing": meta.get("healing", 0),
                "stat_chance": meta.get("stat_chance", 0),
                "stat_changes": [
                    {
                        "stat_name": stat_change["stat"]["name"],
                        "change": stat_change["change"],
                    }
                    for stat_change in payload.get("stat_changes", [])
                ],
                "priority": payload["priority"],
                "target_name": payload["target"]["name"],
            }
            self._cache["move"][cache_key] = trimmed
            self._save_cache()
            return _deserialize_move_data(trimmed)

        raise LookupError(f"Could not resolve move '{move_name}' via PokeAPI.")

    def _fetch_json(self, path: str) -> dict[str, Any]:
        url = f"{API_BASE}/{path}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "pokemon-team-analyzer/0.1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds, context=self._ssl_context) as response:
                return json.load(response)
        except URLError as error:
            raise ConnectionError(f"Failed to fetch '{url}': {error}") from error

    def _fetch_species_payload(self, species_name: str) -> dict[str, Any]:
        for candidate in pokemon_name_candidates(species_name):
            try:
                return self._fetch_json(f"pokemon/{quote(candidate)}")
            except HTTPError as error:
                if error.code == 404:
                    continue
                raise

        raise LookupError(f"Could not resolve Pokemon '{species_name}' via PokeAPI.")

    def _resolve_species_payload(self, species_name: str) -> dict[str, Any]:
        try:
            return self._fetch_species_payload(species_name)
        except LookupError:
            fallback_species_name = _base_species_from_mega_species_name(species_name)
            if fallback_species_name is None:
                raise
            return self._fetch_species_payload(fallback_species_name)

    def _load_cache(self) -> dict[str, dict[str, dict[str, Any]]]:
        if not self.cache_path.exists():
            return {"pokemon": {}, "move": {}}

        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"pokemon": {}, "move": {}}

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache, indent=2, sort_keys=True), encoding="utf-8")
        except OSError:
            # Keep the request alive even if the runtime filesystem is read-only.
            return


def pokemon_name_candidates(species_name: str) -> list[str]:
    base = normalize_showdown_name(species_name, convert_gender_suffix=True)
    mega_candidate = _mega_species_candidate(species_name)
    candidates = [candidate for candidate in (mega_candidate, SPECIES_ALIAS_OVERRIDES.get(base, base)) if candidate]

    if base.endswith("-male"):
        candidates.append(base.removesuffix("-male"))
    if base.endswith("-female"):
        candidates.append(base.removesuffix("-female"))

    return _deduplicate(candidates)


def move_name_candidates(move_name: str) -> list[str]:
    return _deduplicate([normalize_showdown_name(move_name)])


def _mega_species_candidate(species_name: str) -> str | None:
    stripped = species_name.strip()
    lowered = stripped.lower()
    if lowered.startswith("mega "):
        base_name = stripped[5:].strip()
        if base_name.lower().endswith(" x") or base_name.lower().endswith(" y"):
            return f"{normalize_showdown_name(base_name[:-2], convert_gender_suffix=True)}-mega-{base_name[-1].lower()}"
        return f"{normalize_showdown_name(base_name, convert_gender_suffix=True)}-mega"
    if re.search(r"-mega(?:-[xy])?$", lowered):
        return normalize_showdown_name(species_name, convert_gender_suffix=True)
    return None


def _base_species_from_mega_species_name(species_name: str) -> str | None:
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


def normalize_showdown_name(name: str, *, convert_gender_suffix: bool = False) -> str:
    normalized = name.strip().lower()
    normalized = normalized.replace("♀", " female")
    normalized = normalized.replace("♂", " male")
    normalized = normalized.replace("é", "e")
    normalized = normalized.replace("’", "'")

    if convert_gender_suffix:
        normalized = re.sub(r"\s*\((m|f)\)$", lambda match: " male" if match.group(1) == "m" else " female", normalized)

    normalized = normalized.replace("'", "")
    normalized = normalized.replace(".", "")
    normalized = normalized.replace(":", "")
    normalized = normalized.replace(",", "")
    normalized = normalized.replace("%", "")
    normalized = normalized.replace(" ", "-")
    normalized = re.sub(r"[^a-z0-9-]", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _deserialize_move_data(payload: dict[str, Any]) -> MoveData:
    stat_changes = tuple(
        MoveStatChange(
            stat_name=str(stat_change["stat_name"]),
            change=int(stat_change["change"]),
        )
        for stat_change in payload.get("stat_changes", [])
    )

    return MoveData(
        name=str(payload["name"]),
        api_name=str(payload["api_name"]),
        type_name=str(payload["type_name"]),
        damage_class=str(payload["damage_class"]),
        power=_as_optional_int(payload.get("power")),
        accuracy=_as_optional_int(payload.get("accuracy")),
        pp=_as_int(payload.get("pp"), default=0),
        short_effect=str(payload.get("short_effect", "")),
        effect_chance=_as_optional_int(payload.get("effect_chance")),
        category_name=str(payload.get("category_name", "unknown")),
        ailment_name=str(payload.get("ailment_name", "none")),
        ailment_chance=_as_int(payload.get("ailment_chance"), default=0),
        flinch_chance=_as_int(payload.get("flinch_chance"), default=0),
        healing=_as_int(payload.get("healing"), default=0),
        stat_chance=_as_int(payload.get("stat_chance"), default=0),
        stat_changes=stat_changes,
        priority=_as_int(payload.get("priority"), default=0),
        target_name=str(payload.get("target_name", "unknown")),
    )


def _deserialize_species_data(payload: dict[str, Any]) -> SpeciesData:
    return SpeciesData(
        name=str(payload["name"]),
        api_name=str(payload["api_name"]),
        types=tuple(str(type_name) for type_name in payload.get("types", [])),
        base_hp=_as_int(payload.get("base_hp"), default=0),
        base_attack=_as_int(payload.get("base_attack"), default=0),
        base_defense=_as_int(payload.get("base_defense"), default=0),
        base_special_attack=_as_int(payload.get("base_special_attack"), default=0),
        base_special_defense=_as_int(payload.get("base_special_defense"), default=0),
        base_speed=_as_int(payload.get("base_speed"), default=0),
    )


def _trimmed_species_payload(species_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    base_stats = {
        stat["stat"]["name"]: stat["base_stat"]
        for stat in payload["stats"]
    }
    abilities = tuple(
        ability_entry["ability"]["name"]
        for ability_entry in sorted(payload.get("abilities", []), key=lambda entry: entry.get("slot", 0))
    )

    return {
        "name": species_name,
        "api_name": payload["name"],
        "types": tuple(
            slot["type"]["name"]
            for slot in sorted(payload["types"], key=lambda slot: slot["slot"])
        ),
        "abilities": abilities,
        "base_hp": base_stats["hp"],
        "base_attack": base_stats["attack"],
        "base_defense": base_stats["defense"],
        "base_special_attack": base_stats["special-attack"],
        "base_special_defense": base_stats["special-defense"],
        "base_speed": base_stats["speed"],
    }


def _extract_english_short_effect(payload: dict[str, Any]) -> str:
    for effect_entry in payload.get("effect_entries", []):
        language = effect_entry.get("language", {})
        if language.get("name") == "en":
            return str(effect_entry.get("short_effect", ""))
    return ""


def _as_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _cached_species_has_full_stats(payload: dict[str, Any]) -> bool:
    return all(
        key in payload
        for key in (
            "base_hp",
            "base_attack",
            "base_defense",
            "base_special_attack",
            "base_special_defense",
            "base_speed",
        )
    )


def _cached_species_abilities(payload: dict[str, Any] | None) -> tuple[str, ...] | None:
    if not payload or "abilities" not in payload:
        return None
    return tuple(str(ability_name) for ability_name in payload.get("abilities", ()))


def _cached_move_has_full_metadata(payload: dict[str, Any]) -> bool:
    return all(
        key in payload
        for key in (
            "short_effect",
            "effect_chance",
            "power",
            "accuracy",
            "pp",
            "category_name",
            "ailment_name",
            "ailment_chance",
            "flinch_chance",
            "healing",
            "stat_chance",
            "stat_changes",
            "priority",
            "target_name",
        )
    )
