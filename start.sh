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
echo "DEBUG: Ejecutando comando: python migrate_prompts_to_postgresql.py --auto"

# Ejecutar migración con salida detallada
if python migrate_prompts_to_postgresql.py --auto; then
    echo "✅ Script de migración completado"
else
    echo "❌ Error en script de migración"
    exit 1
fi

# Verificar conexión básica a la base de datos
echo "🔍 Verificando conexión a base de datos..."
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()
    print(f'✅ Conexión PostgreSQL exitosa: {version[0][:50]}...')
    conn.close()
except Exception as e:
    print(f'❌ Error conectando a PostgreSQL: {e}')
    exit(1)
"

# Verificar si las tablas fueron creadas
echo "🔍 Verificando tablas creadas..."
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute(\"\"\"
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('custom_prompts', 'default_prompts', 'prompt_versions')
    \"\"\")
    tables = [row[0] for row in cursor.fetchall()]
    print(f'📊 Tablas encontradas: {tables}')
    conn.close()
except Exception as e:
    print(f'❌ Error verificando tablas: {e}')
    exit(1)
"

# Verificar si las funciones fueron creadas
echo "🔍 Verificando funciones creadas..."
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute(\"\"\"
        SELECT routine_name FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name = 'get_prompt_with_fallback'
    \"\"\")
    functions = [row[0] for row in cursor.fetchall()]
    print(f'🔧 Funciones encontradas: {functions}')
    if not functions:
        print('❌ Función get_prompt_with_fallback NO encontrada')
        # Intentar crear la función manualmente
        print('🔧 Intentando crear función manualmente...')
        cursor.execute(\"\"\"
            CREATE OR REPLACE FUNCTION get_prompt_with_fallback(
                p_company_id VARCHAR(100),
                p_agent_name VARCHAR(100)
            ) RETURNS TABLE (
                template TEXT,
                source VARCHAR(50),
                is_custom BOOLEAN,
                version INTEGER,
                modified_at TIMESTAMP WITH TIME ZONE
            ) AS \$\$
            BEGIN
                -- 1. Intentar obtener prompt personalizado activo
                RETURN QUERY
                SELECT 
                    cp.template,
                    'custom'::VARCHAR(50) as source,
                    true as is_custom,
                    cp.version,
                    cp.modified_at
                FROM custom_prompts cp
                WHERE cp.company_id = p_company_id 
                  AND cp.agent_name = p_agent_name 
                  AND cp.is_active = true
                ORDER BY cp.version DESC
                LIMIT 1;
                
                IF FOUND THEN
                    RETURN;
                END IF;
                
                -- 2. Fallback a prompt por defecto
                RETURN QUERY
                SELECT 
                    dp.template,
                    'default'::VARCHAR(50) as source,
                    false as is_custom,
                    1 as version,
                    dp.updated_at as modified_at
                FROM default_prompts dp
                WHERE dp.agent_name = p_agent_name;
                
                -- 3. Fallback de emergencia
                IF NOT FOUND THEN
                    RETURN QUERY
                    SELECT 
                        ('Eres un asistente especializado en ' || p_agent_name || '. Ayuda al usuario de manera profesional.')::TEXT as template,
                        'hardcoded'::VARCHAR(50) as source,
                        false as is_custom,
                        0 as version,
                        CURRENT_TIMESTAMP as modified_at;
                END IF;
                
                RETURN;
            END;
            \$\$ LANGUAGE plpgsql;
        \"\"\")
        conn.commit()
        print('✅ Función creada manualmente')
    conn.close()
except Exception as e:
    print(f'❌ Error verificando/creando funciones: {e}')
    exit(1)
"

# Verificar que la migración funcionó
echo "✅ Verificando migración final..."
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM get_prompt_with_fallback(%s, %s)', ('test', 'router_agent'))
    result = cursor.fetchone()
    if result:
        print('✅ Función get_prompt_with_fallback funcionando correctamente')
        print(f'📝 Prompt de prueba: {result[0][:100]}...')
    else:
        print('❌ Error: función no retorna resultados')
        exit(1)
    conn.close()
except Exception as e:
    print(f'❌ Error verificando migración: {e}')
    exit(1)
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
