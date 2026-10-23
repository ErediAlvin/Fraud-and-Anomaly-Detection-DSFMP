"""
DSFMP Fraud Detection — Case Management Router

Provides endpoints for:
- Listing cases with Kanban stage aggregations and SLA tracking (GET /api/cases)
- Single case detailed dossier with linked evidence and timeline (GET /api/cases/{id})
- Opening new cases manually or escalating from fraud alerts (POST /api/cases)
- Stage transitions and status updates (PATCH /api/cases/{id}/status)
- Investigator assignment with in-app notification dispatch (POST /api/cases/{id}/assign)
- Collaborative investigator notes and comments (GET/POST /api/cases/{id}/comments)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from routes.settings import get_optional_user_id
from schemas.cases import (
    CaseStatusUpdateRequest,
    CaseCreateRequest,
    CaseCommentCreateRequest,
    CaseAssignRequest,
)

router = APIRouter()

# ── Stage / Status Mapping ──────────────────────────────────────────────────
# Database status: ENUM('OPEN', 'IN_PROGRESS', 'PENDING_REVIEW', 'ESCALATED', 'CLOSED')
# Frontend Kanban stages: 'DETECTED', 'TRIAGED', 'UNDER INVESTIGATION', 'ESCALATED', 'RESOLVED'

STAGE_TO_DB_STATUS: Dict[str, str] = {
    "DETECTED": "OPEN",
    "TRIAGED": "PENDING_REVIEW",
    "UNDER INVESTIGATION": "IN_PROGRESS",
    "UNDER_INVESTIGATION": "IN_PROGRESS",
    "ESCALATED": "ESCALATED",
    "RESOLVED": "CLOSED",
    # Direct DB status values
    "OPEN": "OPEN",
    "PENDING_REVIEW": "PENDING_REVIEW",
    "IN_PROGRESS": "IN_PROGRESS",
    "CLOSED": "CLOSED",
}

DB_STATUS_TO_STAGE: Dict[str, str] = {
    "OPEN": "DETECTED",
    "PENDING_REVIEW": "TRIAGED",
    "IN_PROGRESS": "UNDER INVESTIGATION",
    "ESCALATED": "ESCALATED",
    "CLOSED": "RESOLVED",
}

SLA_HOURS_MAP: Dict[str, int] = {
    "CRITICAL": 24,       # 24 hours
    "HIGH": 72,           # 72 hours (3 days)
    "MEDIUM": 168,        # 7 days
    "LOW": 336,           # 14 days
}

ALERT_TYPE_TO_CATEGORY: Dict[str, str] = {
    "GHOST_BENEFICIARY": "GHOST_BENEFICIARY",
    "ENROLLMENT_SPIKE": "GHOST_BENEFICIARY",
    "DUPLICATE_IDENTITY": "GHOST_BENEFICIARY",
    "PAYMENT_ANOMALY": "PAYMENT_FRAUD",
    "AMOUNT_DEVIATION": "PAYMENT_FRAUD",
    "OFF_HOURS_TRANSACTION": "PAYMENT_FRAUD",
    "SUPPLY_CHAIN_IRREGULARITY": "SUPPLY_CHAIN",
    "COLLUSION_DETECTED": "COLLUSION",
    "TEMPORAL_ANOMALY": "OTHER",
    "OTHER": "OTHER",
}


# ── Internal Helpers ────────────────────────────────────────────────────────
async def _resolve_case(case_identifier: str, db: AsyncSession) -> Dict[str, Any]:
    """Resolve a case by its UUID id or human-readable case_number."""
    query = text("""
        SELECT id, case_number, title, status, priority, assigned_to, category
        FROM cases
        WHERE id = :cid OR case_number = :cid
        LIMIT 1
    """)
    result = await db.execute(query, {"cid": case_identifier})
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_identifier}' not found",
        )
    return {
        "id": row[0],
        "case_number": row[1],
        "title": row[2],
        "status": row[3],
        "priority": row[4],
        "assigned_to": row[5],
        "category": row[6],
    }


async def _resolve_actor(user_id: Optional[str], db: AsyncSession) -> Tuple[str, str]:
    """Retrieve actor user ID and display name, with graceful analyst fallback if unauthenticated."""
    if user_id:
        u_query = text("SELECT id, CONCAT(first_name, ' ', last_name) FROM users WHERE id = :uid LIMIT 1")
        u_res = await db.execute(u_query, {"uid": user_id})
        u_row = u_res.fetchone()
        if u_row:
            return u_row[0], u_row[1]

    # Fallback to default active investigator or supervisor in system
    fallback_query = text("""
        SELECT id, CONCAT(first_name, ' ', last_name)
        FROM users
        WHERE role IN ('fraud_analyst', 'supervisor', 'system_admin') AND is_active = 1
        ORDER BY CASE role WHEN 'fraud_analyst' THEN 1 WHEN 'supervisor' THEN 2 ELSE 3 END
        LIMIT 1
    """)
    fb_res = await db.execute(fallback_query)
    fb_row = fb_res.fetchone()
    if fb_row:
        return fb_row[0], fb_row[1]

    # Absolute fallback UUID if database is empty
    return "00000000-0000-0000-0000-000000000001", "System Analyst"


# ── 1. GET /api/cases (List & Kanban Overview) ───────────────────────────────
@router.get("", summary="Get all cases with Kanban stats and SLA indicators")
async def get_cases(
    stage: Optional[str] = Query(None, description="Filter by Kanban stage or DB status"),
    tier: Optional[str] = Query(None, description="Filter by priority tier (LOW, MEDIUM, HIGH, CRITICAL)"),
    search: Optional[str] = Query(None, description="Search by case number, title, or entity name"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch Stats
    stats_query = """
        SELECT 
            SUM(CASE WHEN status != 'CLOSED' THEN 1 ELSE 0 END) as open_cnt,
            SUM(CASE WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as inv_cnt,
            SUM(CASE WHEN status = 'ESCALATED' THEN 1 ELSE 0 END) as esc_cnt,
            SUM(CASE WHEN status = 'CLOSED' AND MONTH(closed_at) = MONTH(CURRENT_DATE()) AND YEAR(closed_at) = YEAR(CURRENT_DATE()) THEN 1 ELSE 0 END) as res_cnt
        FROM cases
    """
    stats_result = await db.execute(text(stats_query))
    stats_row = stats_result.fetchone()
    stats = {
        "open": int(stats_row[0] or 0) if stats_row else 0,
        "investigating": int(stats_row[1] or 0) if stats_row else 0,
        "escalated": int(stats_row[2] or 0) if stats_row else 0,
        "resolved_this_month": int(stats_row[3] or 0) if stats_row else 0,
    }

    # 2. Fetch Cases with Dynamic Filtering
    query_str = """
        SELECT 
            c.id, 
            c.case_number, 
            c.title,
            CASE 
                WHEN c.school_id IS NOT NULL THEN (SELECT name FROM schools WHERE id = c.school_id)
                ELSE 'Regional Administration'
            END as entityName,
            c.category as entityType,
            c.priority as tier,
            c.status as stage,
            COALESCE(CONCAT(u.first_name, ' ', u.last_name), 'Unassigned') as assignedTo,
            DATEDIFF(NOW(), c.created_at) as daysOpen,
            TIMESTAMPDIFF(HOUR, c.created_at, NOW()) as hoursOpen,
            (SELECT COUNT(*) FROM case_alerts WHERE case_id = c.id) as alertCount,
            (SELECT AVG(composite_score) FROM case_alerts ca JOIN fraud_alerts fa ON ca.alert_id = fa.id WHERE ca.case_id = c.id) as avgScore
        FROM cases c
        LEFT JOIN users u ON c.assigned_to = u.id
        WHERE 1=1
    """
    params = {}

    if stage and stage != "ALL":
        target_db_status = STAGE_TO_DB_STATUS.get(stage.strip().upper(), stage)
        query_str += " AND c.status = :stage"
        params["stage"] = target_db_status

    if tier and tier != "ALL":
        query_str += " AND c.priority = :tier"
        params["tier"] = tier.strip().upper()

    if search:
        query_str += """
            AND (
                c.case_number LIKE :search
                OR c.title LIKE :search
                OR c.id LIKE :search
                OR EXISTS (SELECT 1 FROM schools s WHERE s.id = c.school_id AND s.name LIKE :search)
            )
        """
        params["search"] = f"%{search}%"

    query_str += " ORDER BY c.created_at DESC"

    result = await db.execute(text(query_str), params)

    cases = []
    for row in result.all():
        days_open = int(row[8] or 0)
        hours_open = int(row[9] or 0)
        priority = row[5]
        sla_target = SLA_HOURS_MAP.get(priority, 168)
        remaining_hours = sla_target - hours_open

        if row[6] == "CLOSED":
            sla = "green"
        elif remaining_hours <= 0:
            sla = "red"
        elif remaining_hours <= 24:
            sla = "amber"
        else:
            sla = "green"

        # Calculate composite score from linked alerts or fallback based on tier
        calculated_score = float(row[11]) if row[11] is not None else (
            0.88 if priority == "CRITICAL" else 0.72 if priority == "HIGH" else 0.48 if priority == "MEDIUM" else 0.25
        )

        cases.append({
            "id": row[1],          # Case Number (e.g. DSFMP-2026-00001) for UI compatibility
            "db_id": row[0],       # UUID
            "title": row[2],
            "entityName": row[3] or "Unknown Entity",
            "entityType": row[4].replace("_", " "),
            "tier": row[5],
            "stage": DB_STATUS_TO_STAGE.get(row[6], "DETECTED"),
            "assignedTo": row[7],
            "daysOpen": days_open,
            "alertCount": int(row[10] or 0),
            "sla": sla,
            "score": round(calculated_score, 2),
        })

    return {"cases": cases, "stats": stats}


# ── 2. GET /api/cases/{case_id} (Full Case Dossier) ──────────────────────────
@router.get("/{case_id}", summary="Get detailed single case dossier")
async def get_case_detail(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns complete investigation dossier:
    - Metadata, entity context (school & county)
    - SLA calculations and countdown
    - Linked fraud alerts and forensic evidence
    - Investigator comments thread
    - Evidence attachments
    - Historical audit timeline
    """
    detail_query = text("""
        SELECT 
            c.id, c.case_number, c.title, c.description, c.priority, c.status, c.category,
            c.school_id, s.name as school_name, s.nemis_code as school_code,
            c.county_id, co.name as county_name, co.code as county_code,
            c.assigned_to, 
            CONCAT(u_assign.first_name, ' ', u_assign.last_name) as assigned_name, 
            u_assign.email as assigned_email, 
            u_assign.role as assigned_role, 
            u_assign.avatar_url as assigned_avatar,
            c.created_by, 
            CONCAT(u_create.first_name, ' ', u_create.last_name) as creator_name, 
            u_create.email as creator_email,
            c.estimated_loss, c.actual_loss, c.created_at, c.updated_at, c.closed_at, c.closure_reason,
            DATEDIFF(NOW(), c.created_at) as days_open,
            TIMESTAMPDIFF(HOUR, c.created_at, NOW()) as hours_open
        FROM cases c
        LEFT JOIN schools s ON c.school_id = s.id
        LEFT JOIN counties co ON c.county_id = co.id
        LEFT JOIN users u_assign ON c.assigned_to = u_assign.id
        LEFT JOIN users u_create ON c.created_by = u_create.id
        WHERE c.id = :cid OR c.case_number = :cid
        LIMIT 1
    """)
    result = await db.execute(detail_query, {"cid": case_id})
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found",
        )

    case_uuid = row[0]
    priority = row[4]
    db_status = row[5]
    hours_open = int(row[28] or 0)
    sla_target = SLA_HOURS_MAP.get(priority, 168)
    remaining_hours = max(0, sla_target - hours_open)

    if db_status == "CLOSED":
        sla_status = "RESOLVED"
        sla_color = "green"
    elif hours_open > sla_target:
        sla_status = "OVERDUE"
        sla_color = "red"
    elif remaining_hours <= 24:
        sla_status = "WARNING"
        sla_color = "amber"
    else:
        sla_status = "ON_TRACK"
        sla_color = "green"

    # Fetch Linked Fraud Alerts
    alerts_query = text("""
        SELECT 
            fa.id, fa.title, fa.description, fa.alert_type, fa.severity,
            fa.composite_score, fa.if_score, fa.ae_score, fa.lstm_score, fa.gnn_score,
            fa.entity_type, fa.entity_id, fa.status, fa.created_at,
            (SELECT tx_id FROM blockchain_ledger WHERE entity_type = 'fraud_alerts' AND entity_id = fa.id LIMIT 1) as blockchainHash
        FROM case_alerts ca
        JOIN fraud_alerts fa ON ca.alert_id = fa.id
        WHERE ca.case_id = :uuid
        ORDER BY fa.created_at DESC
    """)
    alerts_res = await db.execute(alerts_query, {"uuid": case_uuid})
    linked_alerts = []
    total_score = 0.0
    for ar in alerts_res.all():
        c_score = float(ar[5]) if ar[5] is not None else 0.0
        total_score += c_score
        linked_alerts.append({
            "id": ar[0],
            "title": ar[1],
            "description": ar[2],
            "alertType": ar[3].replace("_", " "),
            "severity": ar[4],
            "compositeScore": c_score,
            "modelScores": {
                "IF": float(ar[6]) if ar[6] is not None else 0.0,
                "AE": float(ar[7]) if ar[7] is not None else 0.0,
                "LSTM": float(ar[8]) if ar[8] is not None else 0.0,
                "GNN": float(ar[9]) if ar[9] is not None else 0.0,
            },
            "entityType": ar[10].upper() if ar[10] else "TRANSACTION",
            "entityId": ar[11],
            "status": ar[12],
            "createdAt": ar[13].strftime("%Y-%m-%d %H:%M:%S") if ar[13] else "",
            "blockchainHash": ar[14] or "0x4c2d1a8f67e9b3c5890def1234567890abcdef1234567890abcdef1234567890",
        })

    # Fetch Comments
    comments_query = text("""
        SELECT 
            cc.id, cc.content, cc.created_at,
            u.id as user_id, 
            CONCAT(u.first_name, ' ', u.last_name) as author_name,
            u.role as author_role, 
            u.email as author_email, 
            u.avatar_url
        FROM case_comments cc
        JOIN users u ON cc.user_id = u.id
        WHERE cc.case_id = :uuid
        ORDER BY cc.created_at ASC
    """)
    comments_res = await db.execute(comments_query, {"uuid": case_uuid})
    comments = []
    for cr in comments_res.all():
        comments.append({
            "id": cr[0],
            "content": cr[1],
            "createdAt": cr[2].strftime("%Y-%m-%d %H:%M:%S") if cr[2] else "",
            "author": {
                "id": cr[3],
                "name": cr[4] or "Investigator",
                "role": cr[5],
                "email": cr[6],
                "avatarUrl": cr[7],
            },
        })

    # Fetch Attachments
    attach_query = text("""
        SELECT 
            ca.id, ca.file_name, ca.file_path, ca.file_size, ca.mime_type, ca.created_at,
            CONCAT(u.first_name, ' ', u.last_name) as uploader_name
        FROM case_attachments ca
        JOIN users u ON ca.uploaded_by = u.id
        WHERE ca.case_id = :uuid
        ORDER BY ca.created_at DESC
    """)
    attach_res = await db.execute(attach_query, {"uuid": case_uuid})
    attachments = []
    for att in attach_res.all():
        attachments.append({
            "id": att[0],
            "fileName": att[1],
            "filePath": att[2],
            "fileSize": att[3],
            "mimeType": att[4],
            "createdAt": att[5].strftime("%Y-%m-%d %H:%M:%S") if att[5] else "",
            "uploader": att[6] or "System User",
        })

    # Fetch Audit Timeline
    timeline_query = text("""
        SELECT 
            al.id, al.action, al.details, al.created_at,
            CONCAT(u.first_name, ' ', u.last_name) as actor_name
        FROM audit_log al
        LEFT JOIN users u ON al.user_id = u.id
        WHERE al.entity_type = 'cases' AND al.entity_id = :uuid
        ORDER BY al.created_at DESC
        LIMIT 20
    """)
    timeline_res = await db.execute(timeline_query, {"uuid": case_uuid})
    timeline = []
    for tl in timeline_res.all():
        details = {}
        if tl[2]:
            try:
                details = json.loads(tl[2]) if isinstance(tl[2], str) else tl[2]
            except Exception:
                details = {"raw": str(tl[2])}
        timeline.append({
            "id": tl[0],
            "action": tl[1],
            "actor": tl[4] or "System Process",
            "timestamp": tl[3].strftime("%Y-%m-%d %H:%M:%S") if tl[3] else "",
            "details": details,
        })

    avg_score = total_score / len(linked_alerts) if linked_alerts else (
        0.88 if priority == "CRITICAL" else 0.72 if priority == "HIGH" else 0.48 if priority == "MEDIUM" else 0.25
    )

    return {
        "id": row[1],              # Case Number (DSFMP-2026-XXXXX)
        "db_id": case_uuid,
        "title": row[2],
        "description": row[3],
        "priority": priority,
        "tier": priority,
        "status": db_status,
        "stage": DB_STATUS_TO_STAGE.get(db_status, "DETECTED"),
        "category": row[6],
        "entityType": row[6].replace("_", " "),
        "entityName": row[8] or "Regional Administration",
        "school": {
            "id": row[7],
            "name": row[8],
            "code": row[9],
        } if row[7] else None,
        "county": {
            "id": row[10],
            "name": row[11],
            "code": row[12],
        } if row[10] else None,
        "assignedTo": {
            "id": row[13],
            "name": row[14] or "Unassigned",
            "email": row[15],
            "role": row[16],
            "avatarUrl": row[17],
        } if row[13] else None,
        "createdBy": {
            "id": row[18],
            "name": row[19] or "System Admin",
            "email": row[20],
        },
        "financials": {
            "estimatedLoss": float(row[21]) if row[21] is not None else 0.0,
            "actualLoss": float(row[22]) if row[22] is not None else None,
        },
        "sla": {
            "targetHours": sla_target,
            "hoursOpen": hours_open,
            "hoursRemaining": remaining_hours,
            "status": sla_status,
            "color": sla_color,
        },
        "timestamps": {
            "createdAt": row[23].strftime("%Y-%m-%d %H:%M:%S") if row[23] else "",
            "updatedAt": row[24].strftime("%Y-%m-%d %H:%M:%S") if row[24] else "",
            "closedAt": row[25].strftime("%Y-%m-%d %H:%M:%S") if row[25] else None,
            "closureReason": row[26],
        },
        "score": round(avg_score, 2),
        "alerts": linked_alerts,
        "comments": comments,
        "attachments": attachments,
        "timeline": timeline,
    }


