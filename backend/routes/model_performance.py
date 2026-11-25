"""
DSFMP ML Model Performance & Inference Testing API Routes
Exposes endpoints to query model metrics and test live model inference.
"""

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from schemas.models import (
    InferenceRequest,
    InferenceResponse,
    ModelInfoResponse,
    EnsembleInferenceRequest,
    EnsembleInferenceResponse,
)
from ml.models.scoring_engine import (
    score_transaction_with_isolation_forest,
    score_transaction_with_autoencoder,
    score_transaction_with_lstm,
    score_transaction_ensemble,
    get_isolation_forest_model,
    get_autoencoder_model,
    get_lstm_model,
    DEFAULT_MODEL_PATH,
    DEFAULT_AE_MODEL_PATH,
    DEFAULT_LSTM_MODEL_PATH,
)
from config.settings import settings
from middleware.dependencies import get_current_user

router = APIRouter()


@router.get("/overview")
async def get_models_overview():
    """
    Returns deployment status, ensemble weights, and benchmarks for all system models.
    """
    artifact_exists = os.path.exists(DEFAULT_MODEL_PATH)
    ae_exists = os.path.exists(DEFAULT_AE_MODEL_PATH)
    lstm_exists = os.path.exists(DEFAULT_LSTM_MODEL_PATH)
    return {
        "weights": {
            "isolation_forest": settings.weight_isolation_forest,
            "autoencoder": settings.weight_autoencoder,
            "lstm": settings.weight_lstm,
        },
        "models": [
            {
                "id": "isolation-forest",
                "name": "Isolation Forest",
                "version": "v1.0.0",
                "deployed": "2026-04-15",
                "status": "HEALTHY" if artifact_exists else "OFFLINE",
                "threshold": 0.65,
                "weight": settings.weight_isolation_forest,
                "precision": 0.87,
                "recall": 0.82,
                "f1": 0.84,
                "roc_auc": 0.9422,
                "type": "Unsupervised Tabular Anomaly",
                "artifact_path": DEFAULT_MODEL_PATH,
                "is_active": True
            },
            {
                "id": "autoencoder",
                "name": "Autoencoder",
                "version": "v1.0.0",
                "deployed": "2026-11-11",
                "status": "HEALTHY" if ae_exists else "OFFLINE",
                "threshold": 0.70,
                "weight": settings.weight_autoencoder,
                "precision": 0.8909,
                "recall": 1.0000,
                "f1": 0.9423,
                "roc_auc": 1.0000,
                "pr_auc": 0.9999,
                "type": "Neural Reconstruction (MLP)",
                "artifact_path": DEFAULT_AE_MODEL_PATH,
                "is_active": ae_exists
            },
            {
                "id": "lstm",
                "name": "LSTM Autoencoder",
                "version": "v1.0.0",
                "deployed": "2026-11-11",
                "status": "HEALTHY" if lstm_exists else "OFFLINE",
                "threshold": 0.68,
                "weight": settings.weight_lstm,
                "precision": 0.5286,
                "recall": 0.7551,
                "f1": 0.6218,
                "roc_auc": 0.9743,
                "pr_auc": 0.5511,
                "type": "Temporal Sequence (PyTorch LSTM)",
                "artifact_path": DEFAULT_LSTM_MODEL_PATH,
                "is_active": lstm_exists
            },
            {
                "id": "xgboost",
                "name": "XGBoost Supervised",
                "version": "v4.1.0",
                "deployed": "2026-05-01",
                "status": "HEALTHY",
                "threshold": 0.75,
                "weight": 0.0,
                "precision": 0.94,
                "recall": 0.91,
                "f1": 0.92,
                "roc_auc": 0.9670,
                "type": "Supervised Classifier",
                "is_active": False
            }
        ]
    }


@router.get("/isolation-forest/info", response_model=ModelInfoResponse)
async def get_isolation_forest_info():
    """
    Returns metadata, hyperparameters, and feature requirements for the trained Isolation Forest model.
    """
    try:
        model = get_isolation_forest_model()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Isolation Forest artifact: {str(e)}")

    features = [
        "log_amount",
        "log_amount_per_student",
        "amount_to_school_avg_ratio",
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "is_off_hours",
        "rolling_24h_count",
        "log_rolling_24h_amount",
        "type",
        "payment_method"
    ]

    return ModelInfoResponse(
        id="isolation_forest_v1",
        name="Isolation Forest Tabular Anomaly Detector",
        version="v1.0.0",
        description="Detects anomalous school feeding fund disbursements, off-hours spikes, and supplier over-billing.",
        status="ACTIVE",
        deployed_at="2026-04-15 08:30:00",
        contamination=float(model.contamination),
        n_estimators=int(model.n_estimators),
        threshold=0.65,
        training_auc=0.9422,
        artifact_path=DEFAULT_MODEL_PATH,
        features=features
    )


