"""
DSFMP LSTM Autoencoder Fraud Model Wrapper
Learns normal sequence trajectories per school over sliding transaction windows.
Scores temporal anomalies (burst smurfing, sudden cadence breaks, off-hours spikes,
EWMA baseline divergence) via Seq2Seq reconstruction error normalized to [0.0000, 1.0000].
"""

import os
from typing import Dict, Any, List, Tuple, Union, Optional
import numpy as np
import pandas as pd
import joblib

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    nn = object

from ml.features.temporal import TemporalSequenceBuilder


if TORCH_AVAILABLE:
    class LSTMAutoencoderNet(nn.Module):
        """
        Symmetric Sequence-to-Sequence LSTM Autoencoder.
        Encoder condenses (seq_len, F) sequence into bottleneck vector z.
        Decoder repeats z across seq_len steps and reconstructs (seq_len, F).
        """

        def __init__(
            self,
            input_dim: int,
            hidden_dim: int = 32,
            latent_dim: int = 16,
            num_layers: int = 1,
            dropout: float = 0.0,
        ):
            super().__init__()
            self.input_dim = input_dim
            self.hidden_dim = hidden_dim
            self.latent_dim = latent_dim
            self.num_layers = num_layers

            self.encoder = nn.LSTM(
                input_size=input_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.enc_proj = nn.Linear(hidden_dim, latent_dim)
            self.dec_proj = nn.Linear(latent_dim, hidden_dim)
            self.decoder = nn.LSTM(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.output_linear = nn.Linear(hidden_dim, input_dim)

        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            # x: [batch, seq_len, input_dim]
            _, (h_n, _) = self.encoder(x)
            h_last = h_n[-1]  # [batch, hidden_dim]
            z = torch.tanh(self.enc_proj(h_last))  # [batch, latent_dim]

            dec_seed = torch.relu(self.dec_proj(z))  # [batch, hidden_dim]
            dec_in = dec_seed.unsqueeze(1).repeat(1, x.size(1), 1)  # [batch, seq_len, hidden_dim]
            dec_out, _ = self.decoder(dec_in)
            recon = self.output_linear(dec_out)  # [batch, seq_len, input_dim]
            return recon, z
else:
    class LSTMAutoencoderNet:
        pass


class LSTMAutoencoderFraudModel:
    """
    High-level semi-supervised LSTM Autoencoder wrapper for temporal sequence anomaly detection.
    Fitted exclusively on normal (non-fraudulent) sliding transaction sequences.
    """

    def __init__(
        self,
        seq_len: int = 10,
        hidden_dim: int = 32,
        latent_dim: int = 16,
        num_layers: int = 1,
        learning_rate: float = 1e-3,
        batch_size: int = 64,
        max_epochs: int = 40,
        patience: int = 6,
        random_state: int = 42,
    ):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch must be installed to use LSTMAutoencoderFraudModel.")

        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        self.latent_dim = latent_dim
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self.random_state = random_state

        torch.manual_seed(random_state)
        np.random.seed(random_state)

        self.builder = TemporalSequenceBuilder(seq_len=seq_len)
        self.net: Optional[LSTMAutoencoderNet] = None
        self.is_fitted = False
        self.feature_names: List[str] = []

        # Error calibration bounds
        self._err_low = 0.0
        self._err_p99 = 1.0
        self._calibration_target_p99 = 0.68

    def fit(
        self,
        train_df: pd.DataFrame,
        val_df: Optional[pd.DataFrame] = None,
        val_fraction: float = 0.15,
        verbose: bool = True,
    ):
        """
        Fits TemporalSequenceBuilder and LSTM Autoencoder on clean normal sequences.
        """
        # Step 1: Fit builder on normal training transactions
        self.builder.fit(train_df)
        self.feature_names = list(self.builder.feature_names)
        input_dim = len(self.feature_names)

        # Step 2: Extract strictly normal sliding windows
        X_train_seq, _ = self.builder.build_sliding_windows(train_df, normal_only=True)
        if len(X_train_seq) == 0:
            raise ValueError("No valid normal sliding sequences found in training data.")

        # Split train / internal validation windows if separate val_df not provided
        if val_df is not None:
            self.builder.is_fitted = True
            X_val_seq, _ = self.builder.build_sliding_windows(val_df, normal_only=True)
        else:
            n_val = max(50, int(len(X_train_seq) * val_fraction))
            indices = np.random.permutation(len(X_train_seq))
            val_idx = indices[:n_val]
            train_idx = indices[n_val:]
            X_val_seq = X_train_seq[val_idx]
            X_train_seq = X_train_seq[train_idx]

        # Initialize network
        self.net = LSTMAutoencoderNet(
            input_dim=input_dim,
            hidden_dim=self.hidden_dim,
            latent_dim=self.latent_dim,
            num_layers=self.num_layers,
        )

        device = torch.device("cpu")
        self.net.to(device)

        train_tensor = torch.from_numpy(X_train_seq).float()
        val_tensor = torch.from_numpy(X_val_seq).float()

        train_loader = DataLoader(
            TensorDataset(train_tensor),
            batch_size=self.batch_size,
            shuffle=True,
            drop_last=False,
        )

        optimizer = torch.optim.Adam(self.net.parameters(), lr=self.learning_rate, weight_decay=1e-5)
        criterion = nn.MSELoss(reduction="none")

        best_val_loss = float("inf")
        best_state = None
        no_improve_epochs = 0

        if verbose:
            print(f"[*] Training LSTM Autoencoder on {len(X_train_seq):,} normal sequences (features: {input_dim}, seq_len: {self.seq_len})...")

        for epoch in range(1, self.max_epochs + 1):
            self.net.train()
            train_loss_accum = 0.0
            total_samples = 0

            for (batch_x,) in train_loader:
                batch_x = batch_x.to(device)
                optimizer.zero_grad()
                recon, _ = self.net(batch_x)

                # Focus 60% loss on final step t, 40% on entire sequence
                loss_step = criterion(recon[:, -1, :], batch_x[:, -1, :]).mean()
                loss_seq = criterion(recon, batch_x).mean()
                loss = 0.60 * loss_step + 0.40 * loss_seq

                loss.backward()
                nn.utils.clip_grad_norm_(self.net.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss_accum += loss.item() * len(batch_x)
                total_samples += len(batch_x)

            epoch_train_loss = train_loss_accum / max(1, total_samples)

            # Validation loss
            self.net.eval()
            with torch.no_grad():
                val_x = val_tensor.to(device)
                val_recon, _ = self.net(val_x)
                val_step = criterion(val_recon[:, -1, :], val_x[:, -1, :]).mean()
                val_seq = criterion(val_recon, val_x).mean()
                epoch_val_loss = (0.60 * val_step + 0.40 * val_seq).item()

            if verbose and (epoch % 5 == 0 or epoch == 1 or epoch == self.max_epochs):
                print(f"  Epoch {epoch:02d}/{self.max_epochs:02d} — Train Loss: {epoch_train_loss:.5f} | Val Loss: {epoch_val_loss:.5f}")

            if epoch_val_loss < best_val_loss - 1e-4:
                best_val_loss = epoch_val_loss
                best_state = {k: v.cpu().clone() for k, v in self.net.state_dict().items()}
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1
                if no_improve_epochs >= self.patience:
                    if verbose:
                        print(f"  [i] Early stopping triggered at epoch {epoch} (best val loss: {best_val_loss:.5f})")
                    break

        if best_state is not None:
            self.net.load_state_dict(best_state)

        # Calibrate error bounds on validation sequences
        val_errors = self._calculate_raw_errors(X_val_seq)
        self._err_low = float(np.percentile(val_errors, 5.0))
        self._err_p99 = float(np.percentile(val_errors, 99.0))
        if self._err_p99 <= self._err_low:
            self._err_p99 = self._err_low + 1.0

        self.is_fitted = True
        if verbose:
            print(f"[OK] Fitting complete. Calibrated raw error bounds: low={self._err_low:.4f}, p99={self._err_p99:.4f}")
        return self

    def _calculate_raw_errors(self, sequences: np.ndarray) -> np.ndarray:
        """Calculates scalar raw reconstruction errors for sequences (N, seq_len, F)."""
        if self.net is None:
            raise RuntimeError("Model is not fitted.")
        self.net.eval()
        device = torch.device("cpu")
        with torch.no_grad():
            x_tensor = torch.from_numpy(sequences).float().to(device)
            recon, _ = self.net(x_tensor)
            # Weighted error: 70% final transaction deviation + 30% sequence drift
            err_last = torch.mean((recon[:, -1, :] - x_tensor[:, -1, :]) ** 2, dim=1)
            err_seq = torch.mean((recon - x_tensor) ** 2, dim=[1, 2])
            combined = 0.70 * err_last + 0.30 * err_seq
            return combined.cpu().numpy().astype(np.float64)

    def reconstruction_errors(self, sequences: np.ndarray) -> np.ndarray:
        """Returns uncalibrated reconstruction MSE errors."""
        return self._calculate_raw_errors(sequences)

    def score_samples(self, sequences: np.ndarray) -> np.ndarray:
        """
        Maps raw reconstruction errors to calibrated anomaly risk scores [0.0000, 1.0000].
        Normal 99th percentile maps to ~0.68.
        """
        raw_errors = self._calculate_raw_errors(sequences)
        norm_ratio = (raw_errors - self._err_low) / (self._err_p99 - self._err_low + 1e-8)
        norm_ratio = np.clip(norm_ratio, 0.0, None)
        # Scaled power curve aligning 99th percentile of normal data with 0.68
        scores = self._calibration_target_p99 * np.tanh(norm_ratio)
        # For extreme outliers, allow score to scale smoothly up to 1.0000
        extreme_boost = np.clip((norm_ratio - 1.0) * 0.25, 0.0, 0.32)
        final_scores = np.clip(scores + extreme_boost, 0.0, 1.0)
        return np.round(final_scores, 4)

    def score_dataframe(
        self,
        df: pd.DataFrame,
        prepend_history_df: Optional[pd.DataFrame] = None,
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Scores each transaction in df causally using preceding school history."""
        sequences, meta = self.builder.build_sliding_windows(
            df=df,
            normal_only=False,
            prepend_history_df=prepend_history_df,
        )
        if len(sequences) == 0:
            return np.array([]), []
        scores = self.score_samples(sequences)
        return scores, meta

    def score_single(
        self,
        transaction_data: Dict[str, Any],
        history_df: Optional[pd.DataFrame] = None,
    ) -> float:
        """
        Scores a single transaction dict using available school history.
        Falls back to self-padded single-step sequence if history is empty.
        """
        single_df = pd.DataFrame([transaction_data])
        sequences, _ = self.builder.build_sliding_windows(
            df=single_df,
            normal_only=False,
            prepend_history_df=history_df,
        )
        if len(sequences) == 0:
            return 0.50
        scores = self.score_samples(sequences)
        return float(scores[0])

    def explain_temporal_anomaly(
        self,
        transaction_data: Dict[str, Any],
        history_df: Optional[pd.DataFrame] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Identifies top temporal/structural reconstruction error drivers for the transaction."""
        single_df = pd.DataFrame([transaction_data])
        sequences, _ = self.builder.build_sliding_windows(
            df=single_df,
            normal_only=False,
            prepend_history_df=history_df,
        )
        if len(sequences) == 0 or self.net is None:
            return []

        self.net.eval()
        with torch.no_grad():
            x_t = torch.from_numpy(sequences).float()
            recon, _ = self.net(x_t)
            # Inspect final step reconstruction error per feature
            step_err = (recon[0, -1, :] - x_t[0, -1, :]) ** 2
            err_arr = step_err.cpu().numpy()

        tot = float(err_arr.sum()) or 1.0
        sorted_indices = np.argsort(err_arr)[::-1]
        results = []
        for idx in sorted_indices[:top_k]:
            fname = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
            sq_err = float(err_arr[idx])
            results.append({
                "feature": fname,
                "squared_error": round(sq_err, 4),
                "share": round(sq_err / tot, 4),
            })
        return results

    def save(self, filepath: str):
        """Serializes network state, sequence builder, and calibration bounds to a joblib artifact."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        artifact = {
            "model_type": "LSTMAutoencoderFraudModel",
            "version": "v1.0.0",
            "seq_len": self.seq_len,
            "hidden_dim": self.hidden_dim,
            "latent_dim": self.latent_dim,
            "num_layers": self.num_layers,
            "learning_rate": self.learning_rate,
            "state_dict": {k: v.cpu() for k, v in self.net.state_dict().items()} if self.net else None,
            "builder": self.builder,
            "feature_names": self.feature_names,
            "_err_low": self._err_low,
            "_err_p99": self._err_p99,
            "_calibration_target_p99": self._calibration_target_p99,
        }
        joblib.dump(artifact, filepath, compress=3)

    @classmethod
    def load(cls, filepath: str) -> "LSTMAutoencoderFraudModel":
        """Loads and reconstructs the LSTM Autoencoder model from artifact file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"LSTM Autoencoder artifact not found: {filepath}")

        artifact = joblib.load(filepath)
        model = cls(
            seq_len=artifact.get("seq_len", 10),
            hidden_dim=artifact.get("hidden_dim", 32),
            latent_dim=artifact.get("latent_dim", 16),
            num_layers=artifact.get("num_layers", 1),
            learning_rate=artifact.get("learning_rate", 1e-3),
        )
        model.builder = artifact["builder"]
        model.feature_names = list(artifact.get("feature_names", []))
        model._err_low = float(artifact.get("_err_low", 0.0))
        model._err_p99 = float(artifact.get("_err_p99", 1.0))
        model._calibration_target_p99 = float(artifact.get("_calibration_target_p99", 0.68))

        state_dict = artifact.get("state_dict")
        if state_dict is not None and TORCH_AVAILABLE:
            input_dim = len(model.feature_names)
            model.net = LSTMAutoencoderNet(
                input_dim=input_dim,
                hidden_dim=model.hidden_dim,
                latent_dim=model.latent_dim,
                num_layers=model.num_layers,
            )
            model.net.load_state_dict(state_dict)
            model.net.eval()
            model.is_fitted = True

        return model

