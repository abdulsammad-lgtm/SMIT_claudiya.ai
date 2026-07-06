import os
import joblib
import numpy as np
import asyncio
from typing import Optional

from app.tools.fraud_patterns import ML_FEATURE_NAMES

_explainer = None
EXPLAINER_AVAILABLE = False

EXPLAINER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "shap_explainer_v1.pkl")


def load_explainer():
    global _explainer, EXPLAINER_AVAILABLE
    try:
        _explainer = joblib.load(EXPLAINER_PATH)
        EXPLAINER_AVAILABLE = True
    except Exception:
        EXPLAINER_AVAILABLE = False


async def explain(feature_vector: list[float], top_n: int = 5) -> Optional[dict]:
    if not EXPLAINER_AVAILABLE or _explainer is None:
        return None

    X = np.array(feature_vector, dtype=float).reshape(1, -1)

    shap_values = await asyncio.to_thread(
        lambda: _explainer.shap_values(X)[0]
    )

    feature_contributions = [
        {
            "feature": name,
            "contribution": round(float(sv), 4),
            "value": round(float(feature_vector[i]), 4),
        }
        for i, (name, sv) in enumerate(zip(ML_FEATURE_NAMES, shap_values))
    ]

    feature_contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

    return {"top_features": feature_contributions[:top_n]}
