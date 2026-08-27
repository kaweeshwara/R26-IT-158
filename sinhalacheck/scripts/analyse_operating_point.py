"""Choose Module 1's decision threshold from data, and test how sensitive fusion is to its weights.

Both analyses need every corpus document scored by the content model, which is the expensive
part, so they share one pass.

--------------------------------------------------------------------------------------
Part 1 — the decision threshold
--------------------------------------------------------------------------------------
The model outputs P(CREDIBLE). Turning that into a verdict needs a cut-off, and 0.5 is a
default rather than a decision. Where the cut sits determines the trade-off between catching
misinformation and wrongly flagging genuine reporting, so it should be chosen deliberately
and reported.

The script first asks a diagnostic question that decides whether tuning can help at all:

    Can the model separate FALSE/PARTIAL documents from UNCERTAIN ones?

If that AUC is near 0.5 the two groups are indistinguishable to the model, no threshold
improves detection without an equal cost in false alarms, and the honest conclusion is that
the corpus does not support fine-grained misinformation detection. If it is meaningfully
above 0.5, a better operating point exists and the sweep will find it.

--------------------------------------------------------------------------------------
Part 2 — fusion weight sensitivity
--------------------------------------------------------------------------------------
The corpus cannot be used to *fit* fusion weights (see fit_fusion_weights.py). Sensitivity
analysis answers the panel's concern a different way: instead of claiming one weighting is
correct, vary the weights across a grid and measure how often the final verdict changes. A
verdict that is stable across a wide range does not depend on the exact numbers, which is
the thing worth demonstrating.

Usage
-----
    python analyse_operating_point.py --model Kaweeshwara/sinhalacheck-module1

    # no GPU:
    python analyse_operating_point.py --model <path> --limit 800
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "module2"))
CORPUS_XLSX = "https://raw.githubusercontent.com/LIRNEasia/MisinformationCorpusSinhala/main/Corpus.xlsx"
OUT_DIR = ROOT / "analysis"


def normalise_type(v):
    if isinstance(v, bool):
        return "FALSE" if v is False else "TRUE"
    return str(v).strip().upper()


def score_corpus(df, model_id, batch_size, device_arg):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = torch.device(device_arg or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"Scoring {len(df)} documents with {model_id} on {device} ...")
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id).to(device).eval()
    id2label = {int(k): str(v).upper() for k, v in model.config.id2label.items()}
    ci = next((i for i, l in id2label.items() if "NOT" not in l and "CREDIBLE" in l), 1)
    print(f"  id2label={id2label}  CREDIBLE index={ci}")

    texts = df["content"].astype(str).tolist()
    out = np.empty(len(texts), dtype=float)
    for i in range(0, len(texts), batch_size):
        b = texts[i:i + batch_size]
        enc = tok(b, truncation=True, padding=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            logits = model(**{k: v.to(device) for k, v in enc.items()}).logits
        out[i:i + len(b)] = torch.softmax(logits, -1)[:, ci].cpu().numpy()
        if i % (batch_size * 20) == 0:
            print(f"  {i}/{len(texts)}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Kaweeshwara/sinhalacheck-module1")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--device", default=None)
    ap.add_argument("--scores", default=None,
                    help="Reuse a previously saved content_scores.csv instead of re-scoring.")
    args = ap.parse_args()

    from sklearn.metrics import roc_auc_score, f1_score
    OUT_DIR.mkdir(exist_ok=True)

    # ------------------------------------------------------------------ corpus
    print("Loading corpus ...")
    df = pd.read_excel(CORPUS_XLSX)
    df["type"] = df["type"].apply(normalise_type)
    df = df[df["content"].astype(str).str.strip().str.len() > 0].reset_index(drop=True)
    if args.limit:
        df = df.sample(min(args.limit, len(df)), random_state=42).reset_index(drop=True)

    if args.scores and Path(args.scores).is_file():
        content = pd.read_csv(args.scores)["content_score"].values
        print(f"Reused {len(content)} scores from {args.scores}")
        assert len(content) == len(df), "saved scores do not match the corpus size"
    else:
        content = score_corpus(df, args.model, args.batch_size, args.device)
        pd.DataFrame({"type": df["type"], "content_score": content}).to_csv(
            OUT_DIR / "content_scores.csv", index=False)
        print(f"Saved scores -> {OUT_DIR/'content_scores.csv'}")

    is_credible = (df["type"] == "CREDIBLE").values
    is_strict = df["type"].isin(["FALSE", "PARTIAL"]).values
    is_uncertain = (df["type"] == "UNCERTAIN").values
    print(f"\nCREDIBLE {is_credible.sum()} | UNCERTAIN {is_uncertain.sum()} | "
          f"FALSE+PARTIAL {is_strict.sum()}")

    # ================================================================== diagnostic
    print("\n" + "=" * 78)
    print("DIAGNOSTIC — what can the content score actually separate?")
    print("=" * 78)

    def auc(mask_pos, mask_neg, label):
        y = np.r_[np.ones(mask_pos.sum()), np.zeros(mask_neg.sum())]
        s = np.r_[content[mask_pos], content[mask_neg]]
        a = roc_auc_score(y, s)
        print(f"  {label:<46s} AUC {a:.4f}")
        return float(a)

    auc_cred_vs_rest = auc(is_credible, ~is_credible, "CREDIBLE vs everything else")
    auc_cred_vs_strict = auc(is_credible, is_strict, "CREDIBLE vs FALSE/PARTIAL")
    auc_unc_vs_strict = auc(is_uncertain, is_strict, "UNCERTAIN vs FALSE/PARTIAL")

    print("\n  The third line is the one that decides whether threshold tuning can help.")
    if auc_unc_vs_strict < 0.55:
        verdict_msg = (
            "  AUC is close to chance: the model does NOT distinguish genuinely false\n"
            "  documents from merely uncertain ones. Moving the threshold will trade\n"
            "  detection against false alarms roughly one-for-one, and cannot create\n"
            "  real misinformation-detection ability. Report this as a limitation of\n"
            "  the corpus (110 FALSE/PARTIAL against 1,887 UNCERTAIN), not of the model.")
    elif auc_unc_vs_strict < 0.65:
        verdict_msg = (
            "  Weak but real separation. A better operating point exists; expect a modest\n"
            "  improvement in detection for a modest cost in false alarms.")
    else:
        verdict_msg = (
            "  Clear separation. Threshold tuning should improve detection substantially,\n"
            "  and a dedicated three-class model would likely do better still.")
    print(verdict_msg)

    # ================================================================== threshold sweep
    print("\n" + "=" * 78)
    print("THRESHOLD SWEEP — predict NOT CREDIBLE when content_score < t")
    print("=" * 78)

    rows = []
    for t in np.arange(0.05, 0.96, 0.01):
        pred_credible = content >= t
        detection = float((~pred_credible[is_strict]).mean())        # of real FALSE/PARTIAL
        cred_recall = float(pred_credible[is_credible].mean())        # of real CREDIBLE kept
        false_alarm = 1.0 - cred_recall
        macro = f1_score(is_credible.astype(int), pred_credible.astype(int), average="macro")
        rows.append({"threshold": round(float(t), 2), "detection_rate": round(detection, 4),
                     "credible_recall": round(cred_recall, 4), "false_alarm_rate": round(false_alarm, 4),
                     "balanced": round((detection + cred_recall) / 2, 4),
                     "macro_f1_binary": round(float(macro), 4)})
    sweep = pd.DataFrame(rows)
    sweep.to_csv(OUT_DIR / "threshold_sweep.csv", index=False)

    best_bal = sweep.loc[sweep["balanced"].idxmax()]
    best_f1 = sweep.loc[sweep["macro_f1_binary"].idxmax()]
    at_half = sweep.loc[(sweep["threshold"] - 0.50).abs().idxmin()]

    show = sweep[sweep["threshold"].isin([0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80])]
    print(show.to_string(index=False))
    print(f"\n  current default t=0.50 : detection {at_half['detection_rate']:.3f} | "
          f"credible recall {at_half['credible_recall']:.3f} | balanced {at_half['balanced']:.3f}")
    print(f"  best balanced  t={best_bal['threshold']:.2f} : detection {best_bal['detection_rate']:.3f} | "
          f"credible recall {best_bal['credible_recall']:.3f} | balanced {best_bal['balanced']:.3f}")
    print(f"  best macro-F1  t={best_f1['threshold']:.2f} : macro-F1 {best_f1['macro_f1_binary']:.4f}")

    gain = best_bal["detection_rate"] - at_half["detection_rate"]
    cost = at_half["credible_recall"] - best_bal["credible_recall"]
    print(f"\n  Moving 0.50 -> {best_bal['threshold']:.2f} changes detection by {gain:+.3f} "
          f"and credible recall by {-cost:+.3f}.")

    # ================================================================== figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8.4, 4.6))
        ax.plot(sweep["threshold"], sweep["detection_rate"], color="#b5443a",
                label="detection rate on FALSE/PARTIAL")
        ax.plot(sweep["threshold"], sweep["credible_recall"], color="#1f6f8b",
                label="recall on CREDIBLE")
        ax.plot(sweep["threshold"], sweep["balanced"], color="#2f7d5d", ls="--", label="balanced")
        ax.axvline(0.50, color="#999", lw=1, ls=":")
        ax.text(0.505, 0.02, "default 0.50", fontsize=8, color="#666")
        ax.axvline(best_bal["threshold"], color="#2f7d5d", lw=1)
        ax.text(best_bal["threshold"] + .005, 0.94, f"chosen {best_bal['threshold']:.2f}",
                fontsize=8, color="#2f7d5d")
        ax.set_xlabel("decision threshold on P(CREDIBLE)"); ax.set_ylabel("rate")
        ax.set_title("Module 1 — choosing the operating point", loc="left", fontsize=13, pad=11)
        ax.legend(frameon=False, fontsize=9); ax.grid(color="#eee")
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        plt.tight_layout(); plt.savefig(OUT_DIR / "fig_threshold_sweep.png", dpi=200); plt.close()

        fig, ax = plt.subplots(figsize=(7.4, 4.4))
        bins = np.linspace(0, 1, 26)
        for mask, lab, col in ((is_credible, "CREDIBLE", "#1f6f8b"),
                               (is_uncertain, "UNCERTAIN", "#8a8f98"),
                               (is_strict, "FALSE / PARTIAL", "#b5443a")):
            ax.hist(content[mask], bins=bins, density=True, histtype="step", lw=2,
                    color=col, label=f"{lab} (n={mask.sum()})")
        ax.set_xlabel("content score  P(CREDIBLE)"); ax.set_ylabel("density")
        ax.set_title("Score distribution by true label", loc="left", fontsize=13, pad=11)
        ax.legend(frameon=False, fontsize=9); ax.grid(color="#eee")
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        plt.tight_layout(); plt.savefig(OUT_DIR / "fig_score_distributions.png", dpi=200); plt.close()
        print(f"\n  figures -> {OUT_DIR}")
    except Exception as e:
        print(f"  (figures skipped: {type(e).__name__})")

    # ================================================================== fusion sensitivity
    print("\n" + "=" * 78)
    print("FUSION WEIGHT SENSITIVITY")
    print("=" * 78)

    from app.credibility import KnowledgeBase, features_for_domain, rule_based_score
    from app.temporal import evaluate_temporal

    kb = KnowledgeBase(ROOT / "services" / "module2" / "data" / "sri_lankan_sources.json")
    dates = pd.to_datetime(df["datestamp"], errors="coerce")
    ref = (dates.max() + timedelta(days=30)).to_pydatetime().replace(tzinfo=timezone.utc)
    source = np.empty(len(df)); temporal = np.empty(len(df))
    for i, (dom, dt) in enumerate(zip(df["domain"].astype(str), dates)):
        f, _, _ = features_for_domain(kb, dom.lower().strip())
        source[i] = rule_based_score(f)
        pub = None if pd.isna(dt) else dt.to_pydatetime().replace(tzinfo=timezone.utc)
        temporal[i] = evaluate_temporal(pub, now=ref)["score"]

    THRESH_CRED, THRESH_UNC = 0.61, 0.41

    def verdicts(wc, ws, wt):
        s = wc * content + ws * source + wt * temporal
        return np.where(s >= THRESH_CRED, 2, np.where(s >= THRESH_UNC, 1, 0))

    baseline = verdicts(0.50, 0.30, 0.20)
    grid = []
    for wc in np.arange(0.30, 0.75, 0.05):
        for ws in np.arange(0.10, 0.55, 0.05):
            wt = 1.0 - wc - ws
            if wt < 0.05 or wt > 0.40:
                continue
            v = verdicts(wc, ws, wt)
            grid.append({"w_content": round(float(wc), 2), "w_source": round(float(ws), 2),
                         "w_temporal": round(float(wt), 2),
                         "agreement_with_default": round(float((v == baseline).mean()), 4),
                         "pct_credible": round(float((v == 2).mean()), 4),
                         "pct_uncertain": round(float((v == 1).mean()), 4),
                         "pct_misinformation": round(float((v == 0).mean()), 4)})
    sens = pd.DataFrame(grid).sort_values("agreement_with_default")
    sens.to_csv(OUT_DIR / "fusion_sensitivity.csv", index=False)

    agree = sens["agreement_with_default"]
    print(f"  {len(sens)} weightings tested "
          f"(content .30-.70, source .10-.50, temporal .05-.40)")
    print(f"  agreement with the default 50/30/20 weighting:")
    print(f"    mean {agree.mean():.3f} | min {agree.min():.3f} | "
          f"share of weightings agreeing >90% of the time: {(agree > 0.90).mean():.3f}")
    print("\n  least-agreeing weightings:")
    print(sens.head(4).to_string(index=False))

    if agree.min() > 0.85:
        sens_msg = ("  The verdict is stable across the whole grid: no weighting inside this "
                    "range changes more than ~15% of decisions. The exact weights are therefore "
                    "not load-bearing, which is the defensible claim to make.")
    elif agree.mean() > 0.80:
        sens_msg = ("  Mostly stable, with some weightings shifting a meaningful share of "
                    "verdicts. Report the range together with the chosen point.")
    else:
        sens_msg = ("  The verdict is sensitive to the weights. They cannot be presented as "
                    "arbitrary-but-harmless; either fit them on labelled fusion data or narrow "
                    "the claim.")
    print("\n" + sens_msg)

    # ================================================================== summary
    summary = {
        "n_documents": int(len(df)),
        "model": args.model,
        "diagnostic_auc": {
            "credible_vs_rest": round(auc_cred_vs_rest, 4),
            "credible_vs_false_partial": round(auc_cred_vs_strict, 4),
            "uncertain_vs_false_partial": round(auc_unc_vs_strict, 4),
        },
        "threshold": {
            "default_0.50": at_half.to_dict(),
            "recommended_balanced": best_bal.to_dict(),
            "best_macro_f1": best_f1.to_dict(),
        },
        "fusion_sensitivity": {
            "n_weightings": int(len(sens)),
            "agreement_mean": round(float(agree.mean()), 4),
            "agreement_min": round(float(agree.min()), 4),
            "share_above_90pct": round(float((agree > 0.90).mean()), 4),
        },
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR}/summary.json, threshold_sweep.csv, fusion_sensitivity.csv")
    print("\nPaste summary.json back into the chat and we will read it together.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
