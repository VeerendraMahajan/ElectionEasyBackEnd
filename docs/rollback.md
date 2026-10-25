# Production Rollback Runbook & Procedures

**Target Domain:** `pdf.electioneasy.in`  
**Application Stack:** VoterLens (FastAPI + Celery + PostgreSQL 15)  

---

## 1. Rollback Overview & Safety Principles

When an application deployment introduces unexpected regressions or critical failures, operations must follow a structured rollback procedure.

### Core Principles
1. **Preserve User Data:** Never perform destructive operations on persistent volumes.
2. **Database First Analysis:** Determine whether the regression is code-only or schema-dependent before downgrading database migrations.
3. **Verify Before Reverting:** Inspect current migration revision with `alembic current`.

---

## 2. Command Impact Matrix

Before issuing Docker commands, understand their operational impact:

| Command | Action | Impact on Data | Downtime |
|:---|:---|:---|:---:|
| `docker compose restart` | Restarts running containers | **Safe.** Volumes, database, and uploads untouched. | ~3-5 seconds |
| `docker compose stop` | Halts container execution | **Safe.** State preserved. | Until started |
| `docker compose down` | Stops containers and removes network | **Safe.** Named volumes (`postgres_data`, etc.) are preserved. | Until started |
| **`docker compose down -v`** | Stops containers and **deletes volumes** | **CRITICAL DATA DESTRUCTION.** Permanently removes database and uploaded PDFs. | **PERMANENT DATA LOSS** |

> [!CAUTION]
> **NEVER** use `docker compose down -v` during a rollback or deployment. Doing so will permanently wipe your PostgreSQL database and voter records.

---

## 3. Code-Only Rollback (No Schema Changes)

If the regression was introduced by application logic without changes to database migrations:

```bash
# 1. Navigate to application deployment directory
cd /var/www/voterlens

# 2. Check Git history to locate the previous stable commit
git log -n 5 --oneline

# 3. Check out the previous stable commit or tag
git checkout <STABLE_COMMIT_HASH>

# 4. Rebuild and restart the application stack
docker compose up --build -d

# 5. Verify service health and readiness probes
docker compose ps
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/ready
```

---

## 4. Database Migration Downgrade (Schema Rollback)

If the deployment included an Alembic migration that must be rolled back:

### Step 1: Inspect Current Revision
```bash
docker compose run --rm migration alembic current
```

### Step 2: Review Down Revision Script
Review the migration file in `alembic/versions/` to verify what `downgrade()` will execute (e.g. dropping columns vs tables).

### Step 3: Execute Alembic Downgrade
```bash
# Downgrade by 1 revision
docker compose run --rm migration alembic downgrade -1

# Or downgrade to a specific revision ID
docker compose run --rm migration alembic downgrade <REVISION_ID>
```

### Step 4: Checkout Matching Application Code & Restart
```bash
git checkout <MATCHING_STABLE_COMMIT>
docker compose up --build -d
```

---

## 5. Complete Database Restoration (Disaster Recovery Rollback)

If data was corrupted and a restoration from a previous backup snapshot is required:

```bash
# 1. Stop API and Worker containers to prevent concurrent writes
docker compose stop api worker

# 2. Restore PostgreSQL database from latest valid backup snapshot
gunzip < /var/backups/voterlens/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U voterlens_app -d voterlens_prod

# 3. Start API and Worker containers
docker compose start api worker

# 4. Verify end-to-end functionality
curl -I https://pdf.electioneasy.in/health
curl https://pdf.electioneasy.in/ready
curl "https://pdf.electioneasy.in/api/v1/records?limit=5"
```
