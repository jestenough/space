from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from scripts.cache import prune


class CacheTests(unittest.TestCase):
    def test_prune_keeps_newest_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(3):
                path = root / f"{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)
                time.sleep(0.01)

            prune(root, 2)
            self.assertFalse(paths[0].exists())
            self.assertTrue(paths[1].exists())
            self.assertTrue(paths[2].exists())
