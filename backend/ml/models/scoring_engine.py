"""
DSFMP ML Scoring Engine
Orchestrates inference across fraud anomaly models, starting with Isolation Forest.
Provides single-transaction scoring, batch scoring, and extracted feature inspection.
"""

import os
import time
import warnings
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd

# Suppress sklearn unpickling version warnings across sub-patch versions
# Compatibility warnings must remain visible.

from ml.models.isolation_forest import IsolationForestFraudModel
from ml.models.autoencoder import AutoencoderFraudModel
from ml.models.lstm_autoencoder import LSTMAutoencoderFraudModel
from config.settings import settings

DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "saved_models",
    "isolation_forest_v1.joblib"
)

DEFAULT_AE_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "saved_models",
    "autoencoder_v1.joblib"
)

DEFAULT_LSTM_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "saved_models",
    "lstm_autoencoder_v1.joblib"
)

_cached_model: Optional[IsolationForestFraudModel] = None
_cached_ae_model: Optional[AutoencoderFraudModel] = None
_cached_lstm_model: Optional[LSTMAutoencoderFraudModel] = None


def get_isolation_forest_model(model_path: str = DEFAULT_MODEL_PATH) -> IsolationForestFraudModel:
    """Loads and caches the Isolation Forest model artifact."""
    global _cached_model
    if _cached_model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Isolation Forest model artifact not found at: {model_path}")
        _cached_model = IsolationForestFraudModel.load(model_path)
    return _cached_model


def get_autoencoder_model(model_path: str = DEFAULT_AE_MODEL_PATH) -> AutoencoderFraudModel:
    """Loads and caches the Autoencoder fraud model artifact."""
    global _cached_ae_model
    if _cached_ae_model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Autoencoder model artifact not found at: {model_path}")
        _cached_ae_model = AutoencoderFraudModel.load(model_path)
    return _cached_ae_model


def get_lstm_model(model_path: str = DEFAULT_LSTM_MODEL_PATH) -> LSTMAutoencoderFraudModel:
    """Loads and caches the LSTM Autoencoder temporal fraud model artifact."""
    global _cached_lstm_model
    if _cached_lstm_model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"LSTM Autoencoder model artifact not found at: {model_path}")
        _cached_lstm_model = LSTMAutoencoderFraudModel.load(model_path)
    return _cached_lstm_model


def _build_domain_reasons(row: Any, is_anomaly: bool, fallback_msg: str) -> List[str]:
    """Generate human-readable risk signals from engineered transaction features."""
    reasons: List[str] = []
    if row.get("is_off_hours", 0) == 1:
        reasons.append(f"Off-hours transaction detected (Hour {int(row.get('hour_of_day', 0))}:00)")
    if row.get("amount_to_school_avg_ratio", 1.0) > 3.0:
        reasons.append(
            f"Disproportionate amount: {float(row.get('amount_to_school_avg_ratio', 1.0)):.1f}x higher than school average"
        )
    if row.get("amount_per_student", 0) > 5000:
        reasons.append(
            f"Inflated per-student cost: KES {float(row.get('amount_per_student', 0)):,.0f}/student"
        )
    if row.get("rolling_24h_count", 1) >= 4:
        reasons.append(
            f"High transaction velocity: {int(row.get('rolling_24h_count', 1))} transactions within 24 hours"
        )
    if not reasons and is_anomaly:
        reasons.append(fallback_msg)
    return reasons


