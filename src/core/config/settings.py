"""Configuration management for Fakelytics platform"""

import json
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Any
from enum import Enum


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App
    APP_NAME: str = "Fakelytics"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]

    # API Keys
    API_KEY: str = Field(default="dev-key", min_length=1)
    API_KEYS: list[str] = Field(default_factory=lambda: ["dev-key"])
    API_KEY_HEADER: str = "X-API-Key"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/fakelytics"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = Field(default_factory=lambda: "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default_factory=lambda: "redis://localhost:6379/0")
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"

    # Content Extraction
    CONTENT_EXTRACTION_TIMEOUT: int = 30
    MAX_CONTENT_SIZE: int = 500 * 1024 * 1024  # 500MB
    DOWNLOADED_MEDIA_DIR: str = "extracted_media"

    # External Services
    OPENAI_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None

    # Feature Flags
    ENABLE_ASYNC_MODE: bool = True
    ENABLE_WEBHOOKS: bool = True
    ENABLE_RATE_LIMITING: bool = True

    # Rate Limiting
    RATE_LIMIT_FREE_TIER: int = 100  # requests per day
    RATE_LIMIT_PRO_TIER: int = 10000  # requests per day
    RATE_LIMIT_ENTERPRISE_TIER: int = 1000000  # unlimited effectively

    # Timeouts
    VERIFICATION_TIMEOUT: int = 60  # seconds
    PIPELINE_TIMEOUT: int = 30  # seconds per pipeline
    WEBHOOK_TIMEOUT: int = 30  # seconds
    WEBHOOK_RETRIES: int = 5
    WEBHOOK_SIGNING_SECRET: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        """Accept common env-style debug values without crashing startup."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on", "debug"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
            return False
        return False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        """Support list, JSON string list, or comma-separated env values."""
        if value is None:
            return ["*"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return ["*"]
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        return ["*"]

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, value: Any) -> list[str]:
        """Allow API keys as list or comma-separated string."""
        if value is None:
            return ["dev-key"]
        if isinstance(value, list):
            parsed = [str(item).strip() for item in value if str(item).strip()]
            return parsed or ["dev-key"]
        if isinstance(value, str):
            parsed = [item.strip() for item in value.split(",") if item.strip()]
            return parsed or ["dev-key"]
        return ["dev-key"]

    class Config:
        """Pydantic settings configuration"""
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
