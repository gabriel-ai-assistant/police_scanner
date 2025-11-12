# ============================================================
# Broadcastify Unified Scheduler + Ingest
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc libpq-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Copy app code
COPY . .

# Make temp directories writable (for MinIO)
RUN mkdir -p /app/shared_bcfy/tmp && chmod -R 777 /app/shared_bcfy

# Default command runs APScheduler
CMD ["python", "scheduler.py"]
