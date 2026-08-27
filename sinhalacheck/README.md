# SinhalaCheck — integrated system

**R26-IT-158** · B.Sc. (Hons) in Information Technology · SLIIT

Sinhala misinformation detection. Three services behind one interface: content credibility,
source credibility and temporal verification, and a fusion layer that combines them.

```
                       ┌──────────────────────────────┐
   browser  ─────────► │  fusion   :8000  (+ web UI)  │
                       └───────┬──────────────┬───────┘
                          HTTP │              │ HTTP
                  ┌────────────▼───┐   ┌──────▼──────────────────┐
                  │ module1  :8001 │   │ module2  :8002          │
                  │ content        │   │ source + temporal       │
                  │ LaBSE          │   │ RandomForest + rules    │
                  └────────────────┘   └─────────────────────────┘
```

---

## Running it

```bash
pip install -r requirements.txt
python run_all.py
```

`run_all.py` starts all three services, waits for each to answer, and opens
<http://127.0.0.1:8000>. Ctrl-C stops everything.

Module 1 loads a ~1.9GB transformer, so first start takes a minute or two — longer on the
very first run, when the weights download from the Hugging Face Hub.

Each service also runs standalone with interactive API docs:

| Service | Port | Docs |
|---|---|---|
| Fusion + UI | 8000 | <http://127.0.0.1:8000> |
| Module 1 — content | 8001 | <http://127.0.0.1:8001/docs> |
| Module 2 — source & temporal | 8002 | <http://127.0.0.1:8002/docs> |

### Pointing Module 1 at a different model

Resolution order: `MODULE1_MODEL_PATH` → a local `./model` directory → the Hugging Face Hub
copy at `Kaweeshwara/sinhalacheck-module1`.

```bash
MODULE1_MODEL_PATH=/path/to/SinhalaCheck_model_final python run_all.py
```

---

## Module 1 — content credibility

LaBSE fine-tuned on the LIRNEasia Sinhala Misinformation Corpus. Binary:
`CREDIBLE` = 1, `NOT_CREDIBLE` = 0.

Selected by 5-fold cross-validation over all 3,000 documents, at 512 tokens:

| Model | Accuracy | Macro-F1 | fold σ |
|---|---|---|---|
| **LaBSE** | **0.7767** | **0.7534** | 0.013 |
| LaBSE + class weights | 0.7520 | 0.7384 | 0.016 |
| SinBERT-large | 0.7287 | 0.7095 | 0.013 |
| TF-IDF + Linear SVM *(baseline)* | 0.7217 | 0.6958 | — |
| TF-IDF + Naive Bayes *(baseline)* | 0.6793 | 0.4705 | — |
| XLM-R base, damaged CSV *(control)* | 0.6663 | 0.4509 | 0.071 |
| Majority class | 0.6657 | 0.3996 | — |

Every comparison is significant by paired bootstrap on macro-F1 (2,000 resamples):
vs the SVM baseline **+0.058**, 95% CI [0.040, 0.076]; vs the damaged-CSV control
**+0.302**, 95% CI [0.280, 0.324]. Both p < 0.0001, and McNemar agrees.

Candidate models follow *BERTifying Sinhala* (Dhananjaya et al., LREC 2022).

### A data-integrity hazard in the published corpus

The LIRNEasia repository distributes the corpus in two formats, with no warning on either:

| File | Sinhala text |
|---|---|
| `Corpus.csv` | **destroyed** — every codepoint replaced by `?` (0.0 Sinhala characters per document) |
| `Corpus.xlsx` | intact (1,714 Sinhala characters per document) |

Same 3,000 documents, same order, same labels — verified row by row.

The CSV is the format most naturally consumed programmatically, and the failure is silent:
a model trained from it does not error, it trains, reports plausible accuracy, and has
learned nothing from the text. The control row above quantifies the cost on identical
documents: macro-F1 **0.451 vs 0.753**, and CREDIBLE recall **0.060 vs 0.702**.

Note that accuracy alone barely moves (0.666 vs 0.777) because the damaged model scores well
by rarely predicting CREDIBLE at all. Reporting accuracy alone would hide the failure
entirely — which is why macro-F1 is the headline metric here.

---

## Module 2 — source credibility & temporal verification

Author: Caldera S.T.H (IT22370778). Vendored unmodified from the `caledra` branch.

Random Forest over five credibility features, combined with a rule-based score from a curated
Sri Lankan source knowledge base, plus recency and recirculation checks.

**Known limitation:** the knowledge base holds 24 domains and recognises only **19.9%** of
publishers in the corpus; the rest fall back to a constant. See
[`services/module2/MISSING_DOMAINS.md`](services/module2/MISSING_DOMAINS.md) — adding the ten
highest-impact domains raises coverage to about 70%.

---

## Fusion

The fusion service calls both modules over HTTP and combines their scores. Three properties
are deliberate, and each answers a specific review finding.

**Modules are called, not imported.** An earlier prototype loaded Module 1's weights directly
into the fusion process, which erases the module boundary: Module 1 stops being independently
deployable, versionable or measurable. Here each module is a service with its own contract.

**Weights carry their provenance.** `services/fusion/weights.json` records the method used and
what it was fitted on, and every API response includes `weights_provenance` with an
`is_fitted` flag. The UI shows a warning banner while the weights are unfitted placeholders.
A reader can always tell a fitted number from an assigned one.

**Missing signals are dropped, not faked.** The primary user pastes a WhatsApp forward: no URL,
no date, so Module 2 cannot contribute. Rather than substituting a neutral 0.5 — which quietly
drags every score toward the middle — fusion renormalises over the signals actually present
and reports which those were.

```jsonc
// text-only request: content is the only available signal
"breakdown":      { "content": 0.18, "source": null, "temporal": null },
"fusion_detail":  { "signals_used": ["content"],
                    "signals_missing": ["source","temporal"],
                    "effective_weights": { "content": 1.0 },
                    "renormalised": true }
```

### Fitting the weights

```bash
python scripts/fit_fusion_weights.py --model Kaweeshwara/sinhalacheck-module1
```

Scores every corpus document with each module, fits a logistic regression predicting the
corpus label, and writes normalised weights with full provenance.

**Read the honesty note in that script before relying on its output.** The corpus does not
support fitting all three weights. It is single-period, so recency is nearly constant, and it
carries no recirculation labels at all. Source credibility is also weak against this
particular target: it reaches only **0.535 ROC-AUC** (chance is 0.5), partly because 80% of
domains are unknown to the knowledge base, and partly because the LIRNEasia label describes
*content* credibility, not publisher reliability. The script fits what the data supports and
records which weights were assigned rather than learned.

---

## Layout

```
services/module1/    content credibility API (this project's Module 1)
services/module2/    source + temporal API (vendored from the caledra branch)
services/fusion/     fusion gateway, weights.json, serves the UI
frontend/            single-page UI, no build step, no dependencies
scripts/             fit_fusion_weights.py
run_all.py           starts all three services
```

## Reproducing the Module 1 results

`SinhalaCheck_Module1_Validated.ipynb` runs end to end on a Colab T4 with no manual input —
it downloads both corpus distributions itself. Roughly 90–120 minutes.
