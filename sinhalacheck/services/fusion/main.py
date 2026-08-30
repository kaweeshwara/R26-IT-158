"""SinhalaCheck — Fusion service.

Calls Module 1 (content credibility), Module 2 (source credibility + temporal
verification), and Module 4 (XAI explainability) over HTTP, combines their
outputs, and serves the demo UI.

Modified by Wishmitha (IT22259752) — Module 4: Fusion, XAI explanation &
user application — to integrate real LIME-based explanations into the
fusion response, so every verdict comes with both a score AND a
human-readable "why" derived from the actual model's decision boundary.

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
then reports which signals were actually used. Module 4 (explainability) is likewise
optional — if it is unreachable, fusion still returns a verdict, just without LIME reasons.

Run:
    uvicorn main:app --port 8000
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

MODULE1_URL = os.environ.get("MODULE1_URL", "http://127.0.0.1:8001")
MODULE2_URL = os.environ.get("MODULE2_URL", "http://127.0.0.1:8002")
MODULE4_URL = os.environ.get("MODULE4_URL", "http://127.0.0.1:8003")
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
    explain: bool = Field(True, description="If true, also fetch a LIME explanation from Module 4.")


class ModuleStatus(BaseModel):
    available: bool
    reason: Optional[str] = None


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
        for name, url in (("module1", MODULE1_URL), ("module2", MODULE2_URL), ("module4", MODULE4_URL)):
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
    m4_data: dict = {}

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

        # ---- Module 4: XAI / LIME explanation. Optional - can be skipped for speed.
        if not req.explain:
            modules["module4"] = ModuleStatus(available=False, reason="explain=false").model_dump()
        else:
            try:
                r = await client.post(f"{MODULE4_URL}/explain", json={"text": req.text, "num_features": 5, "num_samples": 80})
                r.raise_for_status()
                m4_data = r.json()
                modules["module4"] = ModuleStatus(available=True).model_dump()
            except Exception as e:
                modules["module4"] = ModuleStatus(
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

    return {
        "final_score": round(score, 4),
        "verdict": verdict(score, cfg),
        "alert": m2_data.get("alert"),
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
        "module4_explanations": m4_data.get("explanations") if m4_data else None,
    }