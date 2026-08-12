"""Rule-based credibility scoring backed by a Sri Lankan source knowledge base."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .source import domain_variants

# Per the design doc (§10):
#   - history & cross-verification have HIGH impact
#   - registration, domain age, editorial have MODERATE impact
WEIGHTS: dict[str, float] = {
    "registration": 0.15,
    "domain_age":   0.15,
    "history":      0.25,
    "editorial":    0.20,
    "cross":        0.25,
}

FEATURE_COLUMNS: list[str] = list(WEIGHTS.keys())

# Conservative defaults for sources we don't recognise.
UNKNOWN_DEFAULTS: dict[str, float] = {
    "registration": 0,
    "domain_age":   0.30,
    "history":      0.40,
    "editorial":    0.40,
    "cross":        0.30,
}

# Features used when a domain is on the blacklist.
BLACKLIST_FEATURES: dict[str, float] = {
    "registration": 0,
    "domain_age":   0.10,
    "history":      0.05,
    "editorial":    0.05,
    "cross":        0.05,
}

_DEFAULT_KB_PATH = Path(__file__).resolve().parent.parent / "data" / "sri_lankan_sources.json"


class KnowledgeBase:
    """Loads the curated Sri Lankan news source data and exposes lookups."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else _DEFAULT_KB_PATH
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.trusted: dict[str, dict] = data.get("trusted", {})
        self.moderate: dict[str, dict] = data.get("moderate", {})
        self.blacklist: set[str] = {d.lower() for d in data.get("blacklist", [])}

    @property
    def known_domains(self) -> set[str]:
        return set(self.trusted) | set(self.moderate)

    def lookup(self, domain: str) -> Optional[dict]:
        """Return ``{"features": {...}, "tier": "..."}`` if the domain is known."""
        for variant in domain_variants(domain):
            if variant in self.blacklist:
                return {"features": dict(BLACKLIST_FEATURES), "tier": "blacklisted", "matched": variant}
            if variant in self.trusted:
                return {"features": dict(self.trusted[variant]), "tier": "trusted", "matched": variant}
            if variant in self.moderate:
                return {"features": dict(self.moderate[variant]), "tier": "moderate", "matched": variant}
        return None


def features_for_domain(
    kb: KnowledgeBase,
    domain: str,
    *,
    cross_count: Optional[int] = None,
) -> tuple[dict, str, Optional[str]]:
    """Resolve features for a domain, returning (features, tier, matched_variant)."""
    hit = kb.lookup(domain)
    if hit:
        features = hit["features"]
        tier = hit["tier"]
        matched = hit.get("matched")
    else:
        features = dict(UNKNOWN_DEFAULTS)
        tier = "unknown"
        matched = None

    if cross_count is not None:
        # Map the externally-provided count into a 0-1 score (5+ corroborations = 1.0).
        features["cross"] = max(features["cross"], min(1.0, cross_count / 5.0))

    return features, tier, matched


def rule_based_score(features: dict) -> float:
    """Weighted average of credibility features, in [0, 1]."""
    return float(sum(WEIGHTS[k] * float(features[k]) for k in WEIGHTS))


def risk_level(final_score: float) -> str:
    """Translate a final credibility score into a coarse risk label."""
    if final_score >= 0.70:
        return "Trusted"
    if final_score >= 0.40:
        return "Moderate"
    return "Risky"
