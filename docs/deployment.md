# Production Deployment Guide: VoterLens on Ubuntu 24.04 LTS

**Target Host:** Ubuntu 24.04 LTS Server  
**Public IP:** `167.86.97.203`  
**Domain:** `pdf.electioneasy.in`  
**Host Architecture:** 4 CPU Cores, 7.8 GiB RAM, ~145 GB Disk  
**Reverse Proxy:** Nginx (installed on host)  
**Application Port:** `127.0.0.1:8001`  

---

## 1. Prerequisites & Host Validation

Before starting, SSH into the production server:

```bash
ssh user@167.86.97.203
```

Verify available resources and operating system:

```bash
# Verify Ubuntu version
lsb_release -a

# Verify CPU cores (should show 4)
nproc

# Verify available RAM (should be ~7.8 GiB total, >4 GiB available)
free -h

# Verify available disk space
df -h /
```

Ensure Docker Engine and Docker Compose are installed:

```bash
docker --version
docker compose version
```

*If Docker is not installed on Ubuntu 24.04:*
```bash
sudo apt update && sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

---

## 2. Directory Structure & Code Deployment

Create an isolated application directory on the host:

```bash
sudo mkdir -p /var/www/voterlens
sudo chown -R $USER:$USER /var/www/voterlens
cd /var/www/voterlens
```

Clone the repository:

```bash
git clone https://github.com/VeerendraMahajan/ElectionEasyBackEnd.git .
```

Verify that local storage directories exist:

```bash
mkdir -p uploads reports scratch
```

---

## 3. Production Environment Configuration (`.env`)

Generate a cryptographically secure database password:

```bash
openssl rand -base64 32
```

Copy the production environment template:

```bash
cp deploy/.env.production.example .env
chmod 600 .env
```

Edit `.env` using `nano .env` and update the placeholders:

```env
ENVIRONMENT=production
DEBUG=false
APP_NAME=VoterLens
APP_VERSION=1.0.0
PORT=8001
LOG_LEVEL=INFO
ENABLE_DOCS=false

# Security & CORS
CORS_ORIGINS=https://pdf.electioneasy.in
CORS_ALLOW_CREDENTIALS=true
TRUSTED_PROXIES=127.0.0.1,::1

# Database Configuration
POSTGRES_USER=voterlens_app
POSTGRES_PASSWORD=<INSERT_GENERATED_PASSWORD_HERE>
POSTGRES_DB=voterlens_prod

DATABASE_URL=postgresql+asyncpg://voterlens_app:<INSERT_GENERATED_PASSWORD_HERE>@postgres:5432/voterlens_prod
DATABASE_SYNC_URL=postgresql+psycopg2://voterlens_app:<INSERT_GENERATED_PASSWORD_HERE>@postgres:5432/voterlens_prod

DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_WORKER_CONCURRENCY=2

# Gemini API Key (Optional: Leave blank to use 100% offline local EasyOCR)
GEMINI_API_KEY=<OPTIONAL_API_KEY>
GEMINI_MODEL=gemini-3.5-flash-lite
ENABLE_GEMINI_VISION=true
```

> [!IMPORTANT]
> Keep `.env` strictly protected (`chmod 600 .env`). Never commit `.env` into Git.

---

## 4. Application Build & Startup

Start the Docker Compose stack in detached mode:

```bash
docker compose up --build -d
```

### Startup Sequence:
1. `postgres` starts and reaches `service_healthy` status.
2. `redis` starts and reaches `service_healthy` status.
3. `migration` container executes `alembic upgrade head` against PostgreSQL. Once completed successfully, it terminates (`restart: "no"`).
4. `api` starts and binds strictly to `127.0.0.1:8001`.
5. `worker` starts with concurrency 2 to process background jobs.

Verify that all services are healthy and running:

```bash
docker compose ps
```

Expected output:
```
NAME                 IMAGE               COMMAND                  SERVICE      CREATED         STATUS                   PORTS
voterlens-api-1      voterlens-api       "uvicorn app.main:ap…"   api          1 minute ago    Up 1 minute (healthy)    127.0.0.1:8001->8001/tcp
voterlens-migration-1 voterlens-migration "alembic upgrade head"   migration    1 minute ago    Exited (0) 50 seconds ago
voterlens-postgres-1 postgres:15-alpine  "docker-entrypoint.s…"   postgres     1 minute ago    Up 1 minute (healthy)    
voterlens-redis-1    redis:7-alpine      "docker-entrypoint.s…"   redis        1 minute ago    Up 1 minute (healthy)    
voterlens-worker-1   voterlens-worker    "celery -A app.worke…"   worker       1 minute ago    Up 1 minute              
```

Verify that Postgres and Redis ports are NOT exposed to the host:
```bash
# Should NOT show port 5432 or 6379 listening on 0.0.0.0
sudo ss -tulpn | grep -E '5432|6379'
```

Verify loopback API probes:
```bash
# Liveness probe
curl http://127.0.0.1:8001/health

# Readiness probe
curl http://127.0.0.1:8001/ready
```

---

## 5. Host Nginx Reverse Proxy Configuration

Install the virtual host template for `pdf.electioneasy.in`:

```bash
sudo cp deploy/nginx/pdf.electioneasy.in.conf.example /etc/nginx/sites-available/pdf.electioneasy.in.conf
sudo ln -s /etc/nginx/sites-available/pdf.electioneasy.in.conf /etc/nginx/sites-enabled/
```

Test Nginx configuration syntax before reloading to ensure other sites are not disrupted:

```bash
sudo nginx -t
```

Obtain Let's Encrypt TLS Certificate via Certbot:

```bash
sudo certbot --nginx -d pdf.electioneasy.in
```

After Certbot updates the configuration, verify syntax and reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. End-to-End Post-Deployment Verification

Verify public endpoint accessibility:

```bash
# 1. Health Probe
curl -I https://pdf.electioneasy.in/health

# 2. Readiness Probe
curl https://pdf.electioneasy.in/ready

# 3. Query Empty Records (Should return 200 with 0 items)
curl "https://pdf.electioneasy.in/api/v1/records"
```

---

## 7. Operational Management Commands

### Viewing Logs
```bash
# View API live logs
docker compose logs -f api

# View Celery Worker live logs
docker compose logs -f worker

# View all container logs
docker compose logs -f
```

### Restarting Services Safely
```bash
# Quick restart
docker compose restart

# Restart specific service only
docker compose restart worker
```

> [!CAUTION]
> **NEVER** run `docker compose down -v` in production! The `-v` flag deletes all Docker volumes, causing permanent loss of the PostgreSQL database and stored uploads. Use `docker compose restart` or `docker compose down` (without `-v`).
