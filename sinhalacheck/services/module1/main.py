"""SinhalaCheck — Module 1: NLP Content Credibility Analysis.

A standalone HTTP service wrapping the fine-tuned content credibility classifier.

Model selection was decided by 5-fold cross-validation over the full LIRNEasia corpus
(n=3,000): LaBSE reached macro-F1 0.7534 +/- 0.013, significantly ahead of a TF-IDF+SVM
baseline (+0.058, 95% CI [0.040, 0.076]) and of the same architecture trained on the
corpus's damaged CSV distribution (+0.302, 95% CI [0.280, 0.324]).

This module owns *content* only. Source reputation and recency belong to Module 2, and
combining the signals belongs to the fusion service — so this API returns a content score
and nothing else. Any consumer that needs the model should call this endpoint rather than
loading the weights directly, so that the module stays independently versionable and
independently measurable.

Run:
    uvicorn main:app --port 8001
"""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from typing import Optional

import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# --------------------------------------------------------------------------- config
# Resolution order: explicit env var, then a local directory, then the published Hub copy.
MODEL_PATH = os.environ.get("MODULE1_MODEL_PATH", "").strip()
LOCAL_CANDIDATES = ["./model", "../../model", "./SinhalaCheck_model_final"]
HUB_FALLBACK = "Kaweeshwara/sinhalacheck-module1"
MAX_LENGTH = 512

SINHALA_RE = re.compile(r"[඀-෿]")

state: dict = {}


def _resolve_model_source() -> str:
    if MODEL_PATH:
        return MODEL_PATH
    for c in LOCAL_CANDIDATES:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "config.json")):
            return c
    return HUB_FALLBACK


def _explain_load_failure(source: str, err: Exception) -> str:
    """Turn a model-loading failure into something actionable.

    The common case during development is that the Hub repository does not exist yet
    because training has not finished. A 200-line traceback buries that.
    """
    lines = [
        "",
        "=" * 72,
        "  MODULE 1 COULD NOT LOAD ITS MODEL",
        "=" * 72,
        f"  tried: {source}",
        f"  error: {type(err).__name__}",
        "",
    ]
    msg = str(err)
    if "401" in msg or "RepositoryNotFound" in type(err).__name__ or "not a local folder" in msg:
        lines += [
            "  That Hugging Face repository does not exist (or is private).",
            "",
            "  If training has not finished yet, this is expected - the repo appears",
            "  only once the notebook's publish step runs. Wait for it, then retry.",
            "",
            "  To use a local copy instead:",
            "     Windows :  set MODULE1_MODEL_PATH=C:\\path\\to\\SinhalaCheck_model_final",
            "     macOS   :  export MODULE1_MODEL_PATH=/path/to/SinhalaCheck_model_final",
            "     ...then run python run_all.py again.",
            "",
            "  The folder must contain config.json, model.safetensors and the tokenizer files.",
        ]
    else:
        lines += [f"  {msg[:400]}"]
    lines += ["=" * 72, ""]
    return "\n".join(lines)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    source = _resolve_model_source()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[module1] loading model from: {source}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(source)
        model = AutoModelForSequenceClassification.from_pretrained(source).to(device).eval()
    except Exception as err:
        print(_explain_load_failure(source, err), flush=True)
        raise SystemExit(3) from None

    # Trust the checkpoint's own label map rather than assuming index 1 means CREDIBLE.
    id2label = {int(k): str(v).upper() for k, v in model.config.id2label.items()}
    credible_idx = next((i for i, l in id2label.items() if "NOT" not in l and "CREDIBLE" in l), 1)
    print(f"[module1] id2label={id2label}  credible index={credible_idx}  device={device}")

    state.update(tokenizer=tokenizer, model=model, device=device,
                 credible_idx=credible_idx, id2label=id2label, source=source)
    try:
        yield
    finally:
        state.clear()


