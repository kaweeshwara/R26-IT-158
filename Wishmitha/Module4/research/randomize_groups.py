from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def allocate_groups(participant_codes: list[str], seed: int | None = None) -> list[dict[str, str]]:
    codes = [code.strip() if isinstance(code, str) else "" for code in participant_codes]
    if len(codes) != 40:
        raise ValueError(f"Exactly 40 anonymous participant codes are required; found {len(codes)}.")
    if any(not code for code in codes) or len(set(codes)) != len(codes):
        raise ValueError("Participant codes must be present and unique.")

    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    shuffled = list(codes)
    rng.shuffle(shuffled)
    assignment = {code: ("A" if index < 20 else "B") for index, code in enumerate(shuffled)}
    return [{"participant_id": code, "group": assignment[code]} for code in codes]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Randomly allocate 40 anonymous participant codes 20:20."
    )
    parser.add_argument("codes_csv", type=Path, help="CSV with a participant_id column; no names.")
    parser.add_argument("output_csv", type=Path)
    parser.add_argument("--seed", type=int, help="Optional seed to reproduce a documented allocation.")
    args = parser.parse_args()

    with args.codes_csv.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if "participant_id" not in (reader.fieldnames or []):
            parser.error("Input CSV must contain a participant_id column.")
        rows = list(reader)
    assignment = allocate_groups(
        [row["participant_id"] for row in rows],
        seed=args.seed,
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=["participant_id", "group"])
        writer.writeheader()
        writer.writerows(assignment)
    print(f"Wrote randomized 20/20 assignment to {args.output_csv}")


if __name__ == "__main__":
    main()
