# ============================================================================
# STAGE 1: Frontend Builder (React + Tailwind)
# ============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copiar package.json y lock para cache de dependencias
COPY src/package.json ./package.json

# Instalar dependencias sin auditoría (rápido y seguro)
RUN npm install --no-audit --prefer-offline --silent

# Crear estructura de carpetas esperada
RUN mkdir -p src public

# Copiar configuración de Tailwind y PostCSS
COPY src/tailwind.config.js ./tailwind.config.js
COPY src/postcss.config.js ./postcss.config.js

# Copiar archivos del frontend
COPY src/index.js ./src/
@@ -29,23 +31,22 @@ COPY src/hooks/ ./src/hooks/
COPY src/styles/ ./src/styles/
COPY src/public/ ./public/

# Debug: verificar estructura
RUN echo "📂 Frontend structure:" && find src -type f | head -20

# Build optimizado para producción
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# Validar build
RUN test -f build/index.html || (echo "❌ Build failed" && exit 1)

# ============================================================================
# STAGE 2: Backend (Flask + Gunicorn)
# ============================================================================
FROM python:3.11-slim AS backend

# Variables Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
@@ -54,38 +55,50 @@ WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar backend
COPY app/ ./app/
COPY wsgi.py run.py ./ 
COPY companies_config.json ./ 
COPY extended_companies_config.json ./ 

# Copiar build del frontend desde el Stage 1
COPY --from=frontend-builder /frontend/build ./src/build

# Validar build en backend
RUN test -f src/build/index.html || (echo "❌ Build not copied" && exit 1)


# Crear usuario seguro
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Exponer puerto
ENV PORT=8080
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Iniciar servidor con Gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
@@ -98,6 +111,5 @@ CMD ["gunicorn", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "wsgi:app"]

