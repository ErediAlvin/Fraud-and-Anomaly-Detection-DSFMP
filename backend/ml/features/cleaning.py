"""
DSFMP Fraud Detection System — Data Cleaning & Validation Pipeline
Cleans, sanitizes, and validates transaction datasets prior to model training
and feature extraction for Isolation Forest, Autoencoders, and supervised models.
"""

from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import pandas as pd


# Explicit categoricals with known valid domain choices
VALID_TRANSACTION_TYPES = [
    "SUBSIDY_DISBURSEMENT",
    "SUPPLIER_PAYMENT",
    "PARENTAL_CONTRIBUTION",
    "MPESA_PAYMENT",
    "REFUND",
    "ADJUSTMENT"
]

VALID_PAYMENT_METHODS = ["MPESA", "BANK_TRANSFER", "CHEQUE", "CASH", "SYSTEM"]


class TransactionDataCleaner:
    """
    Sanitizes raw transaction data, imputes missing values, removes duplicates,
    enforces correct datatypes, handles infinite/NaN values, and isolates metadata.
    """

    def __init__(
        self,
        impute_strategy: str = "domain_defaults",
        remove_duplicates: bool = True,
        clip_extreme_negatives: bool = True
    ):
        self.impute_strategy = impute_strategy
        self.remove_duplicates = remove_duplicates
        self.clip_extreme_negatives = clip_extreme_negatives
        self.cleaning_stats: Dict[str, Any] = {}

    def clean(
        self,
        df: pd.DataFrame,
        is_training: bool = False,
        normal_only_for_training: bool = False
    ) -> pd.DataFrame:
        """
        Executes full end-to-end data cleaning pipeline.

        Args:
            df: Input DataFrame with raw transactions.
            is_training: Whether dataset is being prepared for training.
            normal_only_for_training: If True, filters out known fraud labels (for semi-supervised models).
        """
        data = df.copy()
        initial_rows = len(data)

        # 1. Deduplication
        if self.remove_duplicates and "transaction_id" in data.columns:
            data = data.drop_duplicates(subset=["transaction_id"]).reset_index(drop=True)
        dup_count = initial_rows - len(data)

        # 2. Timestamp Cleaning & Parsing
        if "transacted_at" in data.columns:
            data["transacted_at"] = pd.to_datetime(data["transacted_at"], errors="coerce")
            # Fill missing timestamps with current time
            data["transacted_at"] = data["transacted_at"].fillna(pd.Timestamp.now(tz="UTC"))
            data["hour_of_day"] = data["transacted_at"].dt.hour
            data["day_of_week"] = data["transacted_at"].dt.dayofweek
            data["is_weekend"] = data["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)
            data["is_off_hours"] = data["hour_of_day"].apply(lambda h: 1 if (h < 6 or h >= 22) else 0)

        # 3. Categorical Missing Value Imputation
        # For non-supplier transactions (subsidies, parent payments), supplier fields are naturally null.
        if "supplier_id" in data.columns:
            data["supplier_id"] = data["supplier_id"].fillna("UNSPECIFIED_SUPPLIER").astype(str).str.strip()
        if "supplier_name" in data.columns:
            data["supplier_name"] = data["supplier_name"].fillna("Direct School Allocation / Beneficiary").astype(str).str.strip()
        if "supplier_category" in data.columns:
            data["supplier_category"] = data["supplier_category"].fillna("NONE").astype(str).str.strip().str.upper()

        if "county" in data.columns:
            data["county"] = data["county"].fillna("UNKNOWN_COUNTY").astype(str).str.strip()
        if "school_name" in data.columns:
            data["school_name"] = data["school_name"].fillna("Unknown School").astype(str).str.strip()

        # Sanitize transaction types and payment methods
        if "type" in data.columns:
            data["type"] = data["type"].astype(str).str.strip().str.upper()
            data["type"] = data["type"].apply(lambda t: t if t in VALID_TRANSACTION_TYPES else "SUPPLIER_PAYMENT")
        else:
            data["type"] = "SUPPLIER_PAYMENT"

        if "payment_method" in data.columns:
            data["payment_method"] = data["payment_method"].astype(str).str.strip().str.upper()
            data["payment_method"] = data["payment_method"].apply(lambda m: m if m in VALID_PAYMENT_METHODS else "BANK_TRANSFER")
        else:
            data["payment_method"] = "BANK_TRANSFER"

        # 4. Numerical Sanitization & Imputation
        if "amount" in data.columns:
            data["amount"] = pd.to_numeric(data["amount"], errors="coerce").fillna(0.0)
            if self.clip_extreme_negatives:
                # Financial disbursements cannot be negative (refunds are positive with type=REFUND)
                data["amount"] = data["amount"].clip(lower=0.0)
        else:
            data["amount"] = 0.0

        if "student_count" in data.columns:
            data["student_count"] = pd.to_numeric(data["student_count"], errors="coerce").fillna(500)
            data["student_count"] = data["student_count"].clip(lower=1)  # Prevent division by zero
        else:
            data["student_count"] = 500

        if "school_avg_amount" in data.columns:
            data["school_avg_amount"] = pd.to_numeric(data["school_avg_amount"], errors="coerce")
            # If school avg missing, fallback to median amount or transaction amount
            fallback_avg = data["amount"].median() if len(data) > 0 else 100000.0
            data["school_avg_amount"] = data["school_avg_amount"].fillna(fallback_avg).clip(lower=1.0)
        else:
            data["school_avg_amount"] = data["amount"].clip(lower=1.0)

        if "rolling_24h_count" in data.columns:
            data["rolling_24h_count"] = pd.to_numeric(data["rolling_24h_count"], errors="coerce").fillna(1).astype(int).clip(lower=1)
        else:
            data["rolling_24h_count"] = 1

        if "rolling_24h_amount" in data.columns:
            data["rolling_24h_amount"] = pd.to_numeric(data["rolling_24h_amount"], errors="coerce").fillna(data["amount"]).clip(lower=0.0)
        else:
            data["rolling_24h_amount"] = data["amount"]

        # 5. Robust Feature Engineering & Zero-Division Guards
        data["log_amount"] = np.log1p(data["amount"])
        data["amount_per_student"] = data["amount"] / data["student_count"]
        data["log_amount_per_student"] = np.log1p(data["amount_per_student"])
        data["amount_to_school_avg_ratio"] = data["amount"] / data["school_avg_amount"]
        data["log_rolling_24h_amount"] = np.log1p(data["rolling_24h_amount"])

        # Check for any remaining inf or nan values in numeric fields
        numeric_cols = [
            "amount", "student_count", "log_amount", "amount_per_student",
            "log_amount_per_student", "amount_to_school_avg_ratio",
            "rolling_24h_count", "log_rolling_24h_amount"
        ]
        for col in numeric_cols:
            data[col] = data[col].replace([np.inf, -np.inf], np.nan)
            col_median = data[col].median() if not pd.isna(data[col].median()) else 0.0
            data[col] = data[col].fillna(col_median)

        # 6. Label Sanitization
        if "is_fraud" in data.columns:
            data["is_fraud"] = pd.to_numeric(data["is_fraud"], errors="coerce").fillna(0).astype(int)
        if "fraud_pattern" in data.columns:
            data["fraud_pattern"] = data["fraud_pattern"].fillna("NORMAL").astype(str)

        # 7. Optional Training Filtering
        if is_training and normal_only_for_training and "is_fraud" in data.columns:
            data = data[data["is_fraud"] == 0].reset_index(drop=True)

        # Record cleaning statistics
        self.cleaning_stats = {
            "initial_rows": initial_rows,
            "final_rows": len(data),
            "duplicates_removed": dup_count,
            "nulls_handled": initial_rows - len(data.dropna(subset=["amount", "transacted_at"]))
        }

        return data

    def split_features_and_metadata(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.Series]]:
        """
        Splits a cleaned DataFrame into:
        1. Feature DataFrame (for feeding into ML model).
        2. Metadata DataFrame (for DB persistence, audits, alerts).
        3. Labels Series (if present, for evaluation or supervised training).
        """
        feature_cols = [
            "log_amount",
            "log_amount_per_student",
            "amount_to_school_avg_ratio",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "is_off_hours",
            "rolling_24h_count",
            "log_rolling_24h_amount",
            "type",
            "payment_method"
        ]

        metadata_cols = [
            col for col in df.columns if col not in feature_cols and col not in ["is_fraud", "fraud_pattern"]
        ]

        X = df[feature_cols].copy()
        meta = df[metadata_cols].copy() if metadata_cols else pd.DataFrame(index=df.index)
        y = df["is_fraud"].copy() if "is_fraud" in df.columns else None

        return X, meta, y
