"""
DSFMP Fraud Detection System — Temporal Feature & Sequence Engineering
Extracts inter-transaction temporal cadence, school-level rolling EWMA baselines,
cyclical timing signals, and constructs strictly causal sliding sequence windows
for the LSTM Autoencoder without future data leakage.
"""

import math
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler


TEMPORAL_NUMERIC_FEATURES = [
    # Inter-transaction temporal cadence
    "log_hours_since_prev",
    "rolling_7d_count",
    "log_rolling_7d_amount",
    "amount_ewma_ratio",
    # Core transaction value & ratios
    "log_amount",
    "log_amount_per_student",
    "amount_to_school_avg_ratio",
    "amount_to_rolling_ratio",
    # 24h short-term velocity
    "rolling_24h_count",
    "log_rolling_24h_amount",
    # Cyclical & operational schedule flags
    "sin_hour",
    "cos_hour",
    "sin_day",
    "cos_day",
    "is_weekend",
    "is_off_hours",
    # Structural amount patterns
    "is_round_100k",
    "is_round_50k",
    "is_round_10k",
    "is_whole_integer",
]

TX_TYPES = [
    "SUBSIDY_DISBURSEMENT",
    "SUPPLIER_PAYMENT",
    "PARENTAL_CONTRIBUTION",
    "MPESA_PAYMENT",
    "REFUND",
    "ADJUSTMENT",
]

PAYMENT_METHODS = ["BANK_TRANSFER", "MPESA", "CHEQUE", "CASH", "SYSTEM"]


