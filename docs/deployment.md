# Deployment & Production Operations

## 1. Quick Start with Docker Compose
The platform runs inside Docker Compose across 4 managed services:

```bash
docker compose up -d
```

### Managed Services:
1. **`api` (`voterlens_api`)**: FastAPI application on port `8000`. Runs database migrations automatically on startup.
2. **`worker` (`voterlens_worker`)**: Celery worker consuming document processing tasks from Redis.
3. **`postgres` (`voterlens_postgres`)**: PostgreSQL 15 database on port `5432` with persistent volume `postgres_data`.
4. **`redis` (`voterlens_redis`)**: Redis 7 message broker and cache on port `6379`.

---

## 2. Docker Container Restart & Maintenance Commands

### Quick Restart (All Running Services)
```bash
docker compose restart
```

### Restart Specific Services
```bash
docker compose restart api
docker compose restart worker
```

### Clean Restart (Re-reads `.env` Configuration & Reloads Volumes)
```bash
docker compose down
docker compose up -d
```

### Live Log Monitoring
```bash
# Follow API logs
docker logs -f voterlens_api

# Follow Celery Worker logs
docker logs -f voterlens_worker
```

### Check Running Status & Container Health
```bash
docker ps
```

---

## 3. Health Checks
- **Liveness Probe**: `GET http://localhost:8000/health`
  Returns `{"status": "ok", "app": "VoterLens", "version": "1.0.0"}` when the process is healthy.
- **Readiness Probe**: `GET http://localhost:8000/ready`
  Executes `SELECT 1` on PostgreSQL and returns `200 OK` when ready to serve traffic.

---

## 4. Database Migrations
Migrations are applied automatically when the API starts. For manual migration execution:
```bash
# Upgrade to latest revision
alembic upgrade head

# Rollback one revision
alembic downgrade -1
```

---

## 5. Production Environment Variables
Configured in `.env`:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/voterlens_db`
- `DATABASE_SYNC_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/voterlens_db`
- `REDIS_URL=redis://redis:6379/0`
- `GEMINI_API_KEY=<your_api_key>`
- `GEMINI_MODEL=gemini-3.5-flash-lite`
- `CASCADE_CONFIDENCE_THRESHOLD=0.82`
