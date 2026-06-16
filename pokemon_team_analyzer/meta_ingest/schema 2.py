"""Validate an assembled feed against the web app's contract before writing.

This is a faithful, dependency-free mirror of the Zod schemas in
``web/src/lib/meta-snapshots.ts`` (``metaSnapshotFeedSchema`` and friends). Like
Zod's non-strict ``z.object``, unknown keys are tolerated (the web strips them),
so the ingestion may carry extra provenance fields that a later pass can adopt
without breaking today's consumer.

Validation is the publish gate: :func:`validate_feed` raises
:class:`FeedValidationError` listing every problem, so a malformed document never
reaches the repo or the database.
"""

from __future__ import annotations

import re
from typing import Any

# Matches Zod's z.string().datetime() default: requires a trailing "Z" (UTC),
# numeric timezone offsets are rejected.
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class FeedValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        joined = "\n  - ".join(errors)
        super().__init__(f"Feed failed schema validation:\n  - {joined}")


class _Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def fail(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def string(self, value: Any, path: str, *, max_len: int, min_len: int = 1) -> None:
        if not isinstance(value, str):
            self.fail(path, "expected a string")
            return
        stripped = value.strip()
        if len(stripped) < min_len:
            self.fail(path, f"must be at least {min_len} character(s)")
        if len(value) > max_len:
            self.fail(path, f"must be at most {max_len} characters")

    def number(self, value: Any, path: str, *, minimum: float, maximum: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.fail(path, "expected a number")
            return
        if value < minimum or value > maximum:
            self.fail(path, f"must be between {minimum} and {maximum}")

    def datetime_opt(self, value: Any, path: str) -> None:
        if value is None:
            return
        if not isinstance(value, str) or not _ISO_DATETIME.match(value):
            self.fail(path, "expected an ISO-8601 datetime string")

    def number_record(self, value: Any, path: str, *, maximum: float) -> None:
        if not isinstance(value, dict):
            self.fail(path, "expected an object of numbers")
            return
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                self.fail(path, "has a non-string key")
            self.number(item, f"{path}.{key}", minimum=0, maximum=maximum)

    def string_array(
        self, value: Any, path: str, *, max_item_len: int, min_items: int, max_items: int
    ) -> None:
        if not isinstance(value, list):
            self.fail(path, "expected an array")
            return
        if len(value) < min_items:
            self.fail(path, f"must contain at least {min_items} item(s)")
        if len(value) > max_items:
            self.fail(path, f"must contain at most {max_items} item(s)")
        for index, item in enumerate(value):
            self.string(item, f"{path}[{index}]", max_len=max_item_len)

    def snapshot(self, value: Any, path: str) -> None:
        if not isinstance(value, dict):
            self.fail(path, "expected an object")
            return
        self.string(value.get("slug"), f"{path}.slug", max_len=120)
        self.string(value.get("label"), f"{path}.label", max_len=120)
        self.string(value.get("source"), f"{path}.source", max_len=240)
        self.string(value.get("result_label"), f"{path}.result_label", max_len=120)
        self.number(value.get("field_relevance"), f"{path}.field_relevance", minimum=0, maximum=2)
        self.number(value.get("popularity_weight"), f"{path}.popularity_weight", minimum=0, maximum=2)
        self.number(value.get("result_weight"), f"{path}.result_weight", minimum=0, maximum=2)
        self.string_array(value.get("modes"), f"{path}.modes", max_item_len=80, min_items=1, max_items=8)
        self.number_record(value.get("mode_weights"), f"{path}.mode_weights", maximum=4)
        self.number_record(value.get("broad_mix"), f"{path}.broad_mix", maximum=4)
        self.string_array(value.get("key_pokemon"), f"{path}.key_pokemon", max_item_len=80, min_items=1, max_items=12)
        self.string_array(value.get("key_cores"), f"{path}.key_cores", max_item_len=160, min_items=1, max_items=8)

        modes = value.get("modes")
        mode_weights = value.get("mode_weights")
        if isinstance(modes, list) and isinstance(mode_weights, dict):
            for mode in modes:
                if isinstance(mode, str) and mode not in mode_weights:
                    self.fail(f"{path}.mode_weights", f"missing an entry for mode {mode!r}")

    def common_meta(self, value: Any, path: str) -> None:
        if not isinstance(value, dict):
            self.fail(path, "expected an object")
            return
        self.string(value.get("species"), f"{path}.species", max_len=120)
        self.number(value.get("metaShare"), f"{path}.metaShare", minimum=0, maximum=100)
        self.string(value.get("whyUsed"), f"{path}.whyUsed", max_len=400)
        self.string(value.get("whatItDoes"), f"{path}.whatItDoes", max_len=400)
        featured = value.get("featuredTeams", [])
        self.string_array(featured, f"{path}.featuredTeams", max_item_len=120, min_items=0, max_items=3)

    def document(self, value: Any, path: str) -> None:
        if not isinstance(value, dict):
            self.fail(path, "expected an object")
            return
        self.string(value.get("regulationId"), f"{path}.regulationId", max_len=120)
        self.datetime_opt(value.get("updatedAt"), f"{path}.updatedAt")
        if value.get("sourceLabel") is not None:
            self.string(value.get("sourceLabel"), f"{path}.sourceLabel", max_len=240)
        self.string_array(value.get("notes", []), f"{path}.notes", max_item_len=400, min_items=0, max_items=20)

        common = value.get("commonMetaPokemon", [])
        if not isinstance(common, list):
            self.fail(f"{path}.commonMetaPokemon", "expected an array")
        else:
            if len(common) > 16:
                self.fail(f"{path}.commonMetaPokemon", "must contain at most 16 item(s)")
            for index, item in enumerate(common):
                self.common_meta(item, f"{path}.commonMetaPokemon[{index}]")

        snapshots = value.get("tournamentTeamSnapshots")
        if not isinstance(snapshots, list):
            self.fail(f"{path}.tournamentTeamSnapshots", "expected an array")
        else:
            if not 1 <= len(snapshots) <= 64:
                self.fail(f"{path}.tournamentTeamSnapshots", "must contain between 1 and 64 item(s)")
            for index, item in enumerate(snapshots):
                self.snapshot(item, f"{path}.tournamentTeamSnapshots[{index}]")

    def feed(self, value: Any) -> None:
        if not isinstance(value, dict):
            self.fail("$", "expected an object")
            return
        if value.get("version") != 1:
            self.fail("$.version", "must be the literal 1")
        self.datetime_opt(value.get("generatedAt"), "$.generatedAt")
        regulations = value.get("regulations")
        if not isinstance(regulations, list):
            self.fail("$.regulations", "expected an array")
            return
        if not 1 <= len(regulations) <= 16:
            self.fail("$.regulations", "must contain between 1 and 16 item(s)")
        for index, item in enumerate(regulations):
            self.document(item, f"$.regulations[{index}]")


def validate_feed(feed: Any) -> None:
    """Validate a full feed document. Raises :class:`FeedValidationError` on failure."""

    validator = _Validator()
    validator.feed(feed)
    if validator.errors:
        raise FeedValidationError(validator.errors)
