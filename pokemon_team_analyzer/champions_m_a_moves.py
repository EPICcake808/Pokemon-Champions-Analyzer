from __future__ import annotations

import json
import re
import ssl
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi
from bs4 import BeautifulSoup

from .cache_paths import resolve_cache_path
# M-B's eligible-species tuple is the union of every regulation's pool (M-A + the M-B
# additions), so form expansion / page caching covers newer species too. The data module
# depends only on M-A data, so this import introduces no cycle.
from .champions_regulation_m_b_data import ELIGIBLE_SPECIES as _ALL_ELIGIBLE_SPECIES


MOVE_CACHE_PATH = resolve_cache_path("champions_m_a_moves_cache.json")
POKEDEX_BASE_URL = "https://www.serebii.net/pokedex-champions"
USER_AGENT = "Mozilla/5.0"

SPECIES_SLUG_OVERRIDES = {
    "eternalflowerfloette": "floette",
    "kommoo": "kommo-o",
    "mrrime": "mr.rime",
    "watchog": "watchog",
}


class CachedChampionsMoveListProvider:
    def __init__(self, cache_path: Path | None = None, timeout_seconds: float = 10.0) -> None:
        self.cache_path = cache_path or MOVE_CACHE_PATH
        self.timeout_seconds = timeout_seconds
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())
        self._cache = self._load_cache()

    def get_allowed_moves(self, species_name: str) -> tuple[str, ...]:
        cached = self._cache.get(species_name)
        if cached:
            return tuple(cached)

        self._populate_page_cache(species_name)
        cached = self._cache.get(species_name)
        if cached:
            return tuple(cached)

        raise LookupError(f"Could not resolve Champions move list for '{species_name}'.")

    def _populate_page_cache(self, species_name: str) -> None:
        page_species_name = _base_species_name(species_name)
        slug = _page_slug_for_species(species_name)
        html = self._fetch_html(f"{POKEDEX_BASE_URL}/{slug}/")
        tables = _parse_move_tables(html)
        related_species = _related_species_names(page_species_name)

        for related_species_name in related_species:
            moves = _moves_for_species_from_tables(related_species_name, tables)
            if moves:
                self._cache[related_species_name] = list(moves)

        self._save_cache()

    def _fetch_html(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=self.timeout_seconds, context=self._ssl_context) as response:
                encoding = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(encoding, errors="replace")
        except (HTTPError, URLError) as error:
            raise LookupError(f"Could not fetch Champions move data from {url}.") from error

    def _load_cache(self) -> dict[str, list[str]]:
        if not self.cache_path.exists():
            return {}

        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(raw, dict):
            return {}

        cache: dict[str, list[str]] = {}
        for species_name, moves in raw.items():
            if isinstance(species_name, str) and isinstance(moves, list):
                cache[species_name] = [str(move) for move in moves]
        return cache

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._cache, indent=2, sort_keys=True), encoding="utf-8")
        except OSError:
            # Keep the request alive even if the runtime filesystem is read-only.
            return


_DEFAULT_MOVE_PROVIDER = CachedChampionsMoveListProvider()


def get_allowed_moves_for_species(species_name: str) -> tuple[str, ...]:
    return _DEFAULT_MOVE_PROVIDER.get_allowed_moves(species_name)


def _base_species_name(species_name: str) -> str:
    return species_name.split(" (", 1)[0].strip()


def _page_slug_for_species(species_name: str) -> str:
    base_species = _base_species_name(species_name)
    normalized = unicodedata.normalize("NFKD", base_species).encode("ascii", "ignore").decode("ascii").lower()
    normalized = normalized.replace("'", "").replace(".", "").replace(":", "")
    normalized = normalized.replace(" ", "")
    return SPECIES_SLUG_OVERRIDES.get(normalized, normalized)


def _related_species_names(base_species_name: str) -> tuple[str, ...]:
    return tuple(species_name for species_name in _ALL_ELIGIBLE_SPECIES if _base_species_name(species_name) == base_species_name)


