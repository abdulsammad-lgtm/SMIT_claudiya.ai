import os
import json
import numpy as np
import asyncio
import xgboost as xgb

_model = None
_metadata = None
MODEL_AVAILABLE = False

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "xgboost_fraud_v1_new.model")
METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "model_metadata.json")


def load_model():
    global _model, _metadata, MODEL_AVAILABLE
    try:
        _model = xgb.XGBClassifier()
        _model.load_model(MODEL_PATH)
        with open(METADATA_PATH) as f:
            _metadata = json.load(f)
        MODEL_AVAILABLE = True
    except FileNotFoundError:
        MODEL_AVAILABLE = False
    except Exception:
        MODEL_AVAILABLE = False


async def predict(feature_vector: list[float]) -> dict:
    if not MODEL_AVAILABLE or _model is None:
        return {
            "fraud_probability": 0.5,
            "ml_score": 50,
            "model_version": "unavailable",
            "error": "model_not_loaded",
        }

    X = np.array(feature_vector, dtype=float).reshape(1, -1)

    fraud_prob = await asyncio.to_thread(
        lambda: float(_model.predict_proba(X)[0, 1])
    )

    if fraud_prob < 0.5:
        ml_score = int(fraud_prob * 140)
    else:
        ml_score = int(70 + (fraud_prob - 0.5) * 60)

    ml_score = min(ml_score, 100)

    return {
        "fraud_probability": round(fraud_prob, 4),
        "ml_score": ml_score,
        "model_version": _metadata.get("version", "unknown") if _metadata else "unknown",
        "error": None,
    }
