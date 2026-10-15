"""
DSFMP Isolation Forest Model Wrapper
Detects tabular anomalies and outlier patterns in school feeding transactions.
Produces bounded [0.0000, 1.0000] risk scores for MySQL schema compatibility.
"""

import os
from typing import Dict, Any, List, Union
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline

from ml.features.preprocessing import TransactionFeatureExtractor, build_preprocessor


class IsolationForestFraudModel:
    """
    Production wrapper for Isolation Forest fraud detection.
    Normalizes decision function scores to a [0.0, 1.0] anomaly risk probability.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        contamination: float = 0.05,
        max_samples: Union[int, float] = "auto",
        random_state: int = 42
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.random_state = random_state

        self.extractor = TransactionFeatureExtractor()
        self.preprocessor = build_preprocessor()
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_samples=self.max_samples,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.is_fitted = False
        self._score_min = -0.5
        self._score_max = 0.5

    def fit(self, X: Union[pd.DataFrame, List[Dict[str, Any]]], y=None):
        """Fits the feature preprocessor and the Isolation Forest model."""
        df_extracted = self.extractor.transform(X)
        X_proc = self.preprocessor.fit_transform(df_extracted)
        self.model.fit(X_proc)
        self.is_fitted = True

        # Calibrate normalization bounds based on empirical training distribution
        raw_scores = self.model.decision_function(X_proc)
        self._score_min = float(np.percentile(raw_scores, 0.5))
        self._score_max = float(np.percentile(raw_scores, 99.5))
        return self

    def score_samples(self, X: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]) -> np.ndarray:
        """
        Computes anomaly score in [0.0, 1.0].
        Higher score = higher likelihood of fraud/anomaly.
        """
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() or load() first.")

        df_extracted = self.extractor.transform(X)
        X_proc = self.preprocessor.transform(df_extracted)

        # In scikit-learn, decision_function returns negative values for outliers,
        # positive values for inliers. We invert and normalize so:
        # 1.0 = highly anomalous/critical fraud, 0.0 = completely normal.
        raw_scores = self.model.decision_function(X_proc)
        
        # Invert: low decision value -> high anomaly risk
        inverted = -raw_scores
        norm_min = -self._score_max
        norm_max = -self._score_min
        
        if norm_max > norm_min:
            normalized = (inverted - norm_min) / (norm_max - norm_min)
        else:
            normalized = 0.5 * np.ones_like(raw_scores)

        # Clip strictly to [0.0, 1.0] and round to 4 decimals
        return np.round(np.clip(normalized, 0.0000, 1.0000), 4)

    def predict(
        self,
        X: Union[pd.DataFrame, List[Dict[str, Any]]],
        threshold: float = 0.65
    ) -> np.ndarray:
        """
        Returns binary fraud classification (1 = Fraud / Anomaly, 0 = Normal)
        based on the configurable risk threshold.
        """
        scores = self.score_samples(X)
        return (scores >= threshold).astype(int)

    def score_single(self, transaction: Dict[str, Any]) -> float:
        """Scores a single incoming transaction dict."""
        score_arr = self.score_samples([transaction])
        return float(score_arr[0])

    def save(self, filepath: str):
        """Serializes the trained model bundle."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "preprocessor": self.preprocessor,
                "extractor": self.extractor,
                "score_min": self._score_min,
                "score_max": self._score_max,
                "contamination": self.contamination,
                "n_estimators": self.n_estimators
            },
            filepath
        )
        print(f"[SAVE] Model serialized successfully to: {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "IsolationForestFraudModel":
        """Loads a serialized model bundle."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact not found at: {filepath}")
        
        bundle = joblib.load(filepath)
        instance = cls(
            n_estimators=bundle.get("n_estimators", 200),
            contamination=bundle.get("contamination", 0.05)
        )
        instance.model = bundle["model"]
        instance.preprocessor = bundle["preprocessor"]
        instance.extractor = bundle["extractor"]
        instance._score_min = bundle.get("score_min", -0.5)
        instance._score_max = bundle.get("score_max", 0.5)
        instance.is_fitted = True
        return instance
