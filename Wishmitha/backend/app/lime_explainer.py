import pickle
from lime.lime_text import LimeTextExplainer

# trained model load
clf = pickle.load(open('sinhala_clf.pkl', 'rb'))
vec = pickle.load(open('vectorizer.pkl', 'rb'))

explainer = LimeTextExplainer(class_names=["CREDIBLE", "FALSE"])

def predict(texts):
    return clf.predict_proba(vec.transform(texts))

def get_lime_reasons(text):
    exp = explainer.explain_instance(
        text, predict,
        num_features=5,
        num_samples=500
    )
    return [
        {
            "word":   w,
            "weight": round(wt, 3),
            "flag":   "suspicious" if wt > 0 else "credible"
        }
        for w, wt in exp.as_list()
    ]

# Test
if __name__ == "__main__":
    test = "share before they delete this bank closing urgent"
    reasons = get_lime_reasons(test)
    print("\n--- LIME Reasons ---")
    for r in reasons:
        icon = "⚠️" if r['flag'] == 'suspicious' else "✅"
        print(f"{icon} '{r['word']}' → {r['weight']}")