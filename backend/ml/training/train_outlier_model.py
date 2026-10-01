"""
DSFMP Fraud Detection System — Train Isolation Forest Outlier Model
Trains and evaluates the Isolation Forest model on the synthetic transaction dataset.
Saves model artifact to `backend/ml/saved_models/isolation_forest_v1.joblib`.
"""

import os
import argparse
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix, precision_score, recall_score, f1_score

from ml.features.cleaning import TransactionDataCleaner
from ml.models.isolation_forest import IsolationForestFraudModel


def train_isolation_forest(
    train_path: str,
    test_path: str,
    output_model_path: str,
    contamination: float = 0.05,
    threshold: float = 0.65,
    clean_normal_only: bool = False
):
    print("=" * 70)
    print("  DSFMP FRAUD DETECTION — ISOLATION FOREST TRAINING PIPELINE")
    print("=" * 70)

    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Training dataset not found: {train_path}")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Testing dataset not found: {test_path}")

    print(f"\n[1/5] Loading raw synthetic datasets...")
    train_raw = pd.read_csv(train_path)
    test_raw = pd.read_csv(test_path)
    print(f" - Train set raw: {len(train_raw):,} records ({train_raw['is_fraud'].sum():,} frauds)")
    print(f" - Test set raw:  {len(test_raw):,} records ({test_raw['is_fraud'].sum():,} frauds)")

    print(f"\n[2/5] Cleaning and sanitizing datasets with TransactionDataCleaner...")
    cleaner = TransactionDataCleaner(remove_duplicates=True, clip_extreme_negatives=True)
    train_df = cleaner.clean(train_raw, is_training=True, normal_only_for_training=clean_normal_only)
    test_df = cleaner.clean(test_raw, is_training=False)
    print(f" - Cleaned train set: {len(train_df):,} records (Duplicates removed: {cleaner.cleaning_stats.get('duplicates_removed', 0)})")
    print(f" - Cleaned test set:  {len(test_df):,} records")
    print(" - Imputed missing supplier values for subsidy & parent contribution records.")
    print(" - Sanitized zero-division ratios and infinite bounds.")

    print(f"\n[3/5] Fitting Isolation Forest model (contamination={contamination:.3f})...")
    # In unsupervised anomaly detection, Isolation Forest learns from the feature distribution
    model = IsolationForestFraudModel(
        n_estimators=200,
        contamination=contamination,
        random_state=42
    )
    model.fit(train_df)
    print(" - Isolation Forest fitting complete.")

    print(f"\n[4/5] Evaluating on test set (Classification Threshold = {threshold:.2f})...")
    test_scores = model.score_samples(test_df)
    y_pred = (test_scores >= threshold).astype(int)
    y_true = test_df["is_fraud"].values

    # Evaluation metrics
    roc_auc = roc_auc_score(y_true, test_scores)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    print("\n" + "-" * 50)
    print("  EVALUATION RESULTS ON TEST SET")
    print("-" * 50)
    print(f"  ROC-AUC Score:      {roc_auc:.4f}")
    print(f"  Precision:          {prec:.4f} ({prec:.1%})")
    print(f"  Recall:             {rec:.4f} ({rec:.1%})")
    print(f"  F1-Score:           {f1:.4f}")
    print("\n  Confusion Matrix:")
    print(f"    TN: {cm[0][0]:<6}  FP: {cm[0][1]:<6}")
    print(f"    FN: {cm[1][0]:<6}  TP: {cm[1][1]:<6}")
    print("-" * 50)

    # Detailed breakdown by fraud pattern
    test_df_eval = test_df.copy()
    test_df_eval["pred_fraud"] = y_pred
    test_df_eval["anomaly_score"] = test_scores
    
    print("\nDetection Rate Breakdown by Fraud Pattern:")
    fraud_patterns = test_df_eval[test_df_eval["is_fraud"] == 1]["fraud_pattern"].unique()
    for pattern in sorted(fraud_patterns):
        subset = test_df_eval[test_df_eval["fraud_pattern"] == pattern]
        detected = subset["pred_fraud"].sum()
        total = len(subset)
        avg_score = subset["anomaly_score"].mean()
        print(f"  - {pattern:<30}: {detected}/{total} caught ({detected/total:.1%}) | Avg Score: {avg_score:.3f}")

    print(f"\n[5/5] Saving model artifact...")
    model.save(output_model_path)

    # Sample single prediction test
    sample_txn = test_df.iloc[0].to_dict()
    sample_score = model.score_single(sample_txn)
    print(f"\n[TEST] Sample inference check:")
    print(f" - Amount: KES {sample_txn['amount']:,.2f}")
    print(f" - School: {sample_txn.get('school_name', 'N/A')}")
    print(f" - Predicted Anomaly Score: {sample_score:.4f} (True Label: {sample_txn['is_fraud']})")
    print("\n[COMPLETE] Model is ready for deployment in the DSFMP scoring pipeline!\n")


def main():
    parser = argparse.ArgumentParser(description="Train Isolation Forest model for DSFMP Fraud Detection.")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ml_root = os.path.dirname(script_dir)

    default_train = os.path.join(ml_root, "datasets", "synthetic_transactions_train.csv")
    default_test = os.path.join(ml_root, "datasets", "synthetic_transactions_test.csv")
    default_model = os.path.join(ml_root, "saved_models", "isolation_forest_v1.joblib")

    parser.add_argument("--train-data", type=str, default=default_train)
    parser.add_argument("--test-data", type=str, default=default_test)
    parser.add_argument("--model-out", type=str, default=default_model)
    parser.add_argument("--contamination", type=float, default=0.05)
    parser.add_argument("--threshold", type=float, default=0.65)

    args = parser.parse_args()

    train_isolation_forest(
        train_path=args.train_data,
        test_path=args.test_data,
        output_model_path=args.model_out,
        contamination=args.contamination,
        threshold=args.threshold
    )


if __name__ == "__main__":
    main()
