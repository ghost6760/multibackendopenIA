# Multi-stage build para backend Flask + frontend React
# Optimizado para Railway deployment - CORREGIDO

# ============================================================================
# STAGE 1: Frontend Builder
# ============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copiar package.json primero para optimizar cache de Docker
COPY src/package.json ./package.json

# Instalar dependencias
RUN npm install --no-audit --prefer-offline --silent

# Crear estructura de carpetas que React Scripts espera
RUN mkdir -p src public

# Copiar archivos del frontend manteniendo estructura
COPY src/index.js ./src/
COPY src/App.js ./src/
COPY src/serviceWorkerRegistration.js ./src/
COPY src/reportWebVitals.js ./src/
COPY src/components/ ./src/components/
COPY src/services/ ./src/services/
COPY src/hooks/ ./src/hooks/
COPY src/styles/ ./src/styles/

# Copiar archivos públicos
COPY src/public/ ./public/

# Verificar que los archivos críticos existen
RUN test -f src/index.js || (echo "❌ src/index.js not found" && exit 1)
RUN test -f src/App.js || (echo "❌ src/App.js not found" && exit 1)
RUN test -f public/index.html || (echo "❌ public/index.html not found" && exit 1)
RUN test -f src/styles/global.css || (echo "❌ src/styles/global.css not found" && exit 1)

# Debug: Mostrar estructura de archivos
RUN echo "📂 Frontend structure:" && \
    find . -type f -name "*.js" -o -name "*.jsx" -o -name "*.css" -o -name "*.html" -o -name "*.json" | head -20

# Build de producción de React
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# Verificar que el build se creó correctamente
RUN test -f build/index.html || (echo "❌ Build failed - index.html not found" && exit 1)
RUN test -d build/static || (echo "❌ Build failed - static directory not found" && exit 1)

# Debug: Mostrar contenido del build
RUN echo "📦 Build contents:" && \
    ls -la build/ && \
    ls -la build/static/ || echo "No static directory found"

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

# Instalar dependencias del sistema necesarias
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json ./
COPY extended_companies_config.json ./

# Copiar archivos build del frontend desde el stage anterior
COPY --from=frontend-builder /frontend/build ./src/build

# Verificar que los archivos se copiaron correctamente
RUN test -f src/build/index.html || (echo "❌ Frontend build not copied correctly" && exit 1)

# Debug: Mostrar estructura final
RUN echo "📁 Final app structure:" && \
    find . -name "*.html" -o -name "*.js" -o -name "*.css" | grep -E "(index\.html|main\.|chunk\.)" | head -10

# Crear usuario no root para seguridad
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto (Railway asigna dinámicamente)
EXPOSE 8080

# Health check mejorado
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Comando de inicio optimizado para Railway
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
     "--capture-output", \
     "wsgi:app"]
