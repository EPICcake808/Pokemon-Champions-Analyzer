"""limitlessvgc.com — official Play! Pokémon event results (Regionals, Internationals,
Special Events, Players Cup, Worlds).

These official events are *not* on the grassroots ``play.limitlesstcg.com`` platform,
so they are ingested separately here to weight the meta board toward the biggest,
most prestigious tournaments and their deepest runs.

The listing (``/tournaments``) is server-rendered HTML; each row carries everything we
need as data-attributes::

    <tr data-date="2026-06-06" data-name="Special Event Turin" data-format="m-a"
        data-players="940" ...><td>…/tournaments/435…</td></tr>

so events are filtered to Regulation M-A by ``data-format`` and tiered by name. Each
tournament detail page (``/tournaments/{id}``) is a standings table of
``<tr data-rank="N">`` rows, each listing a player's team as base-species
``/pokemon/{token}`` links (no items/moves — so these rosters are usage-only, not used
for shell discovery). ``data-rank`` gives the placement used for top-cut weighting.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from bs4 import BeautifulSoup

from ..http import HttpError, get_text
from .limitless import Roster, Tournament, _parse_iso

BASE = "https://limitlessvgc.com"
TARGET_FORMAT = "m-a"

# Official-tier classification from the (trustworthy) official event name.
_INTERNATIONAL_CODES = re.compile(r"\b(naic|euic|ocic|laic)\b")


def classify_tier(name: str) -> str:
    lowered = name.lower()
    if "world" in lowered:
        return "worlds"
    if "international" in lowered or _INTERNATIONAL_CODES.search(lowered):
        return "international"
    if "players cup" in lowered or "player's cup" in lowered:
        return "players_cup"
    if "regional" in lowered:
        return "regional"
    if "special event" in lowered or "special championship" in lowered:
        return "special_event"
    return "other_official"


def parse_listing(html: str, *, since_days: int, now: datetime | None = None) -> list[Tournament]:
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = current_time - timedelta(days=since_days)
    soup = BeautifulSoup(html, "html.parser")
    tournaments: list[Tournament] = []

    for row in soup.select("tr[data-format]"):
        if (row.get("data-format") or "").strip().lower() != TARGET_FORMAT:
            continue
        link = row.select_one('a[href^="/tournaments/"]')
        if not link:
            continue
        tournament_id = link["href"].rstrip("/").rsplit("/", 1)[-1]
        if not tournament_id.isdigit():
            continue
        raw_date = (row.get("data-date") or "").strip()
        parsed_date = _parse_iso(raw_date) if raw_date else None
        if parsed_date is not None and parsed_date < cutoff:
            continue
        name = (row.get("data-name") or link.get_text(strip=True) or "").strip()
        try:
            players = int(row.get("data-players") or 0)
        except ValueError:
            players = 0
        tournaments.append(
            Tournament(
                id=tournament_id,
                name=name,
                date=raw_date,
                format=TARGET_FORMAT,
                players=players,
                tier=classify_tier(name),
                source="limitlessvgc",
            )
        )

    return tournaments


def list_official_tournaments(
    *, since_days: int = 60, now: datetime | None = None, sleep=None
) -> list[Tournament]:
    kwargs = {} if sleep is None else {"sleep": sleep}
    # The format filter narrows server-side; we still filter client-side for safety.
    html = get_text(f"{BASE}/tournaments?format={TARGET_FORMAT}", **kwargs)
    return parse_listing(html, since_days=since_days, now=now)


def parse_standings(tournament: Tournament, html: str) -> list[Roster]:
    soup = BeautifulSoup(html, "html.parser")
    rosters: list[Roster] = []

    for row in soup.select("tr[data-rank]"):
        try:
            placing = int(row.get("data-rank") or 0)
        except ValueError:
            placing = 0
        tokens: list[str] = []
        for anchor in row.select('a[href^="/pokemon/"]'):
            token = anchor["href"].rstrip("/").rsplit("/", 1)[-1].strip().lower()
            if token and token not in tokens:
                tokens.append(token)
        if not 3 <= len(tokens) <= 6:
            continue
        rosters.append(
            Roster(
                tournament=tournament,
                player=(row.get("data-name") or "unknown").strip(),
                placing=placing if placing > 0 else None,
                record_text="",
                species_tokens=tuple(tokens),
                showdown_text="",  # no decklist detail -> usage-only, not for discovery
                decklist=[],
            )
        )

    return rosters


def fetch_official_rosters(tournament: Tournament, *, sleep=None) -> list[Roster]:
    kwargs = {} if sleep is None else {"sleep": sleep}
    html = get_text(f"{BASE}/tournaments/{tournament.id}", **kwargs)
    return parse_standings(tournament, html)


def collect_official_rosters(
    *, since_days: int = 60, now: datetime | None = None, sleep=None, on_progress=None
) -> tuple[list[Roster], list[Tournament], list[str]]:
    """Collect official-event rosters. Best-effort: a single failed page is a warning.

    Officials are infrequent, so the default window is wider (60 days) than the
    grassroots window — a recent Regional or Special Event should still anchor the board.
    """

    warnings: list[str] = []
    try:
        tournaments = list_official_tournaments(since_days=since_days, now=now, sleep=sleep)
    except HttpError as error:
        return [], [], [f"limitlessvgc listing unavailable: {error.reason}"]

    rosters: list[Roster] = []
    used: list[Tournament] = []
    for index, tournament in enumerate(tournaments, start=1):
        try:
            tournament_rosters = fetch_official_rosters(tournament, sleep=sleep)
        except HttpError as error:
            warnings.append(f"official standings failed for {tournament.name!r}: {error.reason}")
            continue
        if tournament_rosters:
            rosters.extend(tournament_rosters)
            used.append(tournament)
        if on_progress is not None:
            on_progress(index, len(tournaments), tournament, len(tournament_rosters))

    return rosters, used, warnings
