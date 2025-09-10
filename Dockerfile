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
RUN cat > start.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 Iniciando aplicación con migración automática..."

# Verificar que DATABASE_URL existe
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL no configurada"
    exit 1
fi

echo "📊 DATABASE_URL configurada: ${DATABASE_URL:0:20}..."

# Ejecutar migración PostgreSQL automáticamente
echo "🔧 Ejecutando migración de base de datos..."
python migrate_prompts_to_postgresql.py --auto

# Verificar que la migración funcionó
echo "✅ Verificando migración..."
if python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM get_prompt_with_fallback(\'test\', \'router_agent\')')
    result = cursor.fetchone()
    if result:
        print('✅ Función get_prompt_with_fallback funcionando')
    else:
        print('❌ Error: función no retorna resultados')
        exit(1)
except Exception as e:
    print(f'❌ Error verificando migración: {e}')
    exit(1)
finally:
    if 'conn' in locals():
        conn.close()
"; then
    echo "✅ Migración verificada exitosamente"
else
    echo "❌ Error en verificación de migración"
    exit 1
fi

# Iniciar aplicación
echo "🎉 Iniciando aplicación Flask..."
exec gunicorn \
     --bind 0.0.0.0:8080 \
     --workers 2 \
     --threads 4 \
     --timeout 120 \
     --keep-alive 2 \
     --max-requests 1000 \
     --max-requests-jitter 100 \
     --preload \
     --log-level info \
     --access-logfile - \
     --error-logfile - \
     wsgi:app
EOF

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
