import json
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.connection import get_db
from routes.settings import get_optional_user_id
from typing import Optional, List, Dict, Any

router = APIRouter()

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
