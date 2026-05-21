from __future__ import annotations

import os
from pathlib import Path
from tempfile import gettempdir


CACHE_DIR_ENV_VAR = "POKEMON_TEAM_ANALYZER_CACHE_DIR"


def resolve_cache_dir() -> Path:
    configured_cache_dir = os.environ.get(CACHE_DIR_ENV_VAR, "").strip()
    if configured_cache_dir:
        return Path(configured_cache_dir).expanduser()

    if os.environ.get("VERCEL"):
        return Path(gettempdir()) / "pokemon_team_analyzer"

    return Path.home() / ".cache" / "pokemon_team_analyzer"


def resolve_cache_path(file_name: str) -> Path:
    return resolve_cache_dir() / file_name