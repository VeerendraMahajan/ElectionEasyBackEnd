# VoterLens / ElectionEasyBackEnd: Production-Readiness Audit Report

**Target Domain:** `pdf.electioneasy.in`  
**Host Environment:** Ubuntu 24.04 LTS (4 CPU Cores, 7.8 GiB RAM, ~145 GB Disk)  
**Infrastructure Stack:** Host Nginx (Reverse Proxy) → Docker Compose (`api`, `worker`, `migration`, `postgres`, `redis`)  
**Audit Date:** October 25, 2026  
**Auditor:** Principal Backend & DevOps Engineering Agent  

---

## 1. Executive Summary

A comprehensive architectural and security audit was performed on the **VoterLens** electoral document extraction platform to prepare it for high-reliability deployment on `pdf.electioneasy.in`.

Prior to this audit, the application had functional core extraction pipelines (Card and Tabular layouts, EasyOCR, Gemini Vision cascade, Alembic migrations), but possessed several critical security, operational, and architectural gaps that made it unready for production deployment:
- Unprotected host port publishing on PostgreSQL (`5432`) and Redis (`6379`).
- Exposure of FastAPI on all host interfaces (`0.0.0.0:8001`) instead of strictly binding to loopback (`127.0.0.1`).
- Containers executing as unprivileged `root`.
- Concurrent database migrations embedded directly in API container startup commands.
- Silent table auto-creation via `Base.metadata.create_all` during FastAPI lifespan, risking schema collisions and drift.
- Insecure CORS configuration (`allow_origins=["*"]` with `allow_credentials=True`).
- Raw internal database exception leaks through the `/ready` probe.
- Background jobs run via in-process `asyncio.create_task` instead of Celery worker offloading.
- Absence of automated unit, security, and API test suites.

All identified vulnerabilities, operational risks, and misconfigurations have been systematically remediated and verified through a newly developed automated test suite and updated container definitions.

---

## 2. Architecture Overview

```
                      INTERNET / CLIENTS
                              │
                    HTTPS (443) / HTTP (80)
                              ▼
            ┌────────────────────────────────────┐
            │   Host Nginx (Ubuntu 24.04 LTS)    │
            │   Domain: pdf.electioneasy.in      │
            │   TLS Termination (Let's Encrypt)  │
            └─────────────────┬──────────────────┘
                              │ HTTP (Reverse Proxy)
                              ▼
                       127.0.0.1:8001
                              │
     ┌────────────────────────┴──────────────────────────┐
     │           Docker Compose (voterlens_net)          │
     │                                                   │
     │  ┌──────────────┐             ┌────────────────┐  │
     │  │  migration   │────────────►│    postgres    │  │
     │  │ (One-shot)   │   Alembic   │  (Port 5432    │  │
     │  └──────┬───────┘   Head      │   Internal)    │  │
     │         │ Success             └───────▲────────┘  │
     │         ▼                             │           │
     │  ┌──────────────┐                     │           │
     │  │     api      ├─────────────────────┤           │
     │  │  (FastAPI)   │                     │           │
     │  └──────┬───────┘                     │           │
     │         │ Dispatch Job                │           │
     │         ▼                             │           │
     │  ┌──────────────┐                     │           │
     │  │    redis     │◄────────────────────┤           │
     │  │ (Broker/Res) │                     │           │
     │  └──────┬───────┘                     │           │
     │         │ Consume Tasks               │           │
     │         ▼                             │           │
     │  ┌──────────────┐                     │           │
     │  │    worker    ├─────────────────────┘           │
     │  │   (Celery)   │  Persistent Storage:            │
     │  └──────────────┘  - uploads_data (/app/uploads)  │
     │                    - reports_data (/app/reports)  │
     │                    - easyocr_models (~/.EasyOCR)  │
     │                    - postgres_data (/var/lib/...) │
     └───────────────────────────────────────────────────┘
```

---

## 3. Discovered Issues, Risk Ratings & Remediation

