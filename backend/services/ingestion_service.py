"""
DSFMP Ingestion Pipeline & Background 3-Model Anomaly Scoring Service.

Automates ingestion of payment disbursements and procurement transactions:
1. Extracts cyclical temporal features, per-student spending ratios, and deviation Z-scores.
2. Evaluates the calibrated 3-model ensemble (Isolation Forest 40%, Autoencoder 30%, LSTM Autoencoder 30%).
3. Updates transaction records with composite risk score and risk tier.
4. Generates automated fraud alerts and investigator notifications for HIGH/CRITICAL anomalies.
5. Auto-flags CRITICAL risk transactions.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from ml.features.preprocessing import extract_ingestion_features
from ml.models.scoring_engine import score_transaction_ensemble

logger = logging.getLogger("ingestion_service")
logging.basicConfig(level=logging.INFO)


async def get_school_context(db: AsyncSession, school_id: Optional[str], txn_id: str, current_time: datetime) -> Dict[str, Any]:
    """
    Retrieve school student roll, county, historical median/average, and rolling 24h activity from MySQL.
    """
    context: Dict[str, Any] = {
        "student_count": 500,
        "county_id": None,
        "school_name": "Unknown School",
        "school_avg_amount": None,
        "school_median_amount": None,
        "school_std_amount": 0.0,
        "rolling_24h_count": 1,
        "rolling_24h_amount": 0.0,
        "history_df": None,
    }

    if not school_id:
        return context

    # 1. Fetch school metadata
    try:
        school_res = await db.execute(
            text("SELECT name, enrollment_count, county_id FROM schools WHERE id = :sid LIMIT 1"),
            {"sid": school_id}
        )
        school_row = school_res.fetchone()
        if school_row:
            context["school_name"] = school_row[0] or "Unknown School"
            context["student_count"] = max(1, int(school_row[1] or 500))
            context["county_id"] = school_row[2]
    except Exception as e:
        logger.warning(f"Failed to fetch school info for {school_id}: {e}")

    # 2. Fetch historical disbursements for school median/average/std
    try:
        hist_res = await db.execute(
            text("""
                SELECT amount 
                FROM transactions 
                WHERE school_id = :sid AND id != :tid AND status != 'FAILED'
                ORDER BY transacted_at DESC 
                LIMIT 50
            """),
            {"sid": school_id, "tid": txn_id}
        )
        amounts = [float(r[0]) for r in hist_res.fetchall() if r[0] is not None]
        if amounts:
            context["school_avg_amount"] = float(np.mean(amounts))
            context["school_median_amount"] = float(np.median(amounts))
            context["school_std_amount"] = float(np.std(amounts)) if len(amounts) > 1 else float(np.mean(amounts) * 0.25)
    except Exception as e:
        logger.warning(f"Failed to fetch historical stats for school {school_id}: {e}")

    # 3. Rolling 24-hour activity
    try:
        t_24h_ago = current_time - timedelta(hours=24)
        roll_res = await db.execute(
            text("""
                SELECT COUNT(*), COALESCE(SUM(amount), 0)
                FROM transactions
                WHERE school_id = :sid AND id != :tid
                  AND transacted_at BETWEEN :start_time AND :end_time
            """),
            {
                "sid": school_id,
                "tid": txn_id,
                "start_time": t_24h_ago,
                "end_time": current_time,
            }
        )
        roll_row = roll_res.fetchone()
        if roll_row:
            context["rolling_24h_count"] = int(roll_row[0] or 0) + 1
            context["rolling_24h_amount"] = float(roll_row[1] or 0.0)
    except Exception as e:
        logger.warning(f"Failed to fetch rolling 24h stats for school {school_id}: {e}")

    # 4. Recent history for LSTM sequence modeling
    try:
        seq_res = await db.execute(
            text("""
                SELECT id, amount, type, payment_method, transacted_at, school_id
                FROM transactions
                WHERE school_id = :sid AND id != :tid AND transacted_at <= :cur_time
                ORDER BY transacted_at ASC
                LIMIT 15
            """),
            {"sid": school_id, "tid": txn_id, "cur_time": current_time}
        )
        seq_rows = seq_res.fetchall()
        if seq_rows:
            context["history_df"] = pd.DataFrame([
                {
                    "id": r[0],
                    "amount": float(r[1]),
                    "type": r[2],
                    "payment_method": r[3],
                    "transacted_at": r[4],
                    "school_id": r[5],
                }
                for r in seq_rows
            ])
    except Exception as e:
        logger.warning(f"Failed to fetch recent sequence history for school {school_id}: {e}")

    return context


def _build_human_readable_drivers(
    features_df: pd.DataFrame,
    amount: float,
    transacted_at: datetime,
    school_name: str,
    school_avg: float,
    model_reasons: List[str],
) -> List[str]:
    """Generate human-readable anomaly drivers describing why the transaction breached thresholds."""
    drivers: List[str] = []
    row = features_df.iloc[0]

    hour = transacted_at.hour
    minute = transacted_at.minute
    time_str = f"{hour:02d}:{minute:02d}"

    # 1. Off-hours timing driver
    if row.get("is_off_hours", 0) == 1 or hour < 6 or hour >= 22:
        drivers.append(f"Disbursement initiated at {time_str} outside authorized banking hours")

    # 2. Ratio to school average / median
    ratio = float(row.get("amount_to_school_avg_ratio", amount / (school_avg + 1.0)))
    if ratio > 2.5:
        drivers.append(f"Disbursement of KES {amount:,.2f} exceeds school historical average by {ratio:.1f}x")

    # 3. Deviation Z-score
    zscore = float(row.get("deviation_zscore", 0.0))
    if abs(zscore) >= 2.0:
        drivers.append(f"Statistical deviation: {zscore:.1f} standard deviations from baseline")

    # 4. Inflated per-student spending
    per_student = float(row.get("amount_per_student", 0.0))
    if per_student > 5000:
        drivers.append(f"Inflated per-student cost allocation (KES {per_student:,.2f}/student)")

    # 5. Velocity burst
    rolling_cnt = int(row.get("rolling_24h_count", 1))
    if rolling_cnt >= 4:
        drivers.append(f"Unusual transaction velocity ({rolling_cnt} disbursements in 24 hours)")

    # Combine with ensemble reasons
    for r in model_reasons:
        if r not in drivers:
            drivers.append(r)

    if not drivers:
        drivers.append(f"Multi-model anomaly detected (KES {amount:,.2f} at {school_name})")

    return drivers


async def process_and_score_transaction(txn_id: str, db_session_factory=None) -> Dict[str, Any]:
    """
    Core automated scoring task:
    1. Retrieve transaction details and associated school context from MySQL.
    2. Extract cyclical temporal features (hour_sin, hour_cos), per-student spending ratios, and deviation Z-scores.
    3. Execute score_transaction_ensemble() using calibrated 3-model weights (0.40*IF + 0.30*AE + 0.30*LSTM).
    4. Update transactions table with if_score, ae_score, lstm_score, risk_score, and risk_tier.
    5. Generate fraud_alerts & notifications if risk_tier is HIGH or CRITICAL.
    6. Automatically flag transaction if risk_tier is CRITICAL.
    """
    if db_session_factory is None:
        from database.connection import async_session_factory
        db_session_factory = async_session_factory

    async with db_session_factory() as db:
        # 1. Retrieve transaction details
        txn_q = text("""
            SELECT 
                t.id, t.school_id, t.supplier_id, t.amount, t.type, t.payment_method,
                t.reference_no, t.description, t.transacted_at, t.status, t.risk_tier
            FROM transactions t
            WHERE t.id = :tid
            LIMIT 1
        """)
        txn_res = await db.execute(txn_q, {"tid": txn_id})
        txn_row = txn_res.fetchone()

        if not txn_row:
            logger.error(f"Transaction {txn_id} not found in database for scoring.")
            return {"status": "NOT_FOUND", "transaction_id": txn_id}

        (
            t_id, school_id, supplier_id, t_amount, t_type, t_method,
            t_ref, t_desc, t_transacted_at, t_status, prev_risk_tier
        ) = txn_row

        amount = float(t_amount or 0.0)
        transacted_at: datetime = (
            t_transacted_at if isinstance(t_transacted_at, datetime)
            else datetime.now(timezone.utc)
        )

        # 2. Retrieve school context
        school_ctx = await get_school_context(db, school_id, txn_id, transacted_at)
        student_count = school_ctx["student_count"]
        school_avg = school_ctx["school_avg_amount"] if school_ctx["school_avg_amount"] is not None else amount
        school_std = school_ctx["school_std_amount"]
        rolling_24h_count = school_ctx["rolling_24h_count"]
        rolling_24h_amount = school_ctx["rolling_24h_amount"] + amount
        history_df = school_ctx["history_df"]
        school_name = school_ctx["school_name"]
        county_id = school_ctx["county_id"]

        # 3. Extract cyclical temporal features and deviation ratios
        raw_payload = {
            "amount": amount,
            "type": t_type or "SUPPLIER_PAYMENT",
            "payment_method": t_method or "BANK_TRANSFER",
            "transacted_at": transacted_at.isoformat(),
            "student_count": student_count,
            "school_avg_amount": school_avg,
            "school_std_amount": school_std,
            "rolling_24h_count": rolling_24h_count,
            "rolling_24h_amount": rolling_24h_amount,
            "school_id": school_id or "UNKNOWN",
        }

        features_df = extract_ingestion_features(raw_payload, school_ctx)

        # 4. Execute 3-model weighted ensemble scoring
        # Calibrated weights: 40% Isolation Forest, 30% Autoencoder, 30% LSTM Autoencoder
        ensemble_res = score_transaction_ensemble(
            transaction_data=raw_payload,
            if_threshold=0.65,
            ae_threshold=0.70,
            lstm_threshold=0.68,
            weights={"weight_if": 0.40, "weight_ae": 0.30, "weight_lstm": 0.30},
            history_df=history_df,
        )

        composite_score = float(ensemble_res["composite_score"])
        risk_tier = str(ensemble_res["risk_tier"])
        if_score = float(ensemble_res["isolation_forest"]["anomaly_score"])
        ae_score = float(ensemble_res["autoencoder"]["anomaly_score"])
        lstm_score = float(ensemble_res["lstm"]["anomaly_score"]) if ensemble_res.get("lstm") else None

        # Determine status update: CRITICAL automatically updates status to FLAGGED
        new_status = "FLAGGED" if risk_tier == "CRITICAL" else t_status

        # 5. Update transactions table
        update_txn_q = text("""
            UPDATE transactions
            SET if_score = :if_score,
                ae_score = :ae_score,
                lstm_score = :lstm_score,
                risk_score = :risk_score,
                risk_tier = :risk_tier,
                status = :status
            WHERE id = :tid
        """)
        await db.execute(
            update_txn_q,
            {
                "if_score": if_score,
                "ae_score": ae_score,
                "lstm_score": lstm_score,
                "risk_score": composite_score,
                "risk_tier": risk_tier,
                "status": new_status,
                "tid": txn_id,
            }
        )

        alert_created = False
        alert_id = None

        # 6. Automated Alert Generation Rule (HIGH >= 0.60, CRITICAL >= 0.80)
        if risk_tier in ("HIGH", "CRITICAL"):
            # Determine alert_type based on extracted feature flags
            feat_row = features_df.iloc[0]
            is_off_hours = bool(feat_row.get("is_off_hours", 0) == 1)
            is_ghost_candidate = bool(student_count < 80 and amount > 500000)

            if is_ghost_candidate:
                alert_type = "GHOST_BENEFICIARY"
            elif is_off_hours:
                alert_type = "OFF_HOURS_DRAIN"
            else:
                alert_type = "PAYMENT_ANOMALY"

            anomaly_drivers = _build_human_readable_drivers(
                features_df=features_df,
                amount=amount,
                transacted_at=transacted_at,
                school_name=school_name,
                school_avg=school_avg,
                model_reasons=ensemble_res.get("reasons", []),
            )

            alert_id = str(uuid.uuid4())
            ref_str = t_ref or txn_id[:8]
            alert_title = f"Automated Ingestion Alert: {risk_tier} Risk ({ref_str})"
            alert_desc = f"Automated Ingestion Alert: {'; '.join(anomaly_drivers)}"

            # Insert into fraud_alerts
            insert_alert_q = text("""
                INSERT INTO fraud_alerts (
                    id, alert_type, severity, title, description,
                    entity_type, entity_id, school_id, county_id,
                    composite_score, if_score, ae_score, lstm_score,
                    status
                ) VALUES (
                    :id, :alert_type, :severity, :title, :description,
                    'transaction', :entity_id, :school_id, :county_id,
                    :composite_score, :if_score, :ae_score, :lstm_score,
                    'NEW'
                )
            """)
            await db.execute(
                insert_alert_q,
                {
                    "id": alert_id,
                    "alert_type": alert_type,
                    "severity": risk_tier,
                    "title": alert_title,
                    "description": alert_desc,
                    "entity_id": txn_id,
                    "school_id": school_id,
                    "county_id": county_id,
                    "composite_score": composite_score,
                    "if_score": if_score,
                    "ae_score": ae_score,
                    "lstm_score": lstm_score,
                }
            )

            # Query active investigators to receive notification
            investigators_q = text("""
                SELECT id FROM users
                WHERE is_active = 1 AND role IN ('fraud_analyst', 'supervisor', 'system_admin')
            """)
            inv_res = await db.execute(investigators_q)
            investigator_ids = [r[0] for r in inv_res.fetchall()]

            # Fallback to any active user if no dedicated investigator role found
            if not investigator_ids:
                fallback_users_q = text("SELECT id FROM users WHERE is_active = 1 LIMIT 5")
                fb_res = await db.execute(fallback_users_q)
                investigator_ids = [r[0] for r in fb_res.fetchall()]

            # Dispatch notification to all active investigators
            for inv_id in investigator_ids:
                notif_id = str(uuid.uuid4())
                await db.execute(
                    text("""
                        INSERT INTO notifications (id, user_id, type, title, message, link)
                        VALUES (:id, :uid, 'ALERT', :title, :message, :link)
                    """),
                    {
                        "id": notif_id,
                        "uid": inv_id,
                        "title": f"New Anomaly Alert: {risk_tier} ({ref_str})",
                        "message": f"{alert_desc} (Transaction ID: {txn_id})",
                        "link": f"/transactions?search={txn_id}",
                    }
                )

            alert_created = True

        await db.commit()
        logger.info(
            f"Successfully processed txn {txn_id}: score={composite_score:.4f}, "
            f"tier={risk_tier}, alert_created={alert_created}"
        )

        return {
            "status": "COMPLETED",
            "transaction_id": txn_id,
            "risk_score": composite_score,
            "risk_tier": risk_tier,
            "scores": {
                "if_score": if_score,
                "ae_score": ae_score,
                "lstm_score": lstm_score,
            },
            "alert_created": alert_created,
            "alert_id": alert_id,
        }


async def process_and_score_batch(txn_ids: List[str], db_session_factory=None) -> List[Dict[str, Any]]:
    """
    Asynchronously processes and scores a batch of transactions across the 3-model ensemble.
    Uses bounded concurrency to eliminate database lock contention while maximizing throughput.
    """
    if db_session_factory is None:
        from database.connection import async_session_factory
        db_session_factory = async_session_factory

    concurrency_limit = 5
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def _safe_score(tid: str):
        async with semaphore:
            try:
                return await process_and_score_transaction(tid, db_session_factory)
            except Exception as e:
                logger.error(f"Error scoring transaction {tid} in batch: {e}")
                return {"status": "ERROR", "transaction_id": tid, "error": str(e)}

    tasks = [_safe_score(tid) for tid in txn_ids]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    logger.info(f"Batch processing completed for {len(txn_ids)} transactions.")
    return results
