"""
Feature Preprocessing Pipeline for Isolation Forest and Tabular Anomaly Detection.
Transforms raw transaction dictionaries or DataFrames into scaled/encoded feature matrices.
"""

from typing import List, Dict, Any, Union, Optional
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler, RobustScaler, OneHotEncoder
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
        if "transacted_at" in df.columns and df["transacted_at"].notnull().any():
            if not pd.api.types.is_datetime64_any_dtype(df["transacted_at"]):
                df["transacted_at"] = pd.to_datetime(df["transacted_at"], errors="coerce")
            df["hour_of_day"] = df["transacted_at"].dt.hour.fillna(12).astype(int)
            if hasattr(df["transacted_at"].dt, "day_of_week"):
                df["day_of_week"] = df["transacted_at"].dt.day_of_week.fillna(2).astype(int)
            else:
                df["day_of_week"] = df["transacted_at"].dt.dayofweek.fillna(2).astype(int)
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

        if "student_count" not in df.columns:
            sc_series = pd.Series(500.0, index=df.index)
        else:
            sc_series = pd.to_numeric(df["student_count"], errors="coerce").fillna(500.0)
        sc_series = np.where(sc_series <= 0, 1.0, sc_series)
        df["student_count"] = sc_series

        if "amount_per_student" not in df.columns:
            df["amount_per_student"] = df["amount"].astype(float) / sc_series
        if "log_amount_per_student" not in df.columns:
            df["log_amount_per_student"] = np.log1p(df["amount_per_student"])

        if "school_avg_amount" not in df.columns:
            school_avg = df["amount"].astype(float)
        else:
            school_avg = pd.to_numeric(df["school_avg_amount"], errors="coerce").fillna(df["amount"].astype(float))

        if "amount_to_school_avg_ratio" not in df.columns:
            df["amount_to_school_avg_ratio"] = df["amount"].astype(float) / (school_avg + 1.0)

        # Deviation Z-score from school historical baseline
        if "deviation_zscore" not in df.columns:
            if "school_std_amount" in df.columns:
                std_series = pd.to_numeric(df["school_std_amount"], errors="coerce").fillna(0.0)
                df["deviation_zscore"] = np.where(
                    std_series > 1e-4,
                    (df["amount"].astype(float) - school_avg) / std_series,
                    (df["amount"].astype(float) - school_avg) / (school_avg * 0.25 + 1.0),
                )
            else:
                df["deviation_zscore"] = (df["amount"].astype(float) - school_avg) / (school_avg * 0.25 + 1.0)

        # Per-student spending ratio compared to historical school per-student benchmark
        if "per_student_spending_ratio" not in df.columns:
            school_avg_per_student = school_avg / sc_series
            df["per_student_spending_ratio"] = df["amount_per_student"] / (school_avg_per_student + 1e-4)

        # Cyclical temporal features
        hours = df["hour_of_day"].astype(float)
        df["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
        df["sin_hour"] = df["hour_sin"]
        df["cos_hour"] = df["hour_cos"]

        if "rolling_24h_count" not in df.columns:
            df["rolling_24h_count"] = 1
        else:
            df["rolling_24h_count"] = pd.to_numeric(df["rolling_24h_count"], errors="coerce").fillna(1).astype(int)

        if "log_rolling_24h_amount" not in df.columns:
            if "rolling_24h_amount" not in df.columns:
                rolling_amt = df["amount"].astype(float)
            else:
                rolling_amt = pd.to_numeric(df["rolling_24h_amount"], errors="coerce").fillna(df["amount"].astype(float))
            df["log_rolling_24h_amount"] = np.log1p(rolling_amt)

        # Fill default types if missing
        if "type" not in df.columns or df["type"].isnull().any():
            df["type"] = df.get("type", pd.Series(["SUPPLIER_PAYMENT"] * len(df))).fillna("SUPPLIER_PAYMENT")
        if "payment_method" not in df.columns or df["payment_method"].isnull().any():
            df["payment_method"] = df.get("payment_method", pd.Series(["BANK_TRANSFER"] * len(df))).fillna("BANK_TRANSFER")

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


# Target feature sets for Autoencoder pattern reconstruction
AE_NUMERIC_FEATURES = [
    "log_amount",
    "log_amount_per_student",
    "amount_to_school_avg_ratio",
    "sin_hour",
    "cos_hour",
    "sin_day",
    "cos_day",
    "is_weekend",
    "is_off_hours",
    "rolling_24h_count",
    "log_rolling_24h_amount",
    "amount_to_rolling_ratio",
    "is_round_100k",
    "is_round_50k",
    "is_round_10k",
    "is_whole_integer",
]


class AutoencoderFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts continuous, cyclical, and structural pattern features for the
    Autoencoder reconstruction model. Preserves compatibility with raw dict
    API payloads and cleaned pandas DataFrames.
    """

    def __init__(self):
        self._base_extractor = TransactionFeatureExtractor()

    def fit(self, X: Union[pd.DataFrame, List[Dict[str, Any]]], y=None):
        return self

    def transform(self, X: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]) -> pd.DataFrame:
        df = self._base_extractor.transform(X)

        # Cyclical temporal coordinates for smooth manifold reconstruction
        hours = pd.to_numeric(df["hour_of_day"], errors="coerce").fillna(12.0)
        days = pd.to_numeric(df["day_of_week"], errors="coerce").fillna(2.0)
        df["sin_hour"] = np.sin(2.0 * np.pi * hours / 24.0)
        df["cos_hour"] = np.cos(2.0 * np.pi * hours / 24.0)
        df["sin_day"] = np.sin(2.0 * np.pi * days / 7.0)
        df["cos_day"] = np.cos(2.0 * np.pi * days / 7.0)

        # Rolling velocity share ratio
        amounts = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0).clip(lower=0.0)
        if "rolling_24h_amount" in df.columns:
            rolling_amt = pd.to_numeric(df["rolling_24h_amount"], errors="coerce").fillna(amounts).clip(lower=0.0)
        else:
            rolling_amt = np.expm1(pd.to_numeric(df["log_rolling_24h_amount"], errors="coerce").fillna(np.log1p(amounts)))
        rolling_amt = np.maximum(amounts, rolling_amt)
        df["amount_to_rolling_ratio"] = amounts / (rolling_amt + 1.0)

        # Round-number and structuring indicators (targets ROUND_NUMBER_DRAIN)
        rounded_amt = np.round(amounts, 2)
        df["is_round_100k"] = ((rounded_amt >= 100000.0) & (np.isclose(rounded_amt % 100000.0, 0.0, atol=1e-4))).astype(float)
        df["is_round_50k"] = ((rounded_amt >= 50000.0) & (np.isclose(rounded_amt % 50000.0, 0.0, atol=1e-4))).astype(float)
        df["is_round_10k"] = ((rounded_amt >= 10000.0) & (np.isclose(rounded_amt % 10000.0, 0.0, atol=1e-4))).astype(float)
        df["is_whole_integer"] = np.isclose(rounded_amt, np.floor(rounded_amt), atol=1e-4).astype(float)

        return df


def build_autoencoder_preprocessor() -> ColumnTransformer:
    """Creates a ColumnTransformer pipeline tailored for Autoencoder reconstruction."""
    return ColumnTransformer(
        transformers=[
            ("num", RobustScaler(), AE_NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def extract_ingestion_features(
    transaction_data: Union[Dict[str, Any], pd.DataFrame, List[Dict[str, Any]]],
    school_context: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Convenience function for the real-time ingestion pipeline.
    Combines raw transaction payload with school context (enrollment/student roll,
    county, historical average/median, standard deviation, rolling activity) and extracts
    cyclical temporal features (hour_sin, hour_cos), per-student spending ratios,
    and deviation Z-scores.
    """
    if isinstance(transaction_data, list):
        df = pd.DataFrame(transaction_data)
    elif isinstance(transaction_data, dict):
        df = pd.DataFrame([transaction_data])
    else:
        df = transaction_data.copy()

    # Overlay school context if provided
    if school_context:
        if "student_count" in school_context and "student_count" not in df.columns:
            df["student_count"] = school_context["student_count"]
        if "school_avg_amount" in school_context and "school_avg_amount" not in df.columns:
            df["school_avg_amount"] = school_context["school_avg_amount"]
        if "school_std_amount" in school_context and "school_std_amount" not in df.columns:
            df["school_std_amount"] = school_context["school_std_amount"]
        if "rolling_24h_count" in school_context and "rolling_24h_count" not in df.columns:
            df["rolling_24h_count"] = school_context["rolling_24h_count"]
        if "rolling_24h_amount" in school_context and "rolling_24h_amount" not in df.columns:
            df["rolling_24h_amount"] = school_context["rolling_24h_amount"]

    extractor = AutoencoderFeatureExtractor()
    return extractor.transform(df)