def _parse_move_tables(html: str) -> dict[str, dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    tables: dict[str, dict[str, object]] = {}

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        heading = rows[0].get_text(" ", strip=True)
        header = rows[1].get_text(" ", strip=True)
        if "Attack Name" not in header or ("Standard Moves" not in heading and "Special Moves" not in heading):
            continue

        moves: list[str] = []
        form_moves: dict[str, list[str]] = {}
        row_index = 2

        while row_index < len(rows):
            cells = rows[row_index].find_all(["td", "th"])
            link = cells[0].find("a", href=re.compile(r"/attackdex-champions/")) if cells else None
            if link is None:
                row_index += 1
                continue

            move_name = _normalized_move_name(link.get_text(" ", strip=True))
            if move_name:
                moves.append(move_name)
                form_label = _form_label_for_row(heading, rows, row_index, cells)
                if form_label is not None:
                    form_moves.setdefault(form_label, []).append(move_name)

            row_index += 1

        tables[heading] = {
            "moves": tuple(sorted(set(moves))),
            "form_moves": {
                label: tuple(sorted(set(label_moves)))
                for label, label_moves in form_moves.items()
            },
        }

    return tables


def _form_label_for_row(
    heading: str,
    rows: list[object],
    row_index: int,
    cells: list[object],
) -> str | None:
    if "Special Moves" in heading and row_index + 1 < len(rows):
        next_cells = rows[row_index + 1].find_all(["td", "th"])
        if len(next_cells) >= 2:
            candidate = next_cells[-1].get_text(" ", strip=True)
            if candidate.endswith("Only"):
                return candidate

    if len(cells) >= 8:
        candidate = cells[-1].get_text(" ", strip=True)
        if candidate:
            return candidate

    return None


def _normalized_move_name(move_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", move_name).encode("ascii", "ignore").decode("ascii").lower()
    normalized = normalized.replace("'", "").replace(".", "").replace(":", "")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized


def _moves_for_species_from_tables(
    species_name: str,
    tables: dict[str, dict[str, object]],
) -> tuple[str, ...]:
    moves: set[str] = set()

    if species_name == "Rotom (Rotom)":
        moves.update(tables.get("Standard Moves", {}).get("moves", ()))
    elif species_name.startswith("Rotom ("):
        moves.update(tables.get("Standard Moves", {}).get("moves", ()))
        form_label = f"{species_name.removeprefix('Rotom (').removesuffix(')')} Only"
        moves.update(tables.get("Special Moves", {}).get("form_moves", {}).get(form_label, ()))
    elif species_name in {"Raichu (Alolan Form)", "Ninetales (Alolan Form)"}:
        moves.update(tables.get("Alola Form Standard Moves", {}).get("moves", ()))
    elif species_name.endswith("(Hisuian Form)"):
        moves.update(tables.get("Hisuian Form Standard Moves", {}).get("moves", ()))
    elif species_name.endswith("(Galarian Form)"):
        moves.update(tables.get("Galarian Form Standard Moves", {}).get("moves", ()))
    elif species_name in {"Meowstic (Male)", "Basculegion (Male)"}:
        moves.update(tables.get("Standard Moves - Male", {}).get("moves", ()))
    elif species_name in {"Meowstic (Female)", "Basculegion (Female)"}:
        moves.update(tables.get("Standard Moves - Female", {}).get("moves", ()))
    elif species_name == "Lycanroc (Midday Form)":
        moves.update(tables.get("Standard Moves", {}).get("moves", ()))
    elif species_name == "Lycanroc (Midnight Form)":
        moves.update(tables.get("Standard Moves - Midnight Form", {}).get("moves", ()))
    elif species_name == "Lycanroc (Dusk Form)":
        moves.update(tables.get("Standard Moves - Dusk Form", {}).get("moves", ()))
    elif species_name.startswith("Tauros (Paldean Form"):
        moves.update(tables.get("Paldean Form Standard Moves", {}).get("moves", ()))
    elif species_name in {"Floette", "Eternal Flower Floette"}:
        moves.update(tables.get("Standard Moves - Eternal Floette", {}).get("moves", ()))
    else:
        moves.update(tables.get("Standard Moves", {}).get("moves", ()))

    return tuple(sorted(moves))