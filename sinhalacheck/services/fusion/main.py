"""SinhalaCheck — Fusion service.

Calls Module 1 (content credibility), Module 2 (source credibility + temporal
verification), and Module 4 (XAI explainability) over HTTP, combines their
outputs, and serves the demo UI.

Modified by Wishmitha (IT22259752) — Module 4: Fusion, XAI explanation &
user application — to integrate real LIME-based explanations into the
fusion response, so every verdict comes with both a score AND a
human-readable "why" derived from the actual model's decision boundary,
available in English, Sinhala, and Tamil, with an optional LLM-narrated
version that rephrases the LIME findings into more natural prose.

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
The optional AI narration layer falls back to the deterministic template if no API key is
configured or the call fails, so the demo never depends on network availability.

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

try:
    import anthropic
except ImportError:
    anthropic = None

MODULE1_URL = os.environ.get("MODULE1_URL", "http://127.0.0.1:8001")
MODULE2_URL = os.environ.get("MODULE2_URL", "http://127.0.0.1:8002")
MODULE4_URL = os.environ.get("MODULE4_URL", "http://127.0.0.1:8003")
WEIGHTS_PATH = Path(__file__).with_name("weights.json")
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "index.html"

# ---- Optional LLM narration (Module 4 - Wishmitha) ----
# API key is read from an environment variable only. Never hardcode a key here.
# If ANTHROPIC_API_KEY is not set, or the package isn't installed, or the API
# call fails for any reason, the system falls back to the deterministic
# template explanation automatically.
_ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
_ai_client = None
if anthropic and _ANTHROPIC_API_KEY:
    try:
        _ai_client = anthropic.Anthropic(api_key=_ANTHROPIC_API_KEY, timeout=8.0)
    except Exception:
        _ai_client = None

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


# --------------------------------------------------------------------------- explanation (Module 4 - Wishmitha)
def generate_natural_explanation(verdict_label: str, m1_data: dict, m4_data: dict, lang: str = "en") -> str:
    """Composes an explanation from LIME weights and Module 1's linguistic
    features, in English, Sinhala, or Tamil. Deliberately conservative in its
    claims: LIME weights describe which words most influenced THIS specific
    prediction, not a learned, general association between those words and
    misinformation — the wording below avoids implying the latter.

    Note: Tamil strings are machine-assisted and should be reviewed by a
    native speaker before being presented as a verified translation.
    """

    lf = m1_data.get("linguistic_features", {}) or {}
    urgency = lf.get("urgency_markers") or 0
    emotion = lf.get("emotional_intensity") or 0
    confidence = m1_data.get("confidence", 0.5)

    explanations = (m4_data.get("explanations") or [])[:3]
    top_words = [e["word"] for e in explanations if e.get("word")]
    words_joined = ", ".join(top_words)

    if confidence >= 0.75:
        conf_level = "high"
    elif confidence >= 0.6:
        conf_level = "moderate"
    else:
        conf_level = "low"

    is_credible = verdict_label == "CREDIBLE"

    # ---------------- English ----------------
    if lang == "en":
        conf_note = {
            "high": "with high confidence",
            "moderate": "with moderate confidence",
            "low": "with low confidence — this assessment is close to the decision boundary",
        }[conf_level]
        if is_credible:
            parts = [f"The content model classified this as credible {conf_note}."]
            if top_words:
                parts.append(
                    f"For this specific text, the words \u201c{words_joined}\u201d had the largest "
                    f"influence on that prediction, based on a local explanation (LIME) of the "
                    f"model's decision boundary \u2014 this reflects the model's behaviour on this "
                    f"input, not a general rule linking these words to credibility."
                )
            if urgency < 2 and emotion < 2:
                parts.append("The text also lacks the urgency-inducing or emotionally charged phrasing often seen in misinformation.")
            return " ".join(parts)
        parts = [f"The content model did not classify this as reliably credible {conf_note}."]
        if top_words:
            parts.append(
                f"For this specific text, the words \u201c{words_joined}\u201d had the largest "
                f"influence on that prediction. This shows what the model was reacting to in this "
                f"instance \u2014 it does not mean these words are inherently associated with false "
                f"claims in general; a full evaluation would require checking the claim itself "
                f"against a reliable source."
            )
        if urgency >= 2:
            parts.append(
                f"Separately, the text contains a high concentration of urgency-inducing phrasing "
                f"({urgency} markers per 100 words), a pattern common in content designed for rapid, "
                f"uncritical sharing."
            )
        if emotion >= 2:
            parts.append(f"It also uses emotionally charged language ({emotion} per 100 words), which can reduce careful reading.")
        parts.append(
            "No independently verifiable details \u2014 named sources, dates, or data \u2014 were found in "
            "the text to support the claim."
        )
        return " ".join(parts)

    # ---------------- Sinhala ----------------
    if lang == "si":
        conf_note = {
            "high": "ඉහළ විශ්වාසයෙන්",
            "moderate": "මධ්‍යම මට්ටමේ විශ්වාසයෙන්",
            "low": "අඩු විශ්වාසයෙන් — මෙම තක්සේරුව තීරණාත්මක සීමාවට ආසන්නයි",
        }[conf_level]
        if is_credible:
            parts = [f"අන්තර්ගත මාදිලිය මෙය {conf_note} විශ්වසනීය බව තීරණය කර ඇත."]
            if top_words:
                parts.append(
                    f"මෙම විශේෂිත පාඨය සඳහා, \u201c{words_joined}\u201d යන වචන එම අනාවැකියට වඩාත්ම බලපෑවේය "
                    f"(LIME විශ්ලේෂණය අනුව) — මෙය මෙම එක් උදාහරණයක් සඳහා මාදිලියේ හැසිරීම පෙන්වයි, "
                    f"මෙම වචන විශ්වසනීයත්වයට සම්බන්ධ පොදු නීතියක් නොවේ."
                )
            if urgency < 2 and emotion < 2:
                parts.append("අසත්‍ය තොරතුරු වල බහුලව දැකිය හැකි හදිසි හෝ චිත්තවේගී වචන ද මෙහි නොමැත.")
            return " ".join(parts)
        parts = [f"අන්තර්ගත මාදිලිය මෙය {conf_note} විශ්වාසදායක ලෙස තහවුරු කළේ නැත."]
        if top_words:
            parts.append(
                f"මෙම විශේෂිත පාඨය සඳහා, \u201c{words_joined}\u201d යන වචන එම අනාවැකියට වඩාත්ම බලපෑවේය. "
                f"මෙය මාදිලිය මෙම අවස්ථාවේදී ප්‍රතිචාර දැක්වූ ආකාරය පෙන්වයි — මෙම වචන පොදුවේ අසත්‍ය "
                f"ප්‍රකාශන සමඟ සම්බන්ධ බව අදහස් නොකරයි; සම්පූර්ණ තක්සේරුවක් සඳහා විශ්වසනීය මූලාශ්‍රයකින් "
                f"ප්‍රකාශනය සත්‍යාපනය කළ යුතුය."
            )
        if urgency >= 2:
            parts.append(
                f"මීට අමතරව, පාඨයේ හදිසි ක්‍රියාමාර්ග අවශ්‍ය බව පෙන්වන වචන ඉහළ සාන්ද්‍රණයකින් ({urgency} "
                f"per 100 words) අඩංගු වේ — මෙය කඩිසර, විවේචනාත්මක නොවන බෙදාගැනීම සඳහා නිර්මාණය කළ "
                f"අන්තර්ගතයන්හි බහුලව දක්නට ලැබෙන රටාවකි."
            )
        if emotion >= 2:
            parts.append(f"චිත්තවේගී වචන ද භාවිතා කර ඇත ({emotion} per 100 words), එය හොඳින් කියවීම අඩාල කළ හැක.")
        parts.append(
            "නම් කළ මූලාශ්‍ර, දින හෝ දත්ත වැනි ස්වාධීනව සත්‍යාපනය කළ හැකි විස්තර පාඨයේ "
            "සොයාගත නොහැකි විය."
        )
        return " ".join(parts)

    # ---------------- Tamil (machine-assisted — recommend native review) ----------------
    if lang == "ta":
        conf_note = {
            "high": "அதிக நம்பிக்கையுடன்",
            "moderate": "மிதமான நம்பிக்கையுடன்",
            "low": "குறைந்த நம்பிக்கையுடன் — இந்த மதிப்பீடு தீர்மான எல்லைக்கு நெருக்கமாக உள்ளது",
        }[conf_level]
        if is_credible:
            parts = [f"உள்ளடக்க மாதிரி இதை {conf_note} நம்பகமானதாக வகைப்படுத்தியுள்ளது."]
            if top_words:
                parts.append(
                    f"இந்த குறிப்பிட்ட உரைக்கு, \u201c{words_joined}\u201d என்ற சொற்கள் அந்த "
                    f"முடிவில் மிகப்பெரிய தாக்கத்தை ஏற்படுத்தின (LIME பகுப்பாய்வின்படி) — இது இந்த "
                    f"ஒரு உள்ளீட்டில் மாதிரியின் நடத்தையை காட்டுகிறது, இந்த சொற்களை நம்பகத்தன்மையுடன் "
                    f"இணைக்கும் பொதுவான விதி அல்ல."
                )
            if urgency < 2 and emotion < 2:
                parts.append("தவறான தகவல்களில் பொதுவாகக் காணப்படும் அவசர அல்லது உணர்ச்சிகரமான சொற்களும் இதில் இல்லை.")
            return " ".join(parts)
        parts = [f"உள்ளடக்க மாதிரி இதை {conf_note} நம்பகமானதாக உறுதிப்படுத்தவில்லை."]
        if top_words:
            parts.append(
                f"இந்த குறிப்பிட்ட உரைக்கு, \u201c{words_joined}\u201d என்ற சொற்கள் அந்த "
                f"முடிவில் மிகப்பெரிய தாக்கத்தை ஏற்படுத்தின. இது இந்த நிகழ்வில் மாதிரி எதற்கு "
                f"எதிர்வினையாற்றியது என்பதைக் காட்டுகிறது — இந்த சொற்கள் பொதுவாக தவறான கூற்றுகளுடன் "
                f"இயல்பாக இணைக்கப்பட்டவை என்று அர்த்தமல்ல; முழுமையான மதிப்பீட்டிற்கு நம்பகமான "
                f"மூலத்திலிருந்து கூற்றை சரிபார்க்க வேண்டும்."
            )
        if urgency >= 2:
            parts.append(
                f"தனியாக, உரையில் அவசரத்தைத் தூண்டும் சொற்றொடர்களின் அதிக செறிவு "
                f"({urgency} per 100 words) உள்ளது — இது விரைவான, விமர்சனமற்ற பகிர்வுக்காக "
                f"வடிவமைக்கப்பட்ட உள்ளடக்கத்தில் பொதுவான ஒரு முறை."
            )
        if emotion >= 2:
            parts.append(f"உணர்ச்சிகரமான மொழியும் பயன்படுத்தப்பட்டுள்ளது ({emotion} per 100 words), இது கவனமான வாசிப்பைக் குறைக்கலாம்.")
        parts.append(
            "பெயரிடப்பட்ட ஆதாரங்கள், தேதிகள் அல்லது தரவு போன்ற சுயாதீனமாக சரிபார்க்கக்கூடிய "
            "விவரங்கள் உரையில் காணப்படவில்லை."
        )
        return " ".join(parts)

    return generate_natural_explanation(verdict_label, m1_data, m4_data, lang="en")


def generate_ai_narration(verdict_label: str, m1_data: dict, m4_data: dict, template_fallback: str) -> str:
    """Uses an LLM to rephrase the LIME-derived findings into more natural
    prose. The LLM does not add outside knowledge or verify the claim itself
    — it only narrates the analytical results LIME and Module 1 already
    produced. Falls back to the deterministic template if no API key is
    configured, the package is missing, or the call fails or times out —
    this keeps the demo reliable without a network dependency."""
    if not _ai_client:
        return template_fallback

    try:
        lf = m1_data.get("linguistic_features", {}) or {}
        top_words = [e["word"] for e in (m4_data.get("explanations") or [])[:5]]
        confidence = m1_data.get("confidence", 0.5)

        prompt = f"""You are explaining an AI misinformation-detection result to an end user.