def _format_extracted_features(row: Any) -> Dict[str, Any]:
    """Format engineered features consistently for API responses."""
    return {
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
    reasons = _build_domain_reasons(
        row, is_anomaly, "Multi-factor tabular anomaly detected by Isolation Forest trees"
    )

    return {
        "model_name": "Isolation Forest",
        "model_version": "v1.0",
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "risk_tier": tier,
        "threshold": threshold,
        "latency_ms": latency_ms,
        "reasons": reasons,
        "features_extracted": _format_extracted_features(row),
    }


def score_transaction_with_autoencoder(
    transaction_data: Dict[str, Any],
    threshold: float = 0.70,
    model_path: str = DEFAULT_AE_MODEL_PATH,
) -> Dict[str, Any]:
    """
    Executes live inference on a transaction payload using the MLP Autoencoder model.
    Returns normalized anomaly score [0.0000, 1.0000], top reconstruction error drivers,
    classification, risk tier, extracted features, and latency.
    """
    model = get_autoencoder_model(model_path)
    start_time = time.perf_counter()

    extracted_df = model.extractor.transform([transaction_data])
    row = extracted_df.iloc[0]

    score = float(model.score_samples(extracted_df)[0])
    drivers = model.explain_reconstruction(transaction_data, top_k=3)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    tier = settings.get_risk_tier(score)
    is_anomaly = score >= threshold
    reasons = _build_domain_reasons(
        row, is_anomaly, "High neural reconstruction error detected by Autoencoder bottleneck"
    )
    if drivers and (is_anomaly or drivers[0]["share"] >= 0.25):
        top_names = ", ".join(
            f"{d['feature']} ({d['share'] * 100:.0f}%)" for d in drivers[:2]
        )
        reasons.insert(0, f"Top reconstruction error drivers: {top_names}")

    return {
        "model_name": "Autoencoder",
        "model_version": "v1.0",
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "risk_tier": tier,
        "threshold": threshold,
        "latency_ms": latency_ms,
        "reasons": reasons,
        "reconstruction_drivers": drivers,
        "features_extracted": _format_extracted_features(row),
    }


def score_transaction_with_lstm(
    transaction_data: Dict[str, Any],
    threshold: float = 0.68,
    model_path: str = DEFAULT_LSTM_MODEL_PATH,
    history_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Executes live temporal sequence inference using the LSTM Autoencoder model.
    Scores sequence cadence deviation, rolling EWMA baseline shifts, and bursts.
    """
    model = get_lstm_model(model_path)
    start_time = time.perf_counter()

    score = model.score_single(transaction_data, history_df=history_df)
    drivers = model.explain_temporal_anomaly(transaction_data, history_df=history_df, top_k=3)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    tier = settings.get_risk_tier(score)
    is_anomaly = score >= threshold

    reasons: List[str] = []
    if float(transaction_data.get("rolling_24h_count", 1)) >= 6:
        reasons.append(f"Abnormal sequence velocity: {int(transaction_data.get('rolling_24h_count', 1))} events within 24 hours")
    if float(transaction_data.get("amount_to_school_avg_ratio", 1.0)) > 3.0:
        reasons.append(f"Temporal EWMA surge: {float(transaction_data.get('amount_to_school_avg_ratio', 1.0)):.1f}x higher than school trailing average")
    if is_anomaly and not reasons:
        reasons.append("Multi-step temporal trajectory anomaly detected by LSTM Autoencoder sequence bottleneck")

    if drivers and (is_anomaly or drivers[0]["share"] >= 0.25):
        top_str = ", ".join(f"{d['feature']} ({d['share']*100:.0f}%)" for d in drivers[:2])
        reasons.insert(0, f"Top temporal error drivers: {top_str}")

    feat_df = model.builder._extract_step_features(pd.DataFrame([transaction_data]))
    row = feat_df.iloc[0]

    return {
        "model_name": "LSTM Autoencoder",
        "model_version": "v1.0",
        "anomaly_score": score,
        "is_anomaly": is_anomaly,
        "risk_tier": tier,
        "threshold": threshold,
        "latency_ms": latency_ms,
        "reasons": reasons,
        "reconstruction_drivers": drivers,
        "features_extracted": _format_extracted_features(row),
    }


def compute_weighted_ensemble_score(
    if_score: float,
    ae_score: float,
    lstm_score: Optional[float] = None,
    gnn_score: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Combine model anomaly scores using configured ensemble weights.
    Active models: Isolation Forest (40%), Autoencoder (30%), LSTM Autoencoder (30%).
    """
    cfg_weights = {
        "if": float((weights or {}).get("weight_if", settings.weight_isolation_forest)),
        "ae": float((weights or {}).get("weight_ae", settings.weight_autoencoder)),
        "lstm": float((weights or {}).get("weight_lstm", settings.weight_lstm)),
    }
    total_cfg = sum(cfg_weights.values()) or 1.0
    norm_cfg = {k: round(v / total_cfg, 4) for k, v in cfg_weights.items()}

    scores = {
        "if": float(if_score),
        "ae": float(ae_score),
        "lstm": float(lstm_score) if lstm_score is not None else 0.0,
    }
    active_flags = {
        "if": True,
        "ae": True,
        "lstm": lstm_score is not None,
    }

    weighted_sum = sum(norm_cfg[k] * scores[k] for k in ("if", "ae", "lstm"))
    active_weight_total = sum(norm_cfg[k] for k, is_on in active_flags.items() if is_on) or 1.0
    composite_score = round(
        sum(norm_cfg[k] * scores[k] for k, is_on in active_flags.items() if is_on) / active_weight_total,
        4,
    )

    breakdown = []
    meta = [
        ("if", "Isolation Forest", "ACTIVE"),
        ("ae", "Autoencoder", "ACTIVE"),
        ("lstm", "LSTM Temporal", "ACTIVE" if active_flags["lstm"] else "PENDING"),
    ]
    for key, label, status in meta:
        effective_w = round((norm_cfg[key] / active_weight_total) if active_flags[key] else 0.0, 4)
        breakdown.append({
            "id": key,
            "name": label,
            "status": status,
            "score": round(scores[key], 4),
            "configured_weight": norm_cfg[key],
            "effective_weight": effective_w,
            "weighted_contribution": round(norm_cfg[key] * scores[key], 4),
            "effective_contribution": round(effective_w * scores[key], 4),
        })

    return {
        "composite_score": composite_score,
        "raw_weighted_sum": round(weighted_sum, 4),
        "risk_tier": settings.get_risk_tier(composite_score),
        "weights": norm_cfg,
        "breakdown": breakdown,
    }


def score_transaction_ensemble(
    transaction_data: Dict[str, Any],
    if_threshold: float = 0.65,
    ae_threshold: float = 0.70,
    lstm_threshold: float = 0.68,
    weights: Optional[Dict[str, float]] = None,
    history_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Run Isolation Forest, Autoencoder, and LSTM Autoencoder, combining with configured ensemble weights."""
    if_res = score_transaction_with_isolation_forest(transaction_data, threshold=if_threshold)
    ae_res = score_transaction_with_autoencoder(transaction_data, threshold=ae_threshold)

    lstm_res = None
    if os.path.exists(DEFAULT_LSTM_MODEL_PATH):
        try:
            lstm_res = score_transaction_with_lstm(
                transaction_data, threshold=lstm_threshold, history_df=history_df
            )
        except Exception as lstm_err:
            print(f"[WARN] LSTM inference skipped in ensemble: {lstm_err}")

    ensemble = compute_weighted_ensemble_score(
        if_score=if_res["anomaly_score"],
        ae_score=ae_res["anomaly_score"],
        lstm_score=lstm_res["anomaly_score"] if lstm_res else None,
        weights=weights,
    )

    combined_reasons = ae_res["reasons"] + if_res["reasons"]
    if lstm_res:
        combined_reasons = lstm_res["reasons"] + combined_reasons
    combined_reasons = list(dict.fromkeys(combined_reasons))

    total_latency = if_res["latency_ms"] + ae_res["latency_ms"] + (lstm_res["latency_ms"] if lstm_res else 0.0)

    res_dict: Dict[str, Any] = {
        "composite_score": ensemble["composite_score"],
        "raw_weighted_sum": ensemble["raw_weighted_sum"],
        "risk_tier": ensemble["risk_tier"],
        "is_anomaly": ensemble["composite_score"] >= min(if_threshold, ae_threshold),
        "total_latency_ms": round(total_latency, 2),
        "weights": ensemble["weights"],
        "breakdown": ensemble["breakdown"],
        "isolation_forest": if_res,
        "autoencoder": ae_res,
        "reasons": combined_reasons,
        "features_extracted": ae_res["features_extracted"],
    }
    if lstm_res:
        res_dict["lstm"] = lstm_res

    return res_dict
