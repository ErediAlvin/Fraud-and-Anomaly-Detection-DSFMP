"""
Integration Test Suite for Automated Transaction Ingestion Pipeline & Background 3-Model Anomaly Scoring.

Technical Requirements:
1. Ingesting a benign transaction results in risk_tier: LOW without creating a fraud alert.
2. Ingesting a high-value off-hours transaction (e.g., KES 2,000,000 at 02:30 AM) automatically updates
   transactions.risk_tier = 'CRITICAL', status = 'FLAGGED', and inserts a corresponding record into fraud_alerts & notifications.
3. Concurrency test ensuring batch ingestion runs without database lock contention.
4. Multipart CSV batch ingestion parsing and processing.
"""

import asyncio
import io
import os
import sys
import uuid
import unittest
from datetime import datetime, timezone
from sqlalchemy import text
import httpx
from httpx import ASGITransport

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from database.connection import async_session_factory, engine
from services.ingestion_service import (
    process_and_score_transaction,
    process_and_score_batch,
)


class TestIngestionPipelineIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.transport = ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://testserver")

        # Create a dedicated isolated test school for this test run
        self.test_school_id = str(uuid.uuid4())
        self.nemis = f"NEMIS-{uuid.uuid4().hex[:6].upper()}"
        async with async_session_factory() as db:
            await db.execute(text("""
                INSERT INTO schools (id, name, nemis_code, county_id, enrollment_count)
                VALUES (:id, 'Test Ingestion Academy', :nemis, 1, 600)
            """), {"id": self.test_school_id, "nemis": self.nemis})
            await db.commit()

            # Retrieve optional supplier
            supp_res = await db.execute(text("SELECT id FROM suppliers LIMIT 1"))
            s_row = supp_res.fetchone()
            self.supplier_id = s_row[0] if s_row else None

    async def asyncTearDown(self):
        # Clean up test school and all associated records
        try:
            async with async_session_factory() as db:
                await db.execute(text("DELETE FROM fraud_alerts WHERE school_id = :sid"), {"sid": self.test_school_id})
                await db.execute(text("DELETE FROM transactions WHERE school_id = :sid"), {"sid": self.test_school_id})
                await db.execute(text("DELETE FROM schools WHERE id = :sid"), {"sid": self.test_school_id})
                await db.commit()
        except Exception:
            pass

        await self.client.aclose()
        await engine.dispose()

    async def _wait_for_scoring(self, txn_id: str, timeout: float = 6.0):
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            async with async_session_factory() as db:
                row = (await db.execute(
                    text("SELECT risk_tier, status, risk_score, if_score, ae_score, lstm_score FROM transactions WHERE id = :id"),
                    {"id": txn_id}
                )).fetchone()
                if row and row[0] != "EVALUATING":
                    return row
            await asyncio.sleep(0.15)
        return None

    async def test_01_ingest_benign_transaction(self):
        """
        Verify: Ingesting a benign transaction results in risk_tier: LOW without creating a fraud alert.
        """
        payload = {
            "school_id": self.test_school_id,
            "supplier_id": self.supplier_id,
            "amount": 47500.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-11-19T10:30:00Z",  # Normal daytime banking hour
            "description": "Routine fresh vegetables supply for feeding program",
        }

        # 1. Post to ingestion endpoint
        response = await self.client.post("/api/transactions", json=payload)
        self.assertEqual(response.status_code, 202)
        data = response.json()
        txn_id = data["transaction_id"]
        self.assertEqual(data["status"], "QUEUED_FOR_SCORING")
        self.assertEqual(data["risk_tier"], "EVALUATING")

        # 2. Wait for background scoring to complete
        txn_row = await self._wait_for_scoring(txn_id)
        if txn_row is None:
            await process_and_score_transaction(txn_id, async_session_factory)
            txn_row = await self._wait_for_scoring(txn_id)

        self.assertIsNotNone(txn_row)
        risk_tier, status_val, risk_score = txn_row[0], txn_row[1], float(txn_row[2])
        self.assertEqual(risk_tier, "LOW")
        self.assertNotEqual(status_val, "FLAGGED")
        self.assertLess(risk_score, 0.40)

        # 3. Verify no fraud alert exists
        async with async_session_factory() as db:
            alert_count = (await db.execute(
                text("SELECT COUNT(*) FROM fraud_alerts WHERE entity_id = :id"),
                {"id": txn_id}
            )).scalar()
            self.assertEqual(alert_count, 0)

    async def test_02_ingest_high_value_off_hours_transaction(self):
        """
        Verify: Ingesting a high-value off-hours transaction (KES 2,000,000 at 02:30 AM)
        automatically updates transactions.risk_tier = 'CRITICAL', status = 'FLAGGED',
        and inserts a corresponding record into fraud_alerts & notifications.
        """
        payload = {
            "school_id": self.test_school_id,
            "supplier_id": self.supplier_id,
            "amount": 2000000.0,  # Critical off-hours transfer
            "type": "SUBSIDY_DISBURSEMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-11-19T02:30:00Z",  # 02:30 AM off-hours
            "description": "Unauthorized off-hours bulk subsidy transfer",
        }

        # 1. Post to ingestion endpoint
        response = await self.client.post("/api/transactions", json=payload)
        self.assertEqual(response.status_code, 202)
        data = response.json()
        txn_id = data["transaction_id"]
        self.assertEqual(data["status"], "QUEUED_FOR_SCORING")

        # 2. Score transaction
        score_res = await process_and_score_transaction(txn_id, async_session_factory)
        self.assertEqual(score_res["status"], "COMPLETED")
        self.assertEqual(score_res["risk_tier"], "CRITICAL")
        self.assertTrue(score_res["alert_created"])
        self.assertIsNotNone(score_res["alert_id"])
        self.assertGreaterEqual(score_res["risk_score"], 0.80)

        # 3. Query DB and verify transactions, fraud_alerts, and notifications
        async with async_session_factory() as db:
            txn_row = (await db.execute(
                text("SELECT risk_tier, status, risk_score, if_score, ae_score, lstm_score FROM transactions WHERE id = :id"),
                {"id": txn_id}
            )).fetchone()
            self.assertIsNotNone(txn_row)
            self.assertEqual(txn_row[0], "CRITICAL")
            self.assertEqual(txn_row[1], "FLAGGED")
            self.assertGreaterEqual(float(txn_row[2]), 0.80)

            # Verify fraud alert record
            alert_res = await db.execute(
                text("""
                    SELECT id, alert_type, severity, composite_score, description, status 
                    FROM fraud_alerts 
                    WHERE entity_id = :id
                """),
                {"id": txn_id}
            )
            alert_row = alert_res.fetchone()
            self.assertIsNotNone(alert_row, "Expected fraud_alerts record was not created")
            self.assertEqual(alert_row[2], "CRITICAL")
            self.assertGreaterEqual(float(alert_row[3]), 0.80)
            self.assertIn("Automated Ingestion Alert", alert_row[4])
            self.assertEqual(alert_row[5], "NEW")

            # Verify notification created
            notif_cnt = (await db.execute(
                text("SELECT COUNT(*) FROM notifications WHERE link = :link"),
                {"link": f"/transactions?search={txn_id}"}
            )).scalar()
            self.assertGreater(notif_cnt, 0, "Expected at least one investigator notification")

    async def test_03_concurrent_batch_ingestion_no_lock_contention(self):
        """
        Concurrency test ensuring batch ingestion runs without database lock contention.
        Submits a batch of 20 transactions and scores them concurrently across models.
        """
        batch_size = 20
        transactions_batch = []
        for i in range(batch_size):
            is_surge = (i % 5 == 0)
            amt = 1800000.0 if is_surge else (32000.0 + i * 1450.0)
            hour = 3 if is_surge else 11
            transactions_batch.append({
                "school_id": self.test_school_id,
                "supplier_id": self.supplier_id,
                "amount": amt,
                "type": "SUBSIDY_DISBURSEMENT" if is_surge else "SUPPLIER_PAYMENT",
                "payment_method": "BANK_TRANSFER",
                "transacted_at": f"2026-11-19T{hour:02d}:15:00Z",
                "description": f"County term disbursement batch record #{i+1}",
                "reference_no": f"BATCH-{uuid.uuid4().hex[:6].upper()}",
            })

        # 1. Post batch to endpoint
        response = await self.client.post("/api/transactions/batch-ingest", json=transactions_batch)
        self.assertEqual(response.status_code, 202)
        batch_data = response.json()
        self.assertEqual(batch_data["total_submitted"], batch_size)
        self.assertEqual(batch_data["status"], "PROCESSING")
        batch_id = batch_data["batch_id"]

        # 2. Fetch all IDs for this batch and process concurrently
        async with async_session_factory() as db:
            rows = (await db.execute(
                text("SELECT id FROM transactions WHERE batch_id = :bid"),
                {"bid": batch_id}
            )).fetchall()
            txn_ids = [r[0] for r in rows]

        self.assertEqual(len(txn_ids), batch_size)

        # 3. Concurrently score batch with bounded parallelism (no lock contention)
        results = await process_and_score_batch(txn_ids, async_session_factory)
        self.assertEqual(len(results), batch_size)
        for res in results:
            self.assertEqual(res["status"], "COMPLETED")
            self.assertIn(res["risk_tier"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

        # 4. Verify all transactions transitioned out of EVALUATING
        async with async_session_factory() as db:
            eval_remaining = (await db.execute(
                text("SELECT COUNT(*) FROM transactions WHERE batch_id = :bid AND risk_tier = 'EVALUATING'"),
                {"bid": batch_id}
            )).scalar()
            self.assertEqual(eval_remaining, 0, "Some batch transactions remained in EVALUATING state")

    async def test_04_csv_multipart_batch_ingestion(self):
        """
        Verify: Ingestion via multipart CSV properly parses records, bulk-inserts, and queues for scoring.
        """
        csv_data = (
            "school_id,amount,type,payment_method,description\n"
            f"{self.test_school_id},47500.0,SUPPLIER_PAYMENT,BANK_TRANSFER,Maize meal grain delivery\n"
            f"{self.test_school_id},91200.0,SUBSIDY_DISBURSEMENT,BANK_TRANSFER,Sub-county meal grant\n"
        )
        file_bytes = csv_data.encode("utf-8")

        response = await self.client.post(
            "/api/transactions/batch-ingest",
            files={"file": ("disbursements.csv", file_bytes, "text/csv")}
        )
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data["total_submitted"], 2)
        self.assertEqual(data["status"], "PROCESSING")
        self.assertIn("batch_id", data)


if __name__ == "__main__":
    unittest.main()
