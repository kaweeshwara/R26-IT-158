from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from scipy import stats

GROUPS = ("A", "B")
LABELS = {"CREDIBLE", "UNCERTAIN", "MISINFORMATION"}
TRIAL_COLUMNS = {
    "participant_id", "group", "item_id", "participant_decision",
    "trust_likert", "decision_time_seconds",
}
KEY_COLUMNS = {"item_id", "gold_label"}
METRICS = ("accuracy", "trust_likert", "decision_time_seconds")


def _validate(trials: pd.DataFrame, answer_key: pd.DataFrame, expected_items: int) -> pd.DataFrame:
    missing_trials = TRIAL_COLUMNS - set(trials.columns)
    missing_key = KEY_COLUMNS - set(answer_key.columns)
    if missing_trials:
        raise ValueError(f"Trial CSV missing columns: {sorted(missing_trials)}")
    if missing_key:
        raise ValueError(f"Answer key missing columns: {sorted(missing_key)}")
    if trials.empty or answer_key.empty:
        raise ValueError("Both trial data and answer key must contain rows.")
    if answer_key["item_id"].duplicated().any():
        raise ValueError("Answer key contains duplicate item IDs.")
    if trials[list(TRIAL_COLUMNS)].isnull().any().any():
        raise ValueError("Participant trial data contains missing required values.")
    if trials.duplicated(["participant_id", "item_id"]).any():
        raise ValueError("A participant has more than one response for a study item.")

    trials = trials.copy()
    answer_key = answer_key.copy()
    trials["group"] = trials["group"].astype(str).str.upper()
    trials["participant_decision"] = trials["participant_decision"].astype(str).str.upper()
    answer_key["gold_label"] = answer_key["gold_label"].astype(str).str.upper()
    if not set(trials["group"]).issubset(GROUPS):
        raise ValueError("Study groups must be A or B.")
    if not set(trials["participant_decision"]).issubset(LABELS):
        raise ValueError(f"Participant decisions must be one of {sorted(LABELS)}.")
    if not set(answer_key["gold_label"]).issubset(LABELS):
        raise ValueError(f"Gold labels must be one of {sorted(LABELS)}.")
    if trials.groupby("participant_id")["group"].nunique().max() != 1:
        raise ValueError("Each participant must belong to only one study group.")
    unknown_items = set(trials["item_id"]) - set(answer_key["item_id"])
    if unknown_items:
        raise ValueError(f"Answer key has no label for item IDs: {sorted(unknown_items)}")

    trials["trust_likert"] = pd.to_numeric(trials["trust_likert"], errors="raise")
    trials["decision_time_seconds"] = pd.to_numeric(
        trials["decision_time_seconds"], errors="raise"
    )
    if not trials["trust_likert"].between(1, 7).all():
        raise ValueError("Trust ratings must be on the 1–7 Likert scale.")
    if not (trials["decision_time_seconds"] > 0).all():
        raise ValueError("Decision times must be positive.")

    item_counts = trials.groupby("participant_id")["item_id"].nunique()
    incomplete = item_counts[item_counts != expected_items]
    if not incomplete.empty:
        raise ValueError(
            f"Every included participant must have {expected_items} distinct completed items; "
            f"incomplete IDs: {list(incomplete.index)}"
        )

    merged = trials.merge(
        answer_key[["item_id", "gold_label"]],
        on="item_id",
        how="left",
        validate="many_to_one",
    )
    merged["accuracy"] = (
        merged["participant_decision"] == merged["gold_label"]
    ).astype(float)
    return merged


