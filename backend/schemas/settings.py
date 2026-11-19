"""
DSFMP Fraud Detection — Settings Schemas

Pydantic models for system configurations, user administration,
and audit log responses.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ── System Configuration Categories ───────────────────

class GeneralSettings(BaseModel):
    system_name: str = "DSFMP Fraud Detection Module"
    version: str = "v2.1.4"
    environment: str = "PRODUCTION"
    default_county: str = "All Counties"
    session_timeout: int = 30
    email_notifications: bool = True
    in_app_notifications: bool = True
    sms_notifications: bool = False


class RiskThresholdSettings(BaseModel):
    model_threshold_if: float = Field(default=0.65, ge=0.0, le=1.0)
    model_threshold_ae: float = Field(default=0.70, ge=0.0, le=1.0)
    model_threshold_lstm: float = Field(default=0.69, ge=0.0, le=1.0)
    model_threshold_gnn: Optional[float] = Field(default=0.71, ge=0.0, le=1.0)
    weight_if: float = Field(default=0.40, ge=0.0, le=1.0)
    weight_ae: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_lstm: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_gnn: Optional[float] = Field(default=0.00, ge=0.0, le=1.0)
    threshold_critical: float = Field(default=0.80, ge=0.0, le=1.0)
    threshold_high: float = Field(default=0.60, ge=0.0, le=1.0)
    threshold_medium: float = Field(default=0.40, ge=0.0, le=1.0)
    threshold_low: float = Field(default=0.40, ge=0.0, le=1.0)


class BlockchainSettings(BaseModel):
    endpoint_url: str = "https://blockchain.dsfmp.go.ke:7051"
    channel_name: str = "dsfmp-channel"
    chaincode_name: str = "fraud-detection-cc"
    sync_interval: int = 60
    certificate_status: str = "VALID"
    certificate_expiry: str = "2027-05-12"


class ScheduleSettings(BaseModel):
    sob_time: str = "06:00"
    cob_time: str = "18:00"
    enable_scheduled_sob: bool = True
    enable_scheduled_cob: bool = True


class AlertSettings(BaseModel):
    email_alerts: bool = True
    in_app_alerts: bool = True
    sms_critical_only: bool = True
    auto_assign: bool = True
    escalation_timeout_hours: int = 24


class AllSettingsResponse(BaseModel):
    general: GeneralSettings
    thresholds: RiskThresholdSettings
    blockchain: BlockchainSettings
    schedule: ScheduleSettings
    alerts: AlertSettings


# ── User Administration Schemas ───────────────────────

class UserListItem(BaseModel):
    id: str
    name: str
    email: str
    role: str
    county: str = "All"
    status: str
    lastLogin: Optional[str] = None
    createdAt: str
    phone: Optional[str] = None


class UserCreateRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: str = "fraud_analyst"
    phone: Optional[str] = None
    county: Optional[str] = "All"


class UserUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# ── Audit Log Schemas ─────────────────────────────────

class AuditLogItem(BaseModel):
    id: int
    user_name: str
    user_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[Any] = None
    created_at: str
