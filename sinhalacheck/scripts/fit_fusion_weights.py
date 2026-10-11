"""Fit the fusion weights from labelled data instead of choosing them by hand.

The review panel's note on Module 4 was that combination weights should come from
"standard and accepted methods" rather than being assigned. This script does that: it
scores every document in the LIRNEasia corpus with each module, fits a logistic regression
predicting the corpus label from those scores, and converts the coefficients into
normalised fusion weights.

Honesty about what can and cannot be fitted
-------------------------------------------
The corpus supports fitting the **content** and **source** weights: it carries article
text and a publisher domain, and Module 2's knowledge base covers many of those domains.

It does **not** support fitting the **temporal** weight. Every document was collected in
the same period, so measured today they are all "Very Old" and the signal has almost no
variance; and the corpus has no recirculation labels at all, which is the phenomenon the
temporal module exists to catch. Fitting a weight on a constant would produce a number
with no meaning behind it.

So this script fits what the data supports, and records in `weights.json` exactly which
weights were fitted and which were not. That distinction is more defensible than a
complete-looking set of numbers where some are quietly invented.

Usage
-----
    python fit_fusion_weights.py --model <path-or-hub-id> [--limit N] [--device cuda]

A GPU makes this quick. On CPU, pass --limit 600 for a representative subsample.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "module2"))

CORPUS_XLSX = "https://raw.githubusercontent.com/LIRNEasia/MisinformationCorpusSinhala/main/Corpus.xlsx"


def normalise_type(v):
    if isinstance(v, bool):
        return "FALSE" if v is False else "TRUE"
    return str(v).strip().upper()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Kaweeshwara/sinhalacheck-module1",
                    help="Module 1 model: local directory or Hugging Face id.")
    ap.add_argument("--limit", type=int, default=None, help="Score only the first N documents.")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--device", default=None, help="cuda | cpu (default: auto)")
    ap.add_argument("--out", default=str(ROOT / "services" / "fusion" / "weights.json"))
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    from app.credibility import KnowledgeBase, features_for_domain, rule_based_score
    from app.temporal import evaluate_temporal

    # ----------------------------------------------------------------- corpus
    print("Loading corpus ...")
    df = pd.read_excel(CORPUS_XLSX)
    df["type"] = df["type"].apply(normalise_type)
    df = df[df["content"].astype(str).str.strip().str.len() > 0].reset_index(drop=True)
    if args.limit:
        df = df.sample(min(args.limit, len(df)), random_state=42).reset_index(drop=True)
    y = (df["type"] == "CREDIBLE").astype(int).values
    print(f"  {len(df)} documents | {y.sum()} CREDIBLE / {len(y)-y.sum()} NOT CREDIBLE")

    # ----------------------------------------------------------------- module 1
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"Scoring content with {args.model} on {device} ...")
    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model).to(device).eval()
    id2label = {int(k): str(v).upper() for k, v in model.config.id2label.items()}
    ci = next((i for i, l in id2label.items() if "NOT" not in l and "CREDIBLE" in l), 1)

    texts = df["content"].astype(str).tolist()
    content = np.empty(len(texts), dtype=float)
    for i in range(0, len(texts), args.batch_size):
        batch = texts[i:i + args.batch_size]
        enc = tok(batch, truncation=True, padding=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            logits = model(**{k: v.to(device) for k, v in enc.items()}).logits
        content[i:i + len(batch)] = torch.softmax(logits, -1)[:, ci].cpu().numpy()
        if i % (args.batch_size * 20) == 0:
            print(f"  {i}/{len(texts)}")

    # ----------------------------------------------------------------- module 2
    print("Scoring source and recency ...")
    kb = KnowledgeBase(ROOT / "services" / "module2" / "data" / "sri_lankan_sources.json")

    # Recency is measured against a fixed reference just after the corpus ends, rather than
    # today. Measured today every article is >3 years old and the feature is a constant.
    dates = pd.to_datetime(df["datestamp"], errors="coerce")
    reference = (dates.max() + timedelta(days=30)).to_pydatetime().replace(tzinfo=timezone.utc)
    print(f"  recency reference date: {reference:%Y-%m-%d}")

    source = np.empty(len(df), dtype=float)
    temporal = np.empty(len(df), dtype=float)
    known = 0
    for i, (dom, dt) in enumerate(zip(df["domain"].astype(str), dates)):
        feats, tier, _ = features_for_domain(kb, dom.lower().strip())
        source[i] = rule_based_score(feats)
        known += tier != "unknown"
        pub = None if pd.isna(dt) else dt.to_pydatetime().replace(tzinfo=timezone.utc)
        temporal[i] = evaluate_temporal(pub, now=reference)["score"]

    print(f"  domains recognised by the knowledge base: {known}/{len(df)} "
          f"({100*known/len(df):.1f}%)")
    for name, arr in (("content", content), ("source", source), ("temporal", temporal)):
        print(f"  {name:9s} mean {arr.mean():.3f}  sd {arr.std():.3f}  "
              f"unique {len(np.unique(np.round(arr,3)))}")

    # ----------------------------------------------------------------- choose fittable signals
    MIN_SD = 0.02
    candidates = {"content": content, "source": source, "temporal": temporal}
    fittable = {k: v for k, v in candidates.items() if v.std() >= MIN_SD}
    excluded = {k: round(float(v.std()), 4) for k, v in candidates.items() if k not in fittable}

    if excluded:
        print("\nExcluded from fitting (insufficient variance in this corpus):")
        for k, sd in excluded.items():
            print(f"  {k}: sd={sd}")

    names = list(fittable)
    X = np.column_stack([fittable[k] for k in names])

    # ----------------------------------------------------------------- fit
    print("\nFitting logistic regression ...")
    clf = LogisticRegression(max_iter=2000, class_weight="balanced")
    cv = cross_val_score(clf, X, y, cv=5, scoring="roc_auc")
    clf.fit(X, y)
    coefs = clf.coef_[0]
    print(f"  cross-validated ROC-AUC: {cv.mean():.4f} +/- {cv.std():.4f}")
    for n, c in zip(names, coefs):
        print(f"  coefficient  {n:9s} {c:+.4f}")

    # Negative coefficients would mean a higher module score predicts LESS credible, which
    # would indicate a sign error in that module rather than a weight worth using.
    clipped = np.clip(coefs, 0, None)
    if (coefs < 0).any():
        print("  !! negative coefficient(s) clipped to zero - inspect the module(s) above.")
    if clipped.sum() == 0:
        print("  !! no positive coefficients; refusing to write degenerate weights.")
        return 1

    fitted = {n: float(c / clipped.sum()) for n, c in zip(names, clipped)}

    # Unfittable signals keep a small fixed weight so they still influence the result, and
    # weights.json records that these specific numbers were assigned, not learned.
    ASSIGNED = {"temporal": 0.20}
    assigned = {k: ASSIGNED.get(k, 0.10) for k in excluded}
    scale = 1.0 - sum(assigned.values())
    weights = {k: round(v * scale, 4) for k, v in fitted.items()}
    weights.update({k: round(v, 4) for k, v in assigned.items()})

    out = {
        "method": "logistic_regression_l2",
        "fitted_on": "LIRNEasia Sinhala Misinformation Corpus (Corpus.xlsx)",
        "fitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_samples": int(len(df)),
        "weights": weights,
        "intercept": 0.0,
        "thresholds": {"credible": 0.61, "uncertain": 0.41},
        "fitting_detail": {
            "fitted_signals": names,
            "raw_coefficients": {n: round(float(c), 4) for n, c in zip(names, coefs)},
            "cv_roc_auc_mean": round(float(cv.mean()), 4),
            "cv_roc_auc_std": round(float(cv.std()), 4),
            "assigned_not_fitted": assigned,
            "excluded_signal_sd": excluded,
            "recency_reference_date": reference.strftime("%Y-%m-%d"),
            "kb_domain_coverage": round(known / len(df), 4),
        },
        "notes": (
            "Content and source weights fitted by logistic regression on the labelled corpus. "
            "Temporal could not be fitted: the corpus is single-period, so recency has no "
            "variance, and it carries no recirculation labels. Its weight is assigned and is "
            "reported as such rather than presented as an empirical result."
        ),
    }

    Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.out}")
    print(json.dumps(weights, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
