"""
DSFMP LSTM Autoencoder Temporal Model Integration Tests
Verifies causal sliding window builder, PyTorch Seq2Seq Autoencoder fit/score/save/load,
temporal anomaly explainability, and backend REST endpoint serving.
"""

import os
import unittest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from main import app
from ml.features.temporal import TemporalSequenceBuilder
from ml.models.lstm_autoencoder import LSTMAutoencoderFraudModel
from ml.models.scoring_engine import (
    get_lstm_model,
    score_transaction_with_lstm,
    score_transaction_ensemble,
    DEFAULT_LSTM_MODEL_PATH,
)


class TestLSTMAutoencoderIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_temporal_sequence_builder(self):
        """Verify TemporalSequenceBuilder creates causal windows of shape (N, 10, F)."""
        builder = TemporalSequenceBuilder(seq_len=10)
        dates = pd.date_range("2026-01-01", periods=15, freq="2h")
        sample_df = pd.DataFrame({
            "transaction_id": [f"tx_{i}" for i in range(15)],
            "school_id": ["school_A"] * 10 + ["school_B"] * 5,
            "transacted_at": dates,
            "amount": [50000.0 + i * 1000.0 for i in range(15)],
            "student_count": [400] * 15,
            "school_avg_amount": [60000.0] * 15,
            "rolling_24h_count": [1] * 15,
            "rolling_24h_amount": [50000.0] * 15,
            "type": ["SUPPLIER_PAYMENT"] * 15,
            "payment_method": ["BANK_TRANSFER"] * 15,
            "is_fraud": [0] * 15,
        })
        builder.fit(sample_df)
        self.assertTrue(builder.is_fitted)
        self.assertGreater(len(builder.feature_names), 20)

        windows, meta = builder.build_sliding_windows(sample_df, normal_only=False)
        self.assertEqual(len(windows), 15)
        self.assertEqual(windows.shape[1], 10)
        self.assertEqual(windows.shape[2], len(builder.feature_names))

    def test_02_model_persistence_and_inference(self):
        """Verify LSTM model artifact exists and can score a single transaction."""
        self.assertTrue(
            os.path.exists(DEFAULT_LSTM_MODEL_PATH),
            f"Artifact missing: {DEFAULT_LSTM_MODEL_PATH}",
        )
        model = get_lstm_model()
        self.assertTrue(model.is_fitted)

        txn = {
            "amount": 150000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-10-29T12:00:00",
            "student_count": 500,
            "school_avg_amount": 140000.0,
            "rolling_24h_count": 1,
            "rolling_24h_amount": 150000.0,
        }
        score = model.score_single(txn)
        self.assertTrue(0.0 <= score <= 1.0)

        drivers = model.explain_temporal_anomaly(txn, top_k=3)
        self.assertIsInstance(drivers, list)
        if drivers:
            self.assertIn("feature", drivers[0])
            self.assertIn("share", drivers[0])

    def test_03_elevated_score_on_velocity_burst(self):
        """Verify rapid velocity burst triggers high LSTM anomaly score."""
        burst_txn = {
            "amount": 95000.0,
            "type": "MPESA_PAYMENT",
            "payment_method": "MPESA",
            "transacted_at": "2026-10-29T03:15:00",
            "student_count": 200,
            "school_avg_amount": 80000.0,
            "rolling_24h_count": 14,  # extreme velocity spike
            "rolling_24h_amount": 1330000.0,
            "threshold": 0.68,
        }
        result = score_transaction_with_lstm(burst_txn)
        self.assertGreaterEqual(result["anomaly_score"], 0.68)
        self.assertTrue(result["is_anomaly"])
        self.assertIn("LSTM Autoencoder", result["model_name"])

    def test_04_api_overview_includes_healthy_lstm(self):
        """Verify /api/models/overview exposes active healthy LSTM."""
        res = self.client.get("/api/models/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        lstm = next((m for m in data["models"] if m["id"] == "lstm"), None)
        self.assertIsNotNone(lstm)
        self.assertEqual(lstm["status"], "HEALTHY")
        self.assertTrue(lstm["is_active"])
        self.assertAlmostEqual(lstm["weight"], 0.30, places=2)
        self.assertGreaterEqual(lstm["roc_auc"], 0.95)

    def test_05_api_lstm_info_and_infer(self):
        """Verify /api/models/lstm/info and /api/models/lstm/infer endpoints."""
        info_res = self.client.get("/api/models/lstm/info")
        self.assertEqual(info_res.status_code, 200)
        info = info_res.json()
        self.assertEqual(info["id"], "lstm_autoencoder_v1")
        self.assertEqual(info["seq_len"], 10)

        infer_payload = {
            "amount": 250000.0,
            "type": "SUBSIDY_DISBURSEMENT",
            "payment_method": "BANK_TRANSFER",
            "transacted_at": "2026-10-29T11:00:00",
            "student_count": 500,
            "school_avg_amount": 240000.0,
            "rolling_24h_count": 1,
            "threshold": 0.68,
        }
        infer_res = self.client.post("/api/models/lstm/infer", json=infer_payload)
        self.assertEqual(infer_res.status_code, 200)
        data = infer_res.json()
        self.assertIn("anomaly_score", data)
        self.assertEqual(data["model_name"], "LSTM Autoencoder")

    def test_06_api_3model_ensemble_infer(self):
        """Verify /api/models/ensemble/infer scores IF, AE, and LSTM together."""
        payload = {
            "amount": 1000000.0,
            "type": "SUPPLIER_PAYMENT",
            "payment_method": "CASH",
            "transacted_at": "2026-10-29T02:00:00",
            "student_count": 200,
            "school_avg_amount": 100000.0,
            "rolling_24h_count": 5,
        }
        res = self.client.post("/api/models/ensemble/infer", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("composite_score", data)
        self.assertIn("isolation_forest", data)
        self.assertIn("autoencoder", data)
        self.assertIn("lstm", data)
        # Check breakdown has active LSTM
        lstm_item = next((item for item in data["breakdown"] if item["id"] == "lstm"), None)
        self.assertIsNotNone(lstm_item)
        self.assertEqual(lstm_item["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()

