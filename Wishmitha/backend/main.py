from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pickle
from lime.lime_text import LimeTextExplainer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model load
clf = pickle.load(open('sinhala_clf.pkl', 'rb'))
vec = pickle.load(open('vectorizer.pkl', 'rb'))
explainer = LimeTextExplainer(class_names=["CREDIBLE", "FALSE"])

def predict(texts):
    return clf.predict_proba(vec.transform(texts))

@app.post("/fuse")
def fuse(data: dict):
    text = data["text"]

    # Module 1 — content score (oya trained model)
    proba = clf.predict_proba(vec.transform([text]))[0]
    content_score = float(proba[0])  # CREDIBLE probability

    # Module 2 — mock (Rocky/Caldera ready wunama swap)
    source_score   = 0.5
    temporal_score = 0.4

    # Weighted fusion formula
    final = round((0.50 * content_score) + (0.30 * source_score) + (0.20 * temporal_score), 2)
    label = "CREDIBLE" if final > 0.6 else "LIKELY FALSE"

    # LIME reasons
    exp = explainer.explain_instance(text, predict, num_features=5, num_samples=300)
    lime_reasons = [
        {"word": w, "weight": round(wt, 3), "flag": "suspicious" if wt > 0 else "credible"}
        for w, wt in exp.as_list()
    ]

    return {
        "final_score":      final,
        "label":            label,
        "content_score":    round(content_score, 2),
        "source_score":     source_score,
        "temporal_score":   temporal_score,
        "temporal_warning": temporal_score < 0.3,
        "lime_reasons":     lime_reasons
    }

@app.get("/")
def root():
    return {"status": "SinhalaCheck Fusion API running!"}