"""
DSFMP Fraud Detection — Settings & Administration Router

Provides endpoints for:
- Reading and updating categorized system configuration
- User administration (listing, creating, updating roles/status)
- Audit log tracking
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from jose import JWTError

from config.security import hash_password, decode_token
from config.settings import settings as app_settings
from database.connection import get_db
from schemas.settings import (
    AllSettingsResponse,
    GeneralSettings,
    RiskThresholdSettings,
    BlockchainSettings,
    ScheduleSettings,
    AlertSettings,
    UserCreateRequest,
    UserUpdateRequest,
)

router = APIRouter()
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_optional_user_id(
    token: Optional[str] = Depends(optional_oauth2_scheme)
) -> Optional[str]:
    """Helper to extract user ID from JWT if present, without failing if missing."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None


# ── Default Configurations ────────────────────────────

DEFAULT_SETTINGS: Dict[str, Dict[str, Any]] = {
    "general": {
        "system_name": "DSFMP Fraud Detection Module",
        "version": "v2.1.4",
        "environment": "PRODUCTION",
        "default_county": "All Counties",
        "session_timeout": 30,
        "email_notifications": True,
        "in_app_notifications": True,
        "sms_notifications": False,
    },
    "thresholds": {
        "model_threshold_if": 0.65,
        "model_threshold_ae": 0.70,
        "model_threshold_lstm": 0.69,
        "model_threshold_gnn": 0.71,
        "weight_if": 0.40,
        "weight_ae": 0.30,
        "weight_lstm": 0.30,
        "weight_gnn": 0.00,
        "threshold_critical": 0.80,
        "threshold_high": 0.60,
        "threshold_medium": 0.40,
        "threshold_low": 0.40,
    },
    "blockchain": {
        "endpoint_url": "https://blockchain.dsfmp.go.ke:7051",
        "channel_name": "dsfmp-channel",
        "chaincode_name": "fraud-detection-cc",
        "sync_interval": 60,
        "certificate_status": "VALID",
        "certificate_expiry": "2027-05-12",
    },
    "schedule": {
        "sob_time": "06:00",
        "cob_time": "18:00",
        "enable_scheduled_sob": True,
        "enable_scheduled_cob": True,
    },
    "alerts": {
        "email_alerts": True,
        "in_app_alerts": True,
        "sms_critical_only": True,
        "auto_assign": True,
        "escalation_timeout_hours": 24,
    },
}


def cast_value(val: str, default_val: Any) -> Any:
    """Cast string stored in MySQL text column to appropriate Python type."""
    if isinstance(default_val, bool):
        return val.lower() in ("true", "1", "t", "yes")
    elif isinstance(default_val, int):
        try:
            return int(val)
        except ValueError:
            return default_val
    elif isinstance(default_val, float):
        try:
            return float(val)
        except ValueError:
            return default_val
    return val


# ── System Settings Endpoints ─────────────────────────

@router.get("", response_model=AllSettingsResponse, summary="Get all system settings")
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    """Retrieve all categorized settings from database with fallback to defaults."""
    result = await db.execute(text("SELECT `key`, `value`, `category` FROM system_settings"))
    rows = result.all()

    # Build dictionary grouped by category
    db_values: Dict[str, Dict[str, str]] = {}
    for k, v, cat in rows:
        category = cat.lower() if cat else "general"
        if category not in db_values:
            db_values[category] = {}
        db_values[category][k] = v

    response_data = {}
    for cat_name, defaults in DEFAULT_SETTINGS.items():
        cat_db = db_values.get(cat_name, {})
        category_obj = {}
        for key, default_val in defaults.items():
            if key in cat_db:
                category_obj[key] = cast_value(cat_db[key], default_val)
            else:
                category_obj[key] = default_val
        response_data[cat_name] = category_obj

    return AllSettingsResponse(
        general=GeneralSettings(**response_data["general"]),
        thresholds=RiskThresholdSettings(**response_data["thresholds"]),
        blockchain=BlockchainSettings(**response_data["blockchain"]),
        schedule=ScheduleSettings(**response_data["schedule"]),
        alerts=AlertSettings(**response_data["alerts"]),
    )


