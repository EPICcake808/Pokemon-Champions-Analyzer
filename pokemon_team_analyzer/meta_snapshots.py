from __future__ import annotations

import json
import os
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
from .regulations import DEFAULT_REGULATION_ID


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
    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    if resolved_regulation_id == DEFAULT_REGULATION_ID and base_url:
        cache_key = f"{resolved_regulation_id}:{base_url}"
        cached_entry = _SNAPSHOT_CACHE.get(cache_key)
        if cached_entry and cached_entry.get("provenance"):
            return cast(dict[str, object], cached_entry["provenance"])
    return _built_in_meta_provenance()


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


def get_tournament_team_snapshots(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[dict[str, object], ...]:
    resolved_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    if resolved_regulation_id != DEFAULT_REGULATION_ID:
        return BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS

    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    if not base_url:
        return BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS

    cache_key = f"{resolved_regulation_id}:{base_url}"
    cached_entry = _SNAPSHOT_CACHE.get(cache_key)
    now = time.monotonic()
    if cached_entry and now < cast(float, cached_entry["expires_at"]):
        return cast(tuple[dict[str, object], ...], cached_entry["snapshots"])

    try:
        runtime_snapshots, runtime_provenance, runtime_common_meta = _fetch_runtime_tournament_team_snapshots(
            base_url, resolved_regulation_id
        )
    except Exception:
        if cached_entry:
            return cast(tuple[dict[str, object], ...], cached_entry["snapshots"])
        return BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS

    _SNAPSHOT_CACHE[cache_key] = {
        "expires_at": now + _runtime_meta_snapshot_ttl_seconds(),
        "snapshots": runtime_snapshots,
        "provenance": runtime_provenance,
        "common_meta": runtime_common_meta,
    }
    return runtime_snapshots


def get_runtime_common_meta_pokemon(
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> tuple[dict[str, object], ...]:
    """Return the live feed's real-usage common-meta rows, or an empty tuple.

    When a configured runtime feed carries ``commonMetaPokemon`` (overall usage),
    those rows are returned in ``meta_analysis.common_pokemon`` shape so the analyzer
    can surface measured usage instead of deriving board share. An empty tuple means
    no live usage is available and the caller should fall back to board-share derivation.
    """

    resolved_regulation_id = regulation_id or DEFAULT_REGULATION_ID
    if resolved_regulation_id != DEFAULT_REGULATION_ID:
        return ()

    base_url = os.getenv("POKEMON_ANALYZER_META_SNAPSHOT_URL", "").strip()
    if not base_url:
        return ()

    # Ensure the runtime feed is fetched/cached (shared fetch populates common_meta too).
    get_tournament_team_snapshots(resolved_regulation_id)
    cached_entry = _SNAPSHOT_CACHE.get(f"{resolved_regulation_id}:{base_url}")
    if not cached_entry:
        return ()
    return cast(tuple[dict[str, object], ...], cached_entry.get("common_meta", ()))