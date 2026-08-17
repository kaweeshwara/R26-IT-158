from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from lime.lime_text import LimeTextExplainer
import torch
import torch.nn.functional as F
import numpy as np
import re

app = FastAPI()

# ---- Load the real trained model (from local ./model folder) ----
MODEL_PATH = "./model"
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print("Loading model... this may take a moment.")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
model.to(device)
model.eval()
print(f"Model loaded on: {device}")

CLASS_NAMES = ['CREDIBLE', 'UNCERTAIN', 'PARTIAL/FALSE']

lime_explainer = LimeTextExplainer(
    class_names=CLASS_NAMES,
    split_expression=r'\s+',
    bow=False
)

# ---- Helper: clean punctuation for better LIME word-splitting ----
def clean_for_lime(text):
    text = re.sub(r'([.,!?;:()"\u0d80-\u0dff]*[.,!?;:()"])', r' \1 ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ---- Helper: real model prediction (single text) ----
def get_model_probs(text):
    inputs = tokenizer(text, truncation=True, padding='max_length', max_length=256, return_tensors='pt').to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
    return probs  # [credible_prob, uncertain_prob, partial_false_prob]

# ---- Helper: batched prediction for LIME (many perturbed texts at once) ----
def lime_predict_proba(texts):
    all_probs = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = list(texts[i:i+batch_size])
        inputs = tokenizer(batch, truncation=True, padding='max_length', max_length=256, return_tensors='pt').to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()
        all_probs.append(probs)
    return np.vstack(all_probs)

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

# ---- Input shape ----
class FusionInput(BaseModel):
    text: str                 # original news text (used by our own model + LIME)
    source_score: float        # from Module 2 (Caldera)
    temporal_score: float      # from Module 2 (Caldera)

@app.post("/predict")
def predict(data: FusionInput):
    # 1. Run our own trained model to get a content_score
    probs = get_model_probs(data.text)
    credible_prob = float(probs[0])
    content_score = credible_prob  # higher = more credible

    # 2. Fusion formula
    final_score = calculate_final_score(content_score, data.source_score, data.temporal_score)
    verdict = get_verdict(final_score)

    # 3. LIME explanation using the real model
    clean_text = clean_for_lime(data.text)
    exp = lime_explainer.explain_instance(
        clean_text,
        lime_predict_proba,
        num_features=5,
        num_samples=200,
        labels=[0, 1, 2]
    )
    top_label = int(np.argmax(probs))
    lime_reasons = [
        {"word": w.strip('.,!?;:()"'), "weight": round(wt, 3)}
        for w, wt in exp.as_list(label=top_label)
    ]

    return {
        "final_score": round(final_score, 3),
        "label": verdict,
        "model_prediction": {
            "credible": round(float(probs[0]), 3),
            "uncertain": round(float(probs[1]), 3),
            "partial_false": round(float(probs[2]), 3)
        },
        "breakdown": {
            "content": round(content_score, 3),
            "source": data.source_score,
            "temporal": data.temporal_score
        },
        "lime_explanations": lime_reasons
    }