# Dockerfile multi-stage as requested, optimized for ARM/RPi3
FROM python:3.11-slim AS builder

# Instalar dependencias de compilación para C extensions (sqlite-vss, etc)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copiar requirements primero para aprovechar la caché de Docker
COPY requirements.txt .

# Crear un entorno virtual para no usar pip global
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ====== Etapa Final ======
FROM python:3.11-slim

# Instalar libsqlite3 necesario en runtime
RUN apt-get update && apt-get install -y \
    libsqlite3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar el entorno virtual
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Crear directorio para la BD y dar permisos al nuevo usuario
RUN mkdir /app/data && groupadd -g 1000 marcoai && useradd -u 1000 -g marcoai -m marcoai && chown -R marcoai:marcoai /app

USER marcoai

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
