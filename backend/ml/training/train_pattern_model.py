"""
DSFMP Fraud Detection System — Train Autoencoder Pattern Reconstruction Model
Trains the Autoencoder strictly on normal (is_fraud == 0) transactions so that
anomalous behavior and round-number/structuring patterns incur high reconstruction error.
Saves serialized model artifact to `backend/ml/saved_models/autoencoder_v1.joblib`.
"""

import os
import sys
import json
import argparse
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

# Allow running directly as a script from repo or backend root
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from ml.features.cleaning import TransactionDataCleaner
from ml.models.autoencoder import AutoencoderFraudModel


def train_autoencoder(
    train_path: str,
    test_path: str,
    output_model_path: str,
    threshold: float = 0.70,
    max_iter: int = 500,
    metrics_out_path: str = None,
):
    print("=" * 70)
    print("  DSFMP FRAUD DETECTION — AUTOENCODER TRAINING PIPELINE")
    print("=" * 70)

    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Training dataset not found: {train_path}")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Testing dataset not found: {test_path}")

    print("\n[1/5] Loading raw synthetic datasets...")
    train_raw = pd.read_csv(train_path)
    test_raw = pd.read_csv(test_path)
    print(f" - Train set raw: {len(train_raw):,} records ({int(train_raw['is_fraud'].sum()):,} frauds)")
    print(f" - Test set raw:  {len(test_raw):,} records ({int(test_raw['is_fraud'].sum()):,} frauds)")

    print("\n[2/5] Cleaning datasets (semi-supervised: normal transactions only for training)...")
    cleaner = TransactionDataCleaner(remove_duplicates=True, clip_extreme_negatives=True)
    train_df = cleaner.clean(train_raw, is_training=True, normal_only_for_training=True)
    test_df = cleaner.clean(test_raw, is_training=False)
    print(
        f" - Cleaned normal-only train set: {len(train_df):,} records "
        f"(Duplicates removed: {cleaner.cleaning_stats.get('duplicates_removed', 0)})"
    )
    print(f" - Cleaned holdout test set:      {len(test_df):,} records")

    print(f"\n[3/5] Fitting Symmetric Bottleneck Autoencoder (max_iter={max_iter})...")
    model = AutoencoderFraudModel(
        hidden_layer_sizes=(24, 10, 4, 10, 24),
        activation="relu",
        alpha=1e-4,
        max_iter=max_iter,
        random_state=42,
        validation_fraction=0.15,
    )
    model.fit(train_df)
    print(
        f" - Training stopped at epoch {model.model.n_iter_} "
        f"(final loss={model.model.loss_:.6f})."
    )
    print(
        f" - Calibration bounds (normal validation MSE): "
        f"P10={model._err_low:.6f}, P99={model._err_p99:.6f}"
    )

    print(f"\n[4/5] Evaluating on isolated holdout test set (Threshold = {threshold:.2f})...")
    test_scores = model.score_samples(test_df)
    y_pred = (test_scores >= threshold).astype(int)
    y_true = test_df["is_fraud"].values

    roc_auc = float(roc_auc_score(y_true, test_scores))
    pr_auc = float(average_precision_score(y_true, test_scores))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0][0]), int(cm[0][1]), int(cm[1][0]), int(cm[1][1])

    print("\n" + "-" * 54)
    print("  AUTOENCODER EVALUATION RESULTS ON TEST SET")
    print("-" * 54)
    print(f"  ROC-AUC Score:      {roc_auc:.4f}")
    print(f"  PR-AUC (Avg Prec):  {pr_auc:.4f}")
    print(f"  Precision:          {prec:.4f} ({prec:.1%})")
    print(f"  Recall:             {rec:.4f} ({rec:.1%})")
    print(f"  F1-Score:           {f1:.4f}")
    print("\n  Confusion Matrix:")
    print(f"    TN: {tn:<6}  FP: {fp:<6}")
    print(f"    FN: {fn:<6}  TP: {tp:<6}")
    print("-" * 54)

    test_df_eval = test_df.copy()
    test_df_eval["pred_fraud"] = y_pred
    test_df_eval["anomaly_score"] = test_scores

    print("\nDetection Rate Breakdown by Fraud Pattern:")
    pattern_breakdown = {}
    fraud_patterns = test_df_eval[test_df_eval["is_fraud"] == 1]["fraud_pattern"].unique()
    for pattern in sorted(fraud_patterns):
        subset = test_df_eval[test_df_eval["fraud_pattern"] == pattern]
        detected = int(subset["pred_fraud"].sum())
        total = int(len(subset))
        avg_score = float(subset["anomaly_score"].mean())
        pattern_breakdown[pattern] = {
            "detected": detected,
            "total": total,
            "rate": round(detected / total, 4) if total else 0.0,
            "avg_score": round(avg_score, 4),
        }
        print(
            f"  - {pattern:<30}: {detected}/{total} caught ({detected/total:.1%}) "
            f"| Avg Score: {avg_score:.3f}"
        )

    print("\n[5/5] Saving Autoencoder model artifact...")
    model.save(output_model_path)

    if metrics_out_path:
        os.makedirs(os.path.dirname(os.path.abspath(metrics_out_path)), exist_ok=True)
        with open(metrics_out_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "model_name": "Autoencoder",
                    "version": "v1.0.0",
                    "architecture": list(model.hidden_layer_sizes),
                    "threshold": threshold,
                    "roc_auc": round(roc_auc, 4),
                    "average_precision": round(pr_auc, 4),
                    "precision": round(prec, 4),
                    "recall": round(rec, 4),
                    "f1": round(f1, 4),
                    "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
                    "pattern_breakdown": pattern_breakdown,
                },
                fh,
                indent=2,
            )

    # Sample round-number drain & normal sanity check
    normal_row = test_df[test_df["is_fraud"] == 0].iloc[0].to_dict()
    round_rows = test_df[test_df["fraud_pattern"] == "ROUND_NUMBER_DRAIN"]
    print("\n[TEST] Sample single-record inference check:")
    print(
        f" - Normal sample (KES {normal_row['amount']:,.2f}): "
        f"score={model.score_single(normal_row):.4f}"
    )
    if len(round_rows) > 0:
        round_row = round_rows.iloc[0].to_dict()
        print(
            f" - Round-Number Drain sample (KES {round_row['amount']:,.2f}): "
            f"score={model.score_single(round_row):.4f}, "
            f"top_drivers={model.explain_reconstruction(round_row, top_k=2)}"
        )

    print("\n[COMPLETE] Autoencoder artifact saved and ready!\n")
    return model


def main():
    parser = argparse.ArgumentParser(
        description="Train Autoencoder pattern model for DSFMP Fraud Detection."
    )
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ml_root = os.path.dirname(script_dir)

    default_train = os.path.join(ml_root, "datasets", "synthetic_transactions_train.csv")
    default_test = os.path.join(ml_root, "datasets", "synthetic_transactions_test.csv")
    default_model = os.path.join(ml_root, "saved_models", "autoencoder_v1.joblib")

    parser.add_argument("--train-data", type=str, default=default_train)
    parser.add_argument("--test-data", type=str, default=default_test)
    parser.add_argument("--model-out", type=str, default=default_model)
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--max-iter", type=int, default=500)
    parser.add_argument("--metrics-out", type=str, default=None)

    args = parser.parse_args()

    train_autoencoder(
        train_path=args.train_data,
        test_path=args.test_data,
        output_model_path=args.model_out,
        threshold=args.threshold,
        max_iter=args.max_iter,
        metrics_out_path=args.metrics_out,
    )


if __name__ == "__main__":
    main()
