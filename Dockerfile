# Dockerfile con migración automática de PostgreSQL
# Optimizado para Railway deployment con setup de DB automático
# ============================================================================
FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema (agregar postgresql-client para psql)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY app/ ./app/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json custom_prompts.json ./

# ============================================================================
# COPIAR ARCHIVOS DE MIGRACIÓN
# ============================================================================
COPY migrate_prompts_to_postgresql.py ./
COPY postgresql_schema.sql ./

# Copiar script de inicio corregido
COPY start.sh ./
RUN chmod +x start.sh

# Crear directorio static y copiar archivos estáticos
RUN mkdir -p ./static
COPY index.html ./static/
COPY script.js ./static/
COPY style.css ./static/

# Verificar que los archivos se copiaron correctamente
RUN ls -la && echo "=== Archivos de migración ===" && ls -la migrate_prompts_to_postgresql.py postgresql_schema.sql start.sh

# Crear usuario no root para seguridad
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8080

# Health check mejorado
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Comando de inicio usando el script con migración
CMD ["./start.sh"]
