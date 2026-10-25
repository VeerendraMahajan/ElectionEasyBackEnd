# Production Operations & Maintenance Manual

**Service:** VoterLens (`pdf.electioneasy.in`)  
**Stack:** FastAPI, Celery, PostgreSQL 15, Redis 7, Docker Compose  
**Environment:** Ubuntu 24.04 LTS (4 Cores, 7.8 GiB RAM)  

---

## 1. Routine Health & Status Checks

### Checking Container State
```bash
# Verify all containers are running and healthy
docker compose ps
```

### Checking Application Probes
```bash
# Liveness Probe (verifies process is responsive)
curl http://127.0.0.1:8001/health

# Readiness Probe (verifies database and Redis connectivity)
curl http://127.0.0.1:8001/ready

# Public Domain Probe (through Nginx TLS)
curl https://pdf.electioneasy.in/health
```

### Live Resource Utilization
```bash
# Real-time CPU, RAM, and Network consumption per container
docker stats --no-stream
```

---

## 2. Container Lifecycle & Safe Restart Procedures

### Service Restart Hierarchy

| Action | Command | Impact | Risk |
|:---|:---|:---|:---|
| **Quick Restart** | `docker compose restart` | Restarts containers in-place. Preserves all volumes, network state, and database. | None |
| **Worker Only Restart** | `docker compose restart worker` | Restarts Celery background worker without dropping HTTP API connections. Active tasks finish within grace period. | Minimal |
| **Full Stack Reload** | `docker compose down`<br>`docker compose up -d` | Stops containers and recreates them, reloading updated `.env` configuration. Named volumes are preserved. | Minimal (brief downtime) |
| **DO NOT USE IN PROD** | `docker compose down -v` | **DESTRUCTIVE:** Deletes named volumes (`postgres_data`, `uploads_data`, `reports_data`). | **CRITICAL DATA LOSS** |

> [!CAUTION]
> **NEVER use `docker compose down -v` in production.** The `-v` flag deletes all persistent Docker volumes, permanently destroying your PostgreSQL database, voter records, and uploaded PDFs.

---

## 3. Log Monitoring & Analysis

All VoterLens components produce structured JSON logs with correlation tracking:

```bash
# Follow FastAPI web application logs
docker compose logs -f api

# Follow Celery worker extraction logs
docker compose logs -f worker

# Follow database logs
docker compose logs -f postgres

# View last 100 log lines with timestamps
docker compose logs --tail=100 -t api
```

Search for error events in API logs:
```bash
docker compose logs api | grep '"level": "ERROR"'
```

---

## 4. Backup & Disaster Recovery Procedures

### 1. PostgreSQL Database Backup
Automate daily database snapshots using `pg_dump`:

```bash
# Set timestamp and backup directory
BACKUP_DIR="/var/backups/voterlens"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Execute pg_dump from within the postgres container
docker compose exec -T postgres pg_dump -U voterlens_app voterlens_prod | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Verify backup file size
ls -lh "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"
```

### 2. Uploaded Documents & Models Backup
Archive persistent uploads and report volumes:

```bash
tar -czvf "$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz" uploads/
```

### 3. Database Restore Procedure
In the event of database recovery:

```bash
# 1. Stop API and Worker to prevent writes during restoration
docker compose stop api worker

# 2. Decompress and restore database dump
gunzip < "$BACKUP_DIR/db_YYYYMMDD_HHMMSS.sql.gz" | docker compose exec -T postgres psql -U voterlens_app -d voterlens_prod

# 3. Restart application stack
docker compose start api worker
```

---

## 5. Storage & Disk Usage Monitoring

Monitor disk space on the ~145 GB host volume:

```bash
# Check host filesystem usage
df -h /

# Check Docker volume disk usage
docker system df -v

# Check size of uploads directory
du -sh uploads/
```

### Pruning Temporary Files & Scratch Data
Scratch files in `scratch/` are temporary intermediate image slices and can be pruned safely:

```bash
# Remove scratch files older than 7 days
find scratch/ -type f -mtime +7 -delete
```

---

## 6. Failed Job Recovery Workflow

When document extraction jobs encounter unexpected errors (e.g. malformed scans, corrupted PDFs), their state is recorded in the database with status `FAILED`.

### 1. Identify Failed Jobs via API
```bash
curl "https://pdf.electioneasy.in/api/v1/records?validation_status=REVIEW_REQUIRED"
```

### 2. Inspect Specific Job Status
```bash
curl "https://pdf.electioneasy.in/api/v1/jobs/{job_id}"
```

### 3. Review Worker Logs for Job ID
```bash
docker compose logs worker | grep "{job_id}"
```

### 4. Re-queue Failed Document
Re-uploading the document triggers deduplication or re-processing:
```bash
curl -X POST "https://pdf.electioneasy.in/api/v1/documents/upload" \
  -F "file=@path/to/document.pdf"
```
