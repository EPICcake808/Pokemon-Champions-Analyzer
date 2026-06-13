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
from .limitless import Roster, Tournament, _parse_iso, render_showdown_text, species_token

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
        team_link = row.select_one('a[href^="/teams/"]')
        team_id = team_link["href"].rstrip("/").rsplit("/", 1)[-1] if team_link else None
        rosters.append(
            Roster(
                tournament=tournament,
                player=(row.get("data-name") or "unknown").strip(),
                placing=placing if placing > 0 else None,
                record_text="",
                # Base species from the standings overview (no items) -> usage-only until
                # enriched from the team-detail page below.
                species_tokens=tuple(tokens),
                showdown_text="",
                decklist=[],
                team_id=team_id if (team_id and team_id.isdigit()) else None,
            )
        )

    return rosters


def parse_team_detail(html: str) -> list[dict]:
    """Parse a /teams/{id} page into a structured decklist (id/name/item/ability/attacks).

    Matches the shape ``limitless.render_showdown_text`` / discovery expect, so official
    top-cut teams reuse the same mega-resolution and mode inference as grassroots teams.
    """

    soup = BeautifulSoup(html, "html.parser")
    decklist: list[dict] = []
    for block in soup.select(".pkmn"):
        species_id = (block.get("data-id") or "").strip().lower()
        name_node = block.select_one(".name")
        name = name_node.get_text(strip=True) if name_node else species_id
        item = _detail_text(block, ".item")
        ability = _detail_text(block, ".ability").removeprefix("Ability:").strip()
        nature = _detail_text(block, ".nature").removesuffix("Nature").strip()
        tera = _detail_text(block, ".tera").replace("Tera Type", "").replace(":", "").strip()
        moves = [m.get_text(strip=True) for m in block.select(".move, .moves li, [class*='move'] li")]
        if not moves:
            move_node = block.select_one("[class*='move']")
            if move_node:
                # Some layouts concatenate moves in one node; split on capitalized words.
                moves = re.findall(r"[A-Z][a-zA-Z'\- ]*?(?=[A-Z]|$)", move_node.get_text(" ", strip=True))
                moves = [m.strip() for m in moves if len(m.strip()) >= 3]
        if not species_id:
            continue
        decklist.append(
            {
                "id": species_id,
                "name": name,
                "item": item,
                "ability": ability,
                "nature": nature,
                "tera": tera,
                "attacks": moves[:4],
            }
        )
    return decklist


def _detail_text(block, selector: str) -> str:
    node = block.select_one(selector)
    return node.get_text(strip=True) if node else ""


def fetch_team_detail(team_id: str, *, sleep=None) -> list[dict]:
    kwargs = {} if sleep is None else {"sleep": sleep}
    html = get_text(f"{BASE}/teams/{team_id}", **kwargs)
    return parse_team_detail(html)


def _enrich_with_decklist(roster: Roster, decklist: list[dict]) -> Roster:
    """Return a copy of ``roster`` carrying a full decklist for shell discovery."""

    tokens = tuple(
        token for token in (species_token(m) for m in decklist if m.get("id")) if token
    )
    return Roster(
        tournament=roster.tournament,
        player=roster.player,
        placing=roster.placing,
        record_text=roster.record_text,
        species_tokens=tokens or roster.species_tokens,
        showdown_text=render_showdown_text(decklist),
        decklist=decklist,
        team_id=roster.team_id,
    )


def fetch_official_rosters(tournament: Tournament, *, sleep=None) -> list[Roster]:
    kwargs = {} if sleep is None else {"sleep": sleep}
    html = get_text(f"{BASE}/tournaments/{tournament.id}", **kwargs)
    return parse_standings(tournament, html)


def collect_official_rosters(
    *,
    since_days: int = 60,
    top_cut_for_discovery: int = 32,
    now: datetime | None = None,
    sleep=None,
    on_progress=None,
) -> tuple[list[Roster], list[Tournament], list[str]]:
    """Collect official-event rosters. Best-effort: a single failed page is a warning.

    Every reported team feeds the weighted usage stats (base species from the standings
    overview). The top ``top_cut_for_discovery`` finishers of each event are additionally
    enriched with full decklists (from their /teams/{id} pages) so the deepest official
    runs become first-class inputs to shell discovery — the teams that actually define the
    metagame and get netdecked to ladder and smaller events.

    Officials are infrequent, so the default window is wider (60 days) than grassroots.
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
        if not tournament_rosters:
            continue

        # Enrich the top finishers with full decklists for discovery.
        ranked = sorted(
            tournament_rosters,
            key=lambda r: r.placing if r.placing is not None else 9_999,
        )
        for roster in ranked[:top_cut_for_discovery]:
            if not roster.team_id:
                continue
            try:
                decklist = fetch_team_detail(roster.team_id, sleep=sleep)
            except HttpError as error:
                warnings.append(f"team detail failed ({tournament.name} #{roster.placing}): {error.reason}")
                continue
            if decklist:
                rosters.append(_enrich_with_decklist(roster, decklist))
            else:
                rosters.append(roster)
        # The remaining finishers contribute to usage with base species only.
        rosters.extend(ranked[top_cut_for_discovery:])

        used.append(tournament)
        if on_progress is not None:
            on_progress(index, len(tournaments), tournament, len(tournament_rosters))

    return rosters, used, warnings
