# SinhalaCheck

## Source Credibility Analysis & Temporal Verification Module

**Project Documentation**

*Module: Source Credibility & Temporal Verification*
*Stack: Python · FastAPI · scikit-learn (Random Forest)*
*Targets: Sri Lankan news · multilingual input (English / Sinhala / Singlish)*

---

## 1. Executive Summary

SinhalaCheck evaluates whether a news article is from a **credible source** and whether the news is **still timely**. It accepts a URL (and optionally the article body in English, Sinhala, or Singlish), runs a hybrid analysis combining **rule-based logic** with a **trained machine-learning model**, and returns a structured verdict that any client app (web or mobile) can render directly.

The module is built specifically for the Sri Lankan news landscape: the knowledge base is seeded with major Sri Lankan publishers, and the language detector understands Sinhala script and Singlish (Sinhala written in Latin characters).

---

## 2. The Problem It Solves

Misinformation spreads faster when readers cannot quickly verify two simple things:

1. **Is the source trustworthy?** (Is this a real publisher with a track record?)
2. **Is the news current?** (Is this a years-old story being recirculated as breaking news?)

Manual verification is slow and inconsistent. SinhalaCheck automates both checks in a single API call and returns a clear verdict (Trusted / Moderate / Risky) along with human-readable reasons.

---

## 3. System Overview

```
                ┌──────────────────────────────────────────────────────┐
                │                                                      │
   User input ──┤    URL  +  optional article text  +  optional date   │
                │                                                      │
                └─────────────────────────┬────────────────────────────┘
                                          │
                                          ▼
                ┌────────────────────────────────────────────────────┐
                │ 1. Source Identification    (extract domain)       │
                │ 2. Knowledge-Base Lookup    (Sri Lankan sources)   │
                │ 3. Rule-Based Score         (weighted formula)     │
                │ 4. ML Prediction            (Random Forest)        │
                │ 5. Hybrid Score             ((rule + ML) / 2)      │
                │ 6. Temporal Verification    (Fresh / Old / ...)    │
                │ 7. Recirculation Check                             │
                │ 8. Risk Level + Alert + Reasons                    │
                └────────────────────────────┬───────────────────────┘
                                             │
                                             ▼
                ┌────────────────────────────────────────────────────┐
                │  Structured JSON output for the client to render   │
                └────────────────────────────────────────────────────┘
```

---

## 4. The Pipeline — Step by Step

### 4.1 Source Identification

The system extracts the domain from the URL (handling subdomains and missing schemes) and derives a publisher name.

**Example**

| Input URL | Extracted Domain | Publisher |
|---|---|---|
| `https://www.adaderana.lk/news/100123/x` | `adaderana.lk` | Adaderana |
| `news.adaderana.lk/article/y` | `news.adaderana.lk` (also matched to `adaderana.lk` in KB) | News |
| `bbc.com/sinhala/...` | `bbc.com` | Bbc |

### 4.2 Source Credibility Analysis (Rule-Based)

Each source is scored on **five features**, all normalised between 0 and 1:

| Feature | Meaning | Impact |
|---|---|---|
| `registration` | Is the publisher officially registered? (0 or 1) | Moderate |
| `domain_age` | How old / established is the domain? | Moderate |
| `history` | Historical accuracy track record | **High** |
| `editorial` | Editorial quality and standards | Moderate |
| `cross` | Cross-source verification rate | **High** |

These features come from a curated **Sri Lankan news knowledge base** (`data/sri_lankan_sources.json`) containing three tiers:

- **Trusted** — well-known, established publishers (e.g., `adaderana.lk`, `news.lk`, `dailymirror.lk`, `hirunews.lk`, `newsfirst.lk`, `lankadeepa.lk`, plus international `bbc.com`, `reuters.com`)
- **Moderate** — publishers with mixed reputation
- **Blacklist** — known unreliable / fake-news domains

For unknown domains, conservative defaults are used (and the response flags `is_known_source: false`).

**Rule-Based Score Formula** *(weighted average)*:

```
rule_score = 0.15·registration + 0.15·domain_age
           + 0.25·history + 0.20·editorial + 0.25·cross
```

The weights reflect the design doc's guidance that **history** and **cross-verification** have the highest impact on credibility.

### 4.3 Machine Learning Prediction

A **Random Forest classifier** (trained separately, saved as `model/source_cred.pkl`) takes the same five features and predicts:

- `prediction`: 1 = trusted, 0 = fake
- `probability_trusted`: confidence of the "trusted" class (0–1)

The model learns patterns from training data rather than relying on fixed thresholds, which makes it robust to edge cases that pure rules miss.

### 4.4 Hybrid Scoring

The final source score is the **average** of the rule-based score and the ML model's probability:

```
final_score = (rule_score + ml_probability_trusted) / 2
```

This is the design choice from the project document (§6). It gives:

- **Stability** from explicit rules (auditable, explainable)
- **Adaptability** from the ML model (learns from data)

The final score maps to a **risk label**:

