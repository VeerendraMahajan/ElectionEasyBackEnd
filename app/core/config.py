import os
from typing import List
from pydantic import Field, field_validator
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
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Redis & Background Tasks
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Google Gemini LLM Settings
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    LLM_BATCH_SIZE: int = 5
    VISION_BATCH_SIZE: int = 5
    ENABLE_GEMINI_VISION: bool = True
    LLM_MAX_RETRIES: int = 3
    CASCADE_CONFIDENCE_THRESHOLD: float = 0.82

    # OCR Settings
    OCR_LANGUAGES: str = "hi,en"
    OCR_GPU: bool = False
    OCR_DPI: int = 200  # Increased from 150 for better LLM/OCR quality

    # Uploads & Security
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024        # 50 MB
    MAX_ZIP_SIZE: int = 200 * 1024 * 1024       # 200 MB
    MAX_ZIP_FILES: int = 100
    MAX_ZIP_EXTRACTED_SIZE: int = 500 * 1024 * 1024  # 500 MB

    # Confidence Thresholds
    CONFIDENCE_THRESHOLD: float = 0.85
    REVIEW_REQUIRED_THRESHOLD: float = 0.70

    @property
    def ocr_languages_list(self) -> List[str]:
        return [lang.strip() for lang in self.OCR_LANGUAGES.split(",") if lang.strip()]


settings = Settings()
