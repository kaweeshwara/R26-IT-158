from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

LABELS = {"CREDIBLE", "UNCERTAIN", "MISINFORMATION"}
FIELDS = {
    "item_id", "text", "url", "published_date", "gold_label",
    "evidence_url", "reviewer", "reviewed_at",
}
APP_DIRECTORY = Path(__file__).resolve().parents[1] / "mobile"


def _https_url(value: str, field: str, row_number: int) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"Row {row_number}: {field} must be a complete HTTPS URL.")


def prepare_items(input_path: Path, public_output: Path, answer_key_output: Path) -> None:
    public_output = public_output.resolve()
    answer_key_output = answer_key_output.resolve()
    if APP_DIRECTORY in answer_key_output.parents or answer_key_output == APP_DIRECTORY:
        raise ValueError("The answer key must be stored outside the mobile app directory.")

    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not FIELDS.issubset(reader.fieldnames):
            missing = sorted(FIELDS - set(reader.fieldnames or []))
            raise ValueError(f"Input CSV is missing required columns: {', '.join(missing)}")
        rows = list(reader)

    if len(rows) != 10:
        raise ValueError(f"Exactly 10 reviewed study items are required; found {len(rows)}.")

    seen: set[str] = set()
    public_items: list[dict[str, str]] = []
    answer_key: list[dict[str, str]] = []
    labels: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        item_id = row["item_id"].strip()
        text = row["text"].strip()
        label = row["gold_label"].strip().upper()
        if not item_id or item_id in seen:
            raise ValueError(f"Row {row_number}: item_id must be present and unique.")
        if not text or len(text) < 20:
            raise ValueError(f"Row {row_number}: provide the full reviewed Sinhala content.")
        if label not in LABELS:
            raise ValueError(f"Row {row_number}: gold_label must be one of {sorted(LABELS)}.")
        if not row["reviewer"].strip():
            raise ValueError(f"Row {row_number}: reviewer is required for auditability.")
        try:
            reviewed_at = date.fromisoformat(row["reviewed_at"].strip())
        except ValueError as exc:
            raise ValueError(f"Row {row_number}: reviewed_at must be YYYY-MM-DD.") from exc
        if reviewed_at > date.today():
            raise ValueError(f"Row {row_number}: reviewed_at cannot be in the future.")

        _https_url(row["url"].strip(), "url", row_number)
        _https_url(row["evidence_url"].strip(), "evidence_url", row_number)
        published_date = row["published_date"].strip()
        if published_date:
            try:
                date.fromisoformat(published_date[:10])
            except ValueError as exc:
                raise ValueError(
                    f"Row {row_number}: published_date must begin with YYYY-MM-DD."
                ) from exc

        seen.add(item_id)
        labels.add(label)
        public_item = {
            "item_id": item_id,
            "text": text,
            "url": row["url"].strip(),
        }
        if published_date:
            public_item["published_date"] = published_date
        public_items.append(public_item)
        answer_key.append({
            "item_id": item_id,
            "gold_label": label,
            "evidence_url": row["evidence_url"].strip(),
            "reviewer": row["reviewer"].strip(),
            "reviewed_at": reviewed_at.isoformat(),
        })

    if len(labels) < 2:
        raise ValueError("The set must include at least two different reviewed verdict labels.")

    public_output.parent.mkdir(parents=True, exist_ok=True)
    answer_key_output.parent.mkdir(parents=True, exist_ok=True)
    public_output.write_text(
        json.dumps(public_items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with answer_key_output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=answer_key[0].keys())
        writer.writeheader()
        writer.writerows(answer_key)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate ten reviewed items and produce a public pack plus private answer key."
    )
    parser.add_argument("input_csv", type=Path)
    parser.add_argument(
        "--public-output", type=Path,
        default=APP_DIRECTORY / "assets" / "study-items.json",
    )
    parser.add_argument("--answer-key-output", type=Path, required=True)
    args = parser.parse_args()
    prepare_items(args.input_csv, args.public_output, args.answer_key_output)
    print(f"Created participant item pack: {args.public_output}")
    print(f"Created private answer key: {args.answer_key_output}")


if __name__ == "__main__":
    main()