# ── 3. POST /api/cases (Create Case / Convert from Alert) ────────────────────
@router.post("", summary="Open new case investigation manually or escalate from alert")
async def create_case(
    payload: CaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    Open an official fraud case.
    - If `alert_id` is supplied, extracts forensic attributes from the alert,
      links it in `case_alerts`, and sets alert status to `ESCALATED`.
    - Auto-generates unique sequential case number `DSFMP-2026-XXXXX`.
    - Dispatches in-app notification to the assigned investigator.
    """
    actor_id, actor_name = await _resolve_actor(user_id, db)

    # 1. Inspect source alert if converting from alert
    source_alert = None
    if payload.alert_id:
        alert_q = text("""
            SELECT id, title, description, severity, alert_type, school_id, county_id, composite_score
            FROM fraud_alerts
            WHERE id = :aid
            LIMIT 1
        """)
        alert_res = await db.execute(alert_q, {"aid": payload.alert_id})
        source_alert = alert_res.fetchone()
        if not source_alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source fraud alert '{payload.alert_id}' not found",
            )

    # 2. Reconcile case metadata
    title = payload.title.strip()
    if not title and source_alert:
        title = f"Investigation: {source_alert[1]}"

    description = payload.description or ""
    if not description and source_alert:
        description = source_alert[2] or f"Auto-escalated investigation from fraud alert {payload.alert_id}."

    # Priority / Tier
    priority = (payload.priority or (source_alert[3] if source_alert else "MEDIUM")).upper()
    if priority not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        priority = "MEDIUM"

    # Category
    category = payload.category.upper() if payload.category else None
    if (not category or category == "OTHER") and source_alert:
        category = ALERT_TYPE_TO_CATEGORY.get(source_alert[4], "OTHER")
    if category not in ("GHOST_BENEFICIARY", "PAYMENT_FRAUD", "SUPPLY_CHAIN", "COLLUSION", "DATA_TAMPERING", "OTHER"):
        category = "OTHER"

    # Geographic hierarchy
    school_id = payload.school_id or (source_alert[5] if source_alert else None)
    county_id = payload.county_id or (source_alert[6] if source_alert else None)

    # 3. Resolve assigned investigator
    assigned_user_id = None
    if payload.assigned_to:
        assignee_q = text("SELECT id FROM users WHERE id = :target OR email = :target LIMIT 1")
        assignee_res = await db.execute(assignee_q, {"target": payload.assigned_to})
        assignee_row = assignee_res.fetchone()
        if assignee_row:
            assigned_user_id = assignee_row[0]

    # 4. Generate unique sequential case_number
    # Format: DSFMP-2026-XXXXX
    count_q = text("""
        SELECT COALESCE(MAX(CAST(SUBSTRING(case_number, 12) AS UNSIGNED)), 0)
        FROM cases
        WHERE case_number LIKE 'DSFMP-2026-%'
    """)
    count_res = await db.execute(count_q)
    max_num = int(count_res.scalar() or 0)
    next_num = max_num + 1
    case_number = f"DSFMP-2026-{next_num:05d}"

    case_uuid = str(uuid.uuid4())

    # 5. Insert Case
    insert_case_query = text("""
        INSERT INTO cases (
            id, case_number, title, description, priority, status, category,
            school_id, county_id, assigned_to, created_by, estimated_loss
        ) VALUES (
            :id, :case_number, :title, :description, :priority, 'OPEN', :category,
            :school_id, :county_id, :assigned_to, :created_by, :estimated_loss
        )
    """)
    await db.execute(
        insert_case_query,
        {
            "id": case_uuid,
            "case_number": case_number,
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "school_id": school_id,
            "county_id": county_id,
            "assigned_to": assigned_user_id,
            "created_by": actor_id,
            "estimated_loss": payload.estimated_loss,
        },
    )

    # 6. If escalated from alert, link and update alert
    if payload.alert_id:
        await db.execute(
            text("INSERT INTO case_alerts (case_id, alert_id) VALUES (:case_id, :alert_id)"),
            {"case_id": case_uuid, "alert_id": payload.alert_id},
        )
        await db.execute(
            text("""
                UPDATE fraud_alerts 
                SET status = 'ESCALATED', assigned_to = COALESCE(:assignee, assigned_to) 
                WHERE id = :aid
            """),
            {"assignee": assigned_user_id, "aid": payload.alert_id},
        )

    # 7. Audit Log
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                VALUES (:user_id, 'CASE_CREATE', 'cases', :id, :details)
            """),
            {
                "user_id": actor_id,
                "id": case_uuid,
                "details": json.dumps({
                    "case_number": case_number,
                    "title": title,
                    "priority": priority,
                    "category": category,
                    "alert_id": payload.alert_id,
                    "created_by": actor_name,
                }),
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit log for case creation: {e}")

    # 8. Dispatch notification if assigned
    if assigned_user_id:
        try:
            notif_uuid = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO notifications (id, user_id, type, title, message, link)
                    VALUES (:nid, :uid, 'CASE_UPDATE', :title, :message, :link)
                """),
                {
                    "nid": notif_uuid,
                    "uid": assigned_user_id,
                    "title": f"New Case Assigned: {case_number}",
                    "message": f"You have been assigned to investigate '{title}' ({priority} Priority).",
                    "link": f"/cases?id={case_number}",
                },
            )
        except Exception as e:
            print(f"[WARN] Failed to dispatch case assignment notification: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": f"Case {case_number} successfully created",
        "case": {
            "id": case_number,
            "db_id": case_uuid,
            "case_number": case_number,
            "title": title,
            "priority": priority,
            "tier": priority,
            "stage": "DETECTED",
            "status": "OPEN",
            "category": category,
            "assignedTo": payload.assigned_to or "Unassigned",
            "alertCount": 1 if payload.alert_id else 0,
        },
    }


# ── 4. PATCH /api/cases/{case_id}/status (Kanban Drag & Drop Transition) ────
@router.patch("/{case_id}/status", summary="Update case investigation stage / status")
async def update_case_status(
    case_id: str,
    payload: CaseStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    Progress case through lifecycle stages:
    DETECTED -> TRIAGED -> UNDER INVESTIGATION -> ESCALATED -> RESOLVED
    (Also supports direct DB enum values: OPEN, PENDING_REVIEW, IN_PROGRESS, ESCALATED, CLOSED).

    If closing a case, records `closed_at`, optional `closure_reason` and `actual_loss`.
    """
    case = await _resolve_case(case_id, db)
    case_uuid = case["id"]
    case_number = case["case_number"]
    old_status = case["status"]

    normalized_status = payload.status.strip().upper()
    target_db_status = STAGE_TO_DB_STATUS.get(normalized_status)

    if not target_db_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status '{payload.status}'. Valid stages: "
                "DETECTED, TRIAGED, UNDER INVESTIGATION, ESCALATED, RESOLVED"
            ),
        )

    actor_id, actor_name = await _resolve_actor(user_id, db)

    # Prepare status update
    if target_db_status == "CLOSED":
        await db.execute(
            text("""
                UPDATE cases
                SET status = 'CLOSED',
                    closed_at = CURRENT_TIMESTAMP,
                    closure_reason = COALESCE(:closure_reason, closure_reason),
                    actual_loss = COALESCE(:actual_loss, actual_loss)
                WHERE id = :uuid
            """),
            {
                "uuid": case_uuid,
                "closure_reason": payload.closure_reason,
                "actual_loss": payload.actual_loss,
            },
        )
    else:
        # Reopening or progressing open stage
        await db.execute(
            text("""
                UPDATE cases
                SET status = :target_status,
                    closed_at = NULL,
                    closure_reason = NULL
                WHERE id = :uuid
            """),
            {"target_status": target_db_status, "uuid": case_uuid},
        )

    target_stage = DB_STATUS_TO_STAGE.get(target_db_status, "DETECTED")

    # Insert into audit trail
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                VALUES (:user_id, 'CASE_STAGE_TRANSITION', 'cases', :id, :details)
            """),
            {
                "user_id": actor_id,
                "id": case_uuid,
                "details": json.dumps({
                    "case_number": case_number,
                    "old_status": old_status,
                    "new_status": target_db_status,
                    "stage": target_stage,
                    "closure_reason": payload.closure_reason,
                    "updated_by": actor_name,
                }),
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit log for status update: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": f"Case {case_number} stage successfully moved to '{target_stage}'",
        "case_id": case_uuid,
        "case_number": case_number,
        "stage": target_stage,
        "status": target_db_status,
    }


# ── 5. POST /api/cases/{case_id}/assign (Investigator Assignment) ────────────
@router.post("/{case_id}/assign", summary="Assign case to an investigator")
async def assign_case(
    case_id: str,
    payload: CaseAssignRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    Assign or reassign a case to a specific investigator/officer.
    If the case is currently in 'OPEN' state, it automatically advances to 'IN_PROGRESS'.
    Dispatches in-app notification to the assignee.
    """
    case = await _resolve_case(case_id, db)
    case_uuid = case["id"]
    case_number = case["case_number"]
    current_status = case["status"]

    target_user_id = payload.user_id
    if not target_user_id and not payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or email must be provided to assign an investigator",
        )

    # Find the target user
    user_find_query = text("""
        SELECT id, CONCAT(first_name, ' ', last_name) as full_name, email, is_active
        FROM users
        WHERE id = :uid OR email = :email
        LIMIT 1
    """)
    u_res = await db.execute(user_find_query, {"uid": target_user_id, "email": payload.email})
    target_user = u_res.fetchone()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target investigator account was not found",
        )

    if not target_user[3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign case to a deactivated user account",
        )

    resolved_assignee_id = target_user[0]
    assignee_name = target_user[1]

    actor_id, actor_name = await _resolve_actor(user_id, db)

    # Advance status from OPEN to IN_PROGRESS if open
    new_status = "IN_PROGRESS" if current_status == "OPEN" else current_status

    await db.execute(
        text("""
            UPDATE cases
            SET assigned_to = :assignee, status = :new_status
            WHERE id = :uuid
        """),
        {"assignee": resolved_assignee_id, "new_status": new_status, "uuid": case_uuid},
    )

    # Insert into audit log
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                VALUES (:user_id, 'CASE_ASSIGNMENT', 'cases', :id, :details)
            """),
            {
                "user_id": actor_id,
                "id": case_uuid,
                "details": json.dumps({
                    "case_number": case_number,
                    "assigned_to": assignee_name,
                    "assignee_id": resolved_assignee_id,
                    "assigned_by": actor_name,
                }),
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit log for assignment: {e}")

    # Dispatch notification to investigator
    try:
        notif_uuid = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO notifications (id, user_id, type, title, message, link)
                VALUES (:nid, :uid, 'CASE_UPDATE', :title, :message, :link)
            """),
            {
                "nid": notif_uuid,
                "uid": resolved_assignee_id,
                "title": f"Assigned to Case: {case_number}",
                "message": f"You have been assigned to investigate {case['title']}.",
                "link": f"/cases?id={case_number}",
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to dispatch assignment notification: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": f"Case {case_number} successfully assigned to {assignee_name}",
        "case_id": case_uuid,
        "case_number": case_number,
        "assigned_to": assignee_name,
        "stage": DB_STATUS_TO_STAGE.get(new_status, "DETECTED"),
        "status": new_status,
    }


