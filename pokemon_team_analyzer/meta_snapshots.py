from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .champions_m_a_tournament_meta import TOURNAMENT_TEAM_SNAPSHOTS as BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS
from .regulations import DEFAULT_REGULATION_ID


_SNAPSHOT_CACHE: dict[str, dict[str, object]] = {}

BUILT_IN_META_SNAPSHOT_SOURCE_LABEL = "Pokemon Champions Analyzer built-in Regulation M-A meta board"
BUILT_IN_META_SNAPSHOT_NOTES = (
    "Generated directly from the analyzer API's built-in Champions Regulation M-A tournament team snapshots.",
    "Use this endpoint as the frontend refresh source when you want the hosted meta board to republish from the analyzer's current curated board automatically.",
)


def clear_runtime_meta_snapshot_cache() -> None:
    _SNAPSHOT_CACHE.clear()


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


def _fetch_runtime_tournament_team_snapshots(
    base_url: str,
    regulation_id: str,
) -> tuple[dict[str, object], ...]:
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

    return tuple(normalized_snapshots)


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
        runtime_snapshots = _fetch_runtime_tournament_team_snapshots(base_url, resolved_regulation_id)
    except Exception:
        if cached_entry:
            return cast(tuple[dict[str, object], ...], cached_entry["snapshots"])
        return BUILT_IN_TOURNAMENT_TEAM_SNAPSHOTS

    _SNAPSHOT_CACHE[cache_key] = {
        "expires_at": now + _runtime_meta_snapshot_ttl_seconds(),
        "snapshots": runtime_snapshots,
    }
    return runtime_snapshots