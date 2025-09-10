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
# COPIAR ARCHIVOS DE MIGRACIÓN (ESTO ES LO QUE FALTABA)
# ============================================================================
COPY migrate_prompts_to_postgresql.py ./
COPY postgresql_schema.sql ./

# Crear directorio static y copiar archivos estáticos
RUN mkdir -p ./static
COPY index.html ./static/
COPY script.js ./static/
COPY style.css ./static/

# Verificar que los archivos se copiaron correctamente
RUN ls -la && echo "=== Archivos de migración ===" && ls -la migrate_prompts_to_postgresql.py postgresql_schema.sql

# ============================================================================
# SCRIPT DE INICIO CON MIGRACIÓN AUTOMÁTICA
# ============================================================================
# Crear script de inicio que ejecute migración antes de la app
RUN echo '#!/bin/bash' > start.sh && \
    echo 'set -e' >> start.sh && \
    echo '' >> start.sh && \
    echo 'echo "🚀 Iniciando aplicación con migración automática..."' >> start.sh && \
    echo '' >> start.sh && \
    echo '# Verificar que DATABASE_URL existe' >> start.sh && \
    echo 'if [ -z "$DATABASE_URL" ]; then' >> start.sh && \
    echo '    echo "❌ ERROR: DATABASE_URL no configurada"' >> start.sh && \
    echo '    exit 1' >> start.sh && \
    echo 'fi' >> start.sh && \
    echo '' >> start.sh && \
    echo 'echo "📊 DATABASE_URL configurada: ${DATABASE_URL:0:20}..."' >> start.sh && \
    echo '' >> start.sh && \
    echo '# Ejecutar migración PostgreSQL automáticamente' >> start.sh && \
    echo 'echo "🔧 Ejecutando migración de base de datos..."' >> start.sh && \
    echo 'python migrate_prompts_to_postgresql.py --auto' >> start.sh && \
    echo '' >> start.sh && \
    echo '# Verificar que la migración funcionó' >> start.sh && \
    echo 'echo "✅ Verificando migración..."' >> start.sh && \
    echo 'python -c "' >> start.sh && \
    echo 'import os' >> start.sh && \
    echo 'import psycopg2' >> start.sh && \
    echo 'try:' >> start.sh && \
    echo '    conn = psycopg2.connect(os.getenv(\"DATABASE_URL\"))' >> start.sh && \
    echo '    cursor = conn.cursor()' >> start.sh && \
    echo '    cursor.execute(\"SELECT * FROM get_prompt_with_fallback(\\\"test\\\", \\\"router_agent\\\")\")' >> start.sh && \
    echo '    result = cursor.fetchone()' >> start.sh && \
    echo '    if result:' >> start.sh && \
    echo '        print(\"✅ Función get_prompt_with_fallback funcionando\")' >> start.sh && \
    echo '    else:' >> start.sh && \
    echo '        print(\"❌ Error: función no retorna resultados\")' >> start.sh && \
    echo '        exit(1)' >> start.sh && \
    echo 'except Exception as e:' >> start.sh && \
    echo '    print(f\"❌ Error verificando migración: {e}\")' >> start.sh && \
    echo '    exit(1)' >> start.sh && \
    echo 'finally:' >> start.sh && \
    echo '    if \"conn\" in locals():' >> start.sh && \
    echo '        conn.close()' >> start.sh && \
    echo '"' >> start.sh && \
    echo '' >> start.sh && \
    echo 'echo "✅ Migración verificada exitosamente"' >> start.sh && \
    echo '' >> start.sh && \
    echo '# Iniciar aplicación' >> start.sh && \
    echo 'echo "🎉 Iniciando aplicación Flask..."' >> start.sh && \
    echo 'exec gunicorn \' >> start.sh && \
    echo '     --bind 0.0.0.0:8080 \' >> start.sh && \
    echo '     --workers 2 \' >> start.sh && \
    echo '     --threads 4 \' >> start.sh && \
    echo '     --timeout 120 \' >> start.sh && \
    echo '     --keep-alive 2 \' >> start.sh && \
    echo '     --max-requests 1000 \' >> start.sh && \
    echo '     --max-requests-jitter 100 \' >> start.sh && \
    echo '     --preload \' >> start.sh && \
    echo '     --log-level info \' >> start.sh && \
    echo '     --access-logfile - \' >> start.sh && \
    echo '     --error-logfile - \' >> start.sh && \
    echo '     wsgi:app' >> start.sh

# Hacer el script ejecutable
RUN chmod +x start.sh

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
