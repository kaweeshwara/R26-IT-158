# R26-IT-158 | SinhalaCheck - Sinhala Fake News Detection System

**Project ID:** R26-IT-158
**Academic Year:** - 2026
**Degree Program:** B.Sc. (Hons) in Information Technology
**Institution:** SLIIT

---

## Project Overview

An AI-powered Sinhala language fake news detection system using 
NLP and transformer-based models to identify misinformation in 
Sri Lankan social media and news platforms.

---

## Team Members

| Student ID | Name | Component | Role |
|------------|------|-----------|------|
| IT22331304 | Kaweeshwara P.D.S. | NLP Content Credibility Analysis | Team Leader |
| IT22370778 | Caledra S.T.H | Source Credibility and Temporal verification | Team Member |
| TBD | Wishmitha | TBD | Team Member |

---

## Individual Component - NLP Content Credibility Analysis
**Developer:** Kaweeshwara P.D.S. (IT22331304)

XLM-RoBERTa transformer model fine-tuned on Sinhala fake news 
corpus for credibility classification.

### Model Performance
| Model | Accuracy | Macro F1 |
|-------|----------|----------|
| Original Naive Bayes (Baseline) | ~65% | ~0.58 |
| XLM-RoBERTa (Ours) | 70% | 0.62 |
| XLM-RoBERTa + Class Weighting | 65% | 0.62 |

### Dataset
- LIRNEasia Sinhala Fake News Corpus (3,576 documents)
- Labels: CREDIBLE, FALSE, PARTIAL, UNCERTAIN
- Binary classification: CREDIBLE vs NOT CREDIBLE

---

## Technology Stack

- Python, PyTorch, HuggingFace Transformers
- XLM-RoBERTa (xlm-roberta-base)
- Flask (upcoming - PP2)
- Google Colab T4 GPU

---

## Research References

- LIRNEasia Sinhala Fake News Corpus (2021)
- NSina Corpus - HuggingFace (LREC-COLING 2024)
- Ontology Based Fake News Detection for Sinhala (ICITR 2021)
- Hybrid Approach for Detection of Fake News in Sinhala (ICTer 2022)
- Early Detection of Sinhala Fake News (UoM 2024)

---

## Phase 2 Plans

- Domain adaptive pretraining on NSina corpus (500k articles)
- Singlish mixed text handling
- Flask REST API for Fusion Engine integration
- Confidence scoring output format

---

## Project Structure

- SinhalaCheck_NLP.ipynb - Training notebook
- models/ - Saved model files
- data/ - Dataset files
- app/ - Flask application (upcoming)

# Individual Component - Source Credibility & Temporal Verification  
Developer: Caldera S.T.H(IT22370778)

Source credibility and temporal verification module for Sinhala fake news detection using a hybrid Machine Learning and Rule-Based approach.

---

# Component Overview

This component evaluates the trustworthiness of news sources and detects outdated or recirculated news that may become misleading when reshared.

The system analyzes:
- Source reliability
- Domain reputation
- Historical accuracy
- Cross-source verification
- Publishing timestamps
- Recirculation behavior

The final output classifies news into:
- TRUSTED
- MODERATE
- RISKY

It also identifies old news being reshared in misleading contexts.

---

# Model / Approach

## Random Forest + Rule-Based Verification

### Machine Learning Part
A Random Forest classifier is used to predict source credibility based on multiple credibility-related features.

### Rule-Based Part
The rule-based engine performs:
- Temporal verification
- Re-circulated news detection
- Outdated news identification
- Time-gap analysis

This hybrid approach improves reliability and practical misinformation detection.

---

# Model Performance

| Model | Purpose |
|---|---|
| Random Forest | Source credibility classification |
| Rule-Based Engine | Temporal verification |

### Credibility Score Labels

| Score Range | Classification |
|---|---|
| 0.70 - 1.00 | Trusted |
| 0.40 - 0.69 | Moderate |
| Below 0.40 | Risky |

---

# Dataset

## Synthetic Source Credibility Dataset

Due to limited publicly available Sinhala datasets for source credibility and temporal verification, a synthetic dataset was created using realistic misinformation-related factors.

Dataset Features:
- Source reliability score
- Domain reputation
- Historical accuracy
- Publishing timestamp
- Verification availability
- Recirculation indicators

---

# Technology Stack

- Python
- Pandas
- Scikit-learn
- Google Colab
- Random Forest Classifier
- Rule-Based Logic
- Flask (Upcoming - PP2)

---

# Research References

- Sinhala Fake News Detection Research
- Source Credibility Analysis Studies
- Temporal Verification Research
- Misinformation Detection Papers
- Re-circulated News Detection Studies

---

# Why Random Forest?

Random Forest was selected because it:
- Handles multiple features effectively
- Reduces overfitting
- Provides stable classification performance
- Works well for structured credibility datasets

---

# Why Temporal Verification?

Old news can become misleading when reshared later without proper context.

Temporal verification helps:
- Detect outdated news
- Identify re-circulated misinformation
- Improve fake news detection reliability

---

# Phase 2 Plans

- Real-time source verification
- Flask REST API integration
- Advanced temporal analysis
- Confidence score output
- Improved recirculated news detection

---

# Project Structure

```bash
SourceCredibility/
│
├── credibility_model.ipynb
├── data/
├── models/
├── temporal_engine/
├── app/
└── README.md