@router.get("/autoencoder/info")
async def get_autoencoder_info():
    """
    Returns metadata, architecture, weights, and evaluation metrics for the trained Autoencoder model.
    """
    try:
        model = get_autoencoder_model()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Autoencoder artifact: {str(e)}")

    return {
        "id": "autoencoder_v1",
        "name": "MLP Bottleneck Autoencoder",
        "version": "v1.0.0",
        "description": "Unsupervised neural reconstruction detector tuned for round-number drains, structural ratio deviations, and atypical disbursements.",
        "status": "ACTIVE",
        "deployed_at": "2026-11-11 08:00:00",
        "architecture": list(model.hidden_layer_sizes),
        "threshold": 0.70,
        "weight": settings.weight_autoencoder,
        "roc_auc": 1.0000,
        "pr_auc": 0.9999,
        "precision": 0.8909,
        "recall": 1.0000,
        "f1": 0.9423,
        "artifact_path": DEFAULT_AE_MODEL_PATH,
        "features": list(getattr(model, "feature_names", None) or []),
    }


@router.get("/lstm/info")
async def get_lstm_info():
    """
    Returns metadata, sequence architecture, weights, and evaluation metrics for the trained LSTM Autoencoder model.
    """
    try:
        model = get_lstm_model()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load LSTM Autoencoder artifact: {str(e)}")

    metrics_path = os.path.join(
        os.path.dirname(DEFAULT_LSTM_MODEL_PATH), "lstm_autoencoder_v1_metrics.json"
    )
    metrics_data = {}
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception:
            pass

    return {
        "id": "lstm_autoencoder_v1",
        "name": "LSTM Autoencoder Temporal Sequence Detector",
        "version": "v1.0.0",
        "description": "Sequence-to-sequence recurrent bottleneck autoencoder profiling temporal cadence, burst smurfing, and school EWMA baseline shifts.",
        "status": "ACTIVE",
        "deployed_at": "2026-11-11 12:00:00",
        "seq_len": model.seq_len,
        "architecture": {
            "hidden_dim": model.hidden_dim,
            "latent_dim": model.latent_dim,
            "num_layers": model.num_layers,
        },
        "threshold": 0.68,
        "weight": settings.weight_lstm,
        "roc_auc": metrics_data.get("roc_auc", 0.9743),
        "pr_auc": metrics_data.get("pr_auc", 0.5511),
        "precision": metrics_data.get("precision", 0.5286),
        "recall": metrics_data.get("recall", 0.7551),
        "f1": metrics_data.get("f1", 0.6218),
        "artifact_path": DEFAULT_LSTM_MODEL_PATH,
        "features": list(getattr(model, "feature_names", None) or []),
    }


