# VoterLens: Configuration & Environment Variable Reference

This document provides a comprehensive specification of all environment variables supported by **VoterLens / ElectionEasyBackEnd**, their defaults, requirements, and security implications.

---

## 1. Environment Variable Reference Table

| Variable | Type | Default | Required in Production? | Security Sensitive? | Description |
|:---|:---|:---|:---:|:---:|:---|
| `ENVIRONMENT` | string | `development` | Yes (`production`) | No | Execution environment (`development`, `testing`, `production`). In production, schema auto-creation is disabled and safety guards are enforced. |
| `DEBUG` | boolean | `true` | Yes (`false`) | Yes | Enables verbose debug mode. **Must be false in production**. |
| `APP_NAME` | string | `VoterLens` | No | No | Application display name. |
| `APP_VERSION` | string | `1.0.0` | No | No | Application semantic version. |
| `PORT` | integer | `8001` | No | No | Port on which the application listens. |
| `LOG_LEVEL` | string | `INFO` | No | No | Minimum logging severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ENABLE_DOCS` | boolean | `null` (auto) | No | No | Controls `/docs`, `/redoc`, and `/openapi.json` exposure. Defaults to `true` in dev, `false` in production. |
| `CORS_ORIGINS` | string | `https://pdf.electioneasy.in` | Yes | Yes | Comma-separated list of allowed origins. **Never use `*` with credentials in production**. |
| `CORS_ALLOW_CREDENTIALS`| boolean | `true` | No | No | Indicates whether browsers can include cookies/credentials in cross-origin requests. |
| `TRUSTED_PROXIES` | string | `127.0.0.1,::1` | Yes | No | Comma-separated list of trusted upstream reverse proxy IPs (Nginx on host). |
| `POSTGRES_USER` | string | `postgres` | Yes (Recommended: `voterlens_app`) | No | PostgreSQL application username. |
| `POSTGRES_PASSWORD` | string | `postgres` | **YES** | **YES** | Strong random database password. |
| `POSTGRES_DB` | string | `voterlens_db` | Yes | No | PostgreSQL database name. |
| `DATABASE_URL` | string | *constructed* | **YES** | **YES** | Async PostgreSQL connection URI (`postgresql+asyncpg://...`). |
| `DATABASE_SYNC_URL` | string | *constructed* | **YES** | **YES** | Sync PostgreSQL connection URI used by Alembic (`postgresql+psycopg2://...`). |
| `DB_POOL_SIZE` | integer | `10` | No | No | Base SQLAlchemy connection pool size. |
| `DB_MAX_OVERFLOW` | integer | `5` | No | No | Maximum burst connections above pool size. Sized conservatively for 8 GB RAM. |
| `DB_POOL_TIMEOUT` | integer | `30` | No | No | Seconds to wait before timing out on connection pool exhaustion. |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Yes (`redis://redis:6379/0` in Docker) | No | Redis connection URI for general cache and locks. |
| `CELERY_BROKER_URL` | string | `redis://localhost:6379/1` | Yes (`redis://redis:6379/1` in Docker) | No | Celery task queue broker connection string. |
| `CELERY_RESULT_BACKEND` | string | `redis://localhost:6379/2` | Yes (`redis://redis:6379/2` in Docker) | No | Celery task state and result backend connection string. |
| `CELERY_WORKER_CONCURRENCY`| integer | `2` | No | No | Number of concurrent worker execution processes. Set to 2 to prevent PyTorch OOM. |
| `CELERY_TASK_TIME_LIMIT` | integer | `3600` | No | No | Hard execution time limit in seconds (1 hour). |
| `CELERY_TASK_SOFT_TIME_LIMIT`| integer | `3300` | No | No | Soft timeout signal in seconds (55 minutes). |
| `GEMINI_API_KEY` | string | `null` | **No** (Optional) | **YES** | Google Cloud API key for Gemini 3.5 Flash Lite vision extraction. |
| `GEMINI_MODEL` | string | `gemini-3.5-flash-lite` | No | No | Gemini model designation for multimodal extraction. |
| `ENABLE_GEMINI_VISION` | boolean | `true` | No | No | Toggles Gemini Vision API calls. If false or key omitted, 100% local EasyOCR is used. |
| `OCR_LANGUAGES` | string | `hi,en` | No | No | Comma-separated languages for EasyOCR (`hi` = Hindi, `en` = English). |
| `OCR_GPU` | boolean | `false` | No | No | Set to `true` if NVIDIA CUDA runtime is available. Defaults to CPU mode. |
| `OCR_DPI` | integer | `200` | No | No | Rendering DPI for PyMuPDF page rasterization before OCR. |
| `UPLOAD_DIR` | string | `./uploads` | No | No | Filesystem directory where raw uploads and extracted PDFs are stored. |
| `REPORTS_DIR` | string | `./reports` | No | No | Directory for generated audit and export reports. |
| `SCRATCH_DIR` | string | `./scratch` | No | No | Temporary working directory for page crops and image slices. |
| `MAX_FILE_SIZE` | integer | `52428800` (50 MB) | No | No | Maximum allowed size in bytes for a single PDF upload. |
| `MAX_ZIP_SIZE` | integer | `209715200` (200 MB) | No | No | Maximum allowed size in bytes for a ZIP archive upload. |
| `MAX_ZIP_FILES` | integer | `100` | No | No | Maximum number of individual files permitted in an uploaded ZIP archive. |
| `MAX_ZIP_EXTRACTED_SIZE` | integer | `524288000` (500 MB) | No | No | Maximum allowed total uncompressed content size for ZIP extraction (anti-ZIP bomb). |
| `MAX_PDF_PAGES` | integer | `500` | No | No | Maximum pages allowed in a single PDF document. |
| `CONFIDENCE_THRESHOLD` | float | `0.85` | No | No | Confidence threshold above which extractions are marked `VALID`. |
| `REVIEW_REQUIRED_THRESHOLD` | float | `0.70` | No | No | Confidence threshold below which extractions are marked `REVIEW_REQUIRED`. |

---

## 2. Gemini Hybrid Cascade & Offline Fallback

VoterLens implements a **Selective Confidence Cascade**:
1. When `GEMINI_API_KEY` is provided and `ENABLE_GEMINI_VISION=true`, scanned card grids are batched and sent to Gemini Vision for maximum precision.
2. If `GEMINI_API_KEY` is empty, or if network timeouts / HTTP 429 quota exhaustion occurs, the pipeline **automatically falls back to local EasyOCR**.
3. No upload will ever fail solely due to the absence or quota exhaustion of Gemini API keys.

---

## 3. Secret Management & Hardening Rules

1. **Never commit `.env` into version control.** The `.gitignore` and `.dockerignore` files must always contain `.env` and `.env.*`.
2. **Generate unique database credentials outside the repository.** Do not reuse passwords across environments.
3. **Use least-privilege PostgreSQL users.** In production, connect as application user `voterlens_app`, never `postgres` superuser.
4. **Inspect permissions:** Ensure production `.env` permissions are `chmod 600 .env` so only the deployer user can read it.
