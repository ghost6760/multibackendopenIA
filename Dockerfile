# --- STAGE 1: Frontend build (Node) - OPCIÓN B (root=src, outDir=../dist) ---
FROM node:18-bullseye AS frontend-builder

# No establecer NODE_ENV=production (necesitamos devDependencies para el build)
WORKDIR /frontend

# Herramientas útiles (git en caso de dependencias desde git)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# npm config
RUN npm config set audit false && \
    npm config set fund false && \
    npm config set loglevel warn

# Copiar package.json / package-lock.json para cache de instalación
COPY src/package*.json ./

# Instalar dependencias (usar package-lock si existe)
RUN if [ -f package-lock.json ]; then \
      echo "✅ package-lock.json encontrado -> npm ci"; \
      npm ci; \
    else \
      echo "⚠ package-lock.json no encontrado -> npm install --package-lock-only && npm ci"; \
      npm install --package-lock-only && npm ci; \
    fi

# Copiar todo el frontend dentro de /frontend/src
COPY src/ ./src/

# Debug: archivos importantes dentro de src antes del build
RUN echo "🔎 Listando /frontend y /frontend/src (archivos clave):" && \
    ls -la /frontend || true && \
    echo "--- /frontend/src ---" && ls -la /frontend/src || true && \
    echo "--- primeras líneas de src/index.html (si existe) ---" && \
    (test -f src/index.html && head -n 40 src/index.html) || true && \
    echo "--- primeras líneas de src/main.js (si existe) ---" && \
    (test -f src/main.js && head -n 40 src/main.js) || true && \
    echo "--- primeras líneas de src/vite.config.js (si existe) ---" && \
    (test -f src/vite.config.js && head -n 40 src/vite.config.js) || true

# Ejecutar build indicando root=src y outDir ../dist (esto genera /frontend/dist)
RUN echo "🏗️ Ejecutando npm run build -- --root src --outDir ../dist" && \
    npm run build -- --root src --outDir ../dist 2>&1 | tee build.log

# Verificación del resultado de build (dist debe estar en /frontend/dist)
RUN echo "📦 Verificando /frontend/dist ..." && \
    ls -la /frontend/dist || (echo "ERROR: /frontend/dist no existe" && cat build.log && exit 1) && \
    test -f /frontend/dist/index.html || (echo "ERROR: /frontend/dist/index.html no encontrado" && cat build.log && exit 1) && \
    echo "✅ /frontend/dist/index.html existe. Listado de archivos dist/:" && \
    find /frontend/dist -maxdepth 2 -type f -print | sed -n '1,200p' && \
    du -sh /frontend/dist

# --- STAGE 2: Backend Python + static files ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json custom_prompts.json ./
COPY migrate_prompts_to_postgresql.py postgresql_schema.sql ./
COPY migrate_companies_to_postgresql.py ./

# Copiar assets estáticos desde builder
COPY --from=frontend-builder /frontend/dist ./static

# Verificaciones en build
RUN echo "🔧 Verificando backend y static files..." && \
    test -f wsgi.py && echo "✅ wsgi.py encontrado" || (echo "❌ wsgi.py faltante" && exit 1) && \
    test -d app && echo "✅ app/ directory encontrado" || (echo "❌ app/ faltante" && exit 1) && \
    test -d static && echo "✅ static/ copiado" || (echo "❌ static/ no copiado" && ls -la . && exit 1) && \
    test -f static/index.html && echo "✅ static/index.html OK" || (echo "❌ static/index.html NO existe" && ls -la static || exit 1)

# Crear usuario no-root y permisos
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app

# Start script (migraciones en runtime, verificación final y Gunicorn)
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


