"""Configuration management for Fakelytics platform"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
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
    CORS_ORIGINS: list = ["*"]

    # API Keys
    API_KEY: str = Field(default="dev-key", min_length=1)
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

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    class Config:
        """Pydantic settings configuration"""
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
