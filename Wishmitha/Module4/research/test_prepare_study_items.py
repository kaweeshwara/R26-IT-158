from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from prepare_study_items import prepare_items


class PrepareStudyItemsTests(unittest.TestCase):
    def _write_input(self, path: Path) -> None:
        fields = [
            "item_id", "text", "url", "published_date", "gold_label",
            "evidence_url", "reviewer", "reviewed_at",
        ]
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for index in range(10):
                writer.writerow({
                    "item_id": f"item-{index + 1:02d}",
                    "text": f"Reviewed Sinhala news statement number {index + 1}.",
                    "url": f"https://news.example.lk/article-{index + 1}",
                    "published_date": "",
                    "gold_label": "CREDIBLE" if index % 2 else "MISINFORMATION",
                    "evidence_url": f"https://factcheck.example.org/check-{index + 1}",
                    "reviewer": "reviewer-1",
                    "reviewed_at": date.today().isoformat(),
                })

    def test_separates_participant_pack_from_answer_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "reviewed.csv"
            public = root / "app" / "study-items.json"
            answer_key = root / "private" / "answer-key.csv"
            self._write_input(source)
            prepare_items(source, public, answer_key)

            items = json.loads(public.read_text(encoding="utf-8"))
            key = answer_key.read_text(encoding="utf-8")

        self.assertEqual(len(items), 10)
        self.assertNotIn("gold_label", items[0])
        self.assertNotIn("evidence_url", items[0])
        self.assertIn("gold_label", key)

    def test_rejects_answer_key_inside_app_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "reviewed.csv"
            self._write_input(source)
            with self.assertRaisesRegex(ValueError, "outside the mobile app"):
                prepare_items(
                    source,
                    root / "public.json",
                    Path(__file__).resolve().parents[1] / "mobile" / "answer-key.csv",
                )


if __name__ == "__main__":
    unittest.main()
