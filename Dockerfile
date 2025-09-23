# Dockerfile simplificado - Solo Backend Flask
# Optimizado para Railway deployment sin frontend React
# CON MIGRACIÓN AUTOMÁTICA DE PROMPTS
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

# 🆕 NUEVO: Copiar script de migración
COPY migrate_prompts_to_postgresql.py postgresql_schema.sql ./

# 🆕 NUEVO: Copiar script de migración de empresas (añadir esta línea)
COPY migrate_companies_to_postgresql.py postgresql_schema.sql ./

# Crear directorio static y copiar archivos estáticos desde la raíz del proyecto
RUN mkdir -p ./static
COPY index.html ./static/
COPY script.js ./static/
COPY style.css ./static/

# Verificar que los archivos estáticos se copiaron
RUN ls -la static/ && test -f static/index.html

# 🆕 NUEVO: Ejecutar migración de prompts durante el build (solo si hay DATABASE_URL)
# Esto se ejecutará cada vez que se construya la imagen
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

# 🆕 NUEVO: Script de inicio que ejecuta migración antes de iniciar gunicorn
# Crear script de startup
USER root
RUN echo '#!/bin/bash\n\
echo "🚀 Iniciando aplicación multi-tenant..."\n\
\n\
# Ejecutar migración de prompts si DATABASE_URL está disponible\n\
if [ ! -z "$DATABASE_URL" ]; then\n\
    echo "🔄 Ejecutando migración de prompts..."\n\
    python migrate_prompts_to_postgresql.py --auto || echo "⚠️ Migración de prompts falló, continuando..." && \\\n\
    echo "🔄 Ejecutando migración de configuración de empresas..."\n\
    python migrate_companies_to_postgresql.py --auto || echo "⚠️ Migración de empresas falló, continuando..."\n\
else\n\
    echo "⚠️ DATABASE_URL no disponible, saltando migraciones"\n\
fi\n\
\n\
echo "✅ Iniciando servidor gunicorn..."\n\
exec gunicorn \\\n\
     --bind 0.0.0.0:8080 \\\n\
     --workers 2 \\\n\
     --threads 4 \\\n\
     --timeout 120 \\\n\
     --keep-alive 2 \\\n\
     --max-requests 1000 \\\n\
     --max-requests-jitter 100 \\\n\
     --preload \\\n\
     --log-level info \\\n\
     --access-logfile - \\\n\
     --error-logfile - \\\n\
     "wsgi:app"' > /app/startup.sh && \
    chmod +x /app/startup.sh && \
    chown appuser:appuser /app/startup.sh

USER appuser

# Usar script de startup en lugar de comando directo
CMD ["/app/startup.sh"]
