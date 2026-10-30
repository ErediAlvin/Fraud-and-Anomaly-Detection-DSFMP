"""
DSFMP ML Model Performance & Inference Testing API Routes
Exposes endpoints to query model metrics and test live model inference.
"""

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from schemas.models import InferenceRequest, InferenceResponse, ModelInfoResponse
from ml.models.scoring_engine import (
    score_transaction_with_isolation_forest,
    get_isolation_forest_model,
    DEFAULT_MODEL_PATH
)
from middleware.dependencies import get_current_user

router = APIRouter()


@router.get("/overview")
async def get_models_overview():
    """
    Returns deployment status and summary benchmarks for all system models.
    """
    artifact_exists = os.path.exists(DEFAULT_MODEL_PATH)
    return {
        "models": [
            {
                "id": "isolation-forest",
                "name": "Isolation Forest",
                "version": "v1.0.0",
                "deployed": "2026-04-15",
                "status": "HEALTHY" if artifact_exists else "OFFLINE",
                "threshold": 0.65,
                "precision": 0.87,
                "recall": 0.82,
                "f1": 0.84,
                "roc_auc": 0.9422,
                "type": "Unsupervised Tabular Anomaly",
                "is_active": True
            },
            {
                "id": "autoencoder",
                "name": "Autoencoder",
                "version": "v3.0.2",
                "deployed": "2026-04-20",
                "status": "HEALTHY",
                "threshold": 0.70,
                "precision": 0.89,
                "recall": 0.85,
                "f1": 0.87,
                "roc_auc": 0.9250,
                "type": "Neural Reconstruction",
                "is_active": False
            },
            {
                "id": "lstm",
                "name": "LSTM Autoencoder",
                "version": "v1.8.1",
                "deployed": "2026-04-18",
                "status": "DRIFTING",
                "threshold": 0.68,
                "precision": 0.83,
                "recall": 0.79,
                "f1": 0.81,
                "roc_auc": 0.8910,
                "type": "Temporal Sequence",
                "is_active": False
            },
            {
                "id": "gnn",
                "name": "Graph Neural Network",
                "version": "v2.3.0",
                "deployed": "2026-04-22",
                "status": "HEALTHY",
                "threshold": 0.72,
                "precision": 0.92,
                "recall": 0.88,
                "f1": 0.90,
                "roc_auc": 0.9510,
                "type": "Relational Network",
                "is_active": False
            },
            {
                "id": "xgboost",
                "name": "XGBoost Supervised",
                "version": "v4.1.0",
                "deployed": "2026-05-01",
                "status": "HEALTHY",
                "threshold": 0.75,
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
                    "amount": 250000.0,
                    "type": "SUBSIDY_DISBURSEMENT",
                    "payment_method": "BANK_TRANSFER",
                    "transacted_at": "2026-10-29T12:15:00",
                    "student_count": 500,
                    "school_avg_amount": 240000.0,
                    "rolling_24h_count": 1,
                    "rolling_24h_amount": 250000.0,
                    "threshold": 0.65
                },
                "expected_outcome": "LOW RISK (Score < 0.25)"
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
            }
        ]
    }


@router.post("/isolation-forest/infer", response_model=InferenceResponse)
async def infer_isolation_forest(payload: InferenceRequest):
    """
    Executes live model inference on transaction data and returns calibrated anomaly risk.
    """
    try:
        txn_dict = payload.model_dump()
        result = score_transaction_with_isolation_forest(
            transaction_data=txn_dict,
            threshold=payload.threshold or 0.65
        )
        return InferenceResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inference execution failed: {str(e)}"
        )

