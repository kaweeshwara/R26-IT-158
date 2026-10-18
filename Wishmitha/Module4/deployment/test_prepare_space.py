from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from prepare_space import prepare_space


class PrepareSpaceTests(unittest.TestCase):
    def test_packages_api_without_overwriting_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "space"
            created = prepare_space(destination)
            self.assertEqual(
                {path.name for path in created},
                {"main.py", "weights.json", "Dockerfile", "requirements.txt", "README.md"},
            )
            with self.assertRaises(FileExistsError):
                prepare_space(destination)

    def test_force_replaces_generated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "space"
            destination.mkdir()
            (destination / "weights.json").write_text("old", encoding="utf-8")
            created = prepare_space(destination, force=True)
            self.assertEqual(len(created), 5)
            self.assertNotEqual(
                (destination / "weights.json").read_text(encoding="utf-8"), "old"
            )


if __name__ == "__main__":
    unittest.main()
