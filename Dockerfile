FROM python:3.11-slim

# Install system dependencies for OpenCV, PyMuPDF, and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications first for caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application source code
COPY . .

# Create uploads and scratch directories
RUN mkdir -p uploads scratch reports

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
