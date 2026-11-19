"""
DSFMP Fraud Detection System — Train LSTM Autoencoder Temporal Model
Learns school-level normal sequence trajectories using causal sliding windows.
Scores temporal anomalies (cadence shifts, burst smurfing, sudden off-hours surges).
Saves serialized artifact to `backend/ml/saved_models/lstm_autoencoder_v1.joblib`
and holdout evaluation metrics to `backend/ml/saved_models/lstm_autoencoder_v1_metrics.json`.
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from ml.features.cleaning import TransactionDataCleaner
from ml.models.lstm_autoencoder import LSTMAutoencoderFraudModel


def train_lstm_autoencoder(
    train_path: str,
    test_path: str,
    output_model_path: str,
    metrics_out_path: Optional[str] = None,
    seq_len: int = 10,
    epochs: int = 35,
    batch_size: int = 64,
    lr: float = 1e-3,
    threshold: float = 0.68,
):
    print("=" * 70)
    print("  DSFMP FRAUD DETECTION — LSTM AUTOENCODER TRAINING PIPELINE")
    print("=" * 70)

    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Train dataset not found: {train_path}")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test dataset not found: {test_path}")

    print("\n[1/5] Loading synthetic transaction datasets...")
    train_raw = pd.read_csv(train_path)
    test_raw = pd.read_csv(test_path)
    print(f" - Train set raw: {len(train_raw):,} records ({int(train_raw['is_fraud'].sum()):,} frauds)")
    print(f" - Test set raw:  {len(test_raw):,} records ({int(test_raw['is_fraud'].sum()):,} frauds)")

    print("\n[2/5] Cleaning datasets and enforcing semi-supervised normal training split...")
    cleaner = TransactionDataCleaner(remove_duplicates=True, clip_extreme_negatives=True)
    train_df = cleaner.clean(train_raw, is_training=True, normal_only_for_training=True)
    test_df = cleaner.clean(test_raw, is_training=False)
    print(f" - Cleaned normal train records: {len(train_df):,}")
    print(f" - Cleaned test records: {len(test_df):,} ({int(test_df['is_fraud'].sum()):,} frauds)")

    print(f"\n[3/5] Instantiating and fitting LSTM Autoencoder (seq_len={seq_len}, epochs={epochs})...")
    model = LSTMAutoencoderFraudModel(
        seq_len=seq_len,
        hidden_dim=32,
        latent_dim=16,
        num_layers=1,
        learning_rate=lr,
        batch_size=batch_size,
        max_epochs=epochs,
        patience=6,
        random_state=42,
    )
    model.fit(train_df=train_df, val_fraction=0.15, verbose=True)

    print("\n[4/5] Evaluating on strictly held-out test sequence population...")
    # Prepend the tail of training data per school so early test records have preceding chronological context
    test_scores, meta_list = model.score_dataframe(
        df=test_df,
        prepend_history_df=train_df,
    )

    if len(test_scores) != len(test_df):
        print(f"  [WARN] Scored {len(test_scores)} windows vs {len(test_df)} test rows.")

    y_test = np.array([m["is_fraud"] for m in meta_list], dtype=int)
    scores = test_scores

    roc_auc = float(roc_auc_score(y_test, scores))
    pr_auc = float(average_precision_score(y_test, scores))

    y_pred = (scores >= threshold).astype(int)
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    print(f"  Results on held-out test set ({len(y_test):,} transactions):")
    print(f"   - ROC-AUC:   {roc_auc:.4f}")
    print(f"   - PR-AUC:    {pr_auc:.4f}")
    print(f"   - Precision: {prec:.4f} (at threshold {threshold})")
    print(f"   - Recall:    {rec:.4f} ({tp}/{tp+fn} frauds caught)")
    print(f"   - F1-Score:  {f1:.4f}")
    print(f"   - False Pos: {fp} / {fp+tn} normal records ({fpr*100:.2f}%)")
    print(f"   - Matrix:    TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    # Per fraud pattern breakdown
    print("\n  Per-Pattern Detection Recall:")
    pattern_stats = {}
    test_df_indexed = pd.DataFrame(meta_list)
    test_df_indexed["score"] = scores
    test_df_indexed["pred"] = y_pred

    for pattern, group in test_df_indexed.groupby("fraud_pattern"):
        if pattern == "NORMAL":
            continue
        total_p = len(group)
        caught_p = int(group["pred"].sum())
        rec_p = caught_p / total_p if total_p > 0 else 0.0
        avg_score = float(group["score"].mean())
        pattern_stats[pattern] = {
            "total": total_p,
            "detected": caught_p,
            "recall": round(rec_p, 4),
            "avg_score": round(avg_score, 4),
        }
        print(f"   - {pattern:<30} {caught_p:>2}/{total_p:<2} caught ({rec_p*100:>5.1f}%) | mean score: {avg_score:.4f}")

    print(f"\n[5/5] Saving model artifact to {output_model_path}...")
    model.save(output_model_path)
    file_size_kb = os.path.getsize(output_model_path) / 1024.0
    print(f"[OK] Model saved successfully ({file_size_kb:.1f} KB).")

    metrics_payload = {
        "model_id": "lstm_autoencoder_v1",
        "model_name": "LSTM Autoencoder Temporal Sequence Detector",
        "version": "v1.0.0",
        "seq_len": seq_len,
        "features": model.feature_names,
        "threshold": threshold,
        "test_records": int(len(y_test)),
        "test_frauds": int(y_test.sum()),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "patterns": pattern_stats,
        "artifact_path": output_model_path,
        "artifact_size_kb": round(file_size_kb, 1),
    }

    if metrics_out_path:
        os.makedirs(os.path.dirname(os.path.abspath(metrics_out_path)), exist_ok=True)
        with open(metrics_out_path, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f, indent=2)
        print(f"[OK] Evaluation metrics exported to {metrics_out_path}")

    return model, metrics_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LSTM Autoencoder Temporal Fraud Model")
    parser.add_argument(
        "--train-path",
        default=os.path.join(BACKEND_ROOT, "ml", "datasets", "synthetic_transactions_train.csv"),
    )
    parser.add_argument(
        "--test-path",
        default=os.path.join(BACKEND_ROOT, "ml", "datasets", "synthetic_transactions_test.csv"),
    )
    parser.add_argument(
        "--output-model-path",
        default=os.path.join(BACKEND_ROOT, "ml", "saved_models", "lstm_autoencoder_v1.joblib"),
    )
    parser.add_argument(
        "--metrics-out-path",
        default=os.path.join(BACKEND_ROOT, "ml", "saved_models", "lstm_autoencoder_v1_metrics.json"),
    )
    parser.add_argument("--seq-len", type=int, default=10)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--threshold", type=float, default=0.68)

    args = parser.parse_args()

    train_lstm_autoencoder(
        train_path=args.train_path,
        test_path=args.test_path,
        output_model_path=args.output_model_path,
        metrics_out_path=args.metrics_out_path,
        seq_len=args.seq_len,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        threshold=args.threshold,
    )
