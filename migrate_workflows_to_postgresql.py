#!/usr/bin/env python3
"""
migrate_workflows_to_postgresql.py
Migración de workflows a PostgreSQL - Compatible con Railway
"""

import os
import sys
import logging
import psycopg2
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def run_workflows_migration(db_url: str = None) -> bool:
    """Ejecutar migración de workflows"""
    try:
        db_url = db_url or os.getenv('DATABASE_URL')
        
        if not db_url:
            logger.warning("⚠️ DATABASE_URL not found - skipping workflows migration")
            return True
        
        logger.info("🚀 Starting workflows migration...")
        
        # Conectar a PostgreSQL
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Verificar si ya existen las tablas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'workflows'
        """)
        
        if cursor.fetchone()[0] > 0:
            logger.info("✅ Workflows tables already exist - skipping migration")
            cursor.close()
            conn.close()
            return True
        
        # Leer y ejecutar schema
        schema_file = os.path.join(os.path.dirname(__file__), 'workflows_schema.sql')
        
        if not os.path.exists(schema_file):
            logger.error(f"❌ workflows_schema.sql not found at {schema_file}")
            return False
        
        logger.info(f"📄 Reading schema from {schema_file}")
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        logger.info("🔨 Executing workflows schema...")
        cursor.execute(schema_sql)
        conn.commit()
        
        # Verificar creación
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name IN ('workflows', 'workflow_versions', 'workflow_executions', 'workflow_templates', 'workflow_nodes')
        """)
        
        table_count = cursor.fetchone()[0]
        
        if table_count == 5:
            logger.info(f"✅ Workflows migration completed successfully ({table_count} tables created)")
        else:
            logger.warning(f"⚠️ Expected 5 tables, found {table_count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Workflows migration failed: {e}")
        return False

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate workflows to PostgreSQL')
    parser.add_argument('--auto', action='store_true', help='Run automatically')
    parser.add_argument('--db-url', type=str, help='PostgreSQL URL')
    
    args = parser.parse_args()
    
    success = run_workflows_migration(args.db_url)
    
    if success:
        logger.info("🎉 Workflows migration completed")
        return 0
    else:
        logger.error("💥 Workflows migration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
