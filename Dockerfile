# Multi-stage build para backend Flask + frontend React
# Optimizado para Railway deployment

# ============================================================================
# STAGE 1: Frontend Builder
# ============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copiar archivos de configuración de npm
COPY src/package.json src/package-lock.json* ./

# Instalar dependencias (usar cache si está disponible)
RUN npm ci --prefer-offline --no-audit

# Copiar código fuente del frontend
COPY src/ .

# Verificar que exista la carpeta public con index.html
RUN ls -la public/ && test -f public/index.html

# Build de producción de React
RUN npm run build

# Verificar que el build se creó correctamente
RUN ls -la build/ && test -f build/index.html

# ============================================================================
# STAGE 2: Backend Python
# ============================================================================
FROM python:3.11-slim AS backend

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json ./

# Copiar archivos build del frontend desde el stage anterior
COPY --from=frontend-builder /frontend/build ./src/build

# Verificar que los archivos se copiaron correctamente
RUN ls -la src/build/ && test -f src/build/index.html

# Crear usuario no root para seguridad
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Comando de inicio con configuración optimizada para Railway
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--keepalive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
