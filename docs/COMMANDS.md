# VoterLens Operational Commands Cheat Sheet

This document contains essential, ready-to-use commands for managing Docker, PostgreSQL database, FastAPI, Celery workers, and Redis in the VoterLens platform.

---

## 1. Database Operations (PostgreSQL)

### A. Clean / Truncate All Data (Fresh Database)
To wipe all electoral records, documents, pages, and extraction jobs without dropping tables:

```bash
docker compose exec -T postgres psql -U postgres -d voterlens_db -c "TRUNCATE TABLE extraction_field_results, person_records, document_pages, processing_errors, extraction_jobs, documents CASCADE;"
```

### B. Check Row Counts Across Tables
Verify how many records currently exist in the database:

```bash
docker compose exec -T postgres psql -U postgres -d voterlens_db -c "
SELECT 'person_records' AS table_name, count(*) FROM person_records
UNION ALL
SELECT 'documents', count(*) FROM documents
UNION ALL
SELECT 'document_pages', count(*) FROM document_pages
UNION ALL
SELECT 'extraction_jobs', count(*) FROM extraction_jobs;
"
```

### C. Connect to PostgreSQL Interactive Shell (`psql`)
```bash
# Open interactive SQL prompt inside the postgres container:
docker compose exec postgres psql -U postgres -d voterlens_db

# Inside psql:
# \dt          -> list all tables
# \d person_records -> inspect person_records table schema
# \q          -> exit psql
```

### D. Complete Database Reset (Drop & Recreate)
If you want to drop the entire database and reapply migrations from scratch:

```bash
# 1. Terminate active connections and drop DB
docker compose exec -T postgres psql -U postgres -d postgres -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'voterlens_db' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS voterlens_db;
CREATE DATABASE voterlens_db;
"

# 2. Run Alembic migrations to recreate all tables
docker compose exec -T api alembic upgrade head
```

### E. Alembic Migrations
```bash
# Check current migration revision:
docker compose exec -T api alembic current

# Upgrade database to the latest schema:
docker compose exec -T api alembic upgrade head

# Downgrade last migration:
docker compose exec -T api alembic downgrade -1

# Generate a new migration automatically after changing models:
docker compose exec -T api alembic revision --autogenerate -m "description_of_change"
```

---

## 2. Docker & Container Management

### A. Start, Stop & Status
```bash
# Start all containers in the background:
docker compose up -d

# Check status and health of all containers:
docker compose ps

# Stop all running containers (preserves database data):
docker compose down

# Stop and wipe database volumes (complete wipe):
docker compose down -v
```

### B. Restart Services
```bash
# Restart API and Celery Worker (e.g. after editing Python code):
docker compose restart api worker

# Restart a single service:
docker compose restart api
docker compose restart worker
docker compose restart postgres
docker compose restart redis
```

### C. View Logs
```bash
# Follow logs for all services in real time:
docker compose logs -f

# Follow logs for API container only:
docker compose logs -f api

# Follow logs for Worker container only:
docker compose logs -f worker

# View the last 50 lines of logs:
docker compose logs --tail 50 api
```

### D. Rebuild Containers
Run this if you modify `Dockerfile`, dependencies in `pyproject.toml`, or configuration files:

```bash
# Rebuild and start without cache:
docker compose build --no-cache api worker
docker compose up -d
```

### E. Execute Commands Inside Containers
```bash
# Open an interactive bash shell in the API container:
docker compose exec api bash

# Open an interactive bash shell in the Worker container:
docker compose exec worker bash
```

---

## 3. FastAPI & API Endpoints

### A. Health & Readiness Probes
Verify that the FastAPI server and database are healthy:

```powershell
# PowerShell:
Invoke-RestMethod -Uri http://localhost:8001/health
Invoke-RestMethod -Uri http://localhost:8001/ready
```

