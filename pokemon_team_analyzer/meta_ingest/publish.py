"""Publish a built feed to the web app's secured publish route.

The inverted pipeline: this (running in CI, not the Vercel request path) POSTs the
already-validated feed to ``/api/meta-snapshot/publish``, which authorizes and upserts
it into the published board. Authorization mirrors the existing refresh routes
(``isMetaSnapshotRefreshAuthorized``): ``Authorization: Bearer <secret>``.
"""

from __future__ import annotations

import os

from .http import HttpError, post_json


def resolve_publish_secret() -> str:
    """Resolve the bearer secret the publish route expects.

    Mirrors the web's ``isMetaSnapshotRefreshAuthorized`` precedence
    (``META_SNAPSHOT_REFRESH_SECRET`` then ``CRON_SECRET``).
    """

    return (
        os.getenv("META_SNAPSHOT_REFRESH_SECRET", "").strip()
        or os.getenv("CRON_SECRET", "").strip()
    )


def publish_feed(feed: dict[str, object], publish_url: str, *, secret: str | None = None) -> dict[str, object]:
    """POST ``feed`` to ``publish_url``. Raises :class:`HttpError` / ``ValueError`` on failure."""

    resolved_secret = secret if secret is not None else resolve_publish_secret()
    if not resolved_secret:
        raise ValueError(
            "No publish secret found. Set META_SNAPSHOT_REFRESH_SECRET (or CRON_SECRET) "
            "to authorize the publish request."
        )

    response = post_json(
        publish_url,
        feed,
        headers={"Authorization": f"Bearer {resolved_secret}"},
    )
    if response.status >= 300:
        raise HttpError(publish_url, response.status, response.body[:300])

    import json

    try:
        return json.loads(response.body)
    except json.JSONDecodeError:
        return {"status": response.status, "body": response.body[:300]}
