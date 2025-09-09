# migrations/migrate.py
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecutar migración completa de JSON a PostgreSQL"""
    
    # 1. Conectar a PostgreSQL
    database_url = os.getenv('DATABASE_URL') or (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'password')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'prompts_db')}"
    )
    
    conn = psycopg2.connect(database_url)
    
    try:
        with conn.cursor() as cursor:
            # 2. Ejecutar schema inicial
            schema_file = os.path.join(os.path.dirname(__file__), '001_initial_schema.sql')
            if os.path.exists(schema_file):
                with open(schema_file, 'r') as f:
                    cursor.execute(f.read())
                logger.info("✅ Schema created successfully")
            
            # 3. Insertar prompts por defecto
            seed_file = os.path.join(os.path.dirname(__file__), '002_seed_default_prompts.sql')
            if os.path.exists(seed_file):
                with open(seed_file, 'r') as f:
                    cursor.execute(f.read())
                logger.info("✅ Default prompts seeded")
            
            # 4. Migrar datos de JSON
            json_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'custom_prompts.json')
            if os.path.exists(json_file):
                migrated = migrate_json_data(cursor, json_file)
                logger.info(f"✅ Migrated {migrated} custom prompts")
            
            conn.commit()
            logger.info("🎉 Migration completed successfully!")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

def migrate_json_data(cursor, json_file):
    """Migrar datos del archivo JSON"""
    with open(json_file, 'r', encoding='utf-8') as f:
        custom_prompts = json.load(f)
    
    migrated_count = 0
    
    for company_id, agents in custom_prompts.items():
        for agent_name, agent_data in agents.items():
            if agent_data.get('is_custom') and agent_data.get('template'):
                cursor.execute("""
                    INSERT INTO custom_prompts (
                        company_id, agent_name, template, 
                        version, created_by, modified_by,
                        created_at, modified_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (company_id, agent_name, is_active) 
                    WHERE is_active = true DO NOTHING
                """, (
                    company_id,
                    agent_name,
                    agent_data['template'],
                    1,
                    agent_data.get('modified_by', 'migrated'),
                    agent_data.get('modified_by', 'migrated'),
                    agent_data.get('modified_at', datetime.utcnow().isoformat()),
                    agent_data.get('modified_at', datetime.utcnow().isoformat())
                ))
                migrated_count += 1
    
    return migrated_count

if __name__ == "__main__":
    run_migration()
