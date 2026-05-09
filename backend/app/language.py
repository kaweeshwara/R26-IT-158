"""Lightweight language detection for English / Sinhala / Singlish input.

Sinhala is detected by Unicode block. Singlish (Sinhala written in Latin
characters) is detected with a small list of high-frequency markers; this is
intentionally simple and dependency-free.
"""

from __future__ import annotations

import re
from typing import Optional

_SINHALA_RE = re.compile(r"[\u0D80-\u0DFF]")
_WORD_RE = re.compile(r"[a-zA-Z]+")

# High-frequency Singlish-only tokens. 
_SINGLISH_HINTS: frozenset[str] = frozenset(
    {
        "machan", "machang", "aiyo", "ado", "ane", "anee", "anne", "akka",
        "aiya", "amma", "thaththa", "putha", "duwa", "patta", "katta",
        "mokada", "kohomada", "kohomdha", "kohey", "koheda", "kawda",
        "puluwan", "beh", "beha", "bari", "thiyenawa", "thiyenne",
        "yanawa", "yanna", "enawa", "enna", "kanawa", "kanna", "balanna",
        "kiyala", "kiyanne", "kiyanawa", "wenna", "wenawa", "wenakota",
        "uba", "umba", "thopi", "nikan", "nika", "ehema", "epa", "issara",
        "thunata", "varak", "wage", "thamai", "thama", "naha", "nedhe",
        "nathnam", "nathuwa", "nemei", "nemeyi",
    }
)

# Hint that the text is *about* Sri Lanka even if written in English.
_SL_PLACE_HINTS: frozenset[str] = frozenset(
    {
        "colombo", "kandy", "galle", "jaffna", "negombo", "matara", "kurunegala",
        "anuradhapura", "ratnapura", "trincomalee", "batticaloa", "vavuniya",
        "lanka", "ceylon", "sinhala", "tamil", "rupee", "rajapaksa",
        "wickremesinghe", "dissanayake", "premadasa",
    }
)


def detect_language(text: Optional[str]) -> str:
    """Return one of ``"sinhala" | "singlish" | "english" | "unknown"``."""
    if not text:
        return "unknown"

    if _SINHALA_RE.search(text):
        return "sinhala"

    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return "unknown"

    singlish_hits = sum(1 for w in words if w in _SINGLISH_HINTS)
    if singlish_hits >= 1 and singlish_hits / len(words) >= 0.04:
        return "singlish"

    return "english"


def mentions_sri_lanka(text: Optional[str]) -> bool:
    """True if the text contains a Sri Lanka-related place/name token."""
    if not text:
        return False
    if _SINHALA_RE.search(text):
        return True
    words = {w.lower() for w in _WORD_RE.findall(text)}
    return bool(words & _SL_PLACE_HINTS)
