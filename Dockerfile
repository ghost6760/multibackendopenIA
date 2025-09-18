# Dockerfile - Backend Flask + Frontend Vue.js 3
# Optimizado para Railway deployment con Vue.js
# Multi-stage build: Node.js para frontend + Python para backend
# ============================================================================

# ============================================================================
# STAGE 1: Build Frontend Vue.js
# ============================================================================
FROM node:18-alpine as frontend-builder

# Directorio de trabajo para el frontend
WORKDIR /frontend

# Copiar package files del frontend
COPY src/package*.json ./

# Instalar dependencias de Node.js
RUN npm ci --only=production

# Copiar el código fuente del frontend
COPY src/ ./

# Build del frontend Vue.js para producción
RUN npm run build

# Verificar que el build se completó correctamente
RUN ls -la dist/ && test -f dist/index.html

# ============================================================================
# STAGE 2: Build Backend Python + Frontend estático
# ============================================================================
FROM python:3.11-slim

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
COPY companies_config.json extended_companies_config.json custom_prompts.json ./

# Copiar scripts de migración
COPY migrate_prompts_to_postgresql.py postgresql_schema.sql ./
COPY migrate_companies_to_postgresql.py ./

# 🆕 NUEVO: Copiar archivos estáticos del frontend Vue.js desde el build
COPY --from=frontend-builder /frontend/dist ./static

# Verificar que los archivos del frontend se copiaron correctamente
RUN ls -la static/ && \
    test -f static/index.html && \
    echo "✅ Frontend Vue.js build copiado correctamente"

# Ejecutar migración de prompts durante el build (solo si hay DATABASE_URL)
RUN if [ ! -z "$DATABASE_URL" ]; then \
        echo "🔄 Ejecutando migración automática de prompts durante build..."; \
        python migrate_prompts_to_postgresql.py --auto || echo "⚠️ Migración de prompts falló, continuando..." && \
        echo "🔄 Ejecutando migración automática de configuración de empresas durante build..."; \
        python migrate_companies_to_postgresql.py --auto || echo "⚠️ Migración de empresas falló, continuando..."; \
    else \
        echo "⚠️ DATABASE_URL no disponible durante build, migraciones se saltarán"; \
    fi

# Crear usuario no root para seguridad
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Script de inicio que ejecuta migración antes de iniciar gunicorn
USER root
RUN echo '#!/bin/bash\n\
echo "🚀 Iniciando aplicación multi-tenant con Frontend Vue.js..."\n\
\n\
# Ejecutar migración de prompts si DATABASE_URL está disponible\n\
if [ ! -z "$DATABASE_URL" ]; then\n\
    echo "🔄 Ejecutando migración automática de prompts..."\n\
    python migrate_prompts_to_postgresql.py --auto || echo "⚠️ Migración de prompts falló"\n\
    \n\
    echo "🔄 Ejecutando migración automática de configuración de empresas..."\n\
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

# Comando de inicio
CMD ["/app/start.sh"]
