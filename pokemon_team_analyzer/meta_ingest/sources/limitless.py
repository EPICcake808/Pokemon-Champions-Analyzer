"""Limitless tournament API source — the authoritative structured backbone.

Uses the official, documented API at ``https://play.limitlesstcg.com/api``
(docs: ``docs.limitlesstcg.com/developer``). A single
``GET /tournaments/{id}/standings`` call returns both placements and each
player's *structured* roster, so one call per tournament yields everything we
need for real usage stats and team discovery — no HTML scraping.

Roster Pokemon arrive as structured entries::

    {"id": "lucario", "name": "Lucario", "item": "Lucarionite",
     "ability": "Inner Focus", "attacks": [...], "nature": "Jolly", "tera": "Fighting"}

The ``id`` is already in the analyzer's catalog slug form (e.g. ``arcanine-hisui``).
Mega evolutions are only signalled by the held item, so :func:`species_token`
applies the mega transform using the analyzer's own
``MEGA_STONE_TO_BASE_SPECIES`` map to stay token-compatible with the rest of the app.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ...data import normalize_showdown_name
from ...regulations import ALL_MEGA_STONE_TO_BASE_SPECIES
from .. import DEFAULT_FORMAT_CODE
from ..http import HttpError, get_json

API_BASE = "https://play.limitlesstcg.com/api"
WEB_BASE = "https://play.limitlesstcg.com"
GAME = "VGC"

# Normalized stone base species (e.g. "charizard") -> indicates the holder mega-evolves.
# Uses the union of every regulation's Mega stones so M-B (and later) Mega holders tokenize
# correctly, not just M-A's.
_STONE_BASE_TOKENS = {
    stone: tuple(normalize_showdown_name(base, convert_gender_suffix=True) for base in bases)
    for stone, bases in ALL_MEGA_STONE_TO_BASE_SPECIES.items()
}

# Mega stones whose resulting catalog token is not simply ``{base_id}-mega``.
# A held mega stone is species-locked, so the item alone identifies the mega.
# ``Floettite`` -> Eternal Flower Floette, which the catalog tokenizes as
# ``floette-mega`` (and which Pikalytics also lists as ``floette-mega``).
_SPECIAL_MEGA_TOKENS = {
    "Floettite": "floette-mega",
}


@dataclass(frozen=True)
class Tournament:
    id: str
    name: str
    date: str
    format: str
    players: int
    # Prestige tier used for usage weighting. Grassroots platform events are "online";
    # official events (from limitlessvgc) carry "regional"/"international"/"worlds"/etc.
    tier: str = "online"
    # Which source the tournament came from ("limitless" platform vs "limitlessvgc").
    source: str = "limitless"

    @property
    def url(self) -> str:
        if self.source == "limitlessvgc":
            return f"https://limitlessvgc.com/tournaments/{self.id}"
        return f"{WEB_BASE}/tournament/{self.id}/standings"


@dataclass
class Roster:
    """One player's team within a tournament."""

    tournament: Tournament
    player: str
    placing: int | None
    record_text: str
    species_tokens: tuple[str, ...]
    showdown_text: str
    decklist: list[dict[str, Any]] = field(default_factory=list)
    # Official-source team-detail id (limitlessvgc /teams/{id}), when known.
    team_id: str | None = None

    @property
    def species_key(self) -> str:
        """Order-independent identity for de-duplicating identical teams."""

        return "|".join(sorted(self.species_tokens))


def _auth_headers() -> dict[str, str]:
    api_key = os.getenv("LIMITLESS_API_KEY", "").strip()
    return {"X-Access-Key": api_key} if api_key else {}


def species_token(entry: dict[str, Any]) -> str:
    """Resolve a decklist entry to a catalog-aligned, mega-aware species token."""

    base_id = str(entry.get("id") or "").strip().lower()
    if not base_id:
        base_id = normalize_showdown_name(str(entry.get("name") or ""), convert_gender_suffix=True)
    if not base_id:
        return ""

    item = str(entry.get("item") or "").strip()
    special_token = _SPECIAL_MEGA_TOKENS.get(item)
    if special_token:
        return special_token
    stone_bases = _STONE_BASE_TOKENS.get(item)
    if stone_bases and base_id in stone_bases:
        lowered_item = item.lower()
        if lowered_item.endswith(" x"):
            return f"{base_id}-mega-x"
        if lowered_item.endswith(" y"):
            return f"{base_id}-mega-y"
        return f"{base_id}-mega"
    return base_id


def render_showdown_text(decklist: list[dict[str, Any]]) -> str:
    """Render a structured Limitless decklist into Showdown export text.

    The output is consumed by ``parse_showdown_team`` / the analyzer, so mega
    resolution, mode inference, and archetype scoring all reuse existing logic.
    """

    blocks: list[str] = []
    for member in decklist:
        name = str(member.get("name") or "").strip()
        if not name:
            continue
        item = str(member.get("item") or "").strip()
        header = f"{name} @ {item}" if item else name
        lines = [header]

        ability = str(member.get("ability") or "").strip()
        if ability:
            lines.append(f"Ability: {ability}")
        tera = str(member.get("tera") or "").strip()
        if tera:
            lines.append(f"Tera Type: {tera}")
        nature = str(member.get("nature") or "").strip()
        if nature:
            lines.append(f"{nature} Nature")
        for move in member.get("attacks", []) or []:
            move_name = str(move).strip()
            if move_name:
                lines.append(f"- {move_name}")
        if len(lines) == 1:  # No usable detail beyond the species name.
            continue
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def _is_target_format(format_code: str, wanted: str) -> bool:
    return format_code.strip().upper() == wanted.strip().upper()