app = FastAPI(
    title="SinhalaCheck — Module 1: NLP Content Credibility Analysis",
    description=(
        "Content credibility scoring for Sinhala news text, using a LaBSE classifier "
        "fine-tuned on the LIRNEasia corpus. Returns a calibrated content score only."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --------------------------------------------------------------------------- schemas
class ContentRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Article body or claim, Sinhala or English.")


class LinguisticFeatures(BaseModel):
    """Surface features from the module specification, reported alongside the score.

    These are transparent, inspectable signals — unlike the transformer's score, a reader
    can verify them by eye. They are reported, not fused, because the classifier already
    learns these patterns from the text directly.
    """
    emotional_intensity: float
    certainty_density: float
    urgency_markers: float
    headline_coherence: Optional[float] = None


class ContentResponse(BaseModel):
    content_score: float = Field(..., description="P(CREDIBLE) in [0,1]. Higher = more credible.")
    label: str
    confidence: float
    probabilities: dict
    linguistic_features: LinguisticFeatures
    script: str
    n_characters: int
    truncated: bool
    model_source: str


# --------------------------------------------------------------------------- features
# Sinhala cue lexicons. Deliberately small and auditable rather than exhaustive.
EMOTION_WORDS = ["භයානක", "බියජනක", "කම්පා", "කණගාටු", "ඛේදනීය", "අනතුරු", "විනාශ",
                 "දරුණු", "අශෝභන", "කැළඹීම", "කෝප", "ද්වේෂ", "shocking", "horrific", "outrage"]
CERTAINTY_WORDS = ["තහවුරු", "නිශ්චිත", "සත්‍ය", "පැහැදිලි", "අනිවාර්ය", "සියයට සියයක්",
                   "confirmed", "breaking", "exclusive", "proven"]
HEDGE_WORDS = ["වාර්තා", "කියැවේ", "සැක", "විය හැකි", "පෙනේ", "ආරංචි",
               "reportedly", "allegedly", "sources say", "claims"]
URGENCY_WORDS = ["ඉක්මනින්", "වහාම", "share කරන්න", "බෙදාගන්න", "delete", "මකා දමන",
                 "share before", "forward this", "they don't want you to know"]


def _per_100_words(text: str, lexicon: list[str]) -> float:
    words = max(1, len(text.split()))
    hits = sum(text.count(w) for w in lexicon)
    return round(100.0 * hits / words, 3)


def compute_features(text: str) -> LinguisticFeatures:
    lowered = text.lower()
    certainty = sum(lowered.count(w.lower()) for w in CERTAINTY_WORDS)
    hedge = sum(lowered.count(w.lower()) for w in HEDGE_WORDS)
    density = round(certainty / (certainty + hedge), 3) if (certainty + hedge) else 0.0
    return LinguisticFeatures(
        emotional_intensity=_per_100_words(lowered, [w.lower() for w in EMOTION_WORDS]),
        certainty_density=density,
        urgency_markers=_per_100_words(lowered, [w.lower() for w in URGENCY_WORDS]),
        headline_coherence=None,   # requires a separate headline field; not supplied here
    )


def detect_script(text: str) -> str:
    if SINHALA_RE.search(text):
        return "sinhala"
    return "latin"


# --------------------------------------------------------------------------- routes
@app.get("/")
def health():
    ready = "model" in state
    return {"service": "module1-content-credibility", "ready": ready,
            "model_source": state.get("source"), "endpoints": ["/predict", "/info"]}


@app.get("/info")
def info():
    if "model" not in state:
        raise HTTPException(503, "model not loaded")
    return {
        "model_source": state["source"],
        "id2label": state["id2label"],
        "max_length": MAX_LENGTH,
        "validation": {
            "protocol": "5-fold cross-validation, n=3000, pooled out-of-fold predictions",
            "macro_f1": 0.7534,
            "macro_f1_fold_std": 0.0129,
            "accuracy": 0.7767,
            "vs_tfidf_svm": {"macro_f1_gap": 0.0576, "ci95": [0.0396, 0.0755], "p": "<0.0001"},
            "vs_damaged_csv_control": {"macro_f1_gap": 0.3024, "ci95": [0.2798, 0.3237], "p": "<0.0001"},
        },
    }


@app.post("/predict", response_model=ContentResponse)
def predict(req: ContentRequest):
    if "model" not in state:
        raise HTTPException(503, "model not loaded")
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "text is empty")

    tok, model, device = state["tokenizer"], state["model"], state["device"]
    enc = tok(text, truncation=True, max_length=MAX_LENGTH, return_tensors="pt")
    n_tokens_full = len(tok.encode(text, truncation=False))

    with torch.no_grad():
        logits = model(**{k: v.to(device) for k, v in enc.items()}).logits
    probs = F.softmax(logits, dim=-1).cpu().numpy()[0]

    ci = state["credible_idx"]
    content_score = float(probs[ci])
    return ContentResponse(
        content_score=round(content_score, 4),
        label="CREDIBLE" if content_score >= 0.5 else "NOT_CREDIBLE",
        confidence=round(float(max(probs)), 4),
        probabilities={state["id2label"][i]: round(float(p), 4) for i, p in enumerate(probs)},
        linguistic_features=compute_features(text),
        script=detect_script(text),
        n_characters=len(text),
        truncated=n_tokens_full > MAX_LENGTH,
        model_source=state["source"],
    )
