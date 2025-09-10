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
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM get_prompt_with_fallback(%s, %s)', ('test', 'router_agent'))
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
"

echo "✅ Migración verificada exitosamente"

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
