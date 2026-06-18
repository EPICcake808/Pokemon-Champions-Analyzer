from __future__ import annotations

import json
import os
import re
import time
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .champions_m_a_tournament_meta import (
    TOURNAMENT_META_AS_OF as BUILT_IN_TOURNAMENT_META_AS_OF,
    TOURNAMENT_META_METHODOLOGY as BUILT_IN_TOURNAMENT_META_METHODOLOGY,
    TOURNAMENT_META_SOURCES as BUILT_IN_TOURNAMENT_META_SOURCES,
    TOURNAMENT_TEAM_SNAPSHOTS as BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS,
)
from .regulations import DEFAULT_REGULATION_ID, get_regulation


_SNAPSHOT_CACHE: dict[str, dict[str, object]] = {}

BUILT_IN_META_SNAPSHOT_SOURCE_LABEL = "Pokemon Champions Analyzer built-in Regulation M-A meta board"
BUILT_IN_META_SNAPSHOT_NOTES = (
    "Generated directly from the analyzer API's built-in Champions Regulation M-A tournament team snapshots.",
    "Use this endpoint as the frontend refresh source when you want the hosted meta board to republish from the analyzer's current curated board automatically.",
)


RUNTIME_USAGE_METHODOLOGY = (
    "Live overall usage from real tournament team lists: each Pokemon's share is the "
    "percentage of sampled Regulation M-A teams running it, cross-checked across sources."
)


# A brand-new regulation borrows the board of the regulation it extends until it has enough
# tournament data of its own. M-B extends M-A: while M-B's own board is thin (or absent) the
# M-B board shows the M-A field (the user's M-B-legal team is still analyzed against it under
# M-B); once M-B's own board reaches the sample-size cutoff the hand-off is automatic. Remove
# an entry to force a regulation onto its own board regardless of sample size.
_META_BOARD_FALLBACK_REGULATION_ID: dict[str, str] = {
    "champions_regulation_m_b": DEFAULT_REGULATION_ID,
}

# Minimum sampled-team count before a regulation switches from its proxy to its own board.
# Below this a board's usage percentages are too noisy to trust, so the proxy (the more
# established regulation it extends) is shown instead. Override via the env var to tune.
_META_BOARD_PROXY_MIN_SAMPLE_SIZE_DEFAULT = 30


