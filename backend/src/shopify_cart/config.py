# config.py
"""Application configuration using pydantic-settings.

All runtime configuration is loaded here. Precedence (highest → lowest):
    1. OS environment variables
    2. .env file
    3. Field defaults below

The `get_settings()` function is `lru_cache`'d so we parse .env exactly once
per process. Tests can call `get_settings.cache_clear()` to force a fresh read.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # ── App ────────────────────────────────────────────
    app_name: str = Field(default="ShopifyCart", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")

    # ── API ────────────────────────────────────────────
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    api_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:3001"],
        alias="API_CORS_ORIGINS",
    )

    # ── JWT ────────────────────────────────────────────
    jwt_secret_key: str = Field(default="dev-secret-change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=15, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # ── MySQL ──────────────────────────────────────────
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="shopify", alias="MYSQL_USER")
    mysql_password: str = Field(default="shopify", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="shopify_cart", alias="MYSQL_DATABASE")

    # ── Kafka ──────────────────────────────────────────
    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_client_id: str = Field(default="shopify-cart", alias="KAFKA_CLIENT_ID")
    kafka_consumer_group: str = Field(
        default="shopify-cart-consumers", alias="KAFKA_CONSUMER_GROUP"
    )
    kafka_enabled: bool = Field(default=False, alias="KAFKA_ENABLED")

    # ── MLflow ─────────────────────────────────────────
    mlflow_tracking_uri: str = Field(default="http://localhost:5000", alias="MLFLOW_TRACKING_URI")
    mlflow_experiment_name: str = Field(
        default="shopify-category-classifier", alias="MLFLOW_EXPERIMENT_NAME"
    )
    mlflow_model_name: str = Field(default="shopify-category-classifier", alias="MLFLOW_MODEL_NAME")
    mlflow_registered_model_name: str = Field(
        default="shopify-category-classifier",
        alias="MLFLOW_REGISTERED_MODEL_NAME",
    )
    # ── নতুন যোগ ──────────────────────────────────────
    ml_enabled: bool = Field(default=False, alias="ML_ENABLED")
    mlflow_request_timeout_seconds: int = Field(default=2, alias="MLFLOW_REQUEST_TIMEOUT_SECONDS")
    mlflow_max_retries: int = Field(default=0, alias="MLFLOW_MAX_RETRIES")

    # ── Model ──────────────────────────────────────────
    model_path: str = Field(default="models/category_classifier.pt", alias="MODEL_PATH")
    model_num_classes: int = Field(default=10, alias="MODEL_NUM_CLASSES")
    model_confidence_threshold: float = Field(default=0.75, alias="MODEL_CONFIDENCE_THRESHOLD")
    model_image_size: int = Field(default=224, alias="MODEL_IMAGE_SIZE")
    model_top_k: int = Field(default=3, alias="MODEL_TOP_K")
    model_stage: str = Field(default="None", alias="MODEL_STAGE")

    # ── Data ───────────────────────────────────────────
    data_raw_dir: str = Field(default="data/raw", alias="DATA_RAW_DIR")
    data_processed_dir: str = Field(default="data/processed", alias="DATA_PROCESSED_DIR")
    data_batch_size: int = Field(default=32, alias="DATA_BATCH_SIZE")
    data_num_workers: int = Field(default=4, alias="DATA_NUM_WORKERS")

    # ── Cart ───────────────────────────────────────────
    cart_max_items: int = Field(default=50, alias="CART_MAX_ITEMS")
    cart_max_quantity_per_item: int = Field(default=10, alias="CART_MAX_QUANTITY_PER_ITEM")

    # ── HuggingFace ────────────────────────────────────
    hf_token: str | None = Field(default=None, alias="HF_TOKEN")

    # ── Computed properties ────────────────────────────
    @property
    def database_url(self) -> str:
        """SQLAlchemy 2.0 URL for MySQL via PyMySQL.

        User, password, and database name are URL-encoded so special
        characters (@, :, /, ?, #, %) don't break the connection string.
        """
        return (
            f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
            f"@{self.mysql_host}:{self.mysql_port}/{quote_plus(self.mysql_database)}"
            "?charset=utf8mb4"
        )

    @property
    def is_production(self) -> bool:
        """True when running in production mode."""
        return self.app_env.lower() == "production"

    # ── Validators ─────────────────────────────────────
    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Normalize to lowercase and reject unknown environments."""
        allowed = {"development", "staging", "production", "test"}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(f"app_env must be one of {sorted(allowed)}")
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings accessor.

    Cached — call `get_settings.cache_clear()` in tests to force a fresh read.
    """

    return Settings()
