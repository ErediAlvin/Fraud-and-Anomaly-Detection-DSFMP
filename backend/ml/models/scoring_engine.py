"""
DSFMP ML Scoring Engine
Orchestrates inference across fraud anomaly models, starting with Isolation Forest.
Provides single-transaction scoring, batch scoring, and extracted feature inspection.
"""

import os
import time
import warnings
from typing import Dict, Any, Optional
import numpy as np

# Suppress sklearn unpickling version warnings across sub-patch versions
warnings.filterwarnings("ignore", category=UserWarning)

from ml.models.isolation_forest import IsolationForestFraudModel
from config.settings import settings

DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "saved_models",
    "isolation_forest_v1.joblib"
)

_cached_model: Optional[IsolationForestFraudModel] = None


def get_isolation_forest_model(model_path: str = DEFAULT_MODEL_PATH) -> IsolationForestFraudModel:
    """Loads and caches the Isolation Forest model artifact."""
    global _cached_model
    if _cached_model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Isolation Forest model artifact not found at: {model_path}")
        _cached_model = IsolationForestFraudModel.load(model_path)
    return _cached_model


def score_transaction_with_isolation_forest(
    transaction_data: Dict[str, Any],
    threshold: float = 0.65,
    model_path: str = DEFAULT_MODEL_PATH
) -> Dict[str, Any]:
    """
    Executes live inference on a transaction payload using the Isolation Forest model.
    Returns the normalized anomaly score [0.0000, 1.0000], classification, risk tier,
    extracted engineered features, and execution latency.
    """
    model = get_isolation_forest_model(model_path)
    start_time = time.perf_counter()

    # Pre-extract features for transparent inspection in UI
    extracted_df = model.extractor.transform([transaction_data])
    row = extracted_df.iloc[0]

    # Calculate calibrated anomaly score
    raw_score_arr = model.score_samples(extracted_df)
    score = float(raw_score_arr[0])
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Determine risk tier based on system configuration settings
    tier = settings.get_risk_tier(score)
    is_anomaly = score >= threshold

    # Generate explainability signals
    reasons = []
    if row.get("is_off_hours", 0) == 1:
        reasons.append(f"Off-hours transaction detected (Hour {int(row.get('hour_of_day', 0))}:00)")
    if row.get("amount_to_school_avg_ratio", 1.0) > 3.0:
        reasons.append(f"Disproportionate amount: {float(row.get('amount_to_school_avg_ratio', 1.0)):.1f}x higher than school average")
    if row.get("amount_per_student", 0) > 5000:
        reasons.append(f"Inflated per-student cost: KES {float(row.get('amount_per_student', 0)):,.0f}/student")
    if row.get("rolling_24h_count", 1) >= 4:
        reasons.append(f"High transaction velocity: {int(row.get('rolling_24h_count', 1))} transactions within 24 hours")
    if not reasons and is_anomaly:
        reasons.append("Multi-factor tabular anomaly detected by Isolation Forest trees")

    return {
        "model_name": "Isolation Forest",
        "model_version": "v1.0",
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "risk_tier": tier,
        "threshold": threshold,
        "latency_ms": latency_ms,
        "reasons": reasons,
        "features_extracted": {
            "amount": float(row.get("amount", 0.0)),
            "type": str(row.get("type", "UNKNOWN")),
            "payment_method": str(row.get("payment_method", "UNKNOWN")),
            "hour_of_day": int(row.get("hour_of_day", 12)),
            "day_of_week": int(row.get("day_of_week", 0)),
            "is_weekend": bool(row.get("is_weekend", 0)),
            "is_off_hours": bool(row.get("is_off_hours", 0)),
            "amount_per_student": round(float(row.get("amount_per_student", 0.0)), 2),
            "amount_to_school_avg_ratio": round(float(row.get("amount_to_school_avg_ratio", 1.0)), 2),
            "rolling_24h_count": int(row.get("rolling_24h_count", 1)),
            "log_amount": round(float(row.get("log_amount", 0.0)), 4),
        }
    }