@router.put("/{category}", summary="Update settings for a category")
async def update_category_settings(
    category: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """Save key-value settings for a category and log to audit_log."""
    cat_lower = category.lower()
    if cat_lower not in DEFAULT_SETTINGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category '{category}'. Allowed: {list(DEFAULT_SETTINGS.keys())}",
        )

    # Upsert each key in MySQL
    for key, value in payload.items():
        val_str = str(value).lower() if isinstance(value, bool) else str(value)
        await db.execute(
            text("""
                INSERT INTO system_settings (`key`, `value`, `category`, `updated_by`)
                VALUES (:key, :value, :category, :user_id)
                ON DUPLICATE KEY UPDATE
                    `value` = VALUES(`value`),
                    `category` = VALUES(`category`),
                    `updated_by` = VALUES(`updated_by`),
                    `updated_at` = CURRENT_TIMESTAMP
            """),
            {
                "key": key,
                "value": val_str,
                "category": cat_lower,
                "user_id": user_id,
            },
        )

    # Record in audit_log
    try:
        details_json = json.dumps(payload)
        await db.execute(
            text("""
                INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                VALUES (:user_id, 'SETTINGS_UPDATE', 'system_settings', :category, :details)
            """),
            {
                "user_id": user_id,
                "category": cat_lower,
                "details": details_json,
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": f"{category.capitalize()} settings updated successfully",
        "category": cat_lower,
        "data": payload,
    }


# ── User Administration Endpoints ─────────────────────

@router.get("/users", summary="List all system users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """Fetch user accounts for the User Management tab."""
    result = await db.execute(
        text("""
            SELECT id, first_name, last_name, email, role, is_active, phone, last_login_at, created_at
            FROM users
            ORDER BY created_at DESC
        """)
    )

    users = []
    for row in result.all():
        u_id, fname, lname, email, role, active, phone, last_login, created_at = row
        users.append({
            "id": u_id,
            "name": f"{fname} {lname}",
            "firstName": fname,
            "lastName": lname,
            "email": email,
            "role": role.replace("_", " ").title(),
            "rawRole": role,
            "county": "All",
            "status": "ACTIVE" if active else "INACTIVE",
            "isActive": bool(active),
            "phone": phone or "N/A",
            "lastLogin": last_login.strftime("%Y-%m-%d %H:%M") if last_login else "Never",
            "createdAt": created_at.strftime("%Y-%m-%d %H:%M") if created_at else "",
        })

    return users


@router.post("/users", status_code=status.HTTP_201_CREATED, summary="Create a new user")
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """Create a new user account with hashed password and role assignment."""
    # Check email duplicate
    existing = await db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": request.email.strip().lower()},
    )
    if existing.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Normalize role
    allowed_roles = ["fraud_analyst", "county_officer", "system_admin", "supervisor", "school_admin"]
    norm_role = request.role.lower().replace(" ", "_")
    if norm_role not in allowed_roles:
        norm_role = "fraud_analyst"

    new_id = str(uuid.uuid4())
    pw_hash = hash_password(request.password)

    await db.execute(
        text("""
            INSERT INTO users (id, email, password_hash, first_name, last_name, role, phone, is_active)
            VALUES (:id, :email, :password_hash, :first_name, :last_name, :role, :phone, 1)
        """),
        {
            "id": new_id,
            "email": request.email.strip().lower(),
            "password_hash": pw_hash,
            "first_name": request.first_name.strip(),
            "last_name": request.last_name.strip(),
            "role": norm_role,
            "phone": request.phone.strip() if request.phone else None,
        },
    )

    # Log action
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                VALUES (:user_id, 'USER_CREATE', 'users', :new_id, :details)
            """),
            {
                "user_id": user_id,
                "new_id": new_id,
                "details": json.dumps({"email": request.email, "role": norm_role}),
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": "User created successfully",
        "user": {
            "id": new_id,
            "name": f"{request.first_name} {request.last_name}",
            "email": request.email,
            "role": norm_role.replace("_", " ").title(),
            "rawRole": norm_role,
            "status": "ACTIVE",
            "isActive": True,
            "phone": request.phone or "N/A",
            "lastLogin": "Never",
        },
    }


@router.patch("/users/{target_user_id}", summary="Update user role or active status")
async def update_user(
    target_user_id: str,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """Update role or activate/deactivate an existing user."""
    check = await db.execute(
        text("SELECT id, email, role, is_active FROM users WHERE id = :id"),
        {"id": target_user_id},
    )
    user_row = check.fetchone()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updates = []
    params: Dict[str, Any] = {"id": target_user_id}

    if payload.role is not None:
        norm_role = payload.role.lower().replace(" ", "_")
        updates.append("role = :role")
        params["role"] = norm_role

    if payload.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = 1 if payload.is_active else 0

    if payload.phone is not None:
        updates.append("phone = :phone")
        params["phone"] = payload.phone

    if payload.first_name is not None:
        updates.append("first_name = :first_name")
        params["first_name"] = payload.first_name

    if payload.last_name is not None:
        updates.append("last_name = :last_name")
        params["last_name"] = payload.last_name

    if updates:
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = :id"
        await db.execute(text(sql), params)

        # Audit log
        try:
            await db.execute(
                text("""
                    INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                    VALUES (:user_id, 'USER_UPDATE', 'users', :target_id, :details)
                """),
                {
                    "user_id": user_id,
                    "target_id": target_user_id,
                    "details": json.dumps(payload.model_dump(exclude_unset=True)),
                },
            )
        except Exception as e:
            print(f"[WARN] Failed to write audit log: {e}")

        await db.commit()

    return {"status": "success", "message": "User updated successfully"}


# ── Audit Log Endpoints ───────────────────────────────

@router.get("/audit-log", summary="Get system audit log")
async def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Fetch system audit log trail."""
    result = await db.execute(
        text(f"""
            SELECT 
                al.id,
                COALESCE(CONCAT(u.first_name, ' ', u.last_name), 'System User') as user_name,
                u.email as user_email,
                al.action,
                al.entity_type,
                al.entity_id,
                al.details,
                al.created_at
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.created_at DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )

    logs = []
    for row in result.all():
        log_id, u_name, u_email, action, e_type, e_id, details, created_at = row
        logs.append({
            "id": log_id,
            "userName": u_name,
            "userEmail": u_email or "system@dsfmp.go.ke",
            "action": action,
            "entityType": e_type or "N/A",
            "entityId": str(e_id) if e_id else "N/A",
            "details": details,
            "createdAt": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "",
        })

    return logs
