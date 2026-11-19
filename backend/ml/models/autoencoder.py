"""
DSFMP Autoencoder Fraud Model Wrapper
Learns the normal transaction manifold via a symmetric bottleneck MLP and scores
behavioral / structural deviations (e.g., round-number drains, multivariate mismatches)
from per-record MSE reconstruction error normalized to [0.0000, 1.0000].
"""

import os
from typing import Dict, Any, List, Tuple, Union
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor

from ml.features.preprocessing import (
    AutoencoderFeatureExtractor,
    build_autoencoder_preprocessor,
)


class AutoencoderFraudModel:
    """
    Semi-supervised Autoencoder wrapper for DSFMP fraud pattern detection.
    Should be fitted exclusively on normal (non-fraudulent) transactions so that
    anomalous patterns incur elevated reconstruction errors.
    """

    def __init__(
        self,
        hidden_layer_sizes: Tuple[int, ...] = (24, 10, 4, 10, 24),
        activation: str = "relu",
        alpha: float = 1e-4,
        max_iter: int = 500,
        random_state: int = 42,
        validation_fraction: float = 0.15,
    ):
        self.hidden_layer_sizes = hidden_layer_sizes
        self.activation = activation
        self.alpha = alpha
        self.max_iter = max_iter
        self.random_state = random_state
        self.validation_fraction = validation_fraction

        self.extractor = AutoencoderFeatureExtractor()
        self.preprocessor = build_autoencoder_preprocessor()
        self.model = MLPRegressor(
            hidden_layer_sizes=self.hidden_layer_sizes,
            activation=self.activation,
            solver="adam",
            alpha=self.alpha,
            batch_size=64,
            learning_rate_init=1e-3,
            max_iter=self.max_iter,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=15,
            random_state=self.random_state,
        )
        self.is_fitted = False
        self.feature_names: List[str] = []
        self._err_low = 0.0
        self._err_p99 = 1.0
        self._calibration_target_p99 = 0.68

    def _transform_features(
        self, X: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]
    ) -> np.ndarray:
        df_extracted = self.extractor.transform(X)
        X_proc = self.preprocessor.transform(df_extracted)
        return np.nan_to_num(X_proc, nan=0.0, posinf=10.0, neginf=-10.0)

    def fit(self, X: Union[pd.DataFrame, List[Dict[str, Any]]], y=None):
        """
        Fits the feature preprocessor and symmetric Autoencoder on normal data,
        then calibrates reconstruction error bounds on an internal holdout slice.
        """
        df_extracted = self.extractor.transform(X)
        if len(df_extracted) >= 50 and self.validation_fraction > 0:
            df_fit, df_cal = train_test_split(
                df_extracted,
                test_size=self.validation_fraction,
                random_state=self.random_state,
            )
        else:
            df_fit, df_cal = df_extracted, df_extracted

        X_fit = np.nan_to_num(
            self.preprocessor.fit_transform(df_fit),
            nan=0.0,
            posinf=10.0,
            neginf=-10.0,
        )
        self.feature_names = list(self.preprocessor.get_feature_names_out())

        # Reconstruct input vector X -> X
        self.model.fit(X_fit, X_fit)
        self.is_fitted = True

        # Calibrate bounds strictly on unseen normal validation errors
        X_cal = np.nan_to_num(
            self.preprocessor.transform(df_cal),
            nan=0.0,
            posinf=10.0,
            neginf=-10.0,
        )
        cal_errors = self._compute_mse(X_cal)
        self._err_low = float(np.percentile(cal_errors, 10))
        self._err_p99 = float(max(np.percentile(cal_errors, 99), self._err_low + 1e-6))
        return self

    def _compute_mse(self, X_proc: np.ndarray) -> np.ndarray:
        reconstructed = self.model.predict(X_proc)
        if reconstructed.ndim == 1:
            reconstructed = reconstructed.reshape(1, -1)
        sq_err = np.square(X_proc - reconstructed)
        return np.mean(sq_err, axis=1)

    def reconstruction_errors(
        self, X: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]
    ) -> np.ndarray:
        """Returns raw per-sample Mean Squared Reconstruction Error."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() or load() first.")
        X_proc = self._transform_features(X)
        return self._compute_mse(X_proc)

    def score_samples(
        self, X: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]
    ) -> np.ndarray:
        """
        Computes calibrated anomaly score in [0.0000, 1.0000].
        Maps log-scaled reconstruction errors so normal validation P10..P99
        span ~0.05..0.68 and higher reconstruction deviations climb toward 1.0.
        """
        raw_errors = self.reconstruction_errors(X)
        log_err = np.log1p(raw_errors)
        log_low = float(np.log1p(self._err_low))
        log_p99 = float(np.log1p(self._err_p99))

        denom = max(log_p99 - log_low, 1e-6)
        scaled_unit = (log_err - log_low) / denom
        # Map [0, 1] -> [0.05, 0.68]; errors > P99 extrapolate smoothly toward 1.0
        normalized = 0.05 + (self._calibration_target_p99 - 0.05) * scaled_unit
        return np.round(np.clip(normalized, 0.0000, 1.0000), 4)

    def predict(
        self,
        X: Union[pd.DataFrame, List[Dict[str, Any]]],
        threshold: float = 0.70,
    ) -> np.ndarray:
        """Returns binary classification (1 = Anomaly, 0 = Normal) against threshold."""
        scores = self.score_samples(X)
        return (scores >= threshold).astype(int)

    def score_single(self, transaction: Dict[str, Any]) -> float:
        """Scores a single incoming transaction dict."""
        return float(self.score_samples([transaction])[0])

    def explain_reconstruction(
        self, transaction: Dict[str, Any], top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Returns top features contributing most to a transaction's reconstruction error."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() or load() first.")

        X_proc = self._transform_features([transaction])
        reconstructed = self.model.predict(X_proc)
        if reconstructed.ndim == 1:
            reconstructed = reconstructed.reshape(1, -1)

        sq_err = np.square(X_proc[0] - reconstructed[0])
        total_err = float(np.sum(sq_err)) or 1.0
        top_indices = np.argsort(sq_err)[::-1][:top_k]

        names = self.feature_names or [f"feature_{i}" for i in range(len(sq_err))]
        return [
            {
                "feature": names[idx],
                "squared_error": round(float(sq_err[idx]), 4),
                "share": round(float(sq_err[idx] / total_err), 4),
            }
            for idx in top_indices
        ]

    def save(self, filepath: str):
        """Serializes the trained Autoencoder model bundle."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "preprocessor": self.preprocessor,
                "extractor": self.extractor,
                "feature_names": self.feature_names,
                "hidden_layer_sizes": self.hidden_layer_sizes,
                "activation": self.activation,
                "alpha": self.alpha,
                "max_iter": self.max_iter,
                "random_state": self.random_state,
                "err_low": self._err_low,
                "err_p99": self._err_p99,
                "calibration_target_p99": self._calibration_target_p99,
            },
            filepath,
        )
        print(f"[SAVE] Autoencoder model serialized successfully to: {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "AutoencoderFraudModel":
        """Loads a serialized Autoencoder model bundle."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Autoencoder model artifact not found at: {filepath}")

        bundle = joblib.load(filepath)
        instance = cls(
            hidden_layer_sizes=bundle.get("hidden_layer_sizes", (24, 10, 4, 10, 24)),
            activation=bundle.get("activation", "relu"),
            alpha=bundle.get("alpha", 1e-4),
            max_iter=bundle.get("max_iter", 300),
            random_state=bundle.get("random_state", 42),
        )
        instance.model = bundle["model"]
        instance.preprocessor = bundle["preprocessor"]
        instance.extractor = bundle["extractor"]
        instance.feature_names = bundle.get("feature_names", [])
        instance._err_low = bundle.get("err_low", 0.0)
        instance._err_p99 = bundle.get("err_p99", 1.0)
        instance._calibration_target_p99 = bundle.get("calibration_target_p99", 0.68)
        instance.is_fitted = True
        return instance

