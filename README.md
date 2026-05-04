# R26-IT-158 | SinhalaCheck - Sinhala Fake News Detection System

**Project ID:** R26-IT-158
**Academic Year:** 2025-2026
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
| TBD | Caledra | Fusion Engine | Team Member |
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