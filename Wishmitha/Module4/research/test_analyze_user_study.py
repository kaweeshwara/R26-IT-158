from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from analyze_user_study import analyze_study


class StudyAnalysisTests(unittest.TestCase):
    def _write_csv(self, path: Path, columns: list[str], rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def test_computes_participant_level_accuracy_and_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trials = []
            for participant, group, decision in (
                ("anon-a1", "A", "CREDIBLE"),
                ("anon-a2", "A", "MISINFORMATION"),
                ("anon-a3", "A", "UNCERTAIN"),
                ("anon-b1", "B", "CREDIBLE"),
                ("anon-b2", "B", "CREDIBLE"),
                ("anon-b3", "B", "UNCERTAIN"),
            ):
                for item_id in ("item-1", "item-2"):
                    trials.append({
                        "participant_id": participant,
                        "group": group,
                        "item_id": item_id,
                        "participant_decision": decision,
                        "trust_likert": 5,
                        "decision_time_seconds": 20,
                    })
            self._write_csv(
                root / "trials.csv",
                [
                    "participant_id", "group", "item_id", "participant_decision",
                    "trust_likert", "decision_time_seconds",
                ],
                trials,
            )
            self._write_csv(
                root / "answer-key.csv", ["item_id", "gold_label"],
                [
                    {"item_id": "item-1", "gold_label": "CREDIBLE"},
                    {"item_id": "item-2", "gold_label": "UNCERTAIN"},
                ],
            )
            report = analyze_study(root / "trials.csv", root / "answer-key.csv", 2)

        self.assertEqual(report["n_participants"], 6)
        self.assertAlmostEqual(report["groups"]["A"]["accuracy_mean"], 1 / 3)
        self.assertAlmostEqual(report["groups"]["B"]["accuracy_mean"], 0.5)
        self.assertIn("accuracy", report["comparisons"])

    def test_rejects_incomplete_participant_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_csv(
                root / "trials.csv",
                [
                    "participant_id", "group", "item_id", "participant_decision",
                    "trust_likert", "decision_time_seconds",
                ],
                [{
                    "participant_id": "anon-a1", "group": "A", "item_id": "item-1",
                    "participant_decision": "CREDIBLE", "trust_likert": 5,
                    "decision_time_seconds": 20,
                }, {
                    "participant_id": "anon-b1", "group": "B", "item_id": "item-1",
                    "participant_decision": "CREDIBLE", "trust_likert": 5,
                    "decision_time_seconds": 20,
                }],
            )
            self._write_csv(
                root / "answer-key.csv", ["item_id", "gold_label"],
                [{"item_id": "item-1", "gold_label": "CREDIBLE"}],
            )
            with self.assertRaisesRegex(ValueError, "completed items"):
                analyze_study(root / "trials.csv", root / "answer-key.csv", 2)


if __name__ == "__main__":
    unittest.main()
