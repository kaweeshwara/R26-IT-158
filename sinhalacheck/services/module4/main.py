"""SinhalaCheck - Module 4: Explainability (XAI) service."""
from __future__ import annotations
import os, re
import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lime.lime_text import LimeTextExplainer
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Explain the SAME model Module 1 predicts with, otherwise the "why" would describe a
# different network from the one that gave the score. Same resolution order as Module 1:
# env var, then a local checkpoint folder, then the published Hub copy.
MAX_LENGTH = 512
HUB_FALLBACK = "Kaweeshwara/sinhalacheck-module1"


def _resolve_model_source() -> str:
    for var in ("MODULE4_MODEL_PATH", "MODULE1_MODEL_PATH"):
        v = os.environ.get(var, "").strip()
        if v:
            return v
    for c in ["./model", "../../model", "./SinhalaCheck_model_final"]:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "config.json")):
            return c
    return HUB_FALLBACK


MODEL_PATH = _resolve_model_source()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
app = FastAPI(title="SinhalaCheck - Module 4: Explainability (XAI)", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

print(f"[module4] loading model from: {MODEL_PATH}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()
# Trust the checkpoint's own label map rather than assuming index 1 means CREDIBLE.
ID2LABEL = {int(k): str(v).upper() for k, v in model.config.id2label.items()}
CLASS_NAMES = [ID2LABEL[i] for i in sorted(ID2LABEL)]
CREDIBLE_IDX = next((i for i, l in ID2LABEL.items() if "NOT" not in l and "CREDIBLE" in l), 1)
NUM_CLASSES = len(CLASS_NAMES)
explainer = LimeTextExplainer(class_names=CLASS_NAMES, split_expression=r"\s+", bow=False)

class ExplainRequest(BaseModel):
    text: str = Field(..., min_length=1)
    num_features: int = Field(5, ge=1, le=10)
    num_samples: int = Field(100, ge=20, le=500)

def clean_for_lime(text: str) -> str:
    text = re.sub(r'([.,!?;:()"\u0d80-\u0dff]*[.,!?;:()"])', r" \1 ", text)
    return re.sub(r"\s+", " ", text).strip()

def get_probs(text: str) -> np.ndarray:
    inputs = tokenizer(text, truncation=True, padding=True, max_length=MAX_LENGTH, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
    return F.softmax(logits, dim=-1).cpu().numpy()[0]

def predict_proba_batch(texts):
    all_probs = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = list(texts[i:i+batch_size])
        inputs = tokenizer(batch, truncation=True, padding=True, max_length=MAX_LENGTH, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
        all_probs.append(F.softmax(logits, dim=-1).cpu().numpy())
    return np.vstack(all_probs)

@app.get("/")
def root():
    return {"module4": "ok"}

@app.get("/health")
def health():
    return {"module4": "ok", "model": MODEL_PATH, "device": str(device)}

@app.post("/explain")
def explain(req: ExplainRequest):
    probs = get_probs(req.text)
    predicted_class = int(np.argmax(probs))
    clean_text = clean_for_lime(req.text)
    exp = explainer.explain_instance(clean_text, predict_proba_batch, num_features=req.num_features, num_samples=req.num_samples, labels=list(range(NUM_CLASSES)))
    reasons = [{"word": w.strip('.,!?;:()"'), "weight": round(wt, 4)} for w, wt in exp.as_list(label=predicted_class)]
    return {
        "model_prediction": {"not_credible": round(float(1 - probs[CREDIBLE_IDX]), 4), "credible": round(float(probs[CREDIBLE_IDX]), 4)},
        "predicted_label": CLASS_NAMES[predicted_class],
        "explanations": reasons,
        "source_model": MODEL_PATH,
    }
