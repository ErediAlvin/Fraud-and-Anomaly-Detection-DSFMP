"""
DSFMP Transaction Schemas
Pydantic schemas for transaction ingestion and batch ingestion pipelines.
"""

from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field


class TransactionIngestRequest(BaseModel):
    school_id: str = Field(..., description="Target School UUID")
    supplier_id: Optional[str] = Field(None, description="Optional Supplier UUID")
    amount: float = Field(..., gt=0.0, description="Transaction amount in KES")
    type: str = Field("SUPPLIER_PAYMENT", description="Transaction type (SUBSIDY, PROCUREMENT, MPESA, etc.)")
    payment_method: str = Field("BANK_TRANSFER", description="Payment method: BANK_TRANSFER, MPESA, CHEQUE, CASH, SYSTEM")
    transacted_at: Optional[Union[datetime, str]] = Field(None, description="ISO timestamp or date string")
    description: Optional[str] = Field(None, description="Human-readable description or remarks")
    reference_no: Optional[str] = Field(None, description="External reference number (e.g. M-Pesa code, Bank Ref)")
    currency: Optional[str] = Field("KES", description="Currency code")


class TransactionIngestResponse(BaseModel):
    transaction_id: str
    status: str = "QUEUED_FOR_SCORING"
    risk_tier: str = "EVALUATING"
    message: str = "Transaction successfully queued for 3-model anomaly scoring."


class BatchIngestResponse(BaseModel):
    total_submitted: int
    batch_id: str
    status: str = "PROCESSING"
    message: str = "Batch submitted and queued for background ensemble scoring."