def _meta_board_proxy_min_sample_size() -> int:
    raw = os.getenv("POKEMON_ANALYZER_META_BOARD_MIN_SAMPLE", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return _META_BOARD_PROXY_MIN_SAMPLE_SIZE_DEFAULT


def _own_board_sample_size(regulation_id: str) -> int:
    """Sampled-team count of a regulation's *own* published board (0 if it has none)."""
    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    if not base_url:
        return 0
    entry = _runtime_board_cache_entry(regulation_id, base_url)
    if not entry:
        return 0
    provenance = entry.get("provenance")
    sample_size = provenance.get("sample_size") if isinstance(provenance, dict) else None
    return sample_size if isinstance(sample_size, int) and not isinstance(sample_size, bool) else 0


def resolve_board_regulation_id(regulation_id: str | None) -> str:
    """The regulation whose meta board should actually be served for ``regulation_id``.

    A regulation with a configured fallback uses its *own* board once that board has enough
    sampled teams; until then it borrows the fallback regulation's board as a proxy.
    """
    resolved = regulation_id or DEFAULT_REGULATION_ID
    fallback = _META_BOARD_FALLBACK_REGULATION_ID.get(resolved)
    if fallback is None:
        return resolved
    if _own_board_sample_size(resolved) >= _meta_board_proxy_min_sample_size():
        return resolved
    return fallback


def _regulation_label(regulation_id: str) -> str:
    """Friendly short label for a regulation id, e.g. 'Regulation M-B'. Falls back to the id."""
    try:
        display_name = get_regulation(regulation_id).display_name
    except KeyError:
        return regulation_id
    return re.sub(r"^Pokemon Champions\s+", "", display_name).strip() or regulation_id


def is_proxy_board(regulation_id: str | None) -> bool:
    """True when ``regulation_id`` is borrowing another regulation's board as a proxy."""
    resolved = regulation_id or DEFAULT_REGULATION_ID
    return resolve_board_regulation_id(resolved) != resolved


def clear_runtime_meta_snapshot_cache() -> None:
    _SNAPSHOT_CACHE.clear()


def _normalize_runtime_common_meta_pokemon(raw_common_meta: Any) -> tuple[dict[str, object], ...]:
    """Normalize a feed's ``commonMetaPokemon`` (real usage) into analyzer row shape.

    The feed uses camelCase keys (``metaShare``/``whyUsed``/...); the analyzer's
    ``meta_analysis.common_pokemon`` rows use snake_case. Returns an empty tuple when
    the feed carries no usable usage rows, so callers fall back to board-share derivation.
    """

    if not isinstance(raw_common_meta, list):
        return ()

    rows: list[dict[str, object]] = []
    for item in raw_common_meta:
        if not isinstance(item, dict):
            continue
        species = item.get("species")
        meta_share = item.get("metaShare")
        if not isinstance(species, str) or not species.strip():
            continue
        if not isinstance(meta_share, (int, float)) or isinstance(meta_share, bool):
            continue
        featured_teams = [
            team.strip()
            for team in item.get("featuredTeams", [])
            if isinstance(team, str) and team.strip()
        ]
        rows.append(
            {
                "species": species.strip(),
                "meta_share": round(float(meta_share), 1),
                "why_used": str(item.get("whyUsed") or "").strip(),
                "what_it_does": str(item.get("whatItDoes") or "").strip(),
                "featured_teams": featured_teams,
            }
        )

    return tuple(rows)


def _built_in_meta_provenance() -> dict[str, object]:
    return {
        "as_of": BUILT_IN_TOURNAMENT_META_AS_OF,
        "source_label": "Built-in curated Regulation M-A board",
        "sources": [dict(source) for source in BUILT_IN_TOURNAMENT_META_SOURCES],
        "methodology": BUILT_IN_TOURNAMENT_META_METHODOLOGY,
        "is_live": False,
        # The built-in board ranks Pokemon by curated board share, not measured usage.
        "usage_based": False,
        "sample_size": None,
    }


def get_tournament_meta_provenance(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> dict[str, object]:
    """Return provenance (as-of date, sources, methodology) for the active meta board.

    When a live runtime snapshot is in use, its ``updatedAt``/``sourceLabel`` are surfaced
    so the UI can stamp the panel with the real publish time. Otherwise the honest built-in
    curated as-of date is used.
    """

    resolved_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    board_regulation_id = resolve_board_regulation_id(resolved_regulation_id)
    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    provenance: dict[str, object] | None = None
    if base_url:
        entry = _runtime_board_cache_entry(board_regulation_id, base_url)
        if entry and entry.get("provenance"):
            provenance = dict(cast(dict[str, object], entry["provenance"]))
    if provenance is None:
        provenance = _built_in_meta_provenance()
    if board_regulation_id != resolved_regulation_id:
        # Disclose that another regulation's field is shown as a proxy for this one.
        target_label = _regulation_label(resolved_regulation_id)
        source_label = _regulation_label(board_regulation_id)
        provenance["proxy_for_regulation_id"] = resolved_regulation_id
        provenance["proxy_source_regulation_id"] = board_regulation_id
        provenance["methodology"] = (
            f"{provenance.get('methodology', '')} Shown as the current proxy field for "
            f"{target_label}: no dedicated board exists for it yet, so the latest {source_label} "
            f"results are displayed and your team is evaluated under {target_label}'s expanded legality."
        ).strip()
    return provenance


def _isoformat_utc(moment: datetime | None = None) -> str:
    resolved_moment = (moment or datetime.now(UTC)).astimezone(UTC)
    return resolved_moment.isoformat().replace("+00:00", "Z")


def _serialize_snapshot_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_serialize_snapshot_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_snapshot_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_snapshot_value(item) for key, item in value.items()}
    return value


def build_built_in_meta_snapshot_document(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
    *,
    updated_at: datetime | None = None,
) -> dict[str, object]:
    resolved_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    timestamp = _isoformat_utc(updated_at)
    return {
        "regulationId": resolved_regulation_id,
        "updatedAt": timestamp,
        "sourceLabel": BUILT_IN_META_SNAPSHOT_SOURCE_LABEL,
        "notes": list(BUILT_IN_META_SNAPSHOT_NOTES),
        "tournamentTeamSnapshots": _serialize_snapshot_value(BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS),
    }


def build_built_in_meta_snapshot_feed(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    timestamp = generated_at or datetime.now(UTC)
    return {
        "version": 1,
        "generatedAt": _isoformat_utc(timestamp),
        "regulations": [
            build_built_in_meta_snapshot_document(
                regulation_id,
                updated_at=timestamp,
            )
        ],
    }


def _runtime_meta_snapshot_ttl_seconds() -> float:
    raw_value = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_TTL_SECONDS", "900").strip()
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        return 900.0


def _build_meta_snapshot_url(base_url: str, regulation_id: str) -> str:
    split_url = urlsplit(base_url)
    query_items = dict(parse_qsl(split_url.query, keep_blank_values=True))
    query_items.setdefault("regulationId", regulation_id)
    return urlunsplit(
        (
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(query_items),
            split_url.fragment,
        )
    )


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"The runtime meta snapshot is missing a valid {key} value.")
    return value.strip()


def _require_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"The runtime meta snapshot is missing a valid {key} value.")
    return float(value)


