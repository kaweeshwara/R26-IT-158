# Analysis scripts

Run these **after** the Module 1 model exists (locally or on the Hugging Face Hub).

| Script | What it answers | Output |
|---|---|---|
| `analyse_operating_point.py` | Where should the decision threshold sit, and do the fusion weights matter? | `analysis/` — CSVs, two figures, `summary.json` |
| `fit_fusion_weights.py` | Can the fusion weights be fitted from the corpus? | rewrites `services/fusion/weights.json` |

```bash
python scripts/analyse_operating_point.py --model Kaweeshwara/sinhalacheck-module1
python scripts/analyse_operating_point.py --model ./path/to/model --limit 800   # CPU
```

Scoring 3,000 documents is the slow step; it is cached to `analysis/content_scores.csv`, so
re-runs can skip it with `--scores analysis/content_scores.csv`.

**Read the honesty notes at the top of both scripts.** They record what the corpus can and
cannot support, which matters more than the numbers they print.
