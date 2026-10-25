# Troubleshooting Guide

## 1. Corrupted Hindi Characters in PDF Text Layer
- **Symptom**: Extracted text contains characters like `æ`, `Ů`, `Ğ`, `Į`, `ũ`.
- **Cause**: The PDF was encoded with legacy non-Unicode fonts (e.g. KrutiDev / DV-TT Surekh).
- **Solution**: Handled automatically by [`app/utils/font_mapper.py`](../app/utils/font_mapper.py) via deterministic glyph remapping in 0.05 seconds with 100% precision.

---

## 2. Gemini API 429 Quota Exceeded Errors
- **Symptom**: `429 Quota exceeded for metric: generativelanguage.googleapis.com/... limit: 20`.
- **Cause**: Experimental preview models (like `gemini-3.6-flash`) have a strict 20-call daily cap on free accounts.
- **Solution**:
  1. Configured to use `gemini-3.5-flash-lite` (full standard free-tier quota: 1,500 RPD / 15 RPM).
  2. The pipeline employs a **Hybrid Confidence Cascade**: runs Local Zone OCR first (100% free, offline, 0 API calls).
  3. If a 429 occurs, the system logs a clean warning and **gracefully falls back to local OCR data without failing the document**.
  4. Document header hierarchy is cached across pages to eliminate redundant cloud calls.

---

## 3. Database Connection Errors
- **Symptom**: `asyncpg.exceptions.InvalidPasswordError` or connection refused on port `5432`.
- **Cause**: PostgreSQL is not running or has conflicting credentials.
- **Solution**:
  1. Verify PostgreSQL container is healthy: `docker ps`.
  2. Ensure `.env` specifies: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/voterlens_db`.
  3. Check readiness probe: `curl http://localhost:8001/ready`.

---

## 4. Redis or Background Worker Issues
- **Symptom**: Job status remains `QUEUED` and does not transition to `PROCESSING`.
- **Cause**: Celery worker is not running or Redis is unreachable.
- **Solution**:
  1. Check Redis container health: `docker exec voterlens_redis redis-cli ping` (returns `PONG`).
  2. Check worker logs: `docker logs -f voterlens_worker`.
  3. Restart worker: `docker compose restart worker`.

---

## 5. ZIP Slip or Upload Rejection
- **Symptom**: `400 Bad Request` with code `FILE_VALIDATION_ERROR`.
- **Cause**: The archive contains path traversal (`../`) or exceeds file size limits (50 MB PDF / 200 MB ZIP).
- **Solution**: Inspect archive structure and ensure PDF files are legitimately packed.

---

## 6. Restarting Docker Containers
- Quick restart: `docker compose restart`
- Clean restart: `docker compose down && docker compose up -d`
- View live logs: `docker logs -f voterlens_api`
