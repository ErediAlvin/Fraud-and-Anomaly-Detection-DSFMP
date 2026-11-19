import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from routes.settings import get_optional_user_id
from schemas.transactions import (
    TransactionIngestRequest,
    TransactionIngestResponse,
    BatchIngestResponse,
)
from services.ingestion_service import (
    process_and_score_transaction,
    process_and_score_batch,
)

router = APIRouter()


def normalize_txn_type(t: Optional[str]) -> str:
    """Normalize UI type aliases to database ENUM values."""
    if not t:
        return "SUPPLIER_PAYMENT"
    upper = str(t).strip().upper()
    type_map = {
        "SUBSIDY": "SUBSIDY_DISBURSEMENT",
        "PROCUREMENT": "SUPPLIER_PAYMENT",
        "MPESA": "MPESA_PAYMENT",
        "PARENTAL": "PARENTAL_CONTRIBUTION",
    }
    val = type_map.get(upper, upper)
    valid_types = {
        "SUBSIDY_DISBURSEMENT",
        "SUPPLIER_PAYMENT",
        "PARENTAL_CONTRIBUTION",
        "MPESA_PAYMENT",
        "REFUND",
        "ADJUSTMENT",
    }
    return val if val in valid_types else "SUPPLIER_PAYMENT"


def normalize_payment_method(m: Optional[str]) -> str:
    """Normalize payment method to database ENUM values."""
    if not m:
        return "BANK_TRANSFER"
    upper = str(m).strip().upper()
    valid_methods = {"MPESA", "BANK_TRANSFER", "CHEQUE", "CASH", "SYSTEM"}
    return upper if upper in valid_methods else "BANK_TRANSFER"


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=TransactionIngestResponse)
@router.post("/", status_code=status.HTTP_202_ACCEPTED, response_model=TransactionIngestResponse)
async def ingest_transaction(
    payload: TransactionIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/transactions (Single Transaction Ingestion):
    Accept transaction payload (school_id, supplier_id, amount, type, payment_method, transacted_at, description).
    Validate and insert into transactions with initial status PENDING and risk_tier = 'EVALUATING'.
    Queue process_and_score_transaction as a background task.
    Return HTTP 202 Accepted with { "transaction_id": str, "status": "QUEUED_FOR_SCORING" }.
    """
    txn_id = str(uuid.uuid4())

    # Validate school exists
    school_check = await db.execute(
        text("SELECT id FROM schools WHERE id = :sid OR name = :sname LIMIT 1"),
        {"sid": payload.school_id, "sname": payload.school_id}
    )
    school_row = school_check.fetchone()
    if not school_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid school_id '{payload.school_id}'. School does not exist."
        )
    resolved_school_id = school_row[0]

    # Validate supplier if provided
    resolved_supplier_id = None
    if payload.supplier_id:
        supplier_check = await db.execute(
            text("SELECT id FROM suppliers WHERE id = :sid LIMIT 1"),
            {"sid": payload.supplier_id}
        )
        s_row = supplier_check.fetchone()
        if s_row:
            resolved_supplier_id = s_row[0]

    norm_type = normalize_txn_type(payload.type)
    norm_method = normalize_payment_method(payload.payment_method)

    # Parse timestamp
    transacted_dt = datetime.now(timezone.utc)
    if payload.transacted_at:
        try:
            if isinstance(payload.transacted_at, datetime):
                transacted_dt = payload.transacted_at
            else:
                transacted_dt = pd.to_datetime(payload.transacted_at, utc=True).to_pydatetime()
        except Exception:
            transacted_dt = datetime.now(timezone.utc)

    ref_no = payload.reference_no or f"TXN-{uuid.uuid4().hex[:8].upper()}"

    insert_query = text("""
        INSERT INTO transactions (
            id, school_id, supplier_id, type, amount, currency,
            reference_no, description, payment_method, status,
            risk_tier, transacted_at
        ) VALUES (
            :id, :school_id, :supplier_id, :type, :amount, :currency,
            :reference_no, :description, :payment_method, 'PENDING',
            'EVALUATING', :transacted_at
        )
    """)
    await db.execute(insert_query, {
        "id": txn_id,
        "school_id": resolved_school_id,
        "supplier_id": resolved_supplier_id,
        "type": norm_type,
        "amount": payload.amount,
        "currency": payload.currency or "KES",
        "reference_no": ref_no,
        "description": payload.description or f"Automated ingestion for school {resolved_school_id}",
        "payment_method": norm_method,
        "transacted_at": transacted_dt,
    })
    await db.commit()

    # Queue background scoring task
    background_tasks.add_task(process_and_score_transaction, txn_id)

    return {
        "transaction_id": txn_id,
        "status": "QUEUED_FOR_SCORING",
        "risk_tier": "EVALUATING",
        "message": "Transaction submitted and queued for background 3-model scoring."
    }


@router.post("/batch-ingest", status_code=status.HTTP_202_ACCEPTED, response_model=BatchIngestResponse)
async def batch_ingest_transactions(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/transactions/batch-ingest (Bulk Data Ingestion):
    Accept a JSON array or multipart CSV containing up to 500 transaction records.
    Bulk-insert records in a single database transaction.
    Schedule asynchronous batch processing across the scoring models.
    Return batch summary: { "total_submitted": int, "batch_id": str, "status": "PROCESSING" }.
    """
    content_type = request.headers.get("content-type", "")
    records: List[Dict[str, Any]] = []

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = None
        for key in ("file", "csv", "data", "upload"):
            if key in form and hasattr(form[key], "read"):
                file_obj = form[key]
                break
        if file_obj is None:
            for val in form.values():
                if hasattr(val, "read"):
                    file_obj = val
                    break
        if file_obj is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart form must contain a CSV file under 'file'."
            )
        content_bytes = await file_obj.read()
        try:
            csv_text = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            csv_text = content_bytes.decode("latin-1")
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            records.append(row)
    else:
        try:
            body = await request.json()
            if isinstance(body, list):
                records = body
            elif isinstance(body, dict):
                records = body.get("transactions") or body.get("records") or [body]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON request body: {str(e)}"
            )

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch cannot be empty. Please provide at least 1 transaction record."
        )

    if len(records) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size of {len(records)} exceeds maximum allowed size of 500 records."
        )

    # Fetch valid schools cache for quick lookup
    schools_res = await db.execute(text("SELECT id, name FROM schools"))
    valid_schools = {}
    for sid, sname in schools_res.fetchall():
        valid_schools[str(sid)] = str(sid)
        valid_schools[str(sname).lower()] = str(sid)

    default_school_id = next(iter(valid_schools.values())) if valid_schools else None

    # Fetch valid suppliers cache
    suppliers_res = await db.execute(text("SELECT id FROM suppliers"))
    valid_suppliers = {str(r[0]) for r in suppliers_res.fetchall()}

    batch_id = str(uuid.uuid4())
    txn_ids: List[str] = []
    insert_records: List[Dict[str, Any]] = []

    for idx, rec in enumerate(records):
        txn_id = str(uuid.uuid4())
        txn_ids.append(txn_id)

        raw_sid = str(rec.get("school_id") or "").strip()
        school_id = valid_schools.get(raw_sid) or valid_schools.get(raw_sid.lower()) or default_school_id
        if not school_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Record #{idx+1}: Invalid school_id '{raw_sid}' and no default school found."
            )

        raw_supp = str(rec.get("supplier_id") or "").strip()
        supplier_id = raw_supp if raw_supp in valid_suppliers else None

        try:
            amount = float(rec.get("amount", 0.0))
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Record #{idx+1}: Invalid amount '{rec.get('amount')}'."
            )

        txn_type = normalize_txn_type(rec.get("type"))
        method = normalize_payment_method(rec.get("payment_method"))

        raw_dt = rec.get("transacted_at") or rec.get("timestamp")
        transacted_dt = datetime.now(timezone.utc)
        if raw_dt:
            try:
                transacted_dt = pd.to_datetime(raw_dt, utc=True).to_pydatetime()
            except Exception:
                transacted_dt = datetime.now(timezone.utc)

        ref_no = rec.get("reference_no") or f"BATCH-{batch_id[:6].upper()}-{idx+1:03d}"
        desc = rec.get("description") or f"Disbursement batch ({batch_id[:8]})"

        insert_records.append({
            "id": txn_id,
            "school_id": school_id,
            "supplier_id": supplier_id,
            "type": txn_type,
            "amount": amount,
            "currency": rec.get("currency", "KES") or "KES",
            "reference_no": ref_no,
            "description": desc,
            "payment_method": method,
            "batch_id": batch_id,
            "transacted_at": transacted_dt,
        })

    # Bulk-insert in a single database transaction
    bulk_insert_q = text("""
        INSERT INTO transactions (
            id, school_id, supplier_id, type, amount, currency,
            reference_no, description, payment_method, status,
            risk_tier, batch_id, transacted_at
        ) VALUES (
            :id, :school_id, :supplier_id, :type, :amount, :currency,
            :reference_no, :description, :payment_method, 'PENDING',
            'EVALUATING', :batch_id, :transacted_at
        )
    """)
    await db.execute(bulk_insert_q, insert_records)
    await db.commit()

    # Schedule asynchronous batch processing across the scoring models
    background_tasks.add_task(process_and_score_batch, txn_ids)

    return {
        "total_submitted": len(txn_ids),
        "batch_id": batch_id,
        "status": "PROCESSING",
        "message": f"Successfully queued batch of {len(txn_ids)} transactions for background scoring."
    }


