"""Loads the pickled Random Forest credibility model from disk."""

from __future__ import annotations

import os
import pickle
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent

_MODEL_CANDIDATES: list[Path] = [
    _BACKEND_DIR / "model" / "source_cred.pkl",
    _BACKEND_DIR / "model" / "model.pkl",
    _BACKEND_DIR / "source_cred.pkl",
    _BACKEND_DIR.parent / "model" / "source_cred.pkl",
]


def _resolve_model_path() -> Path:
    """Pick the model path from the env var or the first existing candidate."""
    if env_path := os.environ.get("SOURCE_CRED_MODEL_PATH"):
        return Path(env_path)
    for candidate in _MODEL_CANDIDATES:
        if candidate.is_file():
            return candidate
    return _MODEL_CANDIDATES[0]


def load_model():
    """Load and return the trained source-credibility classifier."""
    path = _resolve_model_path()
    if not path.is_file():
        tried = ", ".join(str(p) for p in _MODEL_CANDIDATES)
        raise FileNotFoundError(
            f"Model not found at {path}. Set SOURCE_CRED_MODEL_PATH to your .pkl file. "
            f"Searched: {tried}"
        )
    with path.open("rb") as f:
        return pickle.load(f)
