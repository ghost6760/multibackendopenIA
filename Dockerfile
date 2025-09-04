# Dockerfile optimizado para Railway - Frontend React + Backend Flask

# ============================================================================
# STAGE 1: Frontend Builder (React)
# ============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copiar package.json
COPY src/package.json ./

# Instalar dependencias
RUN npm install --no-audit --prefer-offline

# Crear estructura necesaria para React
RUN mkdir -p src public

# Copiar archivos de configuración
COPY src/tailwind.config.js ./
COPY src/postcss.config.js ./

# Copiar archivos del frontend
COPY src/index.js ./src/
COPY src/App.js ./src/
COPY src/serviceWorkerRegistration.js ./src/
COPY src/reportWebVitals.js ./src/
COPY src/components/ ./src/components/
COPY src/services/ ./src/services/
COPY src/hooks/ ./src/hooks/
COPY src/styles/ ./src/styles/
COPY src/public/ ./public/

# Debug: Verificar estructura
RUN echo "📂 Frontend structure:" && find . -type f | head -20

# Build de producción
ENV NODE_ENV=production
RUN npm run build

# Verificar que el build se creó correctamente
RUN ls -la build/ && test -f build/index.html && echo "✅ Build successful"

# ============================================================================
# STAGE 2: Backend Python + Frontend Integration
# ============================================================================
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json ./
COPY extended_companies_config.json ./

# ✅ CLAVE: Copiar build de React a la ubicación correcta
COPY --from=frontend-builder /frontend/build ./src/build

# Debug: Verificar que se copió correctamente
RUN echo "📂 Backend structure:" && \
    ls -la . && \
    echo "📂 React build:" && \
    ls -la src/build/ && \
    echo "📂 Static files:" && \
    ls -la src/build/static/ && \
    test -f src/build/index.html && \
    echo "✅ All files copied successfully"

# Crear usuario no root
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Comando optimizado para Railway
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--keep-alive", "2", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]