def _require_string_list(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"The runtime meta snapshot is missing a valid {key} list.")

    normalized_values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"The runtime meta snapshot has an invalid {key} entry.")
        normalized_values.append(item.strip())

    return tuple(normalized_values)


def _require_float_mapping(payload: dict[str, Any], key: str) -> dict[str, float]:
    value = payload.get(key)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"The runtime meta snapshot is missing a valid {key} mapping.")

    normalized_mapping: dict[str, float] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(f"The runtime meta snapshot has an invalid {key} key.")
        if not isinstance(raw_value, (int, float)):
            raise ValueError(f"The runtime meta snapshot has an invalid {key} value.")
        normalized_mapping[raw_key.strip()] = float(raw_value)

    return normalized_mapping


def _normalize_runtime_snapshot(raw_snapshot: dict[str, Any]) -> dict[str, object]:
    modes = _require_string_list(raw_snapshot, "modes")
    mode_weights = _require_float_mapping(raw_snapshot, "mode_weights")
    for mode_name in modes:
        if mode_name not in mode_weights:
            raise ValueError(f"The runtime meta snapshot is missing mode_weights for {mode_name}.")

    return {
        "slug": _require_string(raw_snapshot, "slug"),
        "label": _require_string(raw_snapshot, "label"),
        "source": _require_string(raw_snapshot, "source"),
        "result_label": _require_string(raw_snapshot, "result_label"),
        "field_relevance": _require_float(raw_snapshot, "field_relevance"),
        "popularity_weight": _require_float(raw_snapshot, "popularity_weight"),
        "result_weight": _require_float(raw_snapshot, "result_weight"),
        "modes": modes,
        "mode_weights": mode_weights,
        "broad_mix": _require_float_mapping(raw_snapshot, "broad_mix"),
        "key_pokemon": _require_string_list(raw_snapshot, "key_pokemon"),
        "key_cores": _require_string_list(raw_snapshot, "key_cores"),
    }


def _runtime_provenance_sources(payload: dict[str, Any]) -> list[dict[str, object]]:
    """Surface the feed's own provenance sources (Limitless/Pikalytics/...) when present.

    The automated feed writes a ``provenance.sources`` list of ``{name, url, available}``;
    map those to the ``{label, url}`` shape the UI renders. Falls back to the built-in
    curated sources when the feed does not carry its own.
    """

    feed_provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    mapped: list[dict[str, object]] = []

    # The authoritative source (Limitless) is recorded separately from the secondary
    # cross-checks; surface it first so the UI never omits the source the data came from.
    authoritative = feed_provenance.get("authoritativeSource")
    if isinstance(authoritative, dict):
        label = authoritative.get("name") or authoritative.get("label")
        url = authoritative.get("url")
        if isinstance(label, str) and isinstance(url, str) and label.strip() and url.strip():
            mapped.append({"label": label.strip(), "url": url.strip()})

    raw_sources = feed_provenance.get("sources")
    if isinstance(raw_sources, list):
        for source in raw_sources:
            if not isinstance(source, dict):
                continue
            label = source.get("name") or source.get("label")
            url = source.get("url")
            if isinstance(label, str) and isinstance(url, str) and label.strip() and url.strip():
                available = source.get("available")
                mapped.append(
                    {
                        "label": label.strip() if available is not False else f"{label.strip()} (unavailable)",
                        "url": url.strip(),
                    }
                )

    return mapped or [dict(source) for source in BUILT_IN_TOURNAMENT_META_SOURCES]


def _runtime_sample_size(payload: dict[str, Any]) -> int | None:
    feed_provenance = payload.get("provenance")
    if isinstance(feed_provenance, dict):
        sample_size = feed_provenance.get("sampleSize")
        if isinstance(sample_size, int) and not isinstance(sample_size, bool):
            return sample_size
    return None


