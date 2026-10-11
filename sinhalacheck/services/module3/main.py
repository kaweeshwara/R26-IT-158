"""Optional XLM-R three-class prediction service with LIME explanations.

The service is deliberately separate from Module 1: it loads only a local
three-class checkpoint and never changes the existing LaBSE/fusion pipeline.
Run from this directory with ``uvicorn main:app --port 8003``.
"""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from lime.lime_text import LimeTextExplainer
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_PATH = Path(os.environ.get(
    "MODULE3_MODEL_PATH", str(Path(__file__).resolve().parent / "model")
)).expanduser()
MAX_LENGTH = 256
CLASS_NAMES = ("CREDIBLE", "UNCERTAIN", "PARTIAL/FALSE")
CLASS_KEYS = ("credible", "uncertain", "partial_false")
LABEL_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
state: dict[str, Any] = {}


def _class_indices(model: Any) -> dict[str, int]:
    """Use the checkpoint's named label map, or the documented order if generic."""
    count = int(model.config.num_labels)
    if count != len(CLASS_NAMES):
        raise ValueError(f"Expected a 3-class checkpoint, found {count} labels.")

    id2label = {int(key): value for key, value in model.config.id2label.items()}
    labels = [str(id2label.get(i, f"LABEL_{i}")).upper() for i in range(count)]
    if all(re.fullmatch(r"LABEL_\d+", label) for label in labels):
        return dict(zip(CLASS_KEYS, range(count)))

    indices: dict[str, int] = {}
    for index, label in enumerate(labels):
        if "UNCERTAIN" in label:
            key = "uncertain"
        elif "CREDIBLE" in label and not any(word in label for word in ("NOT", "NON")):
            key = "credible"
        elif any(word in label for word in ("PARTIAL", "FALSE", "MISINFORMATION", "MISINFO")):
            key = "partial_false"
        else:
            continue
        if key in indices:
            raise ValueError(f"Checkpoint has ambiguous class labels: {labels}.")
        indices[key] = index

    if set(indices) != set(CLASS_KEYS):
        raise ValueError(
            "Checkpoint labels must identify CREDIBLE, UNCERTAIN, and PARTIAL/FALSE; "
            f"found {labels}."
        )
    return indices


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not MODEL_PATH.is_dir() or not (MODEL_PATH / "config.json").is_file():
        raise RuntimeError(
            f"Module 3 model not found at {MODEL_PATH}. Set MODULE3_MODEL_PATH to "
            "a local XLM-R checkpoint containing config.json and tokenizer/model files."
        )

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_PATH), local_files_only=True
    ).to(torch.device("cpu")).eval()
    class_indices = _class_indices(model)
    state.update(tokenizer=tokenizer, model=model, class_indices=class_indices)
    print(f"[module3] loaded local model from {MODEL_PATH} on CPU", flush=True)
    try:
        yield
    finally:
        state.clear()


app = FastAPI(
    title="SinhalaCheck — Optional XLM-R + LIME",
    description=(
        "Independent three-class XLM-R inference and score fusion. "
        "Does not replace the default LaBSE pipeline."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class PredictionRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Sinhala or supported mixed-language text.")
    source_score: float = Field(0.6, ge=0, le=1, allow_inf_nan=False)
    temporal_score: float = Field(0.8, ge=0, le=1, allow_inf_nan=False)


def _probabilities(texts: list[str]) -> np.ndarray:
    tokenizer = state["tokenizer"]
    model = state["model"]
    encoded = tokenizer(
        texts,
        truncation=True,
        padding=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(**encoded).logits
        return F.softmax(logits, dim=-1).cpu().numpy()


def _canonical_probabilities(texts: list[str]) -> np.ndarray:
    indices = state["class_indices"]
    raw = _probabilities(texts)
    return raw[:, [indices[key] for key in CLASS_KEYS]]


def _clean_for_explanation(text: str) -> str:
    return re.sub(r"\s+", " ", LABEL_RE.sub(" ", text)).strip()


def _fused_score(content: float, source: float, temporal: float) -> float:
    return 0.50 * content + 0.30 * source + 0.20 * temporal


def _verdict(score: float) -> str:
    if score >= 0.61:
        return "CREDIBLE"
    if score >= 0.41:
        return "UNCERTAIN"
    return "MISINFORMATION"


@app.get("/")
def health() -> dict[str, Any]:
    return {
        "service": "module3-xlmr-lime",
        "ready": "model" in state,
        "model_path": str(MODEL_PATH),
        "endpoints": ["/predict"],
    }


@app.post("/predict")
def predict(req: PredictionRequest) -> dict[str, Any]:
    if "model" not in state:
        raise HTTPException(status_code=503, detail="Module 3 model is not loaded.")
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must contain non-whitespace characters.")

    probabilities = _canonical_probabilities([text])[0]
    model_prediction = {
        key: round(float(probabilities[index]), 4)
        for index, key in enumerate(CLASS_KEYS)
    }
    content_score = float(probabilities[0])
    final_score = _fused_score(content_score, req.source_score, req.temporal_score)

    explanation_text = _clean_for_explanation(text)
    if not explanation_text:
        raise HTTPException(
            status_code=422,
            detail="text contains no explainable words after punctuation cleanup.",
        )
    explainer = LimeTextExplainer(
        class_names=list(CLASS_NAMES),
        split_expression=r"\s+",
        bow=False,
        random_state=42,
    )
    predicted_class = int(np.argmax(probabilities))
    explanation = explainer.explain_instance(
        explanation_text,
        _canonical_probabilities,
        num_features=5,
        num_samples=150,
        labels=[0, 1, 2],
    )
    lime_explanations = [
        {"word": word, "weight": round(float(weight), 3)}
        for word, weight in explanation.as_list(label=predicted_class)
    ]

    return {
        "final_score": round(final_score, 3),
        "label": _verdict(final_score),
        "model_prediction": model_prediction,
        "breakdown": {
            "content": round(content_score, 4),
            "source": req.source_score,
            "temporal": req.temporal_score,
        },
        "lime_explanations": lime_explanations,
    }
