# ─────────────────────────────────────────────────────────────────────────────
# MarcoAI Backend – Dockerfile
# Base: python:3.11-slim (Debian-slim, ~45 MB compressed)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

ARG UV_VERSION=0.8.1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (curl for healthcheck, gcc for native wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
ADD --chmod=755 https://astral.sh/uv/${UV_VERSION}/install.sh /tmp/install-uv.sh
RUN /tmp/install-uv.sh && rm /tmp/install-uv.sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

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
           "--log-level", "info"]