def _compare(first: pd.Series, second: pd.Series) -> dict[str, Any]:
    if len(first) < 3 or len(second) < 3:
        return {"method": "not_tested", "reason": "At least three participants per group are needed."}

    if first.nunique() < 2 or second.nunique() < 2:
        result = stats.mannwhitneyu(first, second, alternative="two-sided", method="auto")
        return {
            "method": "Mann–Whitney U",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "group_a_median": float(first.median()),
            "group_b_median": float(second.median()),
            "normality_test": "not used because at least one group has zero variance",
            "interpretation_note": "The U test compares distributions; it is not a test of medians alone.",
        }

    normality_a = float(stats.shapiro(first).pvalue)
    normality_b = float(stats.shapiro(second).pvalue)
    if normality_a >= 0.05 and normality_b >= 0.05:
        result = stats.ttest_ind(first, second, equal_var=False)
        difference = float(first.mean() - second.mean())
        variance_a = float(first.var(ddof=1))
        variance_b = float(second.var(ddof=1))
        se = (variance_a / len(first) + variance_b / len(second)) ** 0.5
        numerator = (variance_a / len(first) + variance_b / len(second)) ** 2
        denominator = (
            (variance_a / len(first)) ** 2 / (len(first) - 1)
            + (variance_b / len(second)) ** 2 / (len(second) - 1)
        )
        degrees_freedom = numerator / denominator if denominator else 0
        margin = float(stats.t.ppf(0.975, degrees_freedom) * se)
        return {
            "method": "Welch independent-samples t-test",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "group_a_minus_group_b_mean": difference,
            "difference_ci95": [difference - margin, difference + margin],
            "shapiro_p_group_a": normality_a,
            "shapiro_p_group_b": normality_b,
        }

    result = stats.mannwhitneyu(first, second, alternative="two-sided", method="auto")
    return {
        "method": "Mann–Whitney U",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "group_a_median": float(first.median()),
        "group_b_median": float(second.median()),
        "shapiro_p_group_a": normality_a,
        "shapiro_p_group_b": normality_b,
        "interpretation_note": "The U test compares distributions; it is not a test of medians alone.",
    }


def analyze_study(
    trial_path: Path,
    answer_key_path: Path,
    expected_items: int = 10,
    simulated_demo: bool = False,
) -> dict:
    trials = pd.read_csv(trial_path, dtype={"participant_id": str, "item_id": str})
    answer_key = pd.read_csv(answer_key_path, dtype={"item_id": str})
    merged = _validate(trials, answer_key, expected_items)
    participant_metrics = merged.groupby(["participant_id", "group"], as_index=False).agg(
        accuracy=("accuracy", "mean"),
        trust_likert=("trust_likert", "mean"),
        decision_time_seconds=("decision_time_seconds", "mean"),
    )
    report: dict[str, Any] = {
        "status": "simulated_demo" if simulated_demo else "analyzed",
        "n_participants": int(len(participant_metrics)),
        "n_items_per_participant": expected_items,
        "primary_metric": "accuracy",
        "hypothesis": "Two-sided exploratory comparison; preregister one-sided H1 before collection if required.",
        "groups": {},
        "comparisons": {},
        "caution": (
            (
                "SYNTHETIC DEMO ONLY: these generated rows are not real participants, "
                "study results, or evidence. Never cite or report them as research findings."
                if simulated_demo
                else
                "Report only after protocol approval and verified data collection. "
                "This script does not establish causal effects or replace preregistration."
            )
        ),
    }
    if simulated_demo:
        report["data_provenance"] = "synthetic_demo_not_real_participant_data"

    for group in GROUPS:
        data = participant_metrics[participant_metrics["group"] == group]
        report["groups"][group] = {
            "n_participants": int(len(data)),
            "accuracy_mean": float(data["accuracy"].mean()) if len(data) else None,
            "accuracy_sd": float(data["accuracy"].std(ddof=1)) if len(data) > 1 else None,
            "trust_mean": float(data["trust_likert"].mean()) if len(data) else None,
            "decision_time_mean_seconds": (
                float(data["decision_time_seconds"].mean()) if len(data) else None
            ),
        }

    if any(report["groups"][group]["n_participants"] == 0 for group in GROUPS):
        raise ValueError("Both study groups must contain participant data.")
    for metric in METRICS:
        first = participant_metrics.loc[participant_metrics.group == "A", metric]
        second = participant_metrics.loc[participant_metrics.group == "B", metric]
        report["comparisons"][metric] = _compare(first, second)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze completed, anonymous two-group study responses."
    )
    parser.add_argument("trials_csv", type=Path)
    parser.add_argument("answer_key_csv", type=Path)
    parser.add_argument("--expected-items", type=int, default=10)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--simulated-demo",
        action="store_true",
        help="Mark this output as synthetic demo data, not real study results.",
    )
    args = parser.parse_args()
    if args.expected_items < 1:
        parser.error("--expected-items must be positive.")
    report = analyze_study(
        args.trials_csv,
        args.answer_key_csv,
        args.expected_items,
        simulated_demo=args.simulated_demo,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