| Final Score | Label |
|---|---|
| ≥ 0.70 | **Trusted** |
| 0.40 – 0.70 | **Moderate** |
| < 0.40 | **Risky** |

### 4.5 Temporal Verification

The publication date (when provided) is compared with the current date to compute the article's age and assign a **freshness label**:

| Age | Label | Temporal Score |
|---|---|---|
| ≤ 1 year | Fresh | 1.00 |
| 1–3 years | Recent | 0.70 |
| 3–5 years | Old | 0.40 |
| 5+ years | Very Old | 0.10 |
| Date unknown | Unknown | 0.50 |

### 4.6 Recirculation Detection

A piece of news is flagged as **recirculated** if any of these are true:

1. The client explicitly passes `recirculated: true`.
2. A `seen_count` greater than 1 is provided (the article has been seen before).
3. The URL contains a recirculation hint (`/archive/`, `republished`, `throwback`, `/old/`, `/repost/`).

### 4.7 Risk Level & Alert Banner

The system produces a single, plain-English alert string the client can show as a banner:

| Condition | Alert |
|---|---|
| `final_score < 0.40` AND `temporal_score < 0.30` | High Risk — Outdated and Unreliable |
| `final_score < 0.40` | High Risk News |
| `temporal_score < 0.30` | Outdated News |
| Recirculated AND `final_score < 0.70` | Recirculated Content — Verify Before Sharing |
| `final_score < 0.60` | Moderate Risk News |
| Otherwise | Looks Reliable |

### 4.8 Reasons Generation

The pipeline produces a bullet-list of human-readable explanations the client can show under the verdict, e.g.:

- *"Source is not registered as a recognised publisher"*
- *"Domain is recently created"*
- *"Source has poor historical accuracy"*
- *"Limited cross-source verification for this story"*
- *"Content is outdated (5+ years old)"*
- *"News appears to have been recirculated or republished"*

If everything looks fine, a single positive reason is returned: *"Source meets standard credibility and freshness criteria."*

---

## 5. Multilingual Support

The system is designed for Sri Lankan readers. It accepts and detects three input languages:

| Language | Detection Method |
|---|---|
| **Sinhala** | Unicode block detection (U+0D80 – U+0DFF) |
| **Singlish** | Frequency-based heuristic on common tokens (*machan*, *aiyo*, *kohomada*, *thiyenawa*, *kiyala*, …) |
| **English** | Default fallback for Latin-only text |

The credibility verdict itself is URL-driven (so the score is identical regardless of the article language), but the response includes `detected_language` so the client can render localised UI.

---

## 6. Sri Lankan Focus

| Feature | How it's tuned for Sri Lanka |
|---|---|
| Knowledge Base | Pre-seeded with major Sri Lankan publishers (`.lk` domains and trusted international outlets that cover SL) |
| Domain detection | `is_sri_lankan_source` flag set when the domain ends in `.lk` |
| Topic detection | `mentions_sri_lanka` flag fires when the text mentions Sri Lankan places/names (Colombo, Kandy, Lanka, Rajapaksa, Wickremesinghe, etc.) |
| Language | Sinhala + Singlish detection |
| Curation | Trusted / Moderate / Blacklist tiers maintained in `data/sri_lankan_sources.json` |

---

## 7. Code Structure

```
backend/
├── main.py                          ← FastAPI app — exposes the endpoints
├── requirements.txt
├── data/
│   └── sri_lankan_sources.json      ← curated SL news knowledge base
├── model/
│   └── source_cred.pkl              ← trained Random Forest model
└── app/
    ├── source.py                    ← URL → domain & publisher
    ├── credibility.py               ← rule-based score + KB lookup
    ├── temporal.py                  ← publication-date freshness logic
    ├── language.py                  ← English / Sinhala / Singlish detection
    ├── ml_loader.py                 ← loads the .pkl model at startup
    ├── schemas.py                   ← request / response data shapes
    └── pipeline.py                  ← orchestrates the full pipeline
```

Each file has a single, clear responsibility — easy to maintain, test, and extend.

---

## 8. API Endpoints

The backend exposes three HTTP endpoints. All return JSON.

### 8.1 `GET /` — Health check

Simple "is the service alive?" probe. No input.

### 8.2 `GET /sources` — Known sources

Returns the contents of the knowledge base (trusted / moderate / blacklist). Useful for the frontend to show a "this is a verified Sri Lankan publisher" badge.

### 8.3 `POST /analyze` — Full pipeline (the main endpoint)

The end-to-end endpoint the frontend calls. It runs every step from §4 and returns the complete report.

**Request**
```json
{
  "url": "https://www.adaderana.lk/news/100123/sample",
  "text": "කොළඹ දී අද සිදුවූ සිදුවීම පිළිබඳව...",
  "published_date": "2026-04-01T08:30:00Z",
  "cross_count": 3
}
```

