# ─────────────────────────────────────────────────────────────────────────────
# MarcoAI Backend – Dockerfile
# Base: python:3.11-slim (Debian-slim, ~45 MB compressed)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffers stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (curl for healthcheck, gcc for native wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./app/

# Create directories for persistent data (mounted as Docker volumes)
RUN mkdir -p /app/data /app/uploads

# Run as non-root for security
RUN adduser --disabled-password --gecos "" marcoai && \
    chown -R marcoai:marcoai /app
USER marcoai

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--log-level", "warning"]