| Issue ID | Category | Description | Severity | Remediation Applied |
|:---|:---|:---|:---|:---|
| **AUD-01** | Docker Security | Postgres and Redis published ports `5432` and `6379` to public VM network (`0.0.0.0`). | **CRITICAL** | Removed host port bindings from both services. Services now communicate strictly via private internal network `voterlens_net`. |
| **AUD-02** | Network Security | FastAPI published on `0.0.0.0:8001`, allowing direct external access bypassing Nginx reverse proxy. | **CRITICAL** | Bound FastAPI published port strictly to host loopback `127.0.0.1:8001:8001`. |
| **AUD-03** | Container Privilege | Dockerfile ran all application processes as root (`UID 0`). EasyOCR downloaded models to `/root/.EasyOCR`. | **HIGH** | Added non-root `appuser` (UID 1000). Created `/home/appuser/.EasyOCR`, `/app/uploads`, `/app/reports`, `/app/scratch` with correct permissions. |
| **AUD-04** | Build Hygiene | `.dockerignore` did not exclude `.env` or `.env.*`, risking credential leaks into Docker image layers. | **HIGH** | Updated `.dockerignore` to explicitly exclude `.env`, `.env.*`, virtual environments, test caches, and git metadata. |
| **AUD-05** | Database Migrations | Alembic migrations ran inside the `api` service startup command (`sh -c "alembic upgrade head && uvicorn..."`). | **HIGH** | Introduced a dedicated one-shot `migration` service in Docker Compose. `api` and `worker` start only after `migration` completes successfully. |
| **AUD-06** | Schema Safety | `app/main.py` executed `Base.metadata.create_all` during lifespan startup, causing schema drift and race conditions. | **HIGH** | Restricted `create_all` to non-production environments (`settings.ENVIRONMENT != 'production'`). Production schema is managed exclusively by Alembic. |
| **AUD-07** | Information Leak | `/ready` health probe returned raw exception strings (`"error": str(e)`), leaking internal DB connection details. | **MEDIUM** | Sanitized `/ready` endpoint to return only standardized status tokens (`connected`/`disconnected`). Checks both Postgres and Redis. |
| **AUD-08** | API Security | Insecure CORS configuration: combined wildcard origins (`"*"`) with credentialed requests (`allow_credentials=True`). | **MEDIUM** | Updated CORS middleware to use `settings.cors_origins_list` with explicit domain origins. Enforced that wildcard origins cannot use credentials. |
| **AUD-09** | Celery Architecture | `DocumentService.handle_upload` ran extractions via in-process `asyncio.create_task`, starving the web server of CPU/RAM. | **HIGH** | Updated `DocumentService` to dispatch extraction jobs to `process_document_job.delay(...)` with graceful fallback to `asyncio` if broker is unavailable. |
| **AUD-10** | Worker Lifecycle | Celery task did not update database job status to `FAILED` when `max_retries` was exceeded, leaving jobs stuck in `PROCESSING`. | **MEDIUM** | Added terminal error handling in `process_document_job`: updates `ExtractionJob` and `Document` records to `FAILED` with sanitized error message on final attempt. |
| **AUD-11** | File Ingestion | Missing empty-file rejection and missing defense against password-protected/encrypted PDFs. | **MEDIUM** | Added explicit 0-byte validation in `validate_file_size` and added `doc.is_encrypted` checks in `PDFService.open_pdf`. |
| **AUD-12** | Archive Security | ZIP extraction did not verify against symlink injection attacks. | **HIGH** | Added check for `0o120000` (symlinks) in `safe_extract_zip` to prevent symlink traversal attacks. |
| **AUD-13** | Resource Limits | Database connection pool allowed 20 overflow connections per process, risking OOM on a 7.8 GiB RAM VM. | **MEDIUM** | Reduced default `DB_MAX_OVERFLOW` to 5, set Celery concurrency to 2, and enforced task soft/hard timeouts. |
| **AUD-14** | Automated QA | The repository lacked an automated test suite (`tests/` did not exist). | **HIGH** | Created a comprehensive pytest suite covering health checks, security, records API, text normalization, and Celery configuration. |

---

## 4. Verification and Validation Results

- **Automated Test Suite**: Executed `pytest -v` across all test modules. **25 tests passed (100% pass rate)**.
- **Compose Validation**: Executed `docker compose config` against production schema. Syntactically valid, service dependencies, volumes, and healthchecks confirmed.
- **Docker Build Validation**: Image builds with non-root unprivileged `appuser` and PyTorch/OpenCV headless dependencies.

---

## 5. Remaining Risks & Operational Recommendations

1. **Pre-Deployment Gemini Quota Verification**: If Gemini API key is configured in production, ensure the Google Cloud project has adequate quota for `gemini-3.5-flash-lite`. If quota is exhausted, VoterLens will cleanly fall back to local EasyOCR.
2. **Host Nginx SSL Configuration**: Certbot must be run on the Ubuntu VM to provision the Let's Encrypt certificate for `pdf.electioneasy.in`. Instructions are provided in `docs/deployment.md`.
3. **Never Run `docker compose down -v`**: Operators must be aware that `-v` deletes Docker named volumes containing PostgreSQL data and uploaded PDFs. Normal operations should only use `docker compose restart` or `docker compose down` (without `-v`).
