"""Pikalytics usage cross-check (secondary source).

Pikalytics has no public JSON API, but its "Most Used" leaderboard for the
Champions Reg M-A pokedex is server-rendered. Each row is an
``a.tournament-top20-card`` whose final href path segment is already a
catalog-aligned token (e.g. ``.../Charizard-Mega-Y``) and whose
``span.tournament-top20-usage`` holds the percentage. We parse that with
BeautifulSoup (already a project dependency) and degrade gracefully — any failure
returns ``available=False`` so reconciliation simply flags Pikalytics as missing.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..http import HttpError, get_text
from . import SourceUsage

FORMAT_SLUG = "gen9championsvgc2026regma"
PROVENANCE_URL = f"https://www.pikalytics.com/pokedex/{FORMAT_SLUG}"
_PERCENT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def parse_usage_html(html: str) -> dict[str, float]:
    """Parse the server-rendered leaderboard into ``{token: percent}``."""

    soup = BeautifulSoup(html, "html.parser")
    token_pct: dict[str, float] = {}

    for card in soup.select("a.tournament-top20-card"):
        href = card.get("href") or ""
        slug = href.rstrip("/").rsplit("/", 1)[-1] if href else ""
        token = slug.strip().lower()
        if not token:
            data_name = card.get("data-name") or ""
            token = data_name.strip().lower().replace(" ", "-")
        if not token:
            continue

        usage_node = card.select_one(".tournament-top20-usage")
        usage_text = usage_node.get_text(strip=True) if usage_node else ""
        if not usage_text:
            # Fall back to the aria-label ("... 51.50 percent usage").
            usage_text = str(card.get("aria-label") or "")
        match = _PERCENT_PATTERN.search(usage_text)
        if not match:
            continue
        token_pct[token] = round(float(match.group(1)), 2)

    return token_pct


def fetch_usage(*, sleep=None) -> SourceUsage:
    kwargs = {} if sleep is None else {"sleep": sleep}
    try:
        html = get_text(PROVENANCE_URL, **kwargs)
    except HttpError as error:
        return SourceUsage(
            name="Pikalytics",
            provenance_url=PROVENANCE_URL,
            available=False,
            note=f"fetch failed: {error.reason}",
        )

    token_pct = parse_usage_html(html)
    if not token_pct:
        return SourceUsage(
            name="Pikalytics",
            provenance_url=PROVENANCE_URL,
            available=False,
            note="no usage rows found in page markup",
        )

    return SourceUsage(
        name="Pikalytics",
        provenance_url=PROVENANCE_URL,
        available=True,
        token_pct=token_pct,
        note=f"parsed {len(token_pct)} leaderboard rows",
    )
