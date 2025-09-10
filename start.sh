#!/bin/bash
set -e

echo "🚀 Iniciando aplicación con migración automática MEJORADA..."

# Verificar que DATABASE_URL existe
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL no configurada"
    exit 1
fi

echo "📊 DATABASE_URL configurada: ${DATABASE_URL:0:20}..."

# NUEVA ESTRATEGIA: Verificar y crear schema solo si es necesario
echo "🔧 Verificando y ejecutando schema PostgreSQL..."
python -c "
import os
import psycopg2

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Verificar si las tablas ya existen
    cursor.execute('''
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = \'public\' 
        AND table_name IN (\'custom_prompts\', \'default_prompts\', \'prompt_versions\')
    ''')
    
    existing_tables = [row[0] for row in cursor.fetchall()]
    print(f'📊 Tablas existentes: {existing_tables}')
    
    if len(existing_tables) == 3:
        print('✅ Todas las tablas ya existen, saltando creación de schema')
    else:
        print(f'📄 Ejecutando schema SQL (faltan {3 - len(existing_tables)} tablas)...')
        
        # Leer y ejecutar el schema SQL con CREATE IF NOT EXISTS
        with open('postgresql_schema.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Modificar el SQL para usar IF NOT EXISTS
        schema_sql = schema_sql.replace('CREATE TABLE custom_prompts', 'CREATE TABLE IF NOT EXISTS custom_prompts')
        schema_sql = schema_sql.replace('CREATE TABLE prompt_versions', 'CREATE TABLE IF NOT EXISTS prompt_versions')
        schema_sql = schema_sql.replace('CREATE TABLE default_prompts', 'CREATE TABLE IF NOT EXISTS default_prompts')
        
        cursor.execute(schema_sql)
        print('✅ Schema SQL ejecutado exitosamente')
    
    # Verificar tablas finales
    cursor.execute('''
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = \'public\' 
        AND table_name IN (\'custom_prompts\', \'default_prompts\', \'prompt_versions\')
    ''')
    
    final_tables = [row[0] for row in cursor.fetchall()]
    print(f'📊 Tablas disponibles: {final_tables}')
    
    if len(final_tables) == 3:
        print('✅ Todas las tablas están disponibles')
    else:
        print(f'⚠️ Solo hay {len(final_tables)} de 3 tablas esperadas')
    
    conn.close()
    
except Exception as e:
    print(f'❌ Error verificando/creando schema: {e}')
    exit(1)
"

# Ahora ejecutar el script de migración de datos
echo "🔧 Ejecutando migración de datos..."
if python migrate_prompts_to_postgresql.py --auto; then
    echo "✅ Script de migración de datos completado"
else
    echo "⚠️ Advertencia: Error en migración de datos, pero continuando..."
fi

# Verificar conexión básica a la base de datos
echo "🔍 Verificando conexión final a base de datos..."
python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()
    print(f'✅ Conexión PostgreSQL exitosa: {version[0][:50]}...')
    
    # Verificar tablas finales
    cursor.execute(\"\"\"
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('custom_prompts', 'default_prompts', 'prompt_versions')
    \"\"\")
    tables = [row[0] for row in cursor.fetchall()]
    print(f'📊 Tablas disponibles: {tables}')
    
    # Verificar función
    cursor.execute(\"\"\"
        SELECT routine_name FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name = 'get_prompt_with_fallback'
    \"\"\")
    functions = [row[0] for row in cursor.fetchall()]
    print(f'🔧 Funciones disponibles: {functions}')
    
    # Test básico de la función
    if functions:
        cursor.execute(\"SELECT * FROM get_prompt_with_fallback('test_company', 'general_agent') LIMIT 1\")
        print('✅ Función get_prompt_with_fallback funcionando correctamente')
    
    conn.close()
    
except Exception as e:
    print(f'❌ Error en verificación final: {e}')
    exit(1)
"

echo "🎯 Iniciando aplicación Flask..."

# Determinar el comando correcto para iniciar la aplicación
if command -v gunicorn &> /dev/null; then
    echo "🚀 Iniciando con Gunicorn..."
    exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --log-level info wsgi:app
elif command -v uwsgi &> /dev/null; then
    echo "🚀 Iniciando con uWSGI..."
    exec uwsgi --http 0.0.0.0:$PORT --wsgi-file wsgi.py --callable app --processes 2 --threads 2
else
    echo "🚀 Iniciando con Flask dev server..."
    exec python run.py
fi
