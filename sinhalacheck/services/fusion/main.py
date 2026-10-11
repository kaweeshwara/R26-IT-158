"""SinhalaCheck — Fusion service.

Calls Module 1 (content credibility) and Module 2 (source credibility + temporal
verification) over HTTP, combines their scores, and serves the demo UI.

Two design decisions are worth stating explicitly, because both were review findings:

1. **The modules are called, not imported.** An earlier prototype loaded Module 1's model
   weights directly into the fusion process. That erases the module boundary: Module 1
   stops being independently deployable, versionable or measurable, and a change to its
   preprocessing silently changes fusion's behaviour. Here each module is a service with
   its own contract.

2. **The weights are fitted, not chosen.** The combination weights are loaded from
   `weights.json`, which `scripts/fit_fusion_weights.py` produces by logistic regression
   on the labelled corpus. Every response carries `weights_provenance` so a reader can
   tell a fitted weight from a placeholder without reading the source.

**Graceful degradation.** The primary user pastes a WhatsApp forward, which has no URL and
no publication date — so Module 2 cannot contribute. Rather than failing or inventing a
neutral 0.5, fusion drops the unavailable signals and renormalises the remaining weights,
then reports which signals were actually used.

Run:
    uvicorn main:app --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from lime.lime_text import LimeTextExplainer
from pydantic import BaseModel, Field

MODULE1_URL = os.environ.get("MODULE1_URL", "http://127.0.0.1:8001")
MODULE2_URL = os.environ.get("MODULE2_URL", "http://127.0.0.1:8002")
MODULE3_URL = os.environ.get("MODULE3_URL", "http://127.0.0.1:8003")
WEIGHTS_PATH = Path(__file__).with_name("weights.json")
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "index.html"

app = FastAPI(title="SinhalaCheck — Fusion Engine", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def load_weights() -> dict:
    with WEIGHTS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- schemas
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Article text or forwarded message.")
    url: Optional[str] = Field(None, description="Source URL, if the content came from one.")
    published_date: Optional[datetime] = None
    cross_count: Optional[int] = Field(None, ge=0)
    seen_count: Optional[int] = Field(None, ge=0)
    explain: bool = Field(False, description="Generate bilingual LIME explanations (slower).")


class ModuleStatus(BaseModel):
    available: bool
    reason: Optional[str] = None


class XLMRAnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Article text or forwarded message.")
    source_score: float = Field(0.6, ge=0, le=1, allow_inf_nan=False)
    temporal_score: float = Field(0.8, ge=0, le=1, allow_inf_nan=False)
    url: Optional[str] = Field(None, description="If supplied, obtain both scores from Module 2.")
    published_date: Optional[datetime] = None
    recirculated: Optional[bool] = None
    cross_count: Optional[int] = Field(None, ge=0)
    seen_count: Optional[int] = Field(None, ge=0)


# --------------------------------------------------------------------------- fusion
def fuse(signals: dict, cfg: dict) -> tuple[float, dict]:
    """Weighted combination over *available* signals, with renormalisation.

    Returns (score, detail). `detail` records the effective weight each signal received,
    so the UI can show the arithmetic instead of asking the user to trust it.
    """
    w = cfg["weights"]
    present = {k: v for k, v in signals.items() if v is not None and k in w}
    if not present:
        raise HTTPException(502, "No module returned a usable score.")

    total = sum(w[k] for k in present)
    effective = {k: w[k] / total for k in present}
    score = sum(effective[k] * present[k] for k in present)
    score = min(1.0, max(0.0, score + cfg.get("intercept", 0.0)))

    return score, {
        "signals_used": sorted(present),
        "signals_missing": sorted(set(w) - set(present)),
        "configured_weights": {k: w[k] for k in w},
        "effective_weights": {k: round(v, 4) for k, v in effective.items()},
        "renormalised": len(present) < len(w),
    }


def verdict(score: float, cfg: dict) -> str:
    t = cfg["thresholds"]
    if score >= t["credible"]:
        return "CREDIBLE"
    if score >= t["uncertain"]:
        return "UNCERTAIN"
    return "LIKELY MISINFORMATION"


def generate_lime_explanations(text: str) -> list[dict]:
    """Explain Module 1's actual prediction using batched perturbation inference."""
    if len(text) > 10_000:
        raise HTTPException(
            413,
            "LIME explanations are limited to 10,000 characters per request.",
        )
    if not re.search(r"\w", text, flags=re.UNICODE):
        raise HTTPException(422, "LIME needs at least one explainable word.")

    with httpx.Client(timeout=120) as client:
        info_response = client.get(f"{MODULE1_URL}/info")
        info_response.raise_for_status()
        id2label = info_response.json()["id2label"]
        class_labels = [str(id2label[str(index)]) for index in range(len(id2label))]
        if len(class_labels) != 2:
            raise HTTPException(
                502,
                "LIME currently requires Module 1 to expose a binary classifier.",
            )

        def predict_proba(texts) -> np.ndarray:
            rows: list[list[float]] = []
            for start in range(0, len(texts), 64):
                response = client.post(
                    f"{MODULE1_URL}/predict/batch",
                    json={"texts": list(texts[start:start + 64])},
                )
                response.raise_for_status()
                predictions = response.json()["predictions"]
                if len(predictions) != len(texts[start:start + 64]):
                    raise RuntimeError("Module 1 returned an incomplete LIME batch.")
                rows.extend([
                    [prediction["probabilities"][label] for label in class_labels]
                    for prediction in predictions
                ])
            return np.asarray(rows, dtype=float)

        original_probabilities = predict_proba([text])[0]
        target_index = int(np.argmax(original_probabilities))
        target_label = class_labels[target_index].upper()
        target_si = "විශ්වාසදායක" if "CREDIBLE" in target_label and "NOT" not in target_label else "විශ්වාසදායක නොවන"

        explainer = LimeTextExplainer(
            class_names=class_labels,
            split_expression=r"\s+",
            bow=False,
            random_state=42,
        )
        explanation = explainer.explain_instance(
            text,
            predict_proba,
            labels=[target_index],
            num_features=5,
            num_samples=500,
        )
        contributions = explanation.as_list(label=target_index)

    reasons = []
    for word, contribution in contributions[:5]:
        supports = contribution >= 0
        direction = "supports" if supports else "argues against"
        sinhala_direction = "සහාය වේ" if supports else "එරෙහිව බලපායි"
        reasons.append({
            "word": word,
            "weight": round(float(contribution), 3),
            "english": f'The term "{word}" {direction} the {target_label} prediction.',
            "sinhala": f'“{word}” යන පදය {target_si} තීරණයට {sinhala_direction}.',
        })
    return reasons


