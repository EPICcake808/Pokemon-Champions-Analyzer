"""Local, multi-source meta ingestion for Champions regulations (default Regulation M-A).

This subpackage builds the published meta-snapshot feed from real, structured
tournament data instead of the hand-curated in-repo board. It is intentionally
designed to run *outside* of the Vercel request path (locally now, in CI later):
full Python, real retries, readable logs.

Pipeline overview:

* :mod:`.sources.limitless` is the authoritative backbone. It uses the official
  Limitless tournament API (``play.limitlesstcg.com/api``) to list completed
  Champions tournaments for the requested ``--format-code`` (default ``"M-A"``)
  and pull every player's structured roster. ``--format-code`` (the data source)
  and ``--regulation`` (the board's legality/tag) are decoupled, so a newer
  regulation can be seeded from an older format's results.
* :mod:`.sources.pikalytics` and :mod:`.sources.pokemon_zone` are secondary
  usage cross-checks used only by :mod:`.reconcile`.
* :mod:`.usage` computes real overall usage (teams-containing-species over total
  teams) — the headline metric, replacing curated "board share".
* :mod:`.discover` clusters the real rosters into representative team shells by
  reusing the analyzer (:func:`pokemon_team_analyzer.service.build_analysis_route_payload`).
* :mod:`.schema` validates the assembled feed against the same contract the web
  app enforces (``metaSnapshotFeedSchema`` in ``web/src/lib/meta-snapshots.ts``)
  before anything is written.
* :mod:`.build` orchestrates the above and exposes the CLI
  (``python -m pokemon_team_analyzer.meta_ingest``).
"""

from __future__ import annotations

DEFAULT_REGULATION_ID = "champions_regulation_m_a"
DEFAULT_FORMAT_CODE = "M-A"
USER_AGENT = "pokemon-champions-analyzer-meta-ingest/0.3 (+https://github.com/EPICcake808/Pokemon-Champions-Analyzer)"

__all__ = [
    "DEFAULT_REGULATION_ID",
    "DEFAULT_FORMAT_CODE",
    "USER_AGENT",
]