Use ONLY the data below. Do not add outside facts about the claim. Do not verify
whether the claim is true. Write 2-3 short, clear sentences in plain English.

Verdict: {verdict_label}
Model confidence: {confidence:.2f}
Words that most influenced this specific prediction (from LIME): {', '.join(top_words) if top_words else 'none'}
Urgency-inducing phrasing detected: {lf.get('urgency_markers', 0)} per 100 words
Emotional language detected: {lf.get('emotional_intensity', 0)} per 100 words

Be clear that LIME weights reflect this one prediction, not a general rule about these words."""

        response = _ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        return text if text else template_fallback
    except Exception as e:
        print(f"[AI narration] fell back to template: {type(e).__name__}: {e}")
        return template_fallback


# --------------------------------------------------------------------------- routes
@app.get("/", response_class=HTMLResponse)
def ui():
    if FRONTEND.is_file():
        return HTMLResponse(FRONTEND.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SinhalaCheck</h1><p>Frontend not found.</p>", status_code=200)


@app.get("/health")
async def health():
    out = {"fusion": "ok", "weights": load_weights().get("method"), "ai_narration": _ai_client is not None}
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
    verdict_label = verdict(score, cfg)

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

    natural_explanation_en = generate_natural_explanation(verdict_label, m1_data, m4_data, "en") if m4_data else None

    return {
        "final_score": round(score, 4),
        "verdict": verdict_label,
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
        "natural_explanation": natural_explanation_en,
        "natural_explanation_si": generate_natural_explanation(verdict_label, m1_data, m4_data, "si") if m4_data else None,
        "natural_explanation_ta": generate_natural_explanation(verdict_label, m1_data, m4_data, "ta") if m4_data else None,
        "natural_explanation_ai": generate_ai_narration(verdict_label, m1_data, m4_data, natural_explanation_en) if m4_data else None,
    }