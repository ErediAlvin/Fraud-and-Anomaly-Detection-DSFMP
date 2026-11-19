"""
DSFMP ML Model Schemas
Pydantic schemas for model information, status, and interactive inference testing.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class InferenceRequest(BaseModel):
    """Payload to test model inference on a simulated or historical transaction."""
    amount: float = Field(..., description="Transaction amount in KES", ge=0.0)
    type: str = Field("SUPPLIER_PAYMENT", description="Transaction type")
    payment_method: str = Field("BANK_TRANSFER", description="Payment method: BANK_TRANSFER, MPESA, CASH, CHEQUE")
    transacted_at: Optional[str] = Field(None, description="ISO timestamp or date string")
    student_count: Optional[int] = Field(500, description="School enrollment count", ge=1)
    school_avg_amount: Optional[float] = Field(None, description="Average school disbursement amount")
    rolling_24h_count: Optional[int] = Field(1, description="Number of transactions for school/payer in last 24h", ge=1)
    rolling_24h_amount: Optional[float] = Field(None, description="Cumulative amount in last 24h")
    threshold: Optional[float] = Field(0.65, description="Anomaly classification threshold", ge=0.0, le=1.0)


class InferenceResponse(BaseModel):
    """Inference output returned to frontend tester."""
    model_name: str
    model_version: str
    anomaly_score: float
    is_anomaly: bool
    risk_tier: str
    threshold: float
    latency_ms: float
    reasons: List[str]
    features_extracted: Dict[str, Any]
    reconstruction_drivers: Optional[List[Dict[str, Any]]] = None


class EnsembleInferenceRequest(InferenceRequest):
    """Payload for combined multi-model weighted ensemble scoring."""
    if_threshold: Optional[float] = Field(0.65, ge=0.0, le=1.0)
    ae_threshold: Optional[float] = Field(0.70, ge=0.0, le=1.0)
    lstm_threshold: Optional[float] = Field(0.68, ge=0.0, le=1.0)
    weights: Optional[Dict[str, float]] = None


class EnsembleBreakdownItem(BaseModel):
    id: str
    name: str
    status: str
    score: float
    configured_weight: float
    effective_weight: float
    weighted_contribution: float
    effective_contribution: float


class EnsembleInferenceResponse(BaseModel):
    """Weighted ensemble inference response combining active models."""
    composite_score: float
    raw_weighted_sum: float
    risk_tier: str
    is_anomaly: bool
    total_latency_ms: float
    weights: Dict[str, float]
    breakdown: List[EnsembleBreakdownItem]
    isolation_forest: InferenceResponse
    autoencoder: InferenceResponse
    lstm: Optional[InferenceResponse] = None
    reasons: List[str]
    features_extracted: Dict[str, Any]


class ModelInfoResponse(BaseModel):
    """Model metadata, hyperparams, and deployment metrics."""
    id: str
    name: str
    version: str
    description: str
    status: str
    deployed_at: str
    contamination: float
    n_estimators: int
    threshold: float
    training_auc: float
    artifact_path: str
    features: List[str]

