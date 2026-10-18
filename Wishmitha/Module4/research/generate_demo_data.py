from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

LABELS = ("CREDIBLE", "UNCERTAIN", "MISINFORMATION")
TRIAL_COLUMNS = (
    "participant_id",
    "group",
    "item_id",
    "participant_decision",
    "trust_likert",
    "decision_time_seconds",
)


def generate_demo_data(destination: Path, seed: int = 42, force: bool = False) -> list[Path]:
    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {
        destination / "synthetic_demo_trials.csv",
        destination / "synthetic_demo_answer_key.csv",
        destination / "SYNTHETIC_DEMO_ONLY.txt",
    }
    conflicts = [path for path in outputs if path.exists()]
    if conflicts and not force:
        raise FileExistsError(
            "Refusing to overwrite demo files: " + ", ".join(str(path) for path in conflicts)
        )

    rng = random.Random(seed)
    group_assignments = ["A"] * 20 + ["B"] * 20
    rng.shuffle(group_assignments)
    answer_key = [
        {"item_id": f"demo-item-{index + 1:02d}", "gold_label": LABELS[index % len(LABELS)]}
        for index in range(10)
    ]
    trials = []
    for participant_index, group in enumerate(group_assignments, start=1):
        participant_id = f"demo-participant-{participant_index:02d}"
        accuracy_chance = 0.58 if group == "A" else 0.68
        for item in answer_key:
            gold_label = item["gold_label"]
            if rng.random() < accuracy_chance:
                decision = gold_label
            else:
                decision = rng.choice([label for label in LABELS if label != gold_label])
            trials.append({
                "participant_id": participant_id,
                "group": group,
                "item_id": item["item_id"],
                "participant_decision": decision,
                "trust_likert": rng.randint(2, 7),
                "decision_time_seconds": round(rng.uniform(8, 90), 2),
            })

    trials_path = destination / "synthetic_demo_trials.csv"
    with trials_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=TRIAL_COLUMNS)
        writer.writeheader()
        writer.writerows(trials)

    key_path = destination / "synthetic_demo_answer_key.csv"
    with key_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("item_id", "gold_label"))
        writer.writeheader()
        writer.writerows(answer_key)

    notice_path = destination / "SYNTHETIC_DEMO_ONLY.txt"
    notice_path.write_text(
        "SYNTHETIC DEMO DATA ONLY\n"
        "These records are generated for software testing and are not real participants, "
        "study observations, or evidence. Never cite, submit, or report them as research "
        "results.\n",
        encoding="utf-8",
    )
    return [trials_path, key_path, notice_path]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate clearly marked synthetic data to test the study-analysis pipeline."
    )
    parser.add_argument("destination", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="Replace existing demo output files.")
    args = parser.parse_args()
    for path in generate_demo_data(args.destination, seed=args.seed, force=args.force):
        print(f"Created synthetic demo file: {path}")
    print("Synthetic demo only: these are not real participant data or study results.")


if __name__ == "__main__":
    main()
