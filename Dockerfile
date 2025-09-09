# Dockerfile con auto-migración para Railway
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

# Copiar código del backend y migraciones
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY wsgi.py run.py ./
COPY companies_config.json extended_companies_config.json custom_prompts.json ./

# Crear directorio static y copiar archivos estáticos
RUN mkdir -p ./static
COPY index.html ./static/
COPY script.js ./static/
COPY style.css ./static/

# Verificar que los archivos estáticos se copiaron
RUN ls -la static/ && test -f static/index.html

# Crear usuario no root para seguridad
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Script de inicio que ejecuta migraciones y luego inicia la app
CMD ["sh", "-c", "python migrations/run_migration.py && gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 --preload --log-level info --access-logfile - --error-logfile - wsgi:app"]
