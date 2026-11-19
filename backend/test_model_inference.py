"""
DSFMP Isolation Forest Model Inference — Comprehensive Test Suite
Validates backend integration, endpoints, scoring engine, edge cases, and inference latency.
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure backend root is in python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from ml.models.scoring_engine import (
    score_transaction_with_isolation_forest,
    get_isolation_forest_model
)


class TestIsolationForestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.model = get_isolation_forest_model()

    def test_01_model_loaded_successfully(self):
        """Verify the trained model artifact is loaded and fitted."""
        self.assertIsNotNone(self.model)
        self.assertTrue(self.model.is_fitted)
        self.assertEqual(self.model.n_estimators, 200)
        self.assertAlmostEqual(self.model.contamination, 0.05, places=2)

    def test_02_get_model_info_endpoint(self):
        """Verify GET /api/models/isolation-forest/info returns proper metadata."""
        response = self.client.get("/api/models/isolation-forest/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "isolation_forest_v1")
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["n_estimators"], 200)
        self.assertIn("log_amount", data["features"])
        self.assertIn("hour_of_day", data["features"])

    def test_03_get_models_overview_endpoint(self):
        """Verify GET /api/models/overview lists Isolation Forest as healthy."""
        response = self.client.get("/api/models/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        models = data.get("models", [])
        if_model = next((m for m in models if m["id"] == "isolation-forest"), None)
        self.assertIsNotNone(if_model)
        self.assertEqual(if_model["status"], "HEALTHY")
        self.assertTrue(if_model["is_active"])

    def test_04_get_presets_endpoint(self):
        """Verify GET /api/models/presets returns curated test vectors."""
        response = self.client.get("/api/models/presets")
        self.assertEqual(response.status_code, 200)
        presets = response.json().get("presets", [])
        self.assertGreaterEqual(len(presets), 4)
        preset_ids = [p["id"] for p in presets]
        self.assertIn("normal_subsidy", preset_ids)
        self.assertIn("midnight_surge", preset_ids)
        self.assertIn("ghost_students", preset_ids)

    def test_05_normal_transaction_inference(self):
        """Verify normal daytime transaction produces LOW risk score below threshold."""
        payload = {
            "amount": 250000.0,
            "type": "SUBSIDY_DISBURSEMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-10-29T12:00:00",
            "student_count": 500,
            "school_avg_amount": 240000.0,
            "rolling_24h_count": 1,
            "rolling_24h_amount": 250000.0,
            "threshold": 0.65
        }
        response = self.client.post("/api/models/isolation-forest/infer", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_anomaly"], f"Normal transaction flagged as anomaly: {data}")
        self.assertIn(data["risk_tier"], ["LOW", "MEDIUM"])
        self.assertLess(data["anomaly_score"], 0.65)
        self.assertLess(data["latency_ms"], 300.0)

    def test_06_midnight_off_hours_fraud_inference(self):
        """Verify 2:30 AM off-hours spike is flagged as anomaly with off-hours reason."""
        payload = {
            "amount": 2500000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "CASH",
            "transacted_at": "2026-10-29T02:30:00",
            "student_count": 200,
            "school_avg_amount": 100000.0,
            "rolling_24h_count": 3,
            "rolling_24h_amount": 4000000.0,
            "threshold": 0.65
        }
        response = self.client.post("/api/models/isolation-forest/infer", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_anomaly"])
        self.assertIn(data["risk_tier"], ["HIGH", "CRITICAL"])
        self.assertGreaterEqual(data["anomaly_score"], 0.65)
        # Check reasons
        reasons_text = " ".join(data["reasons"])
        self.assertIn("Off-hours", reasons_text)

    def test_07_ghost_students_extreme_ratio(self):
        """Verify exorbitant disbursement for tiny student count flags per-student anomaly."""
        payload = {
            "amount": 1500000.0,
            "type": "SUBSIDY_DISBURSEMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-10-29T10:00:00",
            "student_count": 25,
            "school_avg_amount": 100000.0,
            "rolling_24h_count": 1,
            "threshold": 0.65
        }
        response = self.client.post("/api/models/isolation-forest/infer", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_anomaly"])
        reasons_text = " ".join(data["reasons"])
        self.assertIn("per-student", reasons_text)

    def test_08_dynamic_threshold_adjustment(self):
        """Verify dynamic threshold properly shifts classification."""
        payload = {
            "amount": 800000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-10-29T14:00:00",
            "student_count": 500,
            "school_avg_amount": 300000.0,
            "threshold": 0.95  # very strict
        }
        res_strict = self.client.post("/api/models/isolation-forest/infer", json=payload)
        self.assertEqual(res_strict.status_code, 200)
        self.assertEqual(res_strict.json()["threshold"], 0.95)

    def test_09_minimal_payload_with_defaults(self):
        """Verify inference gracefully handles minimal payload and imputes missing fields."""
        payload = {
            "amount": 15000.0
        }
        response = self.client.post("/api/models/isolation-forest/infer", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("anomaly_score", data)
        self.assertIn("risk_tier", data)
        self.assertIn("features_extracted", data)
        self.assertEqual(data["features_extracted"]["amount"], 15000.0)

    def test_10_overview_includes_active_autoencoder_and_weights(self):
        """Verify /overview exposes trained Autoencoder and ensemble weights."""
        response = self.client.get("/api/models/overview")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("weights", data)
        self.assertAlmostEqual(data["weights"]["autoencoder"], 0.30, places=2)
        ae = next(m for m in data["models"] if m["id"] == "autoencoder")
        self.assertEqual(ae["status"], "HEALTHY")
        self.assertTrue(ae["is_active"])
        self.assertAlmostEqual(ae["weight"], 0.30, places=2)
        self.assertAlmostEqual(ae["roc_auc"], 1.0, places=4)

    def test_11_autoencoder_info_and_inference(self):
        """Verify /autoencoder/info and /autoencoder/infer detect anomalous drain."""
        info_res = self.client.get("/api/models/autoencoder/info")
        self.assertEqual(info_res.status_code, 200)
        info = info_res.json()
        self.assertEqual(info["id"], "autoencoder_v1")
        self.assertEqual(info["architecture"], [24, 10, 4, 10, 24])

        payload = {
            "amount": 1000000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "CASH",
            "transacted_at": "2026-10-29T02:15:00",
            "student_count": 200,
            "school_avg_amount": 120000.0,
            "rolling_24h_count": 4,
            "threshold": 0.70,
        }
        infer_res = self.client.post("/api/models/autoencoder/infer", json=payload)
        self.assertEqual(infer_res.status_code, 200)
        data = infer_res.json()
        self.assertEqual(data["model_name"], "Autoencoder")
        self.assertGreaterEqual(data["anomaly_score"], 0.70)
        self.assertTrue(data["is_anomaly"])
        self.assertTrue(data["reconstruction_drivers"])

    def test_12_ensemble_inference_with_weights(self):
        """Verify /ensemble/infer computes weighted breakdown and composite score across 3 models."""
        payload = {
            "amount": 1500000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "CASH",
            "transacted_at": "2026-10-29T03:00:00",
            "student_count": 50,
            "school_avg_amount": 100000.0,
            "rolling_24h_count": 3,
            "weights": {"weight_if": 0.40, "weight_ae": 0.60, "weight_lstm": 0.0},
        }
        res = self.client.post("/api/models/ensemble/infer", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("composite_score", data)
        self.assertIn("breakdown", data)
        model_ids = [item["id"] for item in data["breakdown"]]
        self.assertNotIn("gnn", model_ids)
        self.assertIn("if", model_ids)
        self.assertIn("ae", model_ids)
        expected_composite = round(
            0.40 * data["isolation_forest"]["anomaly_score"] + 0.60 * data["autoencoder"]["anomaly_score"],
            4,
        )
        self.assertAlmostEqual(data["composite_score"], expected_composite, places=3)

    def test_13_settings_schema_includes_scoring_weights(self):
        """Verify RiskThresholdSettings exposes the 3 ensemble weights (40% IF, 30% AE, 30% LSTM) summing to 1.0."""
        from schemas.settings import RiskThresholdSettings
        cfg = RiskThresholdSettings()
        total = cfg.weight_if + cfg.weight_ae + cfg.weight_lstm
        self.assertAlmostEqual(total, 1.0, places=4)
        self.assertAlmostEqual(cfg.weight_if, 0.40, places=2)
        self.assertAlmostEqual(cfg.weight_ae, 0.30, places=2)
        self.assertAlmostEqual(cfg.weight_lstm, 0.30, places=2)


if __name__ == "__main__":
    unittest.main()
