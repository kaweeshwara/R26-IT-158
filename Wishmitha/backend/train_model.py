import pickle
import pandas as pd
import requests
import io
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

print("\n=== SINHALACHECK - MODEL TRAINING (FIXED) ===\n")

print("1. Real dataset download karanawa (LIRNEasia)...")
url = "https://raw.githubusercontent.com/LIRNEasia/MisinformationCorpusSinhala/main/Corpus.csv"
response = requests.get(url, timeout=30)
df = pd.read_csv(io.StringIO(response.text))

print(f"2. Downloaded! Records: {len(df)}")

# PARTIAL da FALSE lesa count karanawa - more balance
# UNCERTAIN drop karanawa
df = df[df['type'].isin(['CREDIBLE', 'FALSE', 'PARTIAL'])].copy()
df['label_num'] = df['type'].map({
    'CREDIBLE': 0,
    'FALSE':    1,
    'PARTIAL':  1   # PARTIAL = also not fully credible
})
df = df.dropna(subset=['content'])

print(f"\n3. Clean records: {len(df)}")
print(f"   CREDIBLE        : {(df['label_num']==0).sum()}")
print(f"   FALSE + PARTIAL : {(df['label_num']==1).sum()}")

texts  = df['content'].tolist()
labels = df['label_num'].tolist()

print("\n4. Train/test split (70/30)...")
X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.3, random_state=42
)

print("5. TF-IDF vectorizing...")
vec = TfidfVectorizer(max_features=5000)
X_tr = vec.fit_transform(X_train)
X_te = vec.transform(X_test)

print("6. SVM training with class balancing...")
# class_weight='balanced' = imbalance fix
clf = SVC(kernel="linear", probability=True, class_weight='balanced')
clf.fit(X_tr, y_train)

y_pred = clf.predict(X_te)

print("\n--- Results ---")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
print(classification_report(
    y_test, y_pred,
    target_names=["CREDIBLE","FALSE/PARTIAL"],
    zero_division=0
))

pickle.dump(clf, open("sinhala_clf.pkl", "wb"))
pickle.dump(vec, open("vectorizer.pkl", "wb"))

print("\n✅ DONE! sinhala_clf.pkl + vectorizer.pkl saved!")