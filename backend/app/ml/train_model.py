import os
import sys

# Ensure repository root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from backend.app.config import settings

def train_priority_model():
    """
    Trains the NIEresolve complaint priority prediction model using TF-IDF and Logistic Regression.
    Evaluates precision, recall, F1-score, and confusion matrix.
    Persists model artifacts using joblib.
    """
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "sample_training_data.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Training dataset not found at {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} labeled complaints from {csv_path}")
    print(f"Priority distribution:\n{df['priority'].value_counts()}\n")

    # Feature representation: Combine category, title, and description
    # This captures both contextual category bias and fine-grained grievance wording
    df["full_text"] = df["category"] + " " + df["title"] + " " + df["description"]

    X = df["full_text"]
    y = df["priority"]

    # TF-IDF Vectorizer with unigrams and bigrams
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=1500,
        sublinear_tf=True,
        stop_words="english",
    )
    X_vec = vectorizer.fit_transform(X)

    # Balanced class weights to handle critical/high vs low distribution
    classifier = LogisticRegression(
        C=2.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )

    # 3-Fold Stratified Cross-Validation evaluation
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    y_pred_cv = cross_val_predict(classifier, X_vec, y, cv=cv)

    acc = accuracy_score(y, y_pred_cv)
    f1_weighted = f1_score(y, y_pred_cv, average="weighted")
    print("================ MODEL EVALUATION METRICS ================")
    print(f"Stratified CV Accuracy: {acc * 100:.2f}%")
    print(f"Weighted F1-Score:      {f1_weighted * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y, y_pred_cv, zero_division=0))
    print("Confusion Matrix:")
    classes = sorted(list(set(y)))
    cm = confusion_matrix(y, y_pred_cv, labels=classes)
    cm_df = pd.DataFrame(cm, index=[f"Actual {c}" for c in classes], columns=[f"Pred {c}" for c in classes])
    print(cm_df)
    print("==========================================================")

    # Fit final model on full dataset
    classifier.fit(X_vec, y)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(settings.MODEL_STORAGE_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(settings.VECTORIZER_STORAGE_PATH), exist_ok=True)

    # Persist model artifacts
    joblib.dump(classifier, settings.MODEL_STORAGE_PATH)
    joblib.dump(vectorizer, settings.VECTORIZER_STORAGE_PATH)
    print(f"Model saved to:      {settings.MODEL_STORAGE_PATH}")
    print(f"Vectorizer saved to: {settings.VECTORIZER_STORAGE_PATH}")
    return classifier, vectorizer

if __name__ == "__main__":
    train_priority_model()
