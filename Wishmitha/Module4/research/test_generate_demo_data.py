from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from analyze_user_study import analyze_study
from generate_demo_data import generate_demo_data


class DemoDataTests(unittest.TestCase):
    def test_generates_balanced_synthetic_dataset_and_marked_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trials_path, key_path, notice_path = generate_demo_data(root, seed=7)
            with trials_path.open(encoding="utf-8", newline="") as stream:
                trials = list(csv.DictReader(stream))
            counts = {
                group: len({row["participant_id"] for row in trials if row["group"] == group})
                for group in ("A", "B")
            }
            self.assertEqual(len(trials), 400)
            self.assertEqual(counts, {"A": 20, "B": 20})
            self.assertEqual(
                {row["participant_id"] for row in trials},
                {f"demo-participant-{index:02d}" for index in range(1, 41)},
            )
            self.assertIn("not real participants", notice_path.read_text(encoding="utf-8"))

            report = analyze_study(trials_path, key_path, simulated_demo=True)

        self.assertEqual(report["status"], "simulated_demo")
        self.assertEqual(report["data_provenance"], "synthetic_demo_not_real_participant_data")
        self.assertIn("SYNTHETIC DEMO ONLY", report["caution"])
        self.assertEqual(report["n_participants"], 40)
        self.assertEqual(report["groups"]["A"]["n_participants"], 20)
        self.assertEqual(report["groups"]["B"]["n_participants"], 20)
        json.dumps(report)

    def test_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generate_demo_data(root)
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                generate_demo_data(root)


if __name__ == "__main__":
    unittest.main()