# --------------------------------------------------------------------------- routes
@app.get("/", response_class=HTMLResponse)
def ui():
    if FRONTEND.is_file():
        return HTMLResponse(FRONTEND.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SinhalaCheck</h1><p>Frontend not found.</p>", status_code=200)


@app.get("/health")
async def health():
    out = {"fusion": "ok", "weights": load_weights().get("method")}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in (("module1", MODULE1_URL), ("module2", MODULE2_URL)):
            try:
                r = await client.get(f"{url}/")
                out[name] = "ok" if r.status_code == 200 else f"http {r.status_code}"
            except Exception as e:
                out[name] = f"unreachable ({type(e).__name__})"
    return out


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    cfg = load_weights()
    modules: dict = {}
    signals: dict = {"content": None, "source": None, "temporal": None}
    m1_data: dict = {}
    m2_data: dict = {}

    async with httpx.AsyncClient(timeout=120) as client:
        # ---- Module 1: content. Required - without it there is no analysis.
        try:
            r = await client.post(f"{MODULE1_URL}/predict", json={"text": req.text})
            r.raise_for_status()
            m1_data = r.json()
            signals["content"] = m1_data["content_score"]
            modules["module1"] = ModuleStatus(available=True).model_dump()
        except Exception as e:
            raise HTTPException(502, f"Module 1 (content) unavailable: {type(e).__name__}: {e}")

        # ---- Module 2: source + temporal. Optional - needs a URL.
        if not req.url:
            reason = "no URL supplied; source and recency cannot be assessed from text alone"
            modules["module2"] = ModuleStatus(available=False, reason=reason).model_dump()
        else:
            try:
                payload = {"url": req.url, "text": req.text}
                if req.published_date:
                    payload["published_date"] = req.published_date.isoformat()
                if req.cross_count is not None:
                    payload["cross_count"] = req.cross_count
                if req.seen_count is not None:
                    payload["seen_count"] = req.seen_count
                r = await client.post(f"{MODULE2_URL}/analyze", json=payload)
                r.raise_for_status()
                m2_data = r.json()
                signals["source"] = m2_data["source_score"]
                signals["temporal"] = m2_data["temporal_score"]
                modules["module2"] = ModuleStatus(available=True).model_dump()
            except Exception as e:
                modules["module2"] = ModuleStatus(
                    available=False, reason=f"{type(e).__name__}: {e}").model_dump()

    score, detail = fuse(signals, cfg)

    # ---- assemble human-readable reasons from whichever modules answered
    reasons: list[str] = []
    lf = m1_data.get("linguistic_features", {})
    if signals["content"] is not None:
        reasons.append(
            f"Content model scores this {signals['content']:.0%} credible "
            f"(LaBSE, cross-validated macro-F1 0.753)."
        )
    if lf.get("urgency_markers"):
        reasons.append(f"Contains urgency/manipulation phrasing ({lf['urgency_markers']} per 100 words).")
    if lf.get("emotional_intensity"):
        reasons.append(f"Elevated emotional language ({lf['emotional_intensity']} per 100 words).")
    if m1_data.get("truncated"):
        reasons.append("Article exceeds 512 tokens; the model scored the opening section.")
    if m2_data:
        reasons.extend(m2_data.get("reasons", []))

    try:
        lime_explanations = (
            await asyncio.to_thread(generate_lime_explanations, req.text)
            if req.explain else []
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            502, f"LIME could not obtain Module 1 predictions: {exc}"
        ) from exc

    temporal_warning = (
        {
            "available": True,
            "alert": m2_data.get("alert"),
            "freshness_label": m2_data.get("time_label"),
            "age_days": m2_data.get("age_days"),
            "recirculated": m2_data.get("recirculated"),
        }
        if m2_data else {
            "available": False,
            "message": modules["module2"].get(
                "reason", "Source and temporal signals are unavailable."
            ),
        }
    )

    return {
        "final_score": round(score, 4),
        "verdict": verdict(score, cfg),
        "alert": m2_data.get("alert"),
        "explanation_scope": "module1_content_model",
        "temporal_warning": temporal_warning,
        "lime_explanations": lime_explanations,
        "breakdown": {k: (round(v, 4) if v is not None else None) for k, v in signals.items()},
        "fusion_detail": detail,
        "weights_provenance": {
            "method": cfg.get("method"),
            "fitted_on": cfg.get("fitted_on"),
            "fitted_at": cfg.get("fitted_at"),
            "n_samples": cfg.get("n_samples"),
            "is_fitted": cfg.get("method") not in (None, "uniform_placeholder"),
        },
        "modules": modules,
        "reasons": reasons,
        "module1": m1_data,
        "module2": m2_data or None,
    }


@app.post("/analyze/xlmr")
async def analyze_xlmr(req: XLMRAnalyzeRequest):
    """Run the optional XLM-R pipeline without changing the default analysis route.

    Explicit source/temporal scores are used unless a URL is supplied, in which
    case both are obtained from the existing Module 2 service.
    """
    source_score = req.source_score
    temporal_score = req.temporal_score
    m2_data: Optional[dict] = None

    async with httpx.AsyncClient(timeout=300) as client:
        if req.url:
            payload: dict = {"url": req.url, "text": req.text}
            if req.published_date:
                payload["published_date"] = req.published_date.isoformat()
            if req.recirculated is not None:
                payload["recirculated"] = req.recirculated
            if req.cross_count is not None:
                payload["cross_count"] = req.cross_count
            if req.seen_count is not None:
                payload["seen_count"] = req.seen_count
            try:
                response = await client.post(f"{MODULE2_URL}/analyze", json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise HTTPException(
                    502, f"Module 2 returned HTTP {exc.response.status_code}: "
                    f"{exc.response.text[:300]}"
                ) from exc
            except httpx.RequestError as exc:
                raise HTTPException(502, f"Module 2 request failed: {exc}") from exc
            m2_data = response.json()
            source_score = m2_data["source_score"]
            temporal_score = m2_data["temporal_score"]

        try:
            response = await client.post(
                f"{MODULE3_URL}/predict",
                json={
                    "text": req.text,
                    "source_score": source_score,
                    "temporal_score": temporal_score,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                502, f"Module 3 returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Module 3 request failed: {exc}") from exc

    return {
        "prediction": response.json(),
        "score_source": "module2" if m2_data is not None else "request",
        "module2": m2_data,
    }
