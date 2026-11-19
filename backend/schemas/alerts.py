"""
DSFMP Fraud Detection — Fraud Alerts Pydantic Schemas

Defines request and response payloads for:
- Alert querying and detailed forensic dossiers
- Investigator acknowledgment and status progression
- Alert dismissal with verified false-positive feedback
- Single-click alert escalation into Case Management investigations
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AlertDismissReason(str, Enum):
    FALSE_POSITIVE = "FALSE_POSITIVE"
    LEGITIMATE_BULK_PURCHASE = "LEGITIMATE_BULK_PURCHASE"
    APPROVED_OFF_HOURS_OVERRIDE = "APPROVED_OFF_HOURS_OVERRIDE"
    ENROLLMENT_DISCREPANCY_RESOLVED = "ENROLLMENT_DISCREPANCY_RESOLVED"
    DATA_ENTRY_ERROR = "DATA_ENTRY_ERROR"


class AlertDismissRequest(BaseModel):
    """Payload for dismissing an alert as a verified non-fraud outcome."""
    reason_code: AlertDismissReason = Field(
        ...,
        description="Standardized ground-truth dismissal category"
    )
    notes: Optional[str] = Field(
        None,
        max_length=1000,
        description="Forensic notes or audit justification for dismissal"
    )


class AlertEscalateRequest(BaseModel):
    """Payload for converting an unassigned alert into a formal case."""
    case_title: Optional[str] = Field(
        None,
        max_length=255,
        description="Custom investigation title; defaults to alert title if omitted"
    )
    priority: Optional[str] = Field(
        None,
        description="Case priority override: LOW, MEDIUM, HIGH, CRITICAL"
    )
    notes: Optional[str] = Field(
        None,
        max_length=2000,
        description="Initial case comment or forensic context from investigator"
    )
    assigned_to: Optional[str] = Field(
        None,
        description="UUID or email of investigator to assign to the newly created case"
    )


class AlertActionResponse(BaseModel):
    """Standard response model for alert lifecycle actions."""
    success: bool = True
    alert_id: str
    status: str
    message: str
    case_id: Optional[str] = None
    case_ref: Optional[str] = None
    assigned_to: Optional[str] = None


class AlertEvidenceItem(BaseModel):
    """Individual feature deviation record supporting the fraud alert."""
    feature: str
    expected: str
    actual: str


class AlertDetailResponse(BaseModel):
    """Comprehensive single-alert forensic dossier."""
    id: str
    tier: str
    entityType: str
    entityId: str
    entityName: str
    alertType: str
    title: str
    description: str
    compositeScore: float
    modelScores: Dict[str, float]
    triggeredAt: str
    status: str
    assignedTo: str
    assignedToId: Optional[str] = None
    school: Optional[Dict[str, Any]] = None
    county: Optional[Dict[str, Any]] = None
    entityDetails: Optional[Dict[str, Any]] = None
    evidence: List[AlertEvidenceItem] = []
    blockchainHash: str = "N/A"
    auditTrail: List[Dict[str, Any]] = []