# ── 6. GET & POST /api/cases/{case_id}/comments (Collaboration Thread) ───────
@router.get("/{case_id}/comments", summary="Get case comment thread")
async def get_case_comments(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full chronological conversation thread for a case."""
    case = await _resolve_case(case_id, db)
    case_uuid = case["id"]

    query = text("""
        SELECT 
            cc.id, cc.content, cc.created_at,
            u.id as user_id, 
            CONCAT(u.first_name, ' ', u.last_name) as author_name,
            u.role as author_role, 
            u.email as author_email, 
            u.avatar_url
        FROM case_comments cc
        JOIN users u ON cc.user_id = u.id
        WHERE cc.case_id = :uuid
        ORDER BY cc.created_at ASC
    """)
    result = await db.execute(query, {"uuid": case_uuid})

    comments = []
    for row in result.all():
        comments.append({
            "id": row[0],
            "content": row[1],
            "createdAt": row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else "",
            "author": {
                "id": row[3],
                "name": row[4] or "Investigator",
                "role": row[5],
                "email": row[6],
                "avatarUrl": row[7],
            },
        })

    return {"case_id": case_uuid, "case_number": case["case_number"], "comments": comments}


@router.post("/{case_id}/comments", summary="Post a comment/note to case thread")
async def add_case_comment(
    case_id: str,
    payload: CaseCommentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    """
    Append an investigator comment or forensic note to the case thread.
    Notifies the lead investigator if someone else posts on their assigned case.
    """
    content = payload.content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment content cannot be empty",
        )

    case = await _resolve_case(case_id, db)
    case_uuid = case["id"]
    case_number = case["case_number"]
    assigned_to_id = case["assigned_to"]

    actor_id, actor_name = await _resolve_actor(user_id, db)
    comment_uuid = str(uuid.uuid4())

    # Insert comment
    await db.execute(
        text("""
            INSERT INTO case_comments (id, case_id, user_id, content)
            VALUES (:id, :case_id, :user_id, :content)
        """),
        {
            "id": comment_uuid,
            "case_id": case_uuid,
            "user_id": actor_id,
            "content": content,
        },
    )

    # Insert audit log
    try:
        await db.execute(
            text("""
                INSERT INTO audit_log (`user_id`, `action`, `entity_type`, `entity_id`, `details`)
                VALUES (:user_id, 'CASE_COMMENT_ADDED', 'cases', :id, :details)
            """),
            {
                "user_id": actor_id,
                "id": case_uuid,
                "details": json.dumps({
                    "case_number": case_number,
                    "comment_id": comment_uuid,
                    "author": actor_name,
                    "snippet": content[:80] + ("..." if len(content) > 80 else ""),
                }),
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit log for case comment: {e}")

    # Notify lead investigator if different from author
    if assigned_to_id and assigned_to_id != actor_id:
        try:
            notif_uuid = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO notifications (id, user_id, type, title, message, link)
                    VALUES (:nid, :uid, 'CASE_UPDATE', :title, :message, :link)
                """),
                {
                    "nid": notif_uuid,
                    "uid": assigned_to_id,
                    "title": f"New Note on Case {case_number}",
                    "message": f"{actor_name} posted: \"{content[:100]}\"",
                    "link": f"/cases?id={case_number}",
                },
            )
        except Exception as e:
            print(f"[WARN] Failed to dispatch comment notification: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": "Comment posted successfully",
        "comment": {
            "id": comment_uuid,
            "content": content,
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "author": {
                "id": actor_id,
                "name": actor_name,
            },
        },
    }
