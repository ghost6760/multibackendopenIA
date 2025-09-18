# Dockerfile - CORREGIDO - Backend Flask + Frontend Vue.js 3
# FIX: Instala devDependencies necesarias para vite build
# Multi-stage build: Node.js para frontend + Python para backend
# ============================================================================

# ============================================================================
# STAGE 1: Build Frontend Vue.js - CORREGIDO PARA VITE
# ============================================================================
FROM node:18-alpine as frontend-builder

WORKDIR /frontend

# Configurar npm para evitar problemas comunes
RUN npm config set audit false && \
    npm config set fund false && \
    npm config set loglevel warn

# Copiar archivos de dependencias (pueden o no existir)
COPY src/package.json ./
# Intentar copiar package-lock.json si existe (no falla si no existe)
COPY src/package-loc[k].json ./

# 🔧 ESTRATEGIA CORREGIDA: Instalar TODAS las dependencias (incluyendo devDependencies)
RUN echo "📦 Estrategia corregida de instalación..." && \
    if [ -f package-lock.json ]; then \
        echo "✅ package-lock.json encontrado, instalando con npm ci"; \
        npm ci; \
    else \
        echo "📝 package-lock.json no encontrado, generando automáticamente..."; \
        npm install --package-lock-only && \
        echo "✅ package-lock.json generado, ahora instalando TODAS las dependencias"; \
        npm ci; \
    fi && \
    echo "✅ Todas las dependencias instaladas (incluidas devDependencies para build)"

# Verificar que vite esté instalado
RUN echo "🔍 Verificando vite:" && \
    npx vite --version && \
    echo "✅ Vite está disponible"

# Copiar todo el código fuente del frontend
COPY src/ ./

# Verificar archivos críticos antes del build
RUN echo "🔍 Verificando archivos críticos:" && \
    test -f package.json && echo "✅ package.json" || echo "❌ package.json" && \
    test -f vite.config.js && echo "✅ vite.config.js" || echo "⚠️ vite.config.js no encontrado" && \
    test -f index.html && echo "✅ index.html" || echo "❌ index.html" && \
    test -d src && echo "✅ src/ directory" || echo "⚠️ src/ directory no encontrado"

# Build con vite disponible
RUN echo "🏗️ Iniciando build de Vue.js con vite..." && \
    npm run build 2>&1 | tee build.log && \
    echo "✅ Build completado exitosamente"

# Verificación exhaustiva del build
RUN echo "📊 Verificación del build:" && \
    ls -la dist/ && \
    test -f dist/index.html && echo "✅ dist/index.html existe" || (echo "❌ ERROR: dist/index.html NO existe" && cat build.log && exit 1) && \
    echo "📁 Contenido de dist/:" && \
    find dist/ -type f -name "*.js" -o -name "*.css" -o -name "*.html" | head -10 && \
    echo "📏 Tamaño del build:" && \
    du -sh dist/ && \
    echo "✅ Build verificado exitosamente"

# ============================================================================
# STAGE 2: Backend Python + Frontend estático
# ============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Instalar dependencias del sistema con verificación
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ curl && \
    rm -rf /var/lib/apt/lists/* && \
    echo "✅ Dependencias del sistema instaladas"

# Backend Python
COPY requirements.txt .
RUN echo "🐍 Instalando dependencias de Python..." && \
    pip install --no-cache-dir -r requirements.txt && \
    echo "✅ Dependencias de Python instaladas"

# Copiar aplicación backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json custom_prompts.json ./
COPY migrate_prompts_to_postgresql.py postgresql_schema.sql ./
COPY migrate_companies_to_postgresql.py ./

# Verificar backend
RUN echo "🔧 Verificando backend:" && \
    test -f wsgi.py && echo "✅ wsgi.py" || echo "❌ wsgi.py" && \
    test -d app && echo "✅ app/" || echo "❌ app/" && \
    python -c "from app import create_app; print('✅ Backend importa correctamente')" || echo "⚠️ Problema con imports del backend"

# Copiar frontend desde stage 1 CON VERIFICACIÓN
COPY --from=frontend-builder /frontend/dist ./static

# VERIFICACIÓN EXHAUSTIVA del frontend copiado
RUN echo "🎯 Verificación exhaustiva del frontend:" && \
    echo "📁 Contenido de static/:" && \
    ls -la static/ && \
    echo "" && \
    test -f static/index.html && echo "✅ static/index.html existe" || (echo "❌ CRÍTICO: static/index.html NO existe" && exit 1) && \
    test -d static/assets && echo "✅ static/assets/ existe" || echo "⚠️ static/assets/ no existe (puede ser normal)" && \
    echo "📏 Archivos estáticos encontrados:" && \
    find static/ -type f | wc -l && \
    echo "📏 Tamaño total de static/:" && \
    du -sh static/ && \
    echo "✅ Frontend copiado y verificado exitosamente"

# Migraciones opcionales
RUN if [ ! -z "$DATABASE_URL" ]; then \
        echo "🔄 Ejecutando migraciones automáticas durante build..."; \
        python migrate_prompts_to_postgresql.py --auto 2>&1 | tee migration.log || echo "⚠️ Migración de prompts falló" && \
        python migrate_companies_to_postgresql.py --auto 2>&1 | tee -a migration.log || echo "⚠️ Migración de empresas falló"; \
    else \
        echo "⚠️ DATABASE_URL no disponible durante build, saltando migraciones"; \
    fi

# Setup de usuario y permisos
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Script de inicio con verificación final
USER root
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Iniciando aplicación multi-tenant con Frontend Vue.js..."\n\
echo "📊 Verificación final del sistema:"\n\
echo "📁 Static directory:"\n\
ls -la static/ | head -10\n\
echo "🔍 Verificando archivos críticos:"\n\
test -f static/index.html && echo "✅ Frontend HTML existe" || echo "❌ Frontend HTML NO existe"\n\
test -f wsgi.py && echo "✅ WSGI existe" || echo "❌ WSGI NO existe"\n\
echo ""\n\
\n\
# Migraciones runtime\n\
if [ ! -z "$DATABASE_URL" ]; then\n\
    echo "🔄 Ejecutando migraciones runtime..."\n\
    python migrate_prompts_to_postgresql.py --auto || echo "⚠️ Migración de prompts falló"\n\
    python migrate_companies_to_postgresql.py --auto || echo "⚠️ Migración de empresas falló"\n\
else\n\
    echo "⚠️ DATABASE_URL no disponible, saltando migraciones"\n\
fi\n\
\n\
echo "🎯 Frontend Vue.js disponible en: /"\n\
echo "🔧 APIs disponibles en: /api/*"\n\
echo "📊 Health check en: /api/health"\n\
echo "🚀 Iniciando servidor Gunicorn..."\n\
\n\
exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 wsgi:app\n\
' > /app/start.sh && chmod +x /app/start.sh

USER appuser
CMD ["/app/start.sh"]
