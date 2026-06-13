"""Pokémon Zone usage cross-check (best-effort tertiary source).

Pokémon Zone is bot-protected and frequently answers automated requests with a
403. It is therefore strictly best-effort: a failure returns ``available=False``
and reconciliation proceeds on the authoritative Limitless data. When the page is
reachable, usage rows are parsed leniently (a Pokémon name paired with a nearby
percentage).
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ...data import normalize_showdown_name
from ..http import HttpError, get_text
from . import SourceUsage

PROVENANCE_URL = "https://www.pokemon-zone.com/champions/"
_PERCENT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def parse_usage_html(html: str) -> dict[str, float]:
    """Lenient parse: find rows that contain both a Pokémon link and a percentage."""

    soup = BeautifulSoup(html, "html.parser")
    token_pct: dict[str, float] = {}

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/pokemon/" not in href and "/champions/pokemon" not in href:
            continue
        name = anchor.get_text(strip=True)
        if not name:
            continue
        container = anchor.find_parent(["li", "tr", "div"]) or anchor.parent
        text = container.get_text(" ", strip=True) if container else name
        match = _PERCENT_PATTERN.search(text)
        if not match:
            continue
        token = normalize_showdown_name(name, convert_gender_suffix=True)
        if token and token not in token_pct:
            token_pct[token] = round(float(match.group(1)), 2)

    return token_pct


def fetch_usage(*, sleep=None) -> SourceUsage:
    kwargs = {} if sleep is None else {"sleep": sleep}
    try:
        html = get_text(PROVENANCE_URL, **kwargs)
    except HttpError as error:
        return SourceUsage(
            name="Pokémon Zone",
            provenance_url=PROVENANCE_URL,
            available=False,
            note=f"unavailable ({error.reason})",
        )

    token_pct = parse_usage_html(html)
    if not token_pct:
        return SourceUsage(
            name="Pokémon Zone",
            provenance_url=PROVENANCE_URL,
            available=False,
            note="no usage rows found in page markup",
        )

    return SourceUsage(
        name="Pokémon Zone",
        provenance_url=PROVENANCE_URL,
        available=True,
        token_pct=token_pct,
        note=f"parsed {len(token_pct)} usage rows",
    )
