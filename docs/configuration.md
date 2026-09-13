# Configuration Guide

The platform uses Pydantic Settings (`app/core/config.py`) to manage configuration parameters loaded from environment variables or a `.env` file.

| Variable | Type | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | string | `development` | Runtime environment (`development`, `production`, `testing`) |
| `DEBUG` | boolean | `true` | Enables debug logging and interactive docs |
| `DATABASE_URL` | string | `postgresql+asyncpg://...` | Async database connection URL |
| `DATABASE_SYNC_URL` | string | `postgresql+psycopg2://...` | Sync database connection URL for Alembic |
| `DB_POOL_SIZE` | integer | `10` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | integer | `20` | Max overflow connections above pool size |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Redis URL for caching and state |
| `CELERY_BROKER_URL` | string | `redis://localhost:6379/1` | Celery task message broker URL |
| `CELERY_RESULT_BACKEND`| string | `redis://localhost:6379/2` | Celery task result backend URL |
| `GEMINI_API_KEY` | string | `None` | Google Gemini API key (optional, fallback to local OCR) |
| `GEMINI_MODEL` | string | `gemini-3.5-flash-lite` | Gemini model name with standard free-tier quotas |
| `ENABLE_GEMINI_VISION` | boolean | `true` | Enable vision-based LLM refinement for low-confidence cards |
| `LLM_MAX_RETRIES` | integer | `1` | Max retry attempts before falling back to local OCR |
| `CASCADE_CONFIDENCE_THRESHOLD` | float | `0.82` | Confidence threshold above which cards are resolved locally |
| `OCR_LANGUAGES` | string | `hi,en` | Languages enabled for EasyOCR |
| `OCR_GPU` | boolean | `false` | Enable GPU acceleration if CUDA is available |
| `OCR_DPI` | integer | `150` | Page rendering resolution in DPI |
| `UPLOAD_DIR` | string | `./uploads` | Local upload directory path |
| `MAX_FILE_SIZE` | integer | `52428800` (50 MB) | Maximum uploaded PDF file size in bytes |
| `MAX_ZIP_SIZE` | integer | `209715200` (200 MB) | Maximum uploaded ZIP archive size in bytes |
| `MAX_ZIP_FILES` | integer | `100` | Maximum file count in a ZIP archive |
| `CONFIDENCE_THRESHOLD` | float | `0.85` | Threshold for marking record VALID |
| `REVIEW_REQUIRED_THRESHOLD` | float | `0.70` | Threshold below which record is marked REVIEW_REQUIRED |
