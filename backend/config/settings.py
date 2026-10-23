"""
DSFMP Fraud Detection — Application Settings

Single source of truth for all configuration. Reads from environment
variables (or .env file) and validates at startup via Pydantic.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    """
    All environment variables consumed by the backend.
    Pydantic validates types and raises clear errors on startup
    if any required variable is missing or malformed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────
    app_name: str = "DSFMP Fraud Detection API"
    app_version: str = "0.1.0"
    debug: bool = False
    allowed_origins: str = "http://localhost:5173"

    # ── MySQL ─────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "dsfmp_user"
    db_password: str = "change_me_in_production"
    db_name: str = "dsfmp_test"
    db_echo: bool = False

    # ── Redis ─────────────────────────────────────
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # ── JWT Authentication ────────────────────────
    jwt_secret_key: str = "CHANGE-THIS"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── 2FA ───────────────────────────────────────
    totp_issuer: str = "DSFMP Fraud Detection"

    # ── Risk Scoring Weights ──────────────────────
    weight_isolation_forest: float = 0.25
    weight_autoencoder: float = 0.30
    weight_lstm: float = 0.25
    weight_gnn: float = 0.20

    # ── Risk Tier Thresholds ──────────────────────
    threshold_critical: float = 0.80
    threshold_high: float = 0.60
    threshold_medium: float = 0.40

    # ── Computed Properties ───────────────────────

    @property
    def database_url(self) -> str:
        """Async MySQL connection string for SQLAlchemy."""
        creds = f"{self.db_user}:{self.db_password}" if self.db_password else self.db_user
        return (
            f"mysql+aiomysql://{creds}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync MySQL URL for Alembic migrations."""
        creds = f"{self.db_user}:{self.db_password}" if self.db_password else self.db_user
        return (
            f"mysql+pymysql://{creds}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection string."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    def get_risk_tier(self, score: float) -> str:
        """Map a composite risk score (0.0–1.0) to a risk tier label."""
        if score >= self.threshold_critical:
            return "CRITICAL"
        elif score >= self.threshold_high:
            return "HIGH"
        elif score >= self.threshold_medium:
            return "MEDIUM"
        return "LOW"


# ── Singleton ─────────────────────────────────────
# Import this instance everywhere:  from config.settings import settings
settings = Settings()
