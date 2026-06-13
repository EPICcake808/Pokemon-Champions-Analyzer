"""Data sources for meta ingestion.

* :mod:`.limitless` — authoritative structured backbone (official tournament API).
* :mod:`.pikalytics` — secondary usage cross-check (HTML, server-rendered).
* :mod:`.pokemon_zone` — best-effort tertiary usage cross-check (bot-protected).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceUsage:
    """A secondary source's usage view, used only for reconciliation.

    ``available`` is ``False`` when the source could not be fetched/parsed (e.g.
    Pokémon Zone returning 403). Reconciliation tolerates this and flags it.
    """

    name: str
    provenance_url: str
    available: bool
    token_pct: dict[str, float] = field(default_factory=dict)
    note: str = ""


__all__ = ["SourceUsage"]
