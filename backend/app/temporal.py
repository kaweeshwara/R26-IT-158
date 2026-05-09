"""Temporal verification: publication-date freshness and recirculation hints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

# Per the design doc (§7).
TIME_SCORE = {
    "Fresh":    1.00,
    "Recent":   0.70,
    "Old":      0.40,
    "Very Old": 0.10,
    "Unknown":  0.50,
}

_RECIRCULATION_URL_HINTS = ("/archive/", "/archives/", "republished", "throwback", "/old/", "/repost/")


def time_label(age_days: float) -> str:
    """Map an article's age in days to a human label."""
    years = age_days / 365.25
    if years <= 1:
        return "Fresh"
    if years <= 3:
        return "Recent"
    if years <= 5:
        return "Old"
    return "Very Old"


def evaluate_temporal(
    published_date: Optional[datetime],
    *,
    now: Optional[datetime] = None,
) -> dict:
    """Return ``{label, score, age_days}`` for the given publication date."""
    if published_date is None:
        return {"label": "Unknown", "score": TIME_SCORE["Unknown"], "age_days": None}

    if now is None:
        now = datetime.now(timezone.utc)
    if published_date.tzinfo is None:
        published_date = published_date.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_seconds = (now - published_date).total_seconds()
    age_days = max(0.0, age_seconds / 86400.0)
    label = time_label(age_days)
    return {"label": label, "score": TIME_SCORE[label], "age_days": round(age_days, 2)}


def detect_recirculation(
    url: str,
    *,
    age_days: Optional[float],
    override: Optional[bool],
    seen_count: Optional[int],
) -> bool:
    """Heuristic recirculation flag.

    Real recirculation detection requires historical tracking; here we combine an
    explicit override, a republish-like URL pattern, and an optional ``seen_count``
    of how many times the same article was previously surfaced.
    """
    if override is not None:
        return override
    if seen_count is not None and seen_count > 1:
        return True
    url_lower = url.lower()
    if any(hint in url_lower for hint in _RECIRCULATION_URL_HINTS):
        return True
    return False
