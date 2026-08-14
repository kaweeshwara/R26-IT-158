from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# ---- Input shape (Module 1 + Module 2 send these) ----
class FusionInput(BaseModel):
    content_score: float      # from Module 1 (Rocky) - derived from their label/confidence
    source_score: float       # from Module 2 (Caldera)
    temporal_score: float     # from Module 2 (Caldera)

# ---- Fusion formula (50 / 30 / 20) ----
def calculate_final_score(content_score, source_score, temporal_score):
    return (0.50 * content_score) + (0.30 * source_score) + (0.20 * temporal_score)

def get_verdict(score):
    if score >= 0.61:
        return "CREDIBLE"
    elif score >= 0.41:
        return "UNCERTAIN"
    else:
        return "MISINFORMATION"

@app.post("/predict")
def predict(data: FusionInput):
    final_score = calculate_final_score(data.content_score, data.source_score, data.temporal_score)
    verdict = get_verdict(final_score)
    return {
        "final_score": round(final_score, 3),
        "label": verdict,
        "breakdown": {
            "content": data.content_score,
            "source": data.source_score,
            "temporal": data.temporal_score
        }
    }