def _fetch_runtime_tournament_team_snapshots(
    base_url: str,
    regulation_id: str,
) -> tuple[tuple[dict[str, object], ...], dict[str, object], tuple[dict[str, object], ...]]:
    request = Request(
        _build_meta_snapshot_url(base_url, regulation_id),
        headers={
            "Accept": "application/json",
            "User-Agent": "pokemon-champions-analyzer/0.1",
        },
    )

    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("The runtime meta snapshot response must be a JSON object.")

    raw_snapshots = payload.get("tournamentTeamSnapshots")
    if not isinstance(raw_snapshots, list) or not raw_snapshots:
        raise ValueError("The runtime meta snapshot response is missing tournamentTeamSnapshots.")

    normalized_snapshots: list[dict[str, object]] = []
    for raw_snapshot in raw_snapshots:
        if not isinstance(raw_snapshot, dict):
            raise ValueError("The runtime meta snapshot contains an invalid team snapshot entry.")
        normalized_snapshots.append(_normalize_runtime_snapshot(cast(dict[str, Any], raw_snapshot)))

    common_meta = _normalize_runtime_common_meta_pokemon(payload.get("commonMetaPokemon"))
    usage_based = bool(common_meta)
    sample_size = _runtime_sample_size(payload)

    updated_at = payload.get("updatedAt")
    source_label = payload.get("sourceLabel")
    provenance: dict[str, object] = {
        "as_of": str(updated_at) if isinstance(updated_at, str) and updated_at else BUILT_IN_TOURNAMENT_META_AS_OF,
        "source_label": str(source_label) if isinstance(source_label, str) and source_label else "Live published meta snapshot",
        "sources": _runtime_provenance_sources(payload),
        "methodology": RUNTIME_USAGE_METHODOLOGY if usage_based else BUILT_IN_TOURNAMENT_META_METHODOLOGY,
        "is_live": True,
        "usage_based": usage_based,
        "sample_size": sample_size,
    }

    return tuple(normalized_snapshots), provenance, common_meta


def _runtime_board_cache_entry(regulation_id: str, base_url: str) -> dict[str, object] | None:
    """Fetch (and cache) a single regulation's runtime board, or ``None`` if it has none.

    The result is cached per ``regulation_id:base_url`` for the snapshot TTL. Failures are
    negatively cached so the data-driven proxy resolution (which probes a newer regulation's
    own board every analysis) does not re-hit a missing board repeatedly; a previously good
    entry is kept and served stale on a later failure.
    """
    cache_key = f"{regulation_id}:{base_url}"
    cached_entry = _SNAPSHOT_CACHE.get(cache_key)
    now = time.monotonic()
    if cached_entry and now < cast(float, cached_entry["expires_at"]):
        return None if cached_entry.get("failed") else cached_entry

    try:
        runtime_snapshots, runtime_provenance, runtime_common_meta = _fetch_runtime_tournament_team_snapshots(
            base_url, regulation_id
        )
    except Exception:
        if cached_entry and not cached_entry.get("failed"):
            return cached_entry  # serve the last good board stale rather than dropping it
        _SNAPSHOT_CACHE[cache_key] = {
            "expires_at": now + _runtime_meta_snapshot_ttl_seconds(),
            "failed": True,
        }
        return None

    entry: dict[str, object] = {
        "expires_at": now + _runtime_meta_snapshot_ttl_seconds(),
        "snapshots": runtime_snapshots,
        "provenance": runtime_provenance,
        "common_meta": runtime_common_meta,
    }
    _SNAPSHOT_CACHE[cache_key] = entry
    return entry


def get_tournament_team_snapshots(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[dict[str, object], ...]:
    # Serve the effective board for this regulation: its own once it has enough data, else the
    # board of the regulation it extends (proxy), else the built-in M-A board / empty.
    board_regulation_id = resolve_board_regulation_id(regulation_id)
    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    if base_url:
        entry = _runtime_board_cache_entry(board_regulation_id, base_url)
        if entry:
            return cast(tuple[dict[str, object], ...], entry["snapshots"])
    # No live feed (or it failed): only M-A has a built-in board to fall back to.
    if board_regulation_id == DEFAULT_REGULATION_ID:
        return BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS
    return ()


def get_runtime_common_meta_pokemon(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[dict[str, object], ...]:
    """Return the live feed's real-usage common-meta rows, or an empty tuple.

    When a configured runtime feed carries ``commonMetaPokemon`` (overall usage),
    those rows are returned in ``meta_analysis.common_pokemon`` shape so the analyzer
    can surface measured usage instead of deriving board share. An empty tuple means
    no live usage is available and the caller should fall back to board-share derivation.
    """

    board_regulation_id = resolve_board_regulation_id(regulation_id)
    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    if not base_url:
        return ()

    entry = _runtime_board_cache_entry(board_regulation_id, base_url)
    if not entry:
        return ()
    return cast(tuple[dict[str, object], ...], entry.get("common_meta", ()))