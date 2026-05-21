from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
import unittest
from unittest.mock import patch

from pokemon_team_analyzer.cache_paths import resolve_cache_path
from pokemon_team_analyzer.champions_m_a_moves import CachedChampionsMoveListProvider
from pokemon_team_analyzer.data import CachedPokeApiClient


class CachePathTests(unittest.TestCase):
    def test_resolve_cache_path_uses_tmp_on_vercel(self) -> None:
        with patch.dict("os.environ", {"VERCEL": "1"}, clear=False):
            cache_path = resolve_cache_path("pokeapi_cache.json")

        self.assertEqual(cache_path, Path(gettempdir()) / "pokemon_team_analyzer" / "pokeapi_cache.json")

    def test_pokeapi_cache_save_ignores_filesystem_errors(self) -> None:
        client = CachedPokeApiClient(cache_path=Path("/does/not/matter.json"))
        client._cache = {"pokemon": {}, "move": {}}

        with patch.object(Path, "mkdir", side_effect=OSError("read-only")):
            client._save_cache()

    def test_move_cache_save_ignores_filesystem_errors(self) -> None:
        provider = CachedChampionsMoveListProvider(cache_path=Path("/does/not/matter.json"))
        provider._cache = {}

        with patch.object(Path, "mkdir", side_effect=OSError("read-only")):
            provider._save_cache()