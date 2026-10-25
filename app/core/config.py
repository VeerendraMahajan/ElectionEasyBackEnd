import os
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "VoterLens"
    APP_VERSION: str = "1.0.0"
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"
    ENABLE_DOCS: Optional[bool] = None  # None = True for dev, False for prod unless overridden

    # Security & CORS Settings
    CORS_ORIGINS: str = "https://pdf.electioneasy.in,http://localhost:8001"
    CORS_ALLOW_CREDENTIALS: bool = True
    TRUSTED_PROXIES: str = "127.0.0.1,::1"

    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/electoral_db",
        description="Async database connection string"
    )
    DATABASE_SYNC_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/electoral_db",
        description="Sync database connection string (used by Alembic and sync tools)"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30

    # Redis & Celery Background Tasks
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_WORKER_CONCURRENCY: int = 2
    CELERY_TASK_TIME_LIMIT: int = 3600       # 1 hour hard limit
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3300  # 55 min soft limit

    # Google Gemini LLM Settings (Optional with Local OCR Fallback)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    LLM_BATCH_SIZE: int = 5
    VISION_BATCH_SIZE: int = 5
    ENABLE_GEMINI_VISION: bool = True
    LLM_MAX_RETRIES: int = 3
    CASCADE_CONFIDENCE_THRESHOLD: float = 0.82

    # OCR Settings
    OCR_LANGUAGES: str = "hi,en"
    OCR_GPU: bool = False
    OCR_DPI: int = 200

    # Uploads, Reports & Storage Limits
    UPLOAD_DIR: str = "./uploads"
    REPORTS_DIR: str = "./reports"
    SCRATCH_DIR: str = "./scratch"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024             # 50 MB
    MAX_ZIP_SIZE: int = 200 * 1024 * 1024            # 200 MB
    MAX_ZIP_FILES: int = 100
    MAX_ZIP_EXTRACTED_SIZE: int = 500 * 1024 * 1024  # 500 MB
    MAX_PDF_PAGES: int = 500

    # Confidence Thresholds
    CONFIDENCE_THRESHOLD: float = 0.85
    REVIEW_REQUIRED_THRESHOLD: float = 0.70

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        if self.ENABLE_DOCS is not None:
            return self.ENABLE_DOCS
        return not self.is_production

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_proxies_list(self) -> List[str]:
        return [ip.strip() for ip in self.TRUSTED_PROXIES.split(",") if ip.strip()]

    @property
    def ocr_languages_list(self) -> List[str]:
        return [lang.strip() for lang in self.OCR_LANGUAGES.split(",") if lang.strip()]

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """Fail fast on insecure or misconfigured production settings."""
        if self.is_production:
            if self.DEBUG:
                raise ValueError("SECURITY ALERT: DEBUG must be set to False in production environment.")
            
            # Check default development passwords in production
            default_creds = ["postgres:postgres", "password", "secret", "admin:admin"]
            for cred in default_creds:
                if cred in self.DATABASE_URL:
                    raise ValueError(
                        f"SECURITY ALERT: Default credentials detected in DATABASE_URL in production."
                    )
        return self


settings = Settings()
