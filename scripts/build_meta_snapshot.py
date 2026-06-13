#!/usr/bin/env python3
"""Thin wrapper around the meta ingestion CLI.

Equivalent to ``python -m pokemon_team_analyzer.meta_ingest`` but runnable as a
script (mirrors ``scripts/sync_version.py``). All arguments are forwarded.

Examples::

    python scripts/build_meta_snapshot.py --since 30 --report
    python scripts/build_meta_snapshot.py --since 30 --write   # -> web/public/meta-snapshots.json
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running directly from a checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pokemon_team_analyzer.meta_ingest.build import main

if __name__ == "__main__":
    raise SystemExit(main())
