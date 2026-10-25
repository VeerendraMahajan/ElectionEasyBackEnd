# Comprehensive Production Troubleshooting Guide

**Platform:** VoterLens / ElectionEasyBackEnd (`pdf.electioneasy.in`)  
**Host Environment:** Ubuntu 24.04 LTS (4 CPU Cores, 7.8 GiB RAM, ~145 GB Disk)  

---

## 1. Nginx 502 Bad Gateway Errors

### Symptoms
Accessing `https://pdf.electioneasy.in` returns HTTP `502 Bad Gateway`.

### Root Causes & Solutions
1. **FastAPI container is stopped or unhealthy:**
   ```bash
   docker compose ps api
   ```
   If status is not `Up (healthy)`, check container logs:
   ```bash
   docker compose logs --tail=50 api
   ```
2. **Loopback Port Binding Mismatch:**
   Ensure `docker-compose.yml` publishes port `127.0.0.1:8001:8001` and Nginx upstream points to `http://127.0.0.1:8001`.
   Verify the port is listening on the host:
   ```bash
   curl -I http://127.0.0.1:8001/health
   ```
3. **Nginx SELinux or AppArmor Blocking:**
   Check Nginx host error logs:
   ```bash
   sudo tail -n 50 /var/log/nginx/pdf.electioneasy.in.error.log
   ```

---

## 2. Database Connection Errors & Migration Failures

### Symptoms
API fails to start, readiness check returns HTTP 503, or logs show `asyncpg.exceptions.InvalidPasswordError` or `ConnectionRefusedError`.

### Diagnostics & Resolution
1. **Verify PostgreSQL Container Health:**
   ```bash
   docker compose ps postgres
   ```
   If restarting or unhealthy, view database logs:
   ```bash
   docker compose logs postgres
   ```
2. **Credential Mismatch in `.env`:**
   Ensure `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` match the credentials in `DATABASE_URL` and `DATABASE_SYNC_URL`.
   Inside Docker Compose, the database hostname must be `postgres` (not `localhost`):
   ```env
   DATABASE_URL=postgresql+asyncpg://voterlens_app:<PASSWORD>@postgres:5432/voterlens_prod
   DATABASE_SYNC_URL=postgresql+psycopg2://voterlens_app:<PASSWORD>@postgres:5432/voterlens_prod
   ```
3. **Alembic Migration Lock or Conflict:**
   If a migration failed midway or another process holds an advisory lock:
   ```bash
   # Run manual migration check
   docker compose run --rm migration alembic current
   docker compose run --rm migration alembic upgrade head
   ```

---

## 3. Celery Worker Issues & Stuck Jobs

### Symptoms
Document upload succeeds and returns `202 Accepted`, but job status remains in `QUEUED` or `PROCESSING` indefinitely.

### Diagnostics & Resolution
1. **Verify Redis Container Health:**
   ```bash
   docker compose exec redis redis-cli ping
   # Expected output: PONG
   ```
2. **Check Celery Worker Process Status:**
   ```bash
   docker compose ps worker
   docker compose logs --tail=100 -f worker
   ```
3. **Task Timeout / Memory Exhaustion:**
   EasyOCR running on 4 CPU cores with 7.8 GiB RAM can exceed memory if concurrency is too high.
   Ensure `CELERY_WORKER_CONCURRENCY=2` in `.env`.
   Restart the worker to flush stuck unacknowledged tasks:
   ```bash
   docker compose restart worker
   ```

---

## 4. EasyOCR Model Download Failures & Permissions

### Symptoms
Worker logs show `PermissionError: [Errno 13] Permission denied: '/home/appuser/.EasyOCR'` or download timeout during first document extraction.

### Diagnostics & Resolution
1. **Model Cache Permissions:**
   VoterLens runs as non-root user `appuser` (UID 1000). The model volume `easyocr_models` is mounted at `/home/appuser/.EasyOCR`.
   Verify volume permissions:
   ```bash
   docker compose exec -u 0 worker chown -R appuser:appuser /home/appuser/.EasyOCR
   ```
2. **First-Run Network Timeout:**
   EasyOCR downloads detection and recognition models (~100 MB) upon initial startup. Ensure the host has outbound internet connectivity to GitHub / PyTorch CDN.

---

## 5. Gemini 429 Rate Limits & OCR Fallback

### Symptoms
Logs indicate `429 ResourceExhausted: Quota exceeded for metric: generativelanguage.googleapis.com`.

### Architecture Behavior
1. VoterLens is architected with a **Selective Confidence Cascade**.
2. When a 429 quota error occurs, the system logs a warning, falls back to local EasyOCR, and **continues extraction without failing the document**.
3. If Gemini quota is permanently exhausted, set `ENABLE_GEMINI_VISION=false` in `.env` and restart:
   ```bash
   docker compose restart api worker
   ```

---

## 6. Corrupted Hindi Font Glyphs in PDFs

### Symptoms
Extracted text contains unreadable characters like `æ`, `Ů`, `Ğ`, `Į`, `ũ`.

### Resolution
Handled automatically by [`app/utils/font_mapper.py`](../app/utils/font_mapper.py) via deterministic glyph remapping. Legacy KrutiDev / DV-TT fonts are mapped to clean Unicode Devanagari in ~0.05s.

---

## 7. Let's Encrypt / TLS Certificate Failures

### Symptoms
Certbot error during renewal or invalid SSL certificate on `pdf.electioneasy.in`.

### Diagnostics & Resolution
1. **DNS Resolution Check:**
   Verify `pdf.electioneasy.in` resolves to host IP `167.86.97.203`:
   ```bash
   dig +short pdf.electioneasy.in
   ```
2. **Dry-Run Certbot Renewal:**
   ```bash
   sudo certbot renew --dry-run
   ```
3. **Verify Nginx Port 80 Challenge Location:**
   Ensure `/etc/nginx/sites-available/pdf.electioneasy.in.conf` includes:
   ```nginx
   location /.well-known/acme-challenge/ {
       root /var/www/html;
       allow all;
   }
   ```
