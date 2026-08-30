# Module 4 — Explainability (XAI)

**Wishmitha (IT22259752)** · Fusion, XAI explanation & user application

Runs LIME (Local Interpretable Model-agnostic Explanations) against Module 1's
own published content-credibility model, so every verdict comes with a
human-readable "why" rather than a bare score.

## Why a separate service

Following the same design decision as the rest of the system: **modules are
called, not imported.** This service loads Module 1's model independently
(directly from `Kaweeshwara/sinhalacheck-module1` on the Hugging Face Hub),
so it can be measured, versioned, and swapped without touching Module 1's
own deployment.

## Run

```bash
cd services/module4
pip install -r requirements.txt
uvicorn main:app --port 8003
```

Docs at `http://127.0.0.1:8003/docs`.

## API

`POST /explain`
```json
{ "text": "...", "num_features": 5, "num_samples": 100 }
```

Returns the model's own prediction (`credible` / `not_credible` probabilities)
plus the top contributing words and their signed LIME weights.

## Design notes

- **Sinhala-safe tokenisation.** LIME's default whitespace splitter fractures
  Sinhala conjunct clusters when punctuation is attached to a word
  (e.g. `"විවර."` splitting mid-glyph). Punctuation is separated from words
  before explanation, and stripped again from the returned words for display.
- **`num_samples` is tunable per request.** Lower values (50–100) trade
  explanation stability for response time; this matters on CPU-only
  deployments, where 300 perturbations can take 30–60 seconds.
- **This is a genuinely separate research contribution from Module 1's
  accuracy work**: Module 1 optimises *what* the model predicts; this service
  investigates *why*, and is evaluated separately via a user study comparing
  decision accuracy with and without these explanations shown.