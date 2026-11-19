"""
DSFMP Fraud Alerts Module -- Comprehensive Async Test Suite
Validates:
1. Alert retrieval and filtering (GET /api/alerts, GET /api/alerts/{alert_id})
2. Alert acknowledgment and investigator assignment (POST /api/alerts/{alert_id}/acknowledge)
3. False positive dismissal with structured feedback loop (POST /api/alerts/{alert_id}/dismiss)
4. Alert escalation into Case Management (POST /api/alerts/{alert_id}/escalate)
5. Validation and error handling (404 for unknown IDs, 422 for invalid enums)
"""

import sys
import os
import uuid
import unittest
from httpx import AsyncClient, ASGITransport

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from database.connection import engine
import sqlalchemy as sa


class TestAlertsModule(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Dedicated UUIDs for each test scenario
        self.alert_view_id = str(uuid.uuid4())
        self.alert_ack_id = str(uuid.uuid4())
        self.alert_dismiss_id = str(uuid.uuid4())
        self.alert_escalate_id = str(uuid.uuid4())
        self.nonexistent_id = "00000000-0000-0000-0000-000000000999"

        # Create HTTP client with ASGI transport
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

        # Seed test alerts in database
        async with engine.begin() as conn:
            school_res = await conn.execute(sa.text("SELECT id, county_id FROM schools LIMIT 1"))
            s_row = school_res.fetchone()
            self.school_id = s_row[0] if s_row else None
            self.county_id = s_row[1] if s_row else 1

            test_alerts = [
                (self.alert_view_id, "PAYMENT_ANOMALY", "CRITICAL", "High Anomaly Payment Flag", 0.92, 0.90, 0.88, 0.95),
                (self.alert_ack_id, "GHOST_BENEFICIARY", "HIGH", "Enrollment Discrepancy Flag", 0.78, 0.75, 0.70, 0.82),
                (self.alert_dismiss_id, "OFF_HOURS_TRANSACTION", "MEDIUM", "Night Disbursement Flag", 0.65, 0.60, 0.62, 0.68),
                (self.alert_escalate_id, "SUPPLY_CHAIN_IRREGULARITY", "CRITICAL", "Delivery Shortage Flag", 0.96, 0.95, 0.94, 0.98),
            ]

            for aid, atype, sev, title, comp, i_sc, a_sc, l_sc in test_alerts:
                await conn.execute(sa.text("""
                    INSERT INTO fraud_alerts (
                        id, alert_type, severity, title, description,
                        entity_type, entity_id, school_id, county_id,
                        composite_score, if_score, ae_score, lstm_score,
                        status, created_at, updated_at
                    ) VALUES (
                        :id, :alert_type, :severity, :title, :description,
                        'school', :entity_id, :school_id, :county_id,
                        :composite_score, :if_score, :ae_score, :lstm_score,
                        'NEW', NOW(), NOW()
                    )
                """), {
                    "id": aid,
                    "alert_type": atype,
                    "severity": sev,
                    "title": title,
                    "description": f"Automated test alert description for {title}",
                    "entity_id": self.school_id or str(uuid.uuid4()),
                    "school_id": self.school_id,
                    "county_id": self.county_id,
                    "composite_score": comp,
                    "if_score": i_sc,
                    "ae_score": a_sc,
                    "lstm_score": l_sc,
                })

    async def asyncTearDown(self):
        # Close client session
        await self.client.aclose()

        # Clean up database records created during test
        try:
            async with engine.begin() as conn:
                aids = [self.alert_view_id, self.alert_ack_id, self.alert_dismiss_id, self.alert_escalate_id]
                for aid in aids:
                    case_res = await conn.execute(
                        sa.text("SELECT case_id FROM case_alerts WHERE alert_id = :aid"),
                        {"aid": aid}
                    )
                    case_ids = [row[0] for row in case_res.fetchall()]
                    for cid in case_ids:
                        await conn.execute(sa.text("DELETE FROM case_comments WHERE case_id = :cid"), {"cid": cid})
                        await conn.execute(sa.text("DELETE FROM case_alerts WHERE case_id = :cid"), {"cid": cid})
                        await conn.execute(sa.text("DELETE FROM cases WHERE id = :cid"), {"cid": cid})

                    await conn.execute(sa.text("DELETE FROM audit_log WHERE entity_id = :aid"), {"aid": aid})
                    await conn.execute(sa.text("DELETE FROM fraud_alerts WHERE id = :aid"), {"aid": aid})
        finally:
            await engine.dispose()

    # ── 1. Retrieval & Listing Tests ─────────────────────────────
    async def test_01_get_alerts_list(self):
        """Verify GET /api/alerts returns a list of alert cards with composite & model scores."""
        response = await self.client.get("/api/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 4)

        # Verify field structure on first element
        sample = data[0]
        self.assertIn("id", sample)
        self.assertIn("tier", sample)
        self.assertIn("entityType", sample)
        self.assertIn("compositeScore", sample)
        self.assertIn("modelScores", sample)
        self.assertIn("IF", sample["modelScores"])
        self.assertIn("AE", sample["modelScores"])
        self.assertIn("LSTM", sample["modelScores"])
        self.assertIn("status", sample)

    async def test_02_get_alert_by_id_success(self):
        """Verify GET /api/alerts/{id} returns deep forensic dossier."""
        response = await self.client.get(f"/api/alerts/{self.alert_view_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.alert_view_id)
        self.assertEqual(data["tier"], "CRITICAL")
        self.assertEqual(data["alertType"], "PAYMENT ANOMALY")
        self.assertAlmostEqual(data["compositeScore"], 0.92, places=2)
        self.assertEqual(data["modelScores"]["IF"], 0.90)
        self.assertEqual(data["modelScores"]["AE"], 0.88)
        self.assertEqual(data["modelScores"]["LSTM"], 0.95)
        self.assertIsInstance(data["evidence"], list)
        self.assertGreaterEqual(len(data["evidence"]), 1)
        self.assertIn("auditTrail", data)

    async def test_03_get_nonexistent_alert_returns_404(self):
        """Verify GET /api/alerts/{invalid_id} returns 404."""
        response = await self.client.get(f"/api/alerts/{self.nonexistent_id}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    # ── 2. Acknowledge Tests ─────────────────────────────────────
    async def test_04_acknowledge_alert_success(self):
        """Verify POST /api/alerts/{id}/acknowledge transitions status to UNDER_REVIEW."""
        response = await self.client.post(f"/api/alerts/{self.alert_ack_id}/acknowledge")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["alert_id"], self.alert_ack_id)
        self.assertIn(data["status"], ("UNDER_REVIEW", "INVESTIGATING"))
        self.assertIsNotNone(data["assigned_to"])

        # Verify DB state directly
        async with engine.connect() as conn:
            res = await conn.execute(
                sa.text("SELECT status, assigned_to FROM fraud_alerts WHERE id = :aid"),
                {"aid": self.alert_ack_id}
            )
            row = res.fetchone()
            self.assertIn(row[0], ("UNDER_REVIEW", "INVESTIGATING"))
            self.assertIsNotNone(row[1])

            # Check audit log
            audit_res = await conn.execute(
                sa.text("SELECT action FROM audit_log WHERE entity_id = :aid AND action = 'ALERT_ACKNOWLEDGED'"),
                {"aid": self.alert_ack_id}
            )
            self.assertIsNotNone(audit_res.fetchone())

    async def test_05_acknowledge_nonexistent_alert_returns_404(self):
        """Verify POST /api/alerts/{invalid_id}/acknowledge returns 404."""
        response = await self.client.post(f"/api/alerts/{self.nonexistent_id}/acknowledge")
        self.assertEqual(response.status_code, 404)

    # ── 3. Dismiss Tests ─────────────────────────────────────────
    async def test_06_dismiss_alert_success(self):
        """Verify POST /api/alerts/{id}/dismiss sets DISMISSED, is_true_positive=0 and logs feedback."""
        payload = {
            "reason_code": "APPROVED_OFF_HOURS_OVERRIDE",
            "notes": "Emergency distribution approved by County Director"
        }
        response = await self.client.post(f"/api/alerts/{self.alert_dismiss_id}/dismiss", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "DISMISSED")
        self.assertIn("Feedback recorded for model retraining", data["message"])

        # Verify DB state directly
        async with engine.connect() as conn:
            res = await conn.execute(
                sa.text("SELECT status, is_true_positive, resolution_notes FROM fraud_alerts WHERE id = :aid"),
                {"aid": self.alert_dismiss_id}
            )
            row = res.fetchone()
            self.assertEqual(row[0], "DISMISSED")
            self.assertEqual(row[1], 0)  # is_true_positive = 0 (False positive ground truth)
            self.assertIn("APPROVED_OFF_HOURS_OVERRIDE", row[2])

            # Check audit log
            audit_res = await conn.execute(
                sa.text("SELECT action, details FROM audit_log WHERE entity_id = :aid AND action = 'ALERT_DISMISSED'"),
                {"aid": self.alert_dismiss_id}
            )
            audit_row = audit_res.fetchone()
            self.assertIsNotNone(audit_row)
            self.assertIn("APPROVED_OFF_HOURS_OVERRIDE", audit_row[1])

    async def test_07_dismiss_alert_invalid_enum_validation(self):
        """Verify POST /api/alerts/{id}/dismiss rejects invalid reason codes with 422."""
        invalid_payload = {
            "reason_code": "NOT_A_VALID_REASON",
            "notes": "Testing invalid enum validation"
        }
        response = await self.client.post(f"/api/alerts/{self.alert_dismiss_id}/dismiss", json=invalid_payload)
        self.assertEqual(response.status_code, 422)

    async def test_08_dismiss_nonexistent_alert_returns_404(self):
        """Verify POST /api/alerts/{invalid_id}/dismiss returns 404."""
        response = await self.client.post(f"/api/alerts/{self.nonexistent_id}/dismiss", json={
            "reason_code": "FALSE_POSITIVE",
            "notes": "Nonexistent test"
        })
        self.assertEqual(response.status_code, 404)

    # ── 4. Escalate to Case Tests ────────────────────────────────
    async def test_09_escalate_alert_success(self):
        """Verify POST /api/alerts/{id}/escalate creates case, case_alerts link, comment and notification."""
        payload = {
            "case_title": "Forensic Investigation: Supply Discrepancy",
            "priority": "CRITICAL",
            "notes": "High discrepancy in supplier deliveries requires physical audit."
        }
        response = await self.client.post(f"/api/alerts/{self.alert_escalate_id}/escalate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "ESCALATED")
        self.assertIsNotNone(data["case_id"])
        self.assertTrue(data["case_ref"].startswith("DSFMP-2026-"))

        case_id = data["case_id"]

        # Verify DB state across cases, case_alerts, fraud_alerts, case_comments, audit_log
        async with engine.connect() as conn:
            # 1. Cases table
            c_res = await conn.execute(
                sa.text("SELECT case_number, priority, status, category FROM cases WHERE id = :cid"),
                {"cid": case_id}
            )
            c_row = c_res.fetchone()
            self.assertIsNotNone(c_row)
            self.assertEqual(c_row[1], "CRITICAL")
            self.assertEqual(c_row[2], "OPEN")
            self.assertEqual(c_row[3], "SUPPLY_CHAIN")

            # 2. Case alerts link table
            ca_res = await conn.execute(
                sa.text("SELECT case_id FROM case_alerts WHERE alert_id = :aid AND case_id = :cid"),
                {"aid": self.alert_escalate_id, "cid": case_id}
            )
            self.assertIsNotNone(ca_res.fetchone())

            # 3. Fraud alert status updated to ESCALATED
            fa_res = await conn.execute(
                sa.text("SELECT status FROM fraud_alerts WHERE id = :aid"),
                {"aid": self.alert_escalate_id}
            )
            self.assertEqual(fa_res.fetchone()[0], "ESCALATED")

            # 4. Initial system comment inserted
            comment_res = await conn.execute(
                sa.text("SELECT content FROM case_comments WHERE case_id = :cid"),
                {"cid": case_id}
            )
            comment_row = comment_res.fetchone()
            self.assertIsNotNone(comment_row)
            self.assertIn("Case opened via Alert Escalation", comment_row[0])
            self.assertIn("Supply Discrepancy", payload["case_title"])

            # 5. Audit log
            audit_res = await conn.execute(
                sa.text("SELECT action FROM audit_log WHERE entity_id = :aid AND action = 'ALERT_ESCALATED_TO_CASE'"),
                {"aid": self.alert_escalate_id}
            )
            self.assertIsNotNone(audit_res.fetchone())

    async def test_10_escalate_nonexistent_alert_returns_404(self):
        """Verify POST /api/alerts/{invalid_id}/escalate returns 404."""
        response = await self.client.post(f"/api/alerts/{self.nonexistent_id}/escalate", json={
            "case_title": "Non-existent",
            "priority": "HIGH"
        })
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