```bash
# Linux / Git Bash / macOS:
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

- **Interactive API Documentation:**
  - Swagger UI: [http://localhost:8001/docs](http://localhost:8001/docs)
  - ReDoc: [http://localhost:8001/redoc](http://localhost:8001/redoc)

### B. Upload Electoral Documents

#### 1. Unified Automatic Endpoint (`POST /api/v1/documents/upload`)
Automatically detects whether the PDF is Card Format (`sample_Data.pdf`), Digital Tabular Format (`PAN_076_7_1.pdf`), or Scanned/Raster Tabular List (`sample_data_1.pdf`):

```bash
# Upload via curl:
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -F "file=@sample_data/sample_Data.pdf"

# Upload Panchayat tabular list:
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -F "file=@sample_data/sample_data_1.pdf"
```

```powershell
# PowerShell upload:
$filePath = "sample_data\sample_data_1.pdf"
$form = @{ file = Get-Item -Path $filePath }
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/documents/upload" -Method Post -Form $form
```

#### 2. Dedicated Tabular Endpoint (`POST /api/v1/documents/upload-tabular`)
Dedicated endpoint specifically for uploading 2-column tabular electoral rolls (e.g. Panchayat lists) with guaranteed tabular routing:

```bash
# Upload via dedicated tabular endpoint:
curl -X POST "http://localhost:8001/api/v1/documents/upload-tabular" \
  -F "file=@sample_data/sample_data_1.pdf"
```

```powershell
# PowerShell:
$filePath = "sample_data\sample_data_1.pdf"
$form = @{ file = Get-Item -Path $filePath }
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/documents/upload-tabular" -Method Post -Form $form
```

### C. Query Extracted Records
Retrieve voter records sorted by serial number in ascending order:

```powershell
# Get first 50 records sorted by serial number (ascending 1, 2, 3...):
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/records?sort_by=serial_number&sort_order=asc&skip=0&limit=50"
```

```bash
# Curl:
curl "http://localhost:8001/api/v1/records?sort_by=serial_number&sort_order=asc&skip=0&limit=50"
```

### C. Search Records with Filters
Filter records by gender, age range, EPIC/ID number, or review status:

```bash
# Filter by EPIC / Voter ID:
curl "http://localhost:8001/api/v1/records?id_number=WGX1774694"

# Filter by Gender and Age Range:
curl "http://localhost:8001/api/v1/records?gender=Female&min_age=18&max_age=40"

# Get records flagged for human review:
curl "http://localhost:8001/api/v1/records?validation_status=REVIEW_REQUIRED"
```

### D. Process Electoral PDF via CLI Script
Process a sample PDF directly from the terminal:

```bash
# Process PDF Format New (scanned cards):
python scripts/process_sample.py "sample_data/PDF Format New-3-38.pdf"

# Process PAN_076 (legacy tabular font):
python scripts/process_sample.py "sample_data/PAN_076_7_1.pdf"
```

---

## 4. Celery Worker & Redis Cache

### A. Redis Cache & Queue Management
```bash
# Flush all cached keys and queued jobs:
docker compose exec -T redis redis-cli FLUSHALL

# Check Redis connection:
docker compose exec -T redis redis-cli PING

# Check total queued keys:
docker compose exec -T redis redis-cli DBSIZE
```

### B. Monitor Celery Workers
```bash
# Check worker status and active nodes:
docker compose exec -T worker celery -A app.workers.celery_app status

# Inspect active running tasks:
docker compose exec -T worker celery -A app.workers.celery_app inspect active
```

---

## 5. Quick Reference: Complete One-Line System Refresh

To clean the database, flush Redis, and restart all services cleanly in one single command:

```bash
docker compose exec -T postgres psql -U postgres -d voterlens_db -c "TRUNCATE TABLE extraction_field_results, person_records, document_pages, processing_errors, extraction_jobs, documents CASCADE;" && docker compose exec -T redis redis-cli FLUSHALL && docker compose restart api worker
```