def list_tournaments(
    *,
    since_days: int = 30,
    format_code: str = DEFAULT_FORMAT_CODE,
    min_players: int = 8,
    max_tournaments: int = 60,
    page_size: int = 50,
    max_pages: int = 20,
    now: datetime | None = None,
    sleep=None,
) -> list[Tournament]:
    """List completed VGC tournaments matching ``format_code`` within the date window.

    The API returns tournaments newest-first, so paging stops once results fall
    before the window. Filtering by ``format == format_code`` (default ``"M-A"``) is
    done client-side to be robust regardless of server-side format filtering.
    """

    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = current_time - timedelta(days=since_days)
    headers = _auth_headers()
    collected: list[Tournament] = []

    for page in range(1, max_pages + 1):
        url = f"{API_BASE}/tournaments?game={GAME}&limit={page_size}&page={page}"
        kwargs: dict[str, Any] = {"headers": headers}
        if sleep is not None:
            kwargs["sleep"] = sleep
        rows = get_json(url, **kwargs)
        if not isinstance(rows, list) or not rows:
            break

        crossed_window = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_date = str(row.get("date") or "")
            parsed_date = _parse_iso(raw_date)
            if parsed_date is not None and parsed_date < cutoff:
                crossed_window = True
                continue
            if not _is_target_format(str(row.get("format") or ""), format_code):
                continue
            players = int(row.get("players") or 0)
            if players < min_players:
                continue
            tournament_id = str(row.get("id") or "").strip()
            if not tournament_id:
                continue
            collected.append(
                Tournament(
                    id=tournament_id,
                    name=str(row.get("name") or tournament_id),
                    date=raw_date,
                    format=str(row.get("format") or ""),
                    players=players,
                )
            )
            if len(collected) >= max_tournaments:
                return collected

        if crossed_window:
            break

    return collected


def fetch_rosters(tournament: Tournament, *, sleep=None) -> list[Roster]:
    """Fetch every player's roster for one tournament via the standings endpoint."""

    url = f"{API_BASE}/tournaments/{tournament.id}/standings"
    kwargs: dict[str, Any] = {"headers": _auth_headers()}
    if sleep is not None:
        kwargs["sleep"] = sleep
    entries = get_json(url, **kwargs)
    if not isinstance(entries, list):
        return []

    rosters: list[Roster] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        decklist = entry.get("decklist")
        if not isinstance(decklist, list) or not decklist:
            continue
        tokens = tuple(
            token
            for token in (species_token(member) for member in decklist if isinstance(member, dict))
            if token
        )
        # A legal VGC team is 4-6 distinct species; tolerate the common case only.
        if not 3 <= len(set(tokens)) <= 6:
            continue
        rosters.append(
            Roster(
                tournament=tournament,
                player=str(entry.get("player") or entry.get("name") or "unknown"),
                placing=_coerce_placing(entry.get("placing")),
                record_text=_format_record(entry.get("record")),
                species_tokens=tokens,
                showdown_text=render_showdown_text(decklist),
                decklist=[m for m in decklist if isinstance(m, dict)],
            )
        )
    return rosters


def collect_rosters(
    *,
    since_days: int = 30,
    format_code: str = DEFAULT_FORMAT_CODE,
    min_players: int = 8,
    max_tournaments: int = 60,
    now: datetime | None = None,
    sleep=None,
    on_progress=None,
) -> tuple[list[Roster], list[Tournament], list[str]]:
    """Collect rosters across the tournament window.

    Returns ``(rosters, tournaments, warnings)``. A standings fetch that fails for
    a single tournament is recorded as a warning rather than aborting the run.
    """

    tournaments = list_tournaments(
        since_days=since_days,
        format_code=format_code,
        min_players=min_players,
        max_tournaments=max_tournaments,
        now=now,
        sleep=sleep,
    )
    rosters: list[Roster] = []
    warnings: list[str] = []
    used_tournaments: list[Tournament] = []

    for index, tournament in enumerate(tournaments, start=1):
        try:
            tournament_rosters = fetch_rosters(tournament, sleep=sleep)
        except HttpError as error:
            warnings.append(f"standings fetch failed for {tournament.name!r}: {error.reason}")
            continue
        if tournament_rosters:
            rosters.extend(tournament_rosters)
            used_tournaments.append(tournament)
        if on_progress is not None:
            on_progress(index, len(tournaments), tournament, len(tournament_rosters))

    return rosters, used_tournaments, warnings


def _coerce_placing(value: Any) -> int | None:
    try:
        placing = int(value)
    except (TypeError, ValueError):
        return None
    return placing if placing > 0 else None


def _format_record(record: Any) -> str:
    if not isinstance(record, dict):
        return ""
    wins = int(record.get("wins") or 0)
    losses = int(record.get("losses") or 0)
    ties = int(record.get("ties") or 0)
    return f"{wins}-{losses}-{ties}"


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
