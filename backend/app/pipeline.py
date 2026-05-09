"""End-to-end source-credibility & temporal-verification pipeline.

Pipeline (per design doc §2):
    URL/text -> source identification -> rule-based score -> ML prediction
        -> hybrid score -> temporal verification -> output
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from .credibility import (
    FEATURE_COLUMNS,
    KnowledgeBase,
    features_for_domain,
    risk_level,
    rule_based_score,
)
from .language import detect_language, mentions_sri_lanka
from .source import derive_publisher, extract_domain, is_sri_lankan_domain
from .temporal import detect_recirculation, evaluate_temporal


def _ml_predict(model, features: dict) -> tuple[int, float, float]:
    """Return ``(prediction, prob_trusted, max_confidence)``."""
    X = pd.DataFrame([features], columns=FEATURE_COLUMNS)
    prediction = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0]
    classes = list(getattr(model, "classes_", []))

    if 1 in classes:
        prob_trusted = float(proba[classes.index(1)])
    elif 0 in classes:
        prob_trusted = 1.0 - float(proba[classes.index(0)])
    else:
        prob_trusted = float(max(proba))

    return prediction, prob_trusted, float(max(proba))


def _build_reasons(
    *,
    features: dict,
    tier: str,
    temporal: dict,
    recirculated: bool,
    is_sri_lankan: bool,
    domain: str,
) -> list[str]:
    reasons: list[str] = []

    if tier == "blacklisted":
        reasons.append(f"'{domain}' is on the blacklist of known unreliable sources")
    elif tier == "unknown":
        reasons.append("Unknown source — no curated credibility data available")
    elif tier == "moderate":
        reasons.append("Source has moderate credibility based on past performance")

    if features["registration"] == 0:
        reasons.append("Source is not registered as a recognised publisher")
    if features["domain_age"] < 0.30:
        reasons.append("Domain is recently created")
    if features["history"] < 0.40:
        reasons.append("Source has poor historical accuracy")
    if features["editorial"] < 0.40:
        reasons.append("Source has weak editorial standards")
    if features["cross"] < 0.40:
        reasons.append("Limited cross-source verification for this story")

    label = temporal["label"]
    if label == "Old":
        reasons.append("Content is more than 3 years old")
    elif label == "Very Old":
        reasons.append("Content is outdated (5+ years old)")
    elif label == "Unknown":
        reasons.append("Publication date could not be determined")

    if recirculated:
        reasons.append("News appears to have been recirculated or republished")

    if not is_sri_lankan:
        reasons.append("Source is not based in Sri Lanka")

    if not reasons:
        reasons.append("Source meets standard credibility and freshness criteria")
    return reasons


def _build_alert(final_score: float, temporal_score: float, recirculated: bool) -> str:
    if final_score < 0.40 and temporal_score < 0.30:
        return "High Risk — Outdated and Unreliable"
    if final_score < 0.40:
        return "High Risk News"
    if temporal_score < 0.30:
        return "Outdated News"
    if recirculated and final_score < 0.70:
        return "Recirculated Content — Verify Before Sharing"
    if final_score < 0.60:
        return "Moderate Risk News"
    return "Looks Reliable"


def _overall_confidence(ml_confidence: float, tier: str) -> float:
    """Confidence in the *overall* assessment (not just the ML head).

    Combines the ML's class probability with how much we trust the input
    features (high if the source is in our KB, lower if unknown).
    """
    kb_confidence = {"trusted": 1.0, "moderate": 0.9, "blacklisted": 1.0, "unknown": 0.5}.get(tier, 0.6)
    return 0.6 * ml_confidence + 0.4 * kb_confidence


def analyze(
    *,
    kb: KnowledgeBase,
    model,
    url: str,
    text: Optional[str] = None,
    published_date: Optional[datetime] = None,
    recirculated_override: Optional[bool] = None,
    cross_count: Optional[int] = None,
    seen_count: Optional[int] = None,
) -> dict:
    """Run the full credibility + temporal pipeline and return the result dict."""
    domain = extract_domain(url)
    publisher = derive_publisher(domain)

    features, tier, _matched = features_for_domain(kb, domain, cross_count=cross_count)

    is_sl_source = is_sri_lankan_domain(domain)
    text_mentions_sl = mentions_sri_lanka(text)

    rule_score = rule_based_score(features)
    ml_prediction, ml_prob_trusted, ml_confidence = _ml_predict(model, features)

    # Hybrid score (per design doc §6): mean of rule score and ML probability.
    final_score = (rule_score + ml_prob_trusted) / 2.0

    temporal = evaluate_temporal(published_date)
    recirculated = detect_recirculation(
        url,
        age_days=temporal["age_days"],
        override=recirculated_override,
        seen_count=seen_count,
    )

    confidence = _overall_confidence(ml_confidence, tier)
    alert = _build_alert(final_score, temporal["score"], recirculated)
    reasons = _build_reasons(
        features=features,
        tier=tier,
        temporal=temporal,
        recirculated=recirculated,
        is_sri_lankan=is_sl_source,
        domain=domain,
    )

    return {
        "source_score": round(final_score, 3),
        "source_label": risk_level(final_score),
        "ml_prediction": ml_prediction,
        "ml_confidence": round(ml_confidence, 3),
        "temporal_score": round(temporal["score"], 3),
        "time_label": temporal["label"],
        "recirculated": recirculated,
        "confidence": round(confidence, 3),
        "alert": alert,
        "reasons": reasons,
        "breakdown": {k: round(float(features[k]), 3) for k in FEATURE_COLUMNS},
        "domain": domain,
        "publisher": publisher,
        "detected_language": detect_language(text),
        "is_sri_lankan_source": is_sl_source,
        "mentions_sri_lanka": text_mentions_sl,
        "is_known_source": tier != "unknown",
        "source_tier": tier,
        "rule_score": round(rule_score, 3),
        "ml_probability_trusted": round(ml_prob_trusted, 3),
        "age_days": temporal["age_days"],
    }
