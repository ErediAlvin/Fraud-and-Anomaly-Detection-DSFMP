from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.connection import get_db
from typing import List, Optional

router = APIRouter()

@router.get("")
async def get_alerts(
    tier: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # Construct base query
    query_str = """
        SELECT 
            fa.id, 
            fa.severity as tier, 
            fa.entity_type as entityType,
            CASE 
                WHEN fa.entity_type = 'transaction' THEN (SELECT reference_no FROM transactions WHERE id = fa.entity_id)
                WHEN fa.entity_type = 'beneficiary' THEN (SELECT CONCAT(first_name, ' ', last_name) FROM beneficiaries WHERE id = fa.entity_id)
                WHEN fa.entity_type = 'school' THEN (SELECT name FROM schools WHERE id = fa.entity_id)
                WHEN fa.entity_type = 'supplier' THEN (SELECT name FROM suppliers WHERE id = fa.entity_id)
                ELSE 'Systemwide Process'
            END as entityName,
            fa.alert_type as alertType, 
            fa.composite_score as compositeScore,
            fa.if_score as `IF`, 
            fa.ae_score as `AE`, 
            fa.lstm_score as `LSTM`, 
            fa.gnn_score as `GNN`,
            fa.created_at as triggeredAt, 
            fa.status,
            COALESCE(CONCAT(u.first_name, ' ', u.last_name), 'Unassigned') as assignedTo,
            (SELECT tx_id FROM blockchain_ledger WHERE entity_type = 'fraud_alerts' AND entity_id = fa.id LIMIT 1) as blockchainHash,
            fa.description
        FROM fraud_alerts fa
        LEFT JOIN users u ON fa.assigned_to = u.id
        WHERE 1=1
    """
    
    params = {}
    if tier and tier != 'ALL':
        query_str += " AND fa.severity = :tier"
        params["tier"] = tier
        
    if status and status != 'ALL':
        query_str += " AND fa.status = :status"
        params["status"] = status
        
    if alert_type and alert_type != 'ALL':
        query_str += " AND fa.alert_type = :alert_type"
        params["alert_type"] = alert_type
        
    if search:
        query_str += " AND (fa.id LIKE :search OR fa.description LIKE :search)"
        params["search"] = f"%{search}%"
        
    query_str += " ORDER BY fa.created_at DESC"
    
    result = await db.execute(text(query_str), params)
    
    alerts = []
    for row in result.all():
        # Generate evidence based on alert type
        evidence = []
        a_type = row[4]
        if a_type == "GHOST_BENEFICIARY":
            evidence = [
                {"feature": "Daily enrollment spike", "expected": "2-5 students", "actual": "47 students"},
                {"feature": "Duplicate identity matches", "expected": "0", "actual": "12 matches"}
            ]
        elif a_type == "PAYMENT_ANOMALY":
            evidence = [
                {"feature": "Amount deviation", "expected": "KES 10,000 baseline", "actual": "KES 890,000"},
                {"feature": "Time of transaction", "expected": "Business hours", "actual": "2:14 AM"}
            ]
        elif a_type == "SUPPLY_CHAIN_IRREGULARITY":
            evidence = [
                {"feature": "Quantity discrepancy", "expected": "100% match", "actual": "90% shortage"}
            ]
        elif a_type == "ENROLLMENT_SPIKE":
            evidence = [
                {"feature": "Meals served vs enrollment", "expected": "Max 520 servings", "actual": "1,520 servings"}
            ]
        else:
            evidence = [
                {"feature": "ML Anomaly Score", "expected": "< 0.50 threshold", "actual": f"{row[5]:.2f}"}
            ]

        alerts.append({
            "id": row[0],
            "tier": row[1],
            "entityType": (row[2] or "SYSTEM").upper(),
            "entityName": row[3] or "Unknown Entity",
            "alertType": (a_type or "OTHER").replace("_", " "),
            "compositeScore": float(row[5]) if row[5] is not None else 0.0,
            "modelScores": {
                "IF": float(row[6]) if row[6] is not None else 0.0,
                "AE": float(row[7]) if row[7] is not None else 0.0,
                "LSTM": float(row[8]) if row[8] is not None else 0.0,
                "GNN": float(row[9]) if row[9] is not None else 0.0,
            },
            "triggeredAt": row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else "",
            "status": row[11],
            "assignedTo": row[12],
            "evidence": evidence,
            "blockchainHash": row[13] or "N/A",
            "description": row[14]
        })
        
    return alerts