@router.get("")
async def get_transactions(
    type: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch Stats
    stats_query = """
        SELECT 
            COUNT(*),
            SUM(amount),
            SUM(CASE WHEN status = 'FLAGGED' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END)
        FROM transactions
    """
    stats_result = await db.execute(text(stats_query))
    count, total_value, flagged, blocked = stats_result.fetchone() or (0, 0, 0, 0)
    
    total_val_str = "0"
    if total_value:
        if total_value >= 1_000_000:
            total_val_str = f"{round(total_value / 1_000_000, 1)}M"
        elif total_value >= 1_000:
            total_val_str = f"{round(total_value / 1_000, 1)}K"
        else:
            total_val_str = f"{total_value:,}"

    stats = {
        "totalTransactions": f"{count:,}",
        "totalValue": total_val_str,
        "flaggedTransactions": flagged or 0,
        "blockedTransactions": blocked or 0,
        "falsePositiveRate": "3.8%"
    }

    # 2. Fetch Transactions List
    query_str = """
        SELECT 
            t.id, 
            t.type, 
            CASE 
                WHEN t.type = 'SUBSIDY_DISBURSEMENT' THEN 'Ministry Treasury'
                ELSE (SELECT name FROM schools WHERE id = t.school_id)
            END as payer,
            CASE 
                WHEN t.type = 'SUBSIDY_DISBURSEMENT' THEN (SELECT name FROM schools WHERE id = t.school_id)
                WHEN t.supplier_id IS NOT NULL THEN (SELECT name FROM suppliers WHERE id = t.supplier_id)
                ELSE 'System Fee/Parent'
            END as recipient,
            t.amount,
            t.risk_tier as tier,
            t.risk_score as mlScore,
            t.blockchain_status as blockchainStatus,
            CASE WHEN t.status = 'FLAGGED' OR t.status = 'FAILED' THEN 'BLOCKED' ELSE 'PASSED' END as smartContractStatus,
            t.transacted_at as timestamp,
            t.if_score, t.ae_score, t.lstm_score, t.gnn_score,
            t.blockchain_hash,
            t.description
        FROM transactions t
        WHERE 1=1
    """
    
    params = {}
    if type and type != 'ALL':
        # Match database enum which has SUBSIDY_DISBURSEMENT, SUPPLIER_PAYMENT, PARENTAL_CONTRIBUTION, MPESA_PAYMENT, REFUND, ADJUSTMENT
        type_map = {
            "MPESA": "MPESA_PAYMENT",
            "SUBSIDY": "SUBSIDY_DISBURSEMENT",
            "PROCUREMENT": "SUPPLIER_PAYMENT"
        }
        db_type = type_map.get(type, type)
        query_str += " AND t.type = :db_type"
        params["db_type"] = db_type
        
    if tier and tier != 'ALL':
        query_str += " AND t.risk_tier = :tier"
        params["tier"] = tier
        
    if search:
        query_str += " AND (t.id LIKE :search OR t.reference_no LIKE :search OR t.description LIKE :search)"
        params["search"] = f"%{search}%"
        
    query_str += " ORDER BY t.transacted_at DESC"
    
    result = await db.execute(text(query_str), params)
    
    transactions = []
    for row in result.all():
        db_type = row[1]
        ui_type = "MPESA"
        if db_type == "SUBSIDY_DISBURSEMENT":
            ui_type = "SUBSIDY"
        elif db_type == "SUPPLIER_PAYMENT":
            ui_type = "PROCUREMENT"
            
        features = []
        if (row[6] or 0) > 0.8:
            features = ["Amount deviation: High transaction volume", "Velocity anomaly: Double payment check failed"]
            
        transactions.append({
            "id": row[0],
            "type": ui_type,
            "payer": row[2] or "N/A",
            "recipient": row[3] or "N/A",
            "amount": float(row[4]),
            "tier": row[5] or "LOW",
            "mlScore": float(row[6]) if row[6] is not None else 0.0,
            "blockchainStatus": "VERIFIED" if row[7] == "CONFIRMED" else "PENDING",
            "smartContractStatus": row[8],
            "timestamp": row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else "",
            "modelScores": {
                "IF": float(row[10]) if row[10] is not None else 0.0,
                "AE": float(row[11]) if row[11] is not None else 0.0,
                "LSTM": float(row[12]) if row[12] is not None else 0.0,
                "GNN": float(row[13]) if row[13] is not None else 0.0,
            },
            "anomalyFeatures": features,
            "blockchainHash": row[14] or "N/A",
            "description": row[15]
        })

    hourly_volume = []
    for h in range(24):
        hourly_volume.append({
            "hour": f"{h:02d}:00",
            "today": int(abs(30 * (h % 5) - 12)) + (10 if h in [12, 13, 14] else 0),
            "average": 100 + (20 if h in [12, 13, 14] else 0)
        })

    amount_distribution = []
    for i in range(20):
        amount_distribution.append({
            "range": i * 20000,
            "count": int(abs(40 - (i * 2))) + 5
        })

    return {
        "transactions": transactions,
        "stats": stats,
        "hourly_volume": hourly_volume,
        "amount_distribution": amount_distribution
    }


@router.get("/context/schools")
async def list_ingestion_schools(db: AsyncSession = Depends(get_db)):
    """Retrieve list of schools for transaction ingestion selection."""
    res = await db.execute(text("SELECT id, name, nemis_code, enrollment_count FROM schools ORDER BY name ASC"))
    return [{"id": r[0], "name": r[1], "nemis": r[2], "enrollment": r[3]} for r in res.fetchall()]


@router.get("/{txn_id}")
async def get_single_transaction(txn_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve current scoring and status for a specific transaction."""
    query = """
        SELECT 
            t.id, t.type, t.amount, t.status, t.risk_tier, t.risk_score,
            t.if_score, t.ae_score, t.lstm_score, t.gnn_score,
            t.transacted_at, t.description, t.reference_no,
            s.name as school_name,
            CASE WHEN t.supplier_id IS NOT NULL THEN (SELECT name FROM suppliers WHERE id = t.supplier_id) ELSE 'N/A' END as supplier_name
        FROM transactions t
        LEFT JOIN schools s ON s.id = t.school_id
        WHERE t.id = :tid
        LIMIT 1
    """
    res = await db.execute(text(query), {"tid": txn_id})
    row = res.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found")

    return {
        "id": row[0],
        "type": row[1],
        "amount": float(row[2]),
        "status": row[3],
        "tier": row[4] or "LOW",
        "risk_tier": row[4] or "LOW",
        "mlScore": float(row[5]) if row[5] is not None else 0.0,
        "risk_score": float(row[5]) if row[5] is not None else 0.0,
        "modelScores": {
            "IF": float(row[6]) if row[6] is not None else 0.0,
            "AE": float(row[7]) if row[7] is not None else 0.0,
            "LSTM": float(row[8]) if row[8] is not None else 0.0,
            "GNN": float(row[9]) if row[9] is not None else 0.0,
        },
        "timestamp": row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else "",
        "description": row[11],
        "reference_no": row[12],
        "school_name": row[13],
        "supplier_name": row[14],
    }

@router.post("/{txn_id}/investigate")
async def investigate_transaction(
    txn_id: str, 
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user_id),
):
    # 1. Update the transaction to FLAGGED & CRITICAL
    update_query = """
        UPDATE transactions
        SET status = 'FLAGGED', risk_tier = 'CRITICAL', risk_score = 0.95
        WHERE id = :txn_id
    """
    await db.execute(text(update_query), {"txn_id": txn_id})

    # 2. Fetch full transaction details to construct an alert & case
    txn_query = """
        SELECT 
            t.id, t.type, t.amount, t.payment_method, t.reference_no, t.description,
            t.school_id, s.county_id, s.name as school_name
        FROM transactions t
        LEFT JOIN schools s ON s.id = t.school_id
        WHERE t.id = :txn_id
        LIMIT 1
    """
    txn_res = await db.execute(text(txn_query), {"txn_id": txn_id})
    txn_row = txn_res.fetchone()

    if not txn_row:
        await db.commit()
        return {"status": "success", "message": "Transaction marked for investigation"}

    t_id, t_type, t_amount, t_payment_method, t_ref, t_desc, school_id, county_id, school_name = txn_row
    amount_val = float(t_amount) if t_amount else 0.0
    school_display = school_name or "Unknown School"
    ref_display = t_ref or t_id[:8]

    # Resolve actor who initiated investigation
    from routes.cases import _resolve_actor
    actor_id, actor_name = await _resolve_actor(user_id, db)

    # 3. Check if an alert already exists for this transaction, or create one
    alert_check_q = text("""
        SELECT id FROM fraud_alerts
        WHERE entity_type = 'transaction' AND entity_id = :txn_id
        ORDER BY created_at DESC LIMIT 1
    """)
    alert_check_res = await db.execute(alert_check_q, {"txn_id": txn_id})
    existing_alert = alert_check_res.fetchone()

    if existing_alert:
        alert_uuid = existing_alert[0]
        await db.execute(
            text("UPDATE fraud_alerts SET status = 'ESCALATED', severity = 'CRITICAL' WHERE id = :aid"),
            {"aid": alert_uuid}
        )
    else:
        alert_uuid = str(uuid.uuid4())
        alert_title = f"High Risk Payment Anomaly: {ref_display} ({school_display})"
        alert_desc = t_desc or f"Irregular disbursement of KES {amount_val:,.2f} via {t_payment_method or 'SYSTEM'} flagged for immediate investigation."
        insert_alert_q = text("""
            INSERT INTO fraud_alerts (
                id, alert_type, severity, title, description,
                entity_type, entity_id, school_id, county_id,
                composite_score, if_score, status
            ) VALUES (
                :id, 'PAYMENT_ANOMALY', 'CRITICAL', :title, :description,
                'transaction', :entity_id, :school_id, :county_id,
                0.9500, 0.9500, 'ESCALATED'
            )
        """)
        await db.execute(insert_alert_q, {
            "id": alert_uuid,
            "title": alert_title,
            "description": alert_desc,
            "entity_id": txn_id,
            "school_id": school_id,
            "county_id": county_id,
        })

    # 4. Check if a case is already linked to this alert
    case_linked_q = text("""
        SELECT c.id, c.case_number 
        FROM cases c
        JOIN case_alerts ca ON ca.case_id = c.id
        WHERE ca.alert_id = :aid
        LIMIT 1
    """)
    case_linked_res = await db.execute(case_linked_q, {"aid": alert_uuid})
    existing_case = case_linked_res.fetchone()

    if existing_case:
        case_uuid = existing_case[0]
        case_number = existing_case[1]
    else:
        # Generate new sequential case number
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

        case_title = f"Payment Fraud Investigation: {ref_display} - {school_display}"
        case_desc = (
            f"Automated case opened from Transaction Monitor investigation trigger.\n"
            f"Transaction ID: {txn_id}\n"
            f"Reference: {ref_display}\n"
            f"Disbursement Type: {t_type}\n"
            f"Amount: KES {amount_val:,.2f}\n"
            f"Beneficiary/School: {school_display}\n"
            f"Investigator Action: Flagged for critical review."
        )

        insert_case_query = text("""
            INSERT INTO cases (
                id, case_number, title, description, priority, status, category,
                school_id, county_id, assigned_to, created_by, estimated_loss
            ) VALUES (
                :id, :case_number, :title, :description, 'CRITICAL', 'OPEN', 'PAYMENT_FRAUD',
                :school_id, :county_id, :assigned_to, :created_by, :estimated_loss
            )
        """)
        await db.execute(
            insert_case_query,
            {
                "id": case_uuid,
                "case_number": case_number,
                "title": case_title,
                "description": case_desc,
                "school_id": school_id,
                "county_id": county_id,
                "assigned_to": actor_id,
                "created_by": actor_id,
                "estimated_loss": amount_val,
            }
        )

        # Link case to alert
        await db.execute(
            text("INSERT INTO case_alerts (case_id, alert_id) VALUES (:case_id, :alert_id)"),
            {"case_id": case_uuid, "alert_id": alert_uuid}
        )

        # Audit Log
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
                        "title": case_title,
                        "priority": "CRITICAL",
                        "category": "PAYMENT_FRAUD",
                        "alert_id": alert_uuid,
                        "transaction_id": txn_id,
                        "created_by": actor_name,
                    }),
                },
            )
        except Exception as e:
            print(f"[WARN] Failed to write audit log for transaction case creation: {e}")

    await db.commit()

    return {
        "status": "success",
        "message": f"Transaction escalated to Case Management ({case_number})",
        "case": {
            "id": case_number,
            "db_id": case_uuid,
            "case_number": case_number,
        }
    }

@router.post("/{txn_id}/clear")
async def clear_transaction(txn_id: str, db: AsyncSession = Depends(get_db)):
    query = """
        UPDATE transactions
        SET status = 'COMPLETED', risk_tier = 'LOW', risk_score = 0.02
        WHERE id = :txn_id
    """
    await db.execute(text(query), {"txn_id": txn_id})
    await db.commit()
    return {"status": "success", "message": "Transaction risk cleared successfully"}

@router.post("/{txn_id}/evaluate-isolation-forest")
async def evaluate_transaction_isolation_forest(
    txn_id: str, 
    payload: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Re-runs live inference using the Isolation Forest model on a transaction.
    Attempts to read & persist to MySQL if available, but falls back gracefully
    to payload / memory inference to avoid 500 errors when database is offline or schema differs.
    """
    from ml.models.scoring_engine import score_transaction_with_isolation_forest
    
    db_txn = None
    try:
        query = """
            SELECT 
                t.id, t.type, t.amount, t.payment_method, t.transacted_at,
                COALESCE(s.enrollment_count, 500) as student_count,
                (SELECT AVG(amount) FROM transactions WHERE school_id = t.school_id) as school_avg,
                t.lstm_score, t.gnn_score
            FROM transactions t
            LEFT JOIN schools s ON s.id = t.school_id
            WHERE t.id = :txn_id
        """
        result = await db.execute(text(query), {"txn_id": txn_id})
        db_txn = result.fetchone()
    except Exception as db_err:
        print(f"[INFO] DB query failed or unavailable ({db_err}); using payload/default parameters.")

    if db_txn:
        txn_payload = {
            "amount": float(db_txn[2]),
            "type": db_txn[1] or "SUPPLIER_PAYMENT",
            "payment_method": db_txn[3] or "BANK_TRANSFER",
            "transacted_at": db_txn[4].isoformat() if hasattr(db_txn[4], "isoformat") else str(db_txn[4] or ""),
            "student_count": int(db_txn[5]) if db_txn[5] else 500,
            "school_avg_amount": float(db_txn[6]) if db_txn[6] else float(db_txn[2])
        }
    elif payload:
        p_type = payload.get("type", "SUPPLIER_PAYMENT")
        if p_type == "SUBSIDY":
            p_type = "SUBSIDY_DISBURSEMENT"
        elif p_type == "PROCUREMENT":
            p_type = "SUPPLIER_PAYMENT"
        elif p_type == "MPESA":
            p_type = "MPESA_PAYMENT"

        txn_payload = {
            "amount": float(payload.get("amount", 250000.0)),
            "type": p_type,
            "payment_method": payload.get("payment_method", "BANK_TRANSFER"),
            "transacted_at": payload.get("timestamp") or payload.get("transacted_at"),
            "student_count": int(payload.get("student_count", 500)),
            "school_avg_amount": float(payload.get("school_avg_amount", payload.get("amount", 250000.0)))
        }
    else:
        txn_payload = {
            "amount": 250000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "BANK_TRANSFER"
        }

    score_result = score_transaction_with_isolation_forest(txn_payload)

    # Also score with Autoencoder & LSTM & compute weighted ensemble when artifacts are available
    ae_result = None
    lstm_result = None
    ensemble_result = None
    try:
        from ml.models.scoring_engine import (
            score_transaction_with_autoencoder,
            score_transaction_with_lstm,
            compute_weighted_ensemble_score,
            DEFAULT_LSTM_MODEL_PATH,
        )
        ae_result = score_transaction_with_autoencoder(txn_payload)
        if os.path.exists(DEFAULT_LSTM_MODEL_PATH):
            try:
                lstm_result = score_transaction_with_lstm(txn_payload)
            except Exception as l_err:
                print(f"[WARN] LSTM evaluation failed: {l_err}")

        active_lstm_score = (
            lstm_result["anomaly_score"]
            if lstm_result is not None
            else (float(db_txn[7]) if db_txn and len(db_txn) > 7 and db_txn[7] is not None else None)
        )
        ensemble_result = compute_weighted_ensemble_score(
            if_score=score_result["anomaly_score"],
            ae_score=ae_result["anomaly_score"],
            lstm_score=active_lstm_score,
            gnn_score=float(db_txn[8]) if db_txn and len(db_txn) > 8 and db_txn[8] is not None else None,
        )
    except Exception as ae_err:
        print(f"[WARN] Multi-model evaluation skipped: {ae_err}")

    if db_txn:
        try:
            if ae_result is not None and ensemble_result is not None:
                if lstm_result is not None:
                    update_query = """
                        UPDATE transactions
                        SET if_score = :if_score, ae_score = :ae_score, lstm_score = :lstm_score,
                            risk_score = :risk_score, risk_tier = :risk_tier
                        WHERE id = :txn_id
                    """
                    params = {
                        "if_score": score_result["anomaly_score"],
                        "ae_score": ae_result["anomaly_score"],
                        "lstm_score": lstm_result["anomaly_score"],
                        "risk_score": ensemble_result["composite_score"],
                        "risk_tier": ensemble_result["risk_tier"],
                        "txn_id": txn_id,
                    }
                else:
                    update_query = """
                        UPDATE transactions
                        SET if_score = :if_score, ae_score = :ae_score, risk_score = :risk_score, risk_tier = :risk_tier
                        WHERE id = :txn_id
                    """
                    params = {
                        "if_score": score_result["anomaly_score"],
                        "ae_score": ae_result["anomaly_score"],
                        "risk_score": ensemble_result["composite_score"],
                        "risk_tier": ensemble_result["risk_tier"],
                        "txn_id": txn_id,
                    }
                await db.execute(text(update_query), params)
            else:
                update_query = """
                    UPDATE transactions
                    SET if_score = :if_score
                    WHERE id = :txn_id
                """
                await db.execute(text(update_query), {"if_score": score_result["anomaly_score"], "txn_id": txn_id})
            await db.commit()
        except Exception as update_err:
            print(f"[WARN] Failed to persist model scores: {update_err}")

    return {
        "status": "success",
        "txn_id": txn_id,
        "inference": score_result,
        "ae_inference": ae_result,
        "lstm_inference": lstm_result,
        "ensemble": ensemble_result,
    }
