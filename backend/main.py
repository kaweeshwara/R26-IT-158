"""FastAPI entry point for the SinhalaCheck source-credibility module.

Endpoints
---------
- ``GET  /``         health check
- ``GET  /sources``  list of curated Sri Lankan news sources
- ``POST /analyze``  full pipeline: URL -> rule + ML hybrid score + temporal verification
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.credibility import KnowledgeBase
from app.ml_loader import load_model
from app.pipeline import analyze
from app.schemas import AnalyzeRequest, AnalyzeResponse

state: dict = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    state["model"] = load_model()
    state["kb"] = KnowledgeBase()
    try:
        yield
    finally:
        state.clear()


app = FastAPI(
    title="SinhalaCheck — Source Credibility & Temporal Verification API",
    description=(
        "Hybrid (rule-based + ML) source credibility scoring tuned for Sri Lankan "
        "news. Accepts user input in English, Sinhala, or Singlish."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require(name: str):
    value = state.get(name)
    if value is None:
        raise HTTPException(status_code=503, detail=f"Service not ready: {name} not loaded")
    return value


@app.get("/")
def home():
    return {
        "message": "SinhalaCheck API is running",
        "endpoints": ["/analyze", "/sources"],
    }


@app.get("/sources")
def list_sources():
    """Expose the curated Sri Lankan news source knowledge base."""
    kb: KnowledgeBase = _require("kb")
    return {
        "trusted": sorted(kb.trusted.keys()),
        "moderate": sorted(kb.moderate.keys()),
        "blacklist": sorted(kb.blacklist),
        "total_known": len(kb.known_domains),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest):
    """Full SinhalaCheck pipeline.

    Pass a news article URL (and optionally the article text in English /
    Sinhala / Singlish, plus a publication date) and get back a structured
    credibility & temporal-verification report.
    """
    model = _require("model")
    kb: KnowledgeBase = _require("kb")

    try:
        result = analyze(
            kb=kb,
            model=model,
            url=req.url,
            text=req.text,
            published_date=req.published_date,
            recirculated_override=req.recirculated,
            cross_count=req.cross_count,
            seen_count=req.seen_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result
