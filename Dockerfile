# --- STAGE 1: Frontend build (Node) ---
FROM node:18-bullseye AS frontend-builder

# Evitar poner NODE_ENV=production aquí (necesitamos devDependencies para build)
WORKDIR /frontend

# Mejoros: herramientas comunes (git en caso de deps desde git)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Config npm para logs y audit
RUN npm config set audit false && \
    npm config set fund false && \
    npm config set loglevel warn

# Copiar package.json y package-lock.json (si existe) para cache de instalaciones
COPY src/package*.json ./

# Instalar dependencias (si existe package-lock.json usa npm ci, si no, genera lock y luego ci)
RUN if [ -f package-lock.json ]; then \
      echo "✅ package-lock.json encontrado -> npm ci"; \
      npm ci; \
    else \
      echo "⚠ package-lock.json no encontrado -> npm install --package-lock-only && npm ci"; \
      npm install --package-lock-only && npm ci; \
    fi

# Copiar resto del código del frontend
COPY src/ ./

# Debug: mostrar archivos importantes antes del build
RUN echo "🔎 Antes del build: mostrando package.json, vite.config.js y index.html (primeras 60 líneas)" && \
    (test -f package.json && head -n 40 package.json) || true && \
    (test -f vite.config.js && head -n 40 vite.config.js) || true && \
    (test -f index.html && head -n 40 index.html) || true

# Ejecutar build (guardar salida en build.log para debugging)
RUN echo "🏗️ Ejecutando npm run build" && \
    npm run build 2>&1 | tee build.log

# Verificación del resultado de build
RUN echo "📦 Verificando dist/ ..." && \
    ls -la dist || (echo "ERROR: dist/ no existe" && cat build.log && exit 1) && \
    test -f dist/index.html || (echo "ERROR: dist/index.html no encontrado" && cat build.log && exit 1) && \
    echo "✅ dist/index.html existe. Listado de archivos dist/:" && \
    find dist -maxdepth 2 -type f -print | sed -n '1,200p' && \
    du -sh dist

# --- STAGE 2: Backend Python + static files ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar dependencias del sistema para Python y posibles drivers nativos
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Instalar Python deps (requirements.txt debe estar en la raíz del repo)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json custom_prompts.json ./
COPY migrate_prompts_to_postgresql.py postgresql_schema.sql ./
COPY migrate_companies_to_postgresql.py ./

# Copiar assets estáticos desde el frontend-builder
COPY --from=frontend-builder /frontend/dist ./static

# Verificaciones en build para atrapar problemas temprano
RUN echo "🔧 Verificando backend y static files..." && \
    test -f wsgi.py && echo "✅ wsgi.py encontrado" || (echo "❌ wsgi.py faltante" && exit 1) && \
    test -d app && echo "✅ app/ directory encontrado" || (echo "❌ app/ faltante" && exit 1) && \
    test -d static && echo "✅ static/ copiado" || (echo "❌ static/ no copiado" && ls -la . && exit 1) && \
    test -f static/index.html && echo "✅ static/index.html OK" || (echo "❌ static/index.html NO existe" && ls -la static || exit 1)

# Crear usuario no-root y asignar permisos
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

# Crear start script (migraciones en runtime, verificación final y arranque Gunicorn)
USER root
RUN cat > /app/start.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Iniciando aplicación multi-tenant..."
echo "📁 Verificando static dir:"
ls -la /app/static | sed -n '1,200p' || true

if [ ! -f /app/static/index.html ]; then
  echo "❌ CRÍTICO: /app/static/index.html no existe"
  exit 1
fi

# Migraciones runtime (solo si DATABASE_URL está presente)
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

# HEALTHCHECK recomendable en Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1

USER appuser
EXPOSE 8080
CMD ["/app/start.sh"]

