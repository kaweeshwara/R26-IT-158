"""SinhalaCheck — Module 4: Explainability (XAI) service.

Loads Module 1's own published content-credibility model
(Kaweeshwara/sinhalacheck-module1) directly and runs LIME (Local Interpretable
Model-agnostic Explanations) against it, so the verdict Module 1 and the
Fusion gateway produce comes with a human-readable "why" — not just a score.

This is a standalone service, following the same design philosophy as the
rest of the system: modules are called, not imported, so this can be
versioned, measured, and swapped independently of Module 1 or Fusion.

Run:
    uvicorn main:app --port 8003
"""

from __future__ import annotations

import os
import re

import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lime.lime_text import LimeTextExplainer
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_PATH = os.environ.get("MODULE4_MODEL_PATH", "Kaweeshwara/sinhalacheck-module1")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

app = FastAPI(title="SinhalaCheck — Module 4: Explainability (XAI)", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

print(f"[module4] loading model from: {MODEL_PATH}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()

CLASS_NAMES = ["NOT_CREDIBLE", "CREDIBLE"]

explainer = LimeTextExplainer(
    class_names=CLASS_NAMES,
    split_expression=r"\s+",
    bow=False,
)


class ExplainRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Article text or forwarded message.")
    num_features: int = Field(5, ge=1, le=10)
    num_samples: int = Field(100, ge=20, le=500)


def clean_for_lime(text: str) -> str:
    """Separates punctuation from words so LIME's whitespace splitter does not
    fracture Sinhala conjunct clusters attached to punctuation marks."""
    text = re.sub(r'([.,!?;:()"\u0d80-\u0dff]*[.,!?;:()"])', r" \1 ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_probs(text: str) -> np.ndarray:
    inputs = tokenizer(text, truncation=True, padding="max_length", max_length=256, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
    return F.softmax(logits, dim=-1).cpu().numpy()[0]


def predict_proba_batch(texts: list[str]) -> np.ndarray:
    all_probs = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = list(texts[i : i + batch_size])
        inputs = tokenizer(batch, truncation=True, padding="max_length", max_length=256, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
        all_probs.append(F.softmax(logits, dim=-1).cpu().numpy())
    return np.vstack(all_probs)


@app.get("/health")
def health():
    return {"module4": "ok", "model": MODEL_PATH, "device": str(device)}


@app.post("/explain")
def explain(req: ExplainRequest):
    probs = get_probs(req.text)
    predicted_class = int(np.argmax(probs))

    clean_text = clean_for_lime(req.text)
    exp = explainer.explain_instance(
        clean_text,
        predict_proba_batch,
        num_features=req.num_features,
        num_samples=req.num_samples,
        labels=[0, 1],
    )

    reasons = [
        {"word": w.strip('.,!?;:()"'), "weight": round(wt, 4)}
        for w, wt in exp.as_list(label=predicted_class)
    ]

    return {
        "model_prediction": {
            "not_credible": round(float(probs[0]), 4),
            "credible": round(float(probs[1]), 4),
        },
        "predicted_label": CLASS_NAMES[predicted_class],
        "explanations": reasons,
        "source_model": MODEL_PATH,
    }