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
RUN mkdir -p src public src/styles src/components src/services src/hooks

# Copiar archivos de configuración PRIMERO
COPY src/tailwind.config.js ./tailwind.config.js 2>/dev/null || echo "No tailwind config found"
COPY src/postcss.config.js ./postcss.config.js 2>/dev/null || echo "No postcss config found"

# Copiar archivos del PUBLIC (manifest, favicon, etc)
COPY src/public/ ./public/

# CRÍTICO: Copiar archivos CSS ANTES que los JS
COPY src/styles/ ./src/styles/

# Verificar que el CSS se copió correctamente
RUN ls -la src/styles/ || echo "No styles directory found"
RUN test -f src/styles/globals.css && echo "✅ CSS found" || echo "❌ CSS NOT found"

# Copiar archivos React principales
COPY src/index.js ./src/index.js
COPY src/App.js ./src/App.js

# Copiar el resto de archivos React
COPY src/serviceWorkerRegistration.js ./src/serviceWorkerRegistration.js 2>/dev/null || echo "No serviceWorker found"
COPY src/reportWebVitals.js ./src/reportWebVitals.js 2>/dev/null || echo "No reportWebVitals found"

# Copiar directorios de componentes y servicios
COPY src/components/ ./src/components/ 2>/dev/null || echo "No components directory found"
COPY src/services/ ./src/services/ 2>/dev/null || echo "No services directory found"
COPY src/hooks/ ./src/hooks/ 2>/dev/null || echo "No hooks directory found"

# Debug final: Verificar estructura completa
RUN echo "📂 Complete Frontend structure:" && \
    find src -type f | head -30 && \
    echo "📄 Critical files check:" && \
    test -f src/index.js && echo "✅ index.js exists" || echo "❌ index.js missing" && \
    test -f src/App.js && echo "✅ App.js exists" || echo "❌ App.js missing" && \
    test -f src/styles/globals.css && echo "✅ globals.css exists" || echo "❌ globals.css missing" && \
    test -f public/index.html && echo "✅ index.html exists" || echo "❌ index.html missing"

# Build de producción con variables de entorno específicas
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false
ENV INLINE_RUNTIME_CHUNK=false

# Ejecutar build
RUN npm run build 2>&1 | tee build.log && \
    echo "Build completed, checking results:" && \
    ls -la build/ && \
    test -f build/index.html && echo "✅ Build successful" || (echo "❌ Build failed" && cat build.log && exit 1)

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

# CRÍTICO: Copiar build de React a la ubicación correcta
COPY --from=frontend-builder /frontend/build ./src/build

# Verificar que se copió correctamente
RUN echo "📂 Backend + Frontend structure:" && \
    ls -la . && \
    echo "📂 React build verification:" && \
    ls -la src/build/ && \
    test -f src/build/index.html && echo "✅ React index.html found" || echo "❌ React index.html missing" && \
    echo "📂 Static files:" && \
    ls -la src/build/static/ 2>/dev/null || echo "No static directory" && \
    echo "📂 Static CSS:" && \
    ls -la src/build/static/css/ 2>/dev/null || echo "No CSS directory" && \
    echo "📂 Static JS:" && \
    ls -la src/build/static/js/ 2>/dev/null || echo "No JS directory"

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
