FROM python:3.11-slim

# Install system dependencies required for OpenCV headless, PyMuPDF, PyTorch, and EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN useradd -u 1000 -m -s /bin/bash appuser

WORKDIR /app

# Ensure directories for uploads, reports, scratch, and EasyOCR models exist with correct ownership
ENV HOME=/home/appuser
RUN mkdir -p /app/uploads /app/reports /app/scratch /home/appuser/.EasyOCR && \
    chown -R appuser:appuser /app /home/appuser

# Copy dependency specifications first for Docker layer caching
COPY --chown=appuser:appuser pyproject.toml .

# Install Python dependencies as root to system site-packages, then clean up
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code with proper ownership
COPY --chown=appuser:appuser . .

# Ensure storage directories remain writable by appuser
RUN chown -R appuser:appuser /app/uploads /app/reports /app/scratch /home/appuser/.EasyOCR

# Switch to non-root user for runtime execution
USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -f http://127.0.0.1:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips=*"]
