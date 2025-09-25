# -----------------------------------------------------------------------------
# Dockerfile (Frontend Vue 3 + Backend Flask) - enfoque robusto para Vite build
# -----------------------------------------------------------------------------

# --- STAGE 1: Frontend build (Node) ---
FROM node:18.20.1-bullseye AS frontend-builder
WORKDIR /frontend


# Herramientas útiles
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# npm config para menos ruido
RUN npm config set audit false && npm config set fund false && npm config set loglevel warn

# ---- FORZAR instalación de devDependencies SOLO en esta etapa ----
ENV NODE_ENV=development
ENV NPM_CONFIG_PRODUCTION=false

# Copiar package.json(s) al contexto raíz del builder
COPY src/package*.json ./ 
COPY src/index.html ./ 
COPY src/ ./src/

# Copiar vite.config.js al root para que vite lo use
COPY src/vite.config.js ./vite.config.js

# Instalar dependencias (incluye devDependencies)
RUN if [ -f package-lock.json ]; then \
      echo "✅ package-lock.json encontrado -> npm ci (incluye devDependencies)"; \
      npm ci --include=dev; \
    else \
      echo "⚠ package-lock.json no encontrado -> npm install --package-lock-only && npm ci --include=dev"; \
      npm install --package-lock-only && npm ci --include=dev; \
    fi

# Debug node_modules para ver plugin-vue
RUN ls -la node_modules/@vitejs | grep plugin-vue || echo "❌ plugin-vue no encontrado"

# Ejecutar build desde /frontend
RUN echo "🏗️ Ejecutando npm run build (en /frontend)..." && \
    npm run build 2>&1 | tee /frontend/build.log

# Verificación dist
RUN echo "📦 Verificando /frontend/dist ..." && \
    ls -la /frontend/dist || (echo "ERROR: /frontend/dist no existe" && cat /frontend/build.log && exit 1) && \
    test -f /frontend/dist/index.html || (echo "ERROR: /frontend/dist/index.html no encontrado" && cat /frontend/build.log && exit 1)


# --- STAGE 2: Backend Python + static files ---
FROM python:3.11.6-slim-bullseye

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema necesarias
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json custom_prompts.json ./
COPY migrate_prompts_to_postgresql.py postgresql_schema.sql ./
COPY migrate_companies_to_postgresql.py ./

# Copiar build estático desde el builder
COPY --from=frontend-builder /frontend/dist ./static

# Verificaciones en build para atrapar problemas temprano
RUN echo "🔧 Verificando backend y static files..." && \
    test -f wsgi.py && echo "✅ wsgi.py encontrado" || (echo "❌ wsgi.py faltante" && exit 1) && \
    test -d app && echo "✅ app/ directory encontrado" || (echo "❌ app/ faltante" && exit 1) && \
    test -d static && echo "✅ static/ copiado" || (echo "❌ static/ no copiado" && ls -la . && exit 1) && \
    test -f static/index.html && echo "✅ static/index.html OK" || (echo "❌ static/index.html NO existe" && ls -la static || exit 1)

# Crear usuario no-root y aplicar permisos
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

# Script de arranque (runtime migrations + gunicorn)
USER root
RUN cat > /app/start.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Iniciando aplicación multi-tenant..."
ls -la /app/static | sed -n '1,200p' || true

if [ ! -f /app/static/index.html ]; then
  echo "❌ CRÍTICO: /app/static/index.html no existe"
  exit 1
fi

if [ ! -z "${DATABASE_URL:-}" ]; then
  echo "🔄 DATABASE_URL detectado -> ejecutando migraciones"
  python migrate_prompts_to_postgresql.py --auto || echo "⚠️ Migración de prompts falló (continuando)"
  python migrate_companies_to_postgresql.py --auto || echo "⚠️ Migración de companies falló (continuando)"
else
  echo "⚠️ DATABASE_URL no presente -> saltando migraciones runtime"
fi

echo "🎯 Iniciando Gunicorn en 0.0.0.0:8080"
exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 wsgi:app
EOF

RUN chmod +x /app/start.sh && chown appuser:appuser /app/start.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

USER appuser
EXPOSE 8080
CMD ["/app/start.sh"]