class TemporalSequenceBuilder(BaseEstimator, TransformerMixin):
    """
    Transforms raw school feeding transactions into structured temporal feature matrices
    and causal sliding sequence windows of shape (N, seq_len, num_features).
    """

    def __init__(self, seq_len: int = 10, default_window_hours: float = 24.0):
        self.seq_len = seq_len
        self.default_window_hours = default_window_hours
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_names: List[str] = []

    def _extract_step_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes causal step-level features sorted strictly by (school_id, transacted_at)."""
        df = df.copy()

        # Parse timestamp safely
        if "transacted_at" in df.columns:
            df["transacted_at"] = pd.to_datetime(df["transacted_at"], utc=True, errors="coerce")
        else:
            df["transacted_at"] = pd.Timestamp.now(tz="UTC")
        df["transacted_at"] = df["transacted_at"].fillna(pd.Timestamp.now(tz="UTC"))

        if "school_id" not in df.columns or df["school_id"].isnull().all():
            df["school_id"] = "DEFAULT_SCHOOL"
        else:
            df["school_id"] = df["school_id"].fillna("DEFAULT_SCHOOL").astype(str)

        # Sort chronologically per school (strictly causal)
        df = df.sort_values(by=["school_id", "transacted_at"]).reset_index(drop=True)

        # Amounts & counts
        amt_series = df["amount"] if "amount" in df.columns else pd.Series(0.0, index=df.index)
        amount = pd.to_numeric(amt_series, errors="coerce").fillna(0.0).astype(float)
        
        sc_series = df["student_count"] if "student_count" in df.columns else pd.Series(500.0, index=df.index)
        student_count = pd.to_numeric(sc_series, errors="coerce").fillna(500.0).clip(lower=1.0)
        
        avg_series = df["school_avg_amount"] if "school_avg_amount" in df.columns else amount
        school_avg = pd.to_numeric(avg_series, errors="coerce").fillna(amount)

        df["log_amount"] = np.log1p(np.maximum(0.0, amount))
        df["amount_per_student"] = amount / student_count
        df["log_amount_per_student"] = np.log1p(np.maximum(0.0, df["amount_per_student"]))
        df["amount_to_school_avg_ratio"] = amount / (school_avg + 1.0)

        # 24h rolling velocity
        r24_cnt_series = df["rolling_24h_count"] if "rolling_24h_count" in df.columns else pd.Series(1, index=df.index)
        r24_cnt = pd.to_numeric(r24_cnt_series, errors="coerce").fillna(1).astype(float)
        
        r24_amt_series = df["rolling_24h_amount"] if "rolling_24h_amount" in df.columns else amount
        r24_amt = pd.to_numeric(r24_amt_series, errors="coerce").fillna(amount).astype(float)
        r24_amt = np.maximum(amount, r24_amt)
        df["rolling_24h_count"] = r24_cnt
        df["log_rolling_24h_amount"] = np.log1p(np.maximum(0.0, r24_amt))
        df["amount_to_rolling_ratio"] = amount / (r24_amt + 1.0)

        # Cyclical & timing features
        dt = df["transacted_at"].dt
        hour = dt.hour.fillna(12).astype(float)
        day = (dt.day_of_week if hasattr(dt, "day_of_week") else dt.dayofweek).fillna(0).astype(float)
        df["sin_hour"] = np.sin(2.0 * math.pi * hour / 24.0)
        df["cos_hour"] = np.cos(2.0 * math.pi * hour / 24.0)
        df["sin_day"] = np.sin(2.0 * math.pi * day / 7.0)
        df["cos_day"] = np.cos(2.0 * math.pi * day / 7.0)
        df["is_weekend"] = (day >= 5).astype(float)
        df["is_off_hours"] = ((hour < 6) | (hour >= 18)).astype(float)

        # Structural amount patterns
        mod_100k = amount % 100000.0
        mod_50k = amount % 50000.0
        mod_10k = amount % 10000.0
        df["is_round_100k"] = ((amount >= 100000.0) & (mod_100k == 0.0)).astype(float)
        df["is_round_50k"] = ((amount >= 50000.0) & (mod_50k == 0.0)).astype(float)
        df["is_round_10k"] = ((amount >= 10000.0) & (mod_10k == 0.0)).astype(float)
        df["is_whole_integer"] = ((amount > 0.0) & (amount == np.floor(amount))).astype(float)

        # ── Group-by school inter-transaction temporal dynamics ──
        hours_since_prev_list: List[float] = []
        r7d_cnt_list: List[float] = []
        r7d_amt_list: List[float] = []
        ewma_ratio_list: List[float] = []

        for _, grp in df.groupby("school_id", sort=False):
            grp_ts = grp["transacted_at"].dt.tz_convert(None).to_numpy()
            grp_amt = grp["log_amount"].values
            raw_amt = amount.loc[grp.index].values

            # Time delta in hours
            deltas = np.diff(grp_ts).astype("timedelta64[s]").astype(float) / 3600.0
            # First transaction in series defaults to standard neutral gap
            school_hours = [self.default_window_hours] + [max(0.01, d) for d in deltas]
            hours_since_prev_list.extend(school_hours)

            # Rolling 7-day velocity (168 hours) using chronological window
            n_grp = len(grp)
            grp_dt = grp["transacted_at"].tolist()
            w_left = 0
            cur_7d_amt = 0.0
            for r in range(n_grp):
                cur_7d_amt += raw_amt[r]
                cutoff = grp_dt[r] - pd.Timedelta(days=7)
                while w_left < r and grp_dt[w_left] < cutoff:
                    cur_7d_amt -= raw_amt[w_left]
                    w_left += 1
                r7d_cnt_list.append(float(r - w_left + 1))
                r7d_amt_list.append(max(0.0, float(cur_7d_amt)))

            # Exponential Moving Average baseline (strictly shifted by 1 so current step doesn't leak)
            # EWMA(span=8)
            ewma_series = pd.Series(raw_amt).ewm(span=8, adjust=False).mean().shift(1)
            # For the very first record, fallback to raw_amt
            ewma_series = ewma_series.fillna(raw_amt[0] if n_grp > 0 else 100000.0)
            ratios = raw_amt / (ewma_series.values + 1.0)
            ewma_ratio_list.extend(ratios.tolist())

        df["log_hours_since_prev"] = np.log1p(np.clip(hours_since_prev_list, 0.0, 720.0))
        df["rolling_7d_count"] = r7d_cnt_list
        df["log_rolling_7d_amount"] = np.log1p(np.maximum(0.0, r7d_amt_list))
        df["amount_ewma_ratio"] = np.clip(ewma_ratio_list, 0.0, 50.0)

        # One-hot categorical indicators
        for t in TX_TYPES:
            col = f"type_{t}"
            df[col] = (df.get("type", "") == t).astype(float)
        for pm in PAYMENT_METHODS:
            col = f"pm_{pm}"
            df[col] = (df.get("payment_method", "") == pm).astype(float)

        return df

    def fit(self, X: pd.DataFrame, y=None):
        """Fits StandardScaler on normal/training step features."""
        df_feat = self._extract_step_features(X)
        feat_cols = self._get_feature_columns(df_feat)
        self.feature_names = feat_cols
        X_mat = df_feat[feat_cols].values.astype(np.float32)
        X_mat = np.nan_to_num(X_mat, nan=0.0, posinf=5.0, neginf=-5.0)
        self.scaler.fit(X_mat)
        self.is_fitted = True
        return self

    def transform_steps(self, X: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """Transforms DataFrame into 2D scaled feature matrix (N, F)."""
        if not self.is_fitted:
            raise RuntimeError("TemporalSequenceBuilder must be fitted before calling transform_steps.")
        df_feat = self._extract_step_features(X)
        feat_cols = self.feature_names
        X_mat = df_feat[feat_cols].values.astype(np.float32)
        X_mat = np.nan_to_num(X_mat, nan=0.0, posinf=5.0, neginf=-5.0)
        scaled = self.scaler.transform(X_mat).astype(np.float32)
        return scaled, df_feat

    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        cols = [c for c in TEMPORAL_NUMERIC_FEATURES if c in df.columns]
        for t in TX_TYPES:
            c = f"type_{t}"
            if c in df.columns:
                cols.append(c)
        for pm in PAYMENT_METHODS:
            c = f"pm_{pm}"
            if c in df.columns:
                cols.append(c)
        return cols

    def build_sliding_windows(
        self,
        df: pd.DataFrame,
        normal_only: bool = False,
        prepend_history_df: Optional[pd.DataFrame] = None,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Constructs causal sliding sequence windows of shape (N, seq_len, F).
        
        Args:
            df: Target DataFrame of transactions to score or train on.
            normal_only: If True, only keep windows where every step in the window has is_fraud == 0.
            prepend_history_df: Preceding historical transactions per school to provide context for early rows.
        
        Returns:
            sequences: np.ndarray of shape (N_windows, seq_len, F)
            metadata: list of dicts with target transaction metadata (transaction_id, school_id, is_fraud, transacted_at)
        """
        combined = df.copy()
        target_indices_set = set(combined.index)

        if prepend_history_df is not None and not prepend_history_df.empty:
            prep = prepend_history_df.copy()
            prep["_is_preceding_history"] = True
            combined["_is_preceding_history"] = False
            full_df = pd.concat([prep, combined], ignore_index=True)
        else:
            full_df = combined
            full_df["_is_preceding_history"] = False

        scaled_matrix, enriched_df = self.transform_steps(full_df)

        windows: List[np.ndarray] = []
        meta_list: List[Dict[str, Any]] = []

        for school_id, grp in enriched_df.groupby("school_id", sort=False):
            grp_idx = grp.index.values
            n_steps = len(grp_idx)

            for step_pos in range(n_steps):
                row_idx = grp_idx[step_pos]
                is_history = enriched_df.loc[row_idx, "_is_preceding_history"]
                if is_history:
                    # Skip windows whose target is strictly historical context
                    continue

                # Causal window ending at step_pos: [start_pos .. step_pos]
                start_pos = max(0, step_pos - (self.seq_len - 1))
                win_indices = grp_idx[start_pos : step_pos + 1]
                win_features = scaled_matrix[win_indices]

                # Check normal-only condition across window
                if normal_only and "is_fraud" in enriched_df.columns:
                    window_frauds = enriched_df.loc[win_indices, "is_fraud"].values
                    if np.any(window_frauds != 0):
                        continue

                # Left-pad with earliest row if sequence is shorter than seq_len
                if len(win_features) < self.seq_len:
                    pad_count = self.seq_len - len(win_features)
                    first_row = win_features[0:1]
                    pad_block = np.repeat(first_row, pad_count, axis=0)
                    win_features = np.vstack([pad_block, win_features])

                windows.append(win_features)
                meta_list.append({
                    "transaction_id": enriched_df.loc[row_idx].get("transaction_id", f"txn_{row_idx}"),
                    "school_id": school_id,
                    "is_fraud": int(enriched_df.loc[row_idx].get("is_fraud", 0)),
                    "fraud_pattern": str(enriched_df.loc[row_idx].get("fraud_pattern", "NORMAL")),
                    "transacted_at": enriched_df.loc[row_idx].get("transacted_at"),
                    "amount": float(enriched_df.loc[row_idx].get("amount", 0.0)),
                })

        if not windows:
            F = len(self.feature_names)
            return np.zeros((0, self.seq_len, F), dtype=np.float32), []

        return np.array(windows, dtype=np.float32), meta_list
