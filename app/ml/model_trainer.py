"""
Training pipeline for the XGBoost fraud model.
This is a standalone script — not loaded at application runtime.
Run it when you need to retrain the model with new data.

Usage:
    python -m app.ml.model_trainer

Generates synthetic data, trains XGBoost, evaluates, and saves
model + SHAP explainer to app/models/.
"""

import os
import json
import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
import xgboost as xgb
import shap
import joblib

from app.ml.synthetic_data_generator import generate_synthetic_dataset
from app.tools.fraud_patterns import ML_FEATURE_NAMES


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def train():
    os.makedirs(MODELS_DIR, exist_ok=True)

    print("[Trainer] Generating synthetic training data...")
    df = generate_synthetic_dataset(n_samples=10000)

    X = df[ML_FEATURE_NAMES].values
    y = df["fraud_label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"[Trainer] Train size: {len(X_train)}, Test size: {len(X_test)}")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    auc = roc_auc_score(y_test, y_pred_proba)

    print(f"[Trainer] Test AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred, target_names=["legitimate", "fraud"]))

    model_path = os.path.join(MODELS_DIR, "xgboost_fraud_v1.pkl")
    joblib.dump(model, model_path)
    print(f"[Trainer] Model saved to {model_path}")

    print("[Trainer] Computing SHAP explainer (this may take a moment)...")
    explainer = shap.TreeExplainer(model)
    explainer_path = os.path.join(MODELS_DIR, "shap_explainer_v1.pkl")
    joblib.dump(explainer, explainer_path)
    print(f"[Trainer] Explainer saved to {explainer_path}")

    metadata = {
        "version": "v1",
        "trained_at": datetime.datetime.utcnow().isoformat(),
        "n_features": len(ML_FEATURE_NAMES),
        "feature_names": ML_FEATURE_NAMES,
        "model_file": "xgboost_fraud_v1.pkl",
        "explainer_file": "shap_explainer_v1.pkl",
        "metrics": {
            "train_auc": round(auc, 4),
            "source": "synthetic",
        },
    }
    meta_path = os.path.join(MODELS_DIR, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Trainer] Metadata saved to {meta_path}")
    print("[Trainer] Training complete.")


if __name__ == "__main__":
    train()
