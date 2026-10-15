"""
Feature Preprocessing Pipeline for Isolation Forest and Tabular Anomaly Detection.
Transforms raw transaction dictionaries or DataFrames into scaled/encoded feature matrices.
"""

from typing import List, Dict, Any, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer


# Target tabular feature sets for Isolation Forest
NUMERIC_FEATURES = [
    "log_amount",
    "log_amount_per_student",
    "amount_to_school_avg_ratio",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_off_hours",
    "rolling_24h_count",
    "log_rolling_24h_amount"
]

CATEGORICAL_FEATURES = [
    "type",
    "payment_method"
]


class TransactionFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts numerical and ratio features from raw transaction records.
    Can accept pandas DataFrames or raw dictionaries from API endpoints.
    """

    def fit(self, X: Union[pd.DataFrame, List[Dict[str, Any]]], y=None):
        return self

    def transform(self, X: Union[pd.DataFrame, List[Dict[str, Any]]]) -> pd.DataFrame:
        if isinstance(X, list):
            df = pd.DataFrame(X)
        elif isinstance(X, dict):
            df = pd.DataFrame([X])
        else:
            df = X.copy()

        # Parse timestamp if string
        if "transacted_at" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["transacted_at"]):
                df["transacted_at"] = pd.to_datetime(df["transacted_at"])
            df["hour_of_day"] = df["transacted_at"].dt.hour
            df["day_of_week"] = df["transacted_at"].dt.dayofweek
        else:
            if "hour_of_day" not in df.columns:
                df["hour_of_day"] = 12
            if "day_of_week" not in df.columns:
                df["day_of_week"] = 2

        if "is_weekend" not in df.columns:
            df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)
        if "is_off_hours" not in df.columns:
            df["is_off_hours"] = df["hour_of_day"].apply(lambda h: 1 if (h < 6 or h >= 22) else 0)

        # Amounts and ratios
        if "log_amount" not in df.columns:
            df["log_amount"] = np.log1p(df["amount"].astype(float))

        student_count = df.get("student_count", 500).fillna(500).astype(float)
        student_count = np.where(student_count <= 0, 1.0, student_count)
        
        if "amount_per_student" not in df.columns:
            df["amount_per_student"] = df["amount"].astype(float) / student_count
        if "log_amount_per_student" not in df.columns:
            df["log_amount_per_student"] = np.log1p(df["amount_per_student"])

        school_avg = df.get("school_avg_amount", df["amount"].astype(float)).fillna(df["amount"].astype(float))
        if "amount_to_school_avg_ratio" not in df.columns:
            df["amount_to_school_avg_ratio"] = df["amount"].astype(float) / (school_avg + 1.0)

        if "rolling_24h_count" not in df.columns:
            df["rolling_24h_count"] = 1
        if "log_rolling_24h_amount" not in df.columns:
            rolling_amt = df.get("rolling_24h_amount", df["amount"]).fillna(df["amount"]).astype(float)
            df["log_rolling_24h_amount"] = np.log1p(rolling_amt)

        # Fill default types if missing
        if "type" not in df.columns:
            df["type"] = "SUPPLIER_PAYMENT"
        if "payment_method" not in df.columns:
            df["payment_method"] = "BANK_TRANSFER"

        return df


def build_preprocessor() -> ColumnTransformer:
    """Creates a ColumnTransformer pipeline for Isolation Forest."""
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES)
        ],
        remainder="drop"
    )