@router.get("/presets")
async def get_test_presets():
    """
    Returns curated test scenarios for front-end inference testing.
    """
    return {
        "presets": [
            {
                "id": "normal_subsidy",
                "name": "Normal Lunch Subsidy (Legitimate)",
                "description": "Mid-day school subsidy disbursement with 500 students and normal historical ratio.",
                "payload": {
                    "amount": 248750.0,
                    "type": "SUBSIDY_DISBURSEMENT",
                    "payment_method": "BANK_TRANSFER",
                    "transacted_at": "2026-10-29T12:15:00",
                    "student_count": 500,
                    "school_avg_amount": 240000.0,
                    "rolling_24h_count": 1,
                    "rolling_24h_amount": 248750.0,
                    "threshold": 0.65
                },
                "expected_outcome": "LOW RISK (Score < 0.30)"
            },
            {
                "id": "midnight_surge",
                "name": "Midnight Off-Hours Spike (Fraud)",
                "description": "High-value disbursement transacted at 2:30 AM via Cash, far outside standard banking hours.",
                "payload": {
                    "amount": 1850000.0,
                    "type": "SUPPLIER_PAYMENT",
                    "payment_method": "CASH",
                    "transacted_at": "2026-10-29T02:30:00",
                    "student_count": 250,
                    "school_avg_amount": 150000.0,
                    "rolling_24h_count": 3,
                    "rolling_24h_amount": 3200000.0,
                    "threshold": 0.65
                },
                "expected_outcome": "HIGH / CRITICAL ANOMALY (Score > 0.70)"
            },
            {
                "id": "ghost_students",
                "name": "Ghost Student Ratio Anomaly",
                "description": "Exorbitant disbursement allocated to a school with only 35 enrolled students (KES 45,000/student).",
                "payload": {
                    "amount": 1575000.0,
                    "type": "SUBSIDY_DISBURSEMENT",
                    "payment_method": "BANK_TRANSFER",
                    "transacted_at": "2026-10-29T11:00:00",
                    "student_count": 35,
                    "school_avg_amount": 120000.0,
                    "rolling_24h_count": 1,
                    "rolling_24h_amount": 1575000.0,
                    "threshold": 0.65
                },
                "expected_outcome": "HIGH ANOMALY (Score > 0.65)"
            },
            {
                "id": "velocity_smurfing",
                "name": "Rapid Multi-Disbursement Velocity",
                "description": "Rapid succession of 6 disbursements within 24 hours just below threshold to evade scrutiny.",
                "payload": {
                    "amount": 490000.0,
                    "type": "MPESA_PAYMENT",
                    "payment_method": "MPESA",
                    "transacted_at": "2026-10-29T15:45:00",
                    "student_count": 400,
                    "school_avg_amount": 200000.0,
                    "rolling_24h_count": 6,
                    "rolling_24h_amount": 2940000.0,
                    "threshold": 0.65
                },
                "expected_outcome": "ELEVATED RISK (Velocity Flagged)"
            },
            {
                "id": "round_number_drain",
                "name": "Round-Number Cash Drain (Autoencoder Target)",
                "description": "Exact round million KES 1,000,000 cash withdrawal outside typical school disbursement profile.",
                "payload": {
                    "amount": 1000000.0,
                    "type": "SUPPLIER_PAYMENT",
                    "payment_method": "CASH",
                    "transacted_at": "2026-10-29T18:30:00",
                    "student_count": 320,
                    "school_avg_amount": 180000.0,
                    "rolling_24h_count": 2,
                    "rolling_24h_amount": 1180000.0,
                    "threshold": 0.70
                },
                "expected_outcome": "HIGH / CRITICAL RECONSTRUCTION ANOMALY"
            }
        ]
    }


def _run_single_model_inference(scorer_fn, payload: InferenceRequest, default_threshold: float) -> InferenceResponse:
    """Shared inference wrapper for tabular anomaly models."""
    try:
        txn_dict = payload.model_dump()
        threshold = payload.threshold if payload.threshold is not None else default_threshold
        result = scorer_fn(transaction_data=txn_dict, threshold=threshold)
        return InferenceResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference execution failed: {str(e)}"
        )


@router.post("/isolation-forest/infer", response_model=InferenceResponse)
async def infer_isolation_forest(payload: InferenceRequest):
    """
    Executes live model inference on transaction data and returns calibrated anomaly risk.
    """
    return _run_single_model_inference(score_transaction_with_isolation_forest, payload, 0.65)


@router.post("/autoencoder/infer", response_model=InferenceResponse)
async def infer_autoencoder(payload: InferenceRequest):
    """
    Executes live neural reconstruction inference using the trained Autoencoder model.
    """
    return _run_single_model_inference(score_transaction_with_autoencoder, payload, 0.70)


@router.post("/lstm/infer", response_model=InferenceResponse)
async def infer_lstm(payload: InferenceRequest):
    """
    Executes live temporal sequence inference using the trained LSTM Autoencoder model.
    """
    return _run_single_model_inference(score_transaction_with_lstm, payload, 0.68)


@router.post("/ensemble/infer", response_model=EnsembleInferenceResponse)
async def infer_ensemble(payload: EnsembleInferenceRequest):
    """
    Executes Isolation Forest, Autoencoder, and LSTM inference and computes the weighted composite score.
    """
    try:
        txn_dict = payload.model_dump(exclude={"if_threshold", "ae_threshold", "lstm_threshold", "weights"})
        result = score_transaction_ensemble(
            transaction_data=txn_dict,
            if_threshold=payload.if_threshold if payload.if_threshold is not None else 0.65,
            ae_threshold=payload.ae_threshold if payload.ae_threshold is not None else 0.70,
            lstm_threshold=payload.lstm_threshold if payload.lstm_threshold is not None else 0.68,
            weights=payload.weights,
        )
        return EnsembleInferenceResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ensemble inference execution failed: {str(e)}"
        )

