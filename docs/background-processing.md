# Background Task Processing

## 1. Why Background Processing is Used
Electoral PDFs contain dozens to hundreds of pages and thousands of voter records. Running OCR and document extraction inside a synchronous HTTP request would cause:
- Web server worker exhaustion.
- Client connection timeouts.
- Poor user experience.

Instead, the upload endpoint responds immediately with HTTP `202 Accepted` and an `extraction_job_id`.

## 2. Architecture
```
FastAPI (POST /upload)
       ↓
Enqueues Task (Redis Broker)
       ↓
Background Worker (Celery / Asyncio Task)
       ↓
Processes Pages Iteratively
       ↓
Updates Extraction Job Progress in DB
       ↓
Marks Job COMPLETED
```

## 3. Real-Time Progress Tracking
Clients query `GET /api/v1/jobs/{job_id}` to track:
- `processed_pages` vs `total_pages`
- `processed_records` vs `total_records`
- `failed_records`

## 4. Retries & Resilience
- **Transient Failures**: Network glitches or brief OCR timeouts are retried with exponential backoff up to 3 times.
- **Permanent Failures**: Corrupted or unreadable pages log an entry in `processing_errors` and mark the page `REVIEW_REQUIRED`, allowing other pages in the document to complete successfully without crashing the job.
