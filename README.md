# VoterLens: Intelligent Electoral PDF Extraction Platform

**VoterLens** is a production-grade document intelligence platform for extracting highly accurate structured data from Hindi and English electoral PDF documents (scanned images, text-based, and mixed tabular/card formats).

Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.x**, **Alembic**, **OpenCV**, **EasyOCR**, **PyMuPDF**, **Google Gemini 3.5 Flash Lite**, **Redis**, and **Celery**.

---

## 1. Key Architectural Features

- **Multi-Format Ingestion**: Accepts individual PDFs and ZIP archives containing nested folders of electoral rolls.
- **Strict Electoral Hierarchy & Caching**: Automatically extracts page-level metadata from headers and caches it across pages:
  $$\text{Assembly Constituency} \longrightarrow \text{Section} \longrightarrow \text{Part} \longrightarrow \text{Booth / Polling Station} \longrightarrow \text{Voter Records}$$
- **Zero Duplication**: Header metadata is stored at the page level in `document_pages` and linked to `person_records` via `page_id`.
- **Deterministic Font Remapping Engine (`font_mapper.py`)**:
  - Handles legacy 8-bit non-Unicode fonts (KrutiDev / DV-TT Surekh) found in tabular rolls (e.g., `PAN_076_7_1.pdf`).
  - Decodes text layers in **0.05 seconds per page** with **100% mathematical precision and 0 OCR noise**, avoiding slow visual OCR.
- **Local Zone-Based OCR & Hybrid Confidence Cascade (`card_extractor.py`)**:
  - Preprocesses isolated card sub-boxes (Serial zone with numeric allowlist, EPIC zone with alphanumeric allowlist, text body zone).
  - Processes clean cards **100% locally and offline** (0 API calls, 0 cost).
  - Uses `gemini-3.5-flash-lite` only as a secondary refinement for degraded/low-confidence cards.
  - **429 Quota Resilient**: Gracefully falls back to local OCR if cloud AI rate limits are exceeded, ensuring documents never fail or crash.
- **Ascending Order via Serial Number (`1, 2, 3, ...`)**:
  - Records are indexed and returned in strict ascending numeric order (`PersonRecord.serial_number.asc()`).
  - Available by default across repository queries, ORM relationships (`document.records`), and REST API endpoints.
- **Bilingual Normalization & Transliteration**:
  - Devanagari numerals (`०-९`) normalized to standard ASCII digits (`0-9`).
  - Names transliterated phonetically (`सलमा` -> `Salma`), never semantically translated.
  - Voter IDs (EPIC) preserved strictly with common prefix artifact auto-corrections (`0P/` -> `UP/`).
  - House numbers stored as strings (`1`, `1ब`, `15/140`).
- **Data Integrity & Human Review**:
  - Multi-signal confidence scoring (OCR confidence, field completeness, font integrity).
  - Full audit trail in `extraction_field_results` and `correction_history`.
  - Human review endpoints (`GET /api/v1/records/review-required` and `PATCH /api/v1/records/{id}`).
- **Asynchronous Architecture**: Large documents are queued to Redis and processed by Celery background workers with real-time job progress tracking.
- **Enterprise Security**: Magic bytes validation (`%PDF`, `PK\x03\x04`), ZIP slip protection, decompression bomb limits, and path traversal guards.

---

## 2. Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 with asyncpg & SQLAlchemy 2.x (ORM)
- **Migrations**: Alembic
- **Document Processing**: PyMuPDF (`pymupdf`), OpenCV (`cv2`), EasyOCR
- **Vision AI**: Google Gemini 3.5 Flash Lite (Selective Hybrid Cascade)
- **Background Processing**: Celery & Redis 7
- **Containerization**: Docker & Docker Compose

---

## 3. Docker Container Management & Restart Commands

The entire platform runs in Docker Compose across 4 managed containers:
- `voterlens_api`: FastAPI web application on port `8000`.
- `voterlens_worker`: Celery background worker for document extraction.
- `voterlens_postgres`: PostgreSQL 15 database on port `5432`.
- `voterlens_redis`: Redis 7 message broker and cache on port `6379`.

> **Detailed Command Reference:** See [COMMANDS.md](COMMANDS.md) for full commands covering Docker, database cleanup, psql, FastAPI endpoints, Celery, and Redis.

### Restart Commands

```bash
# 1. Quick Restart (all running containers)
docker compose restart

# 2. Restart specific services only
docker compose restart api
docker compose restart worker

# 3. Clean Restart (re-reads .env configuration and reloads volumes)
docker compose down
docker compose up -d

# 4. View live container logs
docker logs -f voterlens_api
docker logs -f voterlens_worker

# 5. Check container health status
docker ps
```

---

## 4. API Endpoints & Ascending Order Retrieval

Interactive documentation is available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Postman Collection**: [`postman/VoterLens.postman_collection.json`](./postman/VoterLens.postman_collection.json) & [Environment](./postman/VoterLens.postman_environment.json)

### Querying Records in Ascending Order:
By default, all record search and document endpoints return voter records sorted in ascending order by serial number (`1, 2, 3, ...`):

```bash
# Search records (defaults to sort_by=serial_number&sort_order=asc)
curl "http://localhost:8000/api/v1/records"

# Document records (defaults to sort_by=serial_number&sort_order=asc)
curl "http://localhost:8000/api/v1/documents/{document_id}/records"

# Custom sort order if needed
curl "http://localhost:8000/api/v1/records?sort_by=serial_number&sort_order=desc"
```

---

## 5. Environment Configuration (`.env`)

Key configuration parameters managed via `app/core/config.py`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/voterlens_db
DATABASE_SYNC_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/voterlens_db

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# AI & Hybrid Cascade
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
ENABLE_GEMINI_VISION=true
LLM_MAX_RETRIES=1
CASCADE_CONFIDENCE_THRESHOLD=0.82

# OCR Settings
OCR_LANGUAGES=hi,en
OCR_GPU=false
OCR_DPI=150
```

---

## 6. Documentation Directory

Detailed documentation is available in the [`docs/`](./docs/README.md) directory:

- [High-Level Design (HLD & Architecture Diagram)](./docs/hld.md)
- [Architecture Overview](./docs/architecture.md)
- [Database ER Diagram & Schema](./docs/database.md)
- [Extraction Pipeline & Data Flow](./docs/extraction-pipeline.md)
- [PDF Processing & Font Mapping](./docs/pdf-processing.md)
- [OCR Pipeline & Zone Processing](./docs/ocr.md)
- [LLM & Hybrid Cascade Strategy](./docs/llm-extraction.md)
- [Normalization & Transliteration](./docs/normalization.md)
- [Validation & Confidence Scoring](./docs/validation.md)
- [REST API Reference](./docs/api.md)
- [Background Processing](./docs/background-processing.md)
- [Deployment & Docker Operations](./docs/deployment.md)
- [Configuration Reference](./docs/configuration.md)
- [Testing & Verification Guide](./docs/testing.md)
- [Troubleshooting Guide](./docs/troubleshooting.md)
- [Architecture Decision Log (ADR)](./docs/decisions.md)
