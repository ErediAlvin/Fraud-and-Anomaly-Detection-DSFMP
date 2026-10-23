"""
DSFMP Fraud Detection — Case Management Pydantic Schemas

Validates payloads for:
- Creating investigations (manually or from alerts)
- Stage transitions and status updates
- Investigator assignment
- Collaborative case comments
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CaseStatusUpdateRequest(BaseModel):
    status: str = Field(
        ...,
        description=(
            "Target stage or status. Accepts UI stages (DETECTED, TRIAGED, UNDER INVESTIGATION, "
            "UNDER_INVESTIGATION, ESCALATED, RESOLVED) or DB enums (OPEN, PENDING_REVIEW, "
            "IN_PROGRESS, ESCALATED, CLOSED)."
        ),
    )
    closure_reason: Optional[str] = Field(
        None,
        description="Mandatory or recommended explanation when closing a case",
    )
    actual_loss: Optional[float] = Field(
        None,
        ge=0,
        description="Confirmed financial loss in KES upon case resolution",
    )


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Case title/summary")
    description: Optional[str] = Field("", description="Detailed investigation background")
    priority: Optional[str] = Field(
        "MEDIUM",
        description="Severity priority: LOW, MEDIUM, HIGH, CRITICAL",
    )
    category: Optional[str] = Field(
        "OTHER",
        description=(
            "Investigation domain: GHOST_BENEFICIARY, PAYMENT_FRAUD, "
            "SUPPLY_CHAIN, COLLUSION, DATA_TAMPERING, OTHER"
        ),
    )
    school_id: Optional[str] = Field(None, description="UUID of the school involved")
    county_id: Optional[int] = Field(None, description="ID of the county")
    assigned_to: Optional[str] = Field(None, description="UUID or email of investigator")
    estimated_loss: Optional[float] = Field(None, ge=0, description="Estimated financial impact in KES")
    alert_id: Optional[str] = Field(
        None,
        description="UUID of the source fraud alert if escalating directly from an alert",
    )


class CaseCommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Comment text or forensic update note")


class CaseAssignRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="UUID of the investigator to assign")
    email: Optional[str] = Field(None, description="Email of the investigator to assign")
