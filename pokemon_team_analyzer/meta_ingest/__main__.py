"""CLI entry point: ``python -m pokemon_team_analyzer.meta_ingest``."""

from __future__ import annotations

import sys

from .build import main

if __name__ == "__main__":
    sys.exit(main())