**Response (every field returned by the API)**
```json
{
  "source_score": 0.956,
  "source_label": "Trusted",
  "ml_prediction": 1,
  "ml_confidence": 0.999,
  "temporal_score": 1.0,
  "time_label": "Fresh",
  "recirculated": false,
  "confidence": 0.999,
  "alert": "Looks Reliable",
  "reasons": ["Source meets standard credibility and freshness criteria"],
  "breakdown": {
    "registration": 1.0,
    "domain_age": 0.95,
    "history": 0.9,
    "editorial": 0.85,
    "cross": 0.9
  },
  "domain": "adaderana.lk",
  "publisher": "Adaderana",
  "detected_language": "sinhala",
  "is_sri_lankan_source": true,
  "mentions_sri_lanka": true,
  "is_known_source": true,
  "source_tier": "trusted",
  "rule_score": 0.912,
  "ml_probability_trusted": 0.999,
  "age_days": 35.33
}
```

---

## 9. Worked Examples

### Example A — Trusted Sri Lankan source, recent article, Sinhala input

| Input | Value |
|---|---|
| URL | `https://www.adaderana.lk/news/100123/sample` |
| Text | `කොළඹ දී අද සිදුවූ සිදුවීම පිළිබඳව` |
| Date | 5 weeks ago |

| Output | Value |
|---|---|
| Source Score | **0.96** |
| Label | **Trusted** |
| Time Label | Fresh |
| Detected Language | Sinhala |
| Alert | "Looks Reliable" |
| Reason | "Source meets standard credibility and freshness criteria" |

### Example B — Unknown source, 7-year-old article, Singlish input

| Input | Value |
|---|---|
| URL | `https://random-blog.example/post/1` |
| Text | `Aiyo machan, Colombo eke aluth news ekak thiyenawa.` |
| Date | 2019-01-01 |

| Output | Value |
|---|---|
| Source Score | **0.15** |
| Label | **Risky** |
| Time Label | Very Old |
| Detected Language | Singlish |
| `mentions_sri_lanka` | true |
| Alert | "High Risk — Outdated and Unreliable" |
| Reasons | "Unknown source — no curated credibility data available", "Source is not registered as a recognised publisher", "Limited cross-source verification for this story", "Content is outdated (5+ years old)" |

### Example C — Blacklisted domain

| Input | Value |
|---|---|
| URL | `http://fakelanka-news.com/article/breaking` |

| Output | Value |
|---|---|
| Source Score | **0.03** |
| Label | **Risky** |
| Source Tier | blacklisted |
| Alert | "High Risk News" |
| First Reason | *"'fakelanka-news.com' is on the blacklist of known unreliable sources"* |

---

## 10. Technical Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI |
| ML library | scikit-learn (Random Forest Classifier) |
| Data validation | Pydantic v2 |
| Data handling | pandas |
| Server | Uvicorn (ASGI) |

**Dependencies (requirements.txt):**

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pandas>=2.0.0
scikit-learn==1.6.1
pydantic>=2.0.0
```

No external API calls or paid services are required. Everything runs locally.

---

## 11. How to Run

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Once running:

- Browse `http://localhost:8000/docs` for an interactive Swagger UI.
- Test with `curl`:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.adaderana.lk/news/123/test\",\"published_date\":\"2026-04-01T00:00:00Z\"}"
```

---

## 12. How the ML Model Is Used (Proof)

The trained Random Forest model is loaded **once** when the server starts and is reused on every request:

1. **At startup** (`main.py`) → `load_model()` reads `model/source_cred.pkl` and stores it in memory.
2. **On every `POST /analyze`** call → `pipeline.py` calls `model.predict(...)` and `model.predict_proba(...)` with the resolved features.
3. **The model's output drives 50% of the final score** via the hybrid formula `final_score = (rule_score + ml_probability_trusted) / 2`.
4. **Every response contains `ml_prediction`, `ml_confidence`, and `ml_probability_trusted`** — these come directly from the model.

If `model/source_cred.pkl` were missing, the server would refuse to start (it raises a `FileNotFoundError`).

---

## 13. Future Enhancements

| Enhancement | Notes |
|---|---|
| Live WHOIS lookup for `domain_age` | Auto-update domain age instead of using curated values |
| Live cross-verification | Scrape headlines from competing trusted sources to compute `cross_count` automatically |
| Sinhala-translated `reasons` | Return reasons in the user's detected language |
| Author-level credibility | Add a per-author trust score on top of source-level scoring |
| Article-text content analysis | Detect sensational language, clickbait headlines, etc. |
| Admin dashboard | Allow editors to add / remove domains from the knowledge base via a UI |

---

## 14. Conclusion

This module delivers a **robust, explainable, multilingual** source-credibility and temporal-verification engine, purpose-built for Sri Lankan news. It combines deterministic rule-based logic with a machine-learning model, exposes the result through a clean REST API, and is ready to be consumed by web or mobile clients.

Each verdict is **transparent**: every score has an audit trail (rule score, ML probability, breakdown, reasons), so end-users and editors alike can understand *why* a story was flagged.

---

*Document version 1.0 · Module: Source Credibility & Temporal Verification*
