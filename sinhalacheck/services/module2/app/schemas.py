"""Pydantic request/response schemas for the API surface."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    """Full pipeline input. ``url`` is required; everything else is optional."""

    url: str = Field(..., description="News article URL (e.g. https://www.adaderana.lk/news/...)")
    text: Optional[str] = Field(
        None,
        description="Article body or claim. Accepts English, Sinhala, or Singlish.",
    )
    published_date: Optional[datetime] = Field(
        None, description="Publication date (ISO 8601)."
    )
    recirculated: Optional[bool] = Field(
        None, description="Override recirculation flag if known."
    )
    cross_count: Optional[int] = Field(
        None, ge=0, description="Number of independent reputable sources confirming this story."
    )
    seen_count: Optional[int] = Field(
        None, ge=0, description="How many times this article has been observed previously."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://www.adaderana.lk/news/100123/sample-headline",
                "text": "කොළඹ දී අද සිදුවූ සිදුවීම පිළිබඳව...",
                "published_date": "2025-12-01T08:30:00Z",
                "cross_count": 3,
            }
        }
    )


class Breakdown(BaseModel):
    registration: float
    domain_age: float
    history: float
    editorial: float
    cross: float


class AnalyzeResponse(BaseModel):
    """Final output (matches the document spec, plus a few helpful diagnostics)."""

    source_score: float
    source_label: str
    ml_prediction: int
    ml_confidence: float
    temporal_score: float
    time_label: str
    recirculated: bool
    confidence: float
    alert: str
    reasons: list[str]
    breakdown: Breakdown

    # Extra context (useful for clients & debugging)
    domain: str
    publisher: str
    detected_language: str
    is_sri_lankan_source: bool
    mentions_sri_lanka: bool
    is_known_source: bool
    source_tier: str
    rule_score: float
    ml_probability_trusted: float
    age_days: Optional[float] = None
