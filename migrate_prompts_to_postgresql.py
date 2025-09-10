#!/usr/bin/env python3
# migrate_prompts_to_postgresql.py
# Script de migración para refactorización del sistema de prompts

import os
import sys
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Any

# Añadir el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.prompt_service import PromptService, get_prompt_service
from app.config.company_config import get_company_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class PromptMigrationManager:
    """Gestor de migración de prompts de JSON a PostgreSQL"""
    
    def __init__(self, db_connection_string: str = None):
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.prompt_service = None
        self.migration_stats = {
            "schema_created": False,
            "defaults_populated": False,
            "json_migrated": False,
            "companies_processed": 0,
            "prompts_migrated": 0,
            "errors": [],
            "start_time": None,
            "end_time": None
        }
    
    def run_complete_migration(self) -> Dict[str, Any]:
        """
        Ejecutar migración completa del sistema de prompts
        
        FASES:
        1. Crear schema PostgreSQL
        2. Poblar default_prompts desde agentes del repositorio
        3. Migrar custom_prompts.json existente
        4. Validar migración
        """
        logger.info("🚀 Iniciando migración completa del sistema de prompts")
        self.migration_stats["start_time"] = datetime.utcnow()
        
        try:
            # Fase 1: Crear schema
            if self._create_database_schema():
                self.migration_stats["schema_created"] = True
                logger.info("✅ Fase 1: Schema PostgreSQL creado")
            else:
                logger.error("❌ Fase 1: Error creando schema")
                return self.migration_stats
            
            # Fase 2: Poblar defaults
            if self._populate_default_prompts():
                self.migration_stats["defaults_populated"] = True
                logger.info("✅ Fase 2: Default prompts poblados")
            else:
                logger.error("❌ Fase 2: Error poblando defaults")
                return self.migration_stats
            
            # Fase 3: Migrar JSON existente
            if self._migrate_custom_prompts_file():
                self.migration_stats["json_migrated"] = True
                logger.info("✅ Fase 3: Prompts JSON migrados")
            else:
                logger.warning("⚠️ Fase 3: Migración JSON parcial o sin datos")
            
            # Fase 4: Validar
            if self._validate_migration():
                logger.info("✅ Fase 4: Migración validada exitosamente")
            else:
                logger.warning("⚠️ Fase 4: Validación con advertencias")
            
            self.migration_stats["end_time"] = datetime.utcnow()
            duration = (self.migration_stats["end_time"] - self.migration_stats["start_time"]).total_seconds()
            
            logger.info(f"🎉 Migración completada en {duration:.2f} segundos")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"💥 Error crítico en migración: {e}")
            self.migration_stats["errors"].append(f"Critical error: {str(e)}")
            self.migration_stats["end_time"] = datetime.utcnow()
            return self.migration_stats
    
    def _create_database_schema(self) -> bool:
        """Crear schema PostgreSQL si no existe"""
        logger.info("Creando schema PostgreSQL...")
        
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Leer archivo SQL del schema
                schema_file = os.path.join(os.path.dirname(__file__), 'postgresql_schema.sql')
                
                if os.path.exists(schema_file):
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    cursor.execute(schema_sql)
                else:
                    # Usar schema embebido si no existe el archivo
                    cursor.execute(self._get_embedded_schema_sql())
                
                conn.commit()
                logger.info("Schema PostgreSQL creado exitosamente")
                return True
                
        except Exception as e:
            logger.error(f"Error creando schema: {e}")
            self.migration_stats["errors"].append(f"Schema creation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _populate_default_prompts(self) -> bool:
        """Poblar default_prompts desde agentes del repositorio"""
        logger.info("Poblando default_prompts desde repositorio...")
        
        try:
            # Prompts extraídos de los agentes del repositorio
            default_prompts = {
                'router_agent': {
                    'template': 'Eres un asistente especializado en clasificar intenciones de usuarios. Analiza el mensaje y determina si es: VENTAS, SOPORTE, EMERGENCIA, AGENDAMIENTO, o DISPONIBILIDAD. Responde solo con la categoría en mayúsculas.',
                    'description': 'Clasificador de intenciones principal del sistema',
                    'category': 'routing'
                },
                'sales_agent': {
                    'template': 'Eres un especialista en ventas para servicios médicos y estéticos. Proporciona información comercial precisa, destacando beneficios y promoviendo la reserva de citas. Mantén un tono profesional y persuasivo.',
                    'description': 'Agente comercial especializado en conversión',
                    'category': 'commercial'
                },
                'support_agent': {
                    'template': 'Eres un asistente de soporte técnico amigable y eficiente. Ayuda a resolver dudas generales, problemas técnicos y proporciona información sobre servicios. Mantén un tono servicial y profesional.',
                    'description': 'Soporte general y atención al cliente',
                    'category': 'support'
                },
                'emergency_agent': {
                    'template': 'Eres un asistente para situaciones de emergencia médica. Proporciona información de primeros auxilios básicos, recomienda buscar atención médica inmediata cuando sea necesario, y ofrece números de emergencia. NUNCA des diagnósticos médicos.',
                    'description': 'Asistencia en emergencias médicas',
                    'category': 'emergency'
                },
                'schedule_agent': {
                    'template': 'Eres un asistente especializado en agendamiento de citas. Ayuda a los usuarios a programar, modificar o cancelar citas médicas. Proporciona información sobre disponibilidad y confirma los detalles de las citas.',
                    'description': 'Gestión de citas y programación',
                    'category': 'scheduling'
                },
                'availability_agent': {
                    'template': 'Eres un asistente que proporciona información sobre disponibilidad de servicios, horarios de atención, y disponibilidad de profesionales. Ofrece alternativas cuando no hay disponibilidad inmediata.',
                    'description': 'Consulta de disponibilidad y horarios',
                    'category': 'availability'
                }
            }
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                for agent_name, data in default_prompts.items():
                    cursor.execute("""
                        INSERT INTO default_prompts (agent_name, template, description, category)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (agent_name) DO UPDATE SET
                            template = EXCLUDED.template,
                            description = EXCLUDED.description,
                            category = EXCLUDED.category,
                            updated_at = CURRENT_TIMESTAMP
                    """, (agent_name, data['template'], data['description'], data['category']))
                
                conn.commit()
                logger.info(f"Default prompts poblados: {len(default_prompts)} agentes")
                return True
                
        except Exception as e:
            logger.error(f"Error poblando default prompts: {e}")
            self.migration_stats["errors"].append(f"Default prompts population failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _migrate_custom_prompts_file(self) -> bool:
        """Migrar custom_prompts.json existente a PostgreSQL"""
        logger.info("Migrando custom_prompts.json...")
        
        custom_prompts_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            logger.info("No se encontró custom_prompts.json - creando archivo vacío")
            return True
        
        try:
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            if not custom_prompts:
                logger.info("custom_prompts.json está vacío")
                return True
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                for company_id, company_data in custom_prompts.items():
                    if not isinstance(company_data, dict):
                        continue
                    
                    self.migration_stats["companies_processed"] += 1
                    logger.info(f"Migrando empresa: {company_id}")
                    
                    for agent_name, agent_data in company_data.items():
                        if not isinstance(agent_data, dict):
                            continue
                        
                        # Solo migrar si es personalizado y tiene template
                        if agent_data.get('is_custom', False) and agent_data.get('template'):
                            try:
                                cursor.execute("""
                                    INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                        template = EXCLUDED.template,
                                        modified_by = EXCLUDED.modified_by,
                                        modified_at = CURRENT_TIMESTAMP,
                                        notes = EXCLUDED.notes
                                """, (
                                    company_id,
                                    agent_name,
                                    agent_data['template'],
                                    agent_data.get('modified_by', 'migration'),
                                    agent_data.get('modified_by', 'migration'),
                                    f"Migrated from JSON at {datetime.utcnow().isoformat()}"
                                ))
                                
                                self.migration_stats["prompts_migrated"] += 1
                                logger.debug(f"Migrado: {company_id}/{agent_name}")
                                
                            except Exception as e:
                                error_msg = f"Error migrando {company_id}/{agent_name}: {str(e)}"
                                logger.warning(error_msg)
                                self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"Migración JSON completada: {self.migration_stats['prompts_migrated']} prompts")
                return True
                
        except Exception as e:
            logger.error(f"Error en migración JSON: {e}")
            self.migration_stats["errors"].append(f"JSON migration failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _validate_migration(self) -> bool:
        """Validar que la migración fue exitosa"""
        logger.info("Validando migración...")
        
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar que las tablas existen
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('custom_prompts', 'prompt_versions', 'default_prompts')
                """)
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                if len(tables) != 3:
                    logger.error(f"Faltan tablas: {set(['custom_prompts', 'prompt_versions', 'default_prompts']) - set(tables)}")
                    return False
                
                # Verificar conteos
                cursor.execute("SELECT COUNT(*) as count FROM default_prompts")
                default_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM custom_prompts WHERE is_active = true")
                custom_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM prompt_versions")
                version_count = cursor.fetchone()['count']
                
                # Verificar funciones
                cursor.execute("""
                    SELECT routine_name FROM information_schema.routines 
                    WHERE routine_schema = 'public' 
                    AND routine_name IN ('get_prompt_with_fallback', 'repair_prompts_from_repository')
                """)
                functions = [row['routine_name'] for row in cursor.fetchall()]
                
                # Log de validación
                logger.info(f"✅ Tablas creadas: {len(tables)}/3")
                logger.info(f"✅ Default prompts: {default_count}")
                logger.info(f"✅ Custom prompts: {custom_count}")
                logger.info(f"✅ Version records: {version_count}")
                logger.info(f"✅ Funciones: {len(functions)}/2")
                
                # Probar función de fallback
                cursor.execute("SELECT * FROM get_prompt_with_fallback('test_company', 'router_agent')")
                fallback_test = cursor.fetchone()
                
                if fallback_test and fallback_test['template']:
                    logger.info("✅ Función de fallback operativa")
                    return True
                else:
                    logger.error("❌ Función de fallback no funciona")
                    return False
                
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            self.migration_stats["errors"].append(f"Validation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _get_embedded_schema_sql(self) -> str:
        """Schema SQL embebido como fallback"""
        return """
        -- Schema básico embebido
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        
        CREATE TABLE IF NOT EXISTS custom_prompts (
            id BIGSERIAL PRIMARY KEY,
            company_id VARCHAR(100) NOT NULL,
            agent_name VARCHAR(100) NOT NULL,
            template TEXT NOT NULL,
            is_active BOOLEAN DEFAULT true,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100) DEFAULT 'admin',
            modified_by VARCHAR(100) DEFAULT 'admin',
            notes TEXT,
            CONSTRAINT unique_active_prompt UNIQUE (company_id, agent_name)
        );
        
        CREATE TABLE IF NOT EXISTS prompt_versions (
            id BIGSERIAL PRIMARY KEY,
            prompt_id BIGINT REFERENCES custom_prompts(id) ON DELETE CASCADE,
            company_id VARCHAR(100) NOT NULL,
            agent_name VARCHAR(100) NOT NULL,
            template TEXT NOT NULL,
            version INTEGER NOT NULL,
            action VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100) DEFAULT 'admin',
            notes TEXT
        );
        
        CREATE TABLE IF NOT EXISTS default_prompts (
            id BIGSERIAL PRIMARY KEY,
            agent_name VARCHAR(100) UNIQUE NOT NULL,
            template TEXT NOT NULL,
            description TEXT,
            category VARCHAR(50) DEFAULT 'general',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Índices básicos
        CREATE INDEX IF NOT EXISTS idx_custom_prompts_company_agent ON custom_prompts(company_id, agent_name);
        CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompt_versions(prompt_id);
        CREATE INDEX IF NOT EXISTS idx_default_prompts_agent ON default_prompts(agent_name);
        """
    
    def create_backup(self) -> str:
        """Crear backup del archivo JSON antes de migrar"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'custom_prompts.json'
            )
            
            if os.path.exists(custom_prompts_file):
                backup_file = f"{custom_prompts_file}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                
                with open(custom_prompts_file, 'r', encoding='utf-8') as src:
                    content = src.read()
                
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(content)
                
                logger.info(f"Backup creado: {backup_file}")
                return backup_file
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error creando backup: {e}")
            return ""


def main():
    """Función principal del script de migración"""
    print("🚀 Benova Multi-Tenant Prompts Migration Tool")
    print("=" * 50)
    
    # Verificar variables de entorno
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ Error: DATABASE_URL no configurada")
        print("   Configura la variable de entorno DATABASE_URL con la conexión PostgreSQL")
        sys.exit(1)
    
    print(f"📊 Base de datos: {db_url.split('@')[1] if '@' in db_url else 'configurada'}")
    
    # Confirmar migración
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        confirm = True
    else:
        confirm = input("\n¿Proceder con la migración? (y/N): ").lower().strip() == 'y'
    
    if not confirm:
        print("Migración cancelada")
        sys.exit(0)
    
    # Ejecutar migración
    migrator = PromptMigrationManager(db_url)
    
    # Crear backup
    backup_file = migrator.create_backup()
    if backup_file:
        print(f"✅ Backup creado: {os.path.basename(backup_file)}")
    
    # Ejecutar migración completa
    stats = migrator.run_complete_migration()
    
    # Mostrar resultados
    print("\n" + "=" * 50)
    print("📊 RESULTADOS DE MIGRACIÓN")
    print("=" * 50)
    
    duration = 0
    if stats["start_time"] and stats["end_time"]:
        duration = (stats["end_time"] - stats["start_time"]).total_seconds()
    
    print(f"⏱️  Duración: {duration:.2f} segundos")
    print(f"🏢 Empresas procesadas: {stats['companies_processed']}")
    print(f"🤖 Prompts migrados: {stats['prompts_migrated']}")
    
    if stats["schema_created"]:
        print("✅ Schema PostgreSQL creado")
    else:
        print("❌ Error creando schema")
    
    if stats["defaults_populated"]:
        print("✅ Default prompts poblados")
    else:
        print("❌ Error poblando defaults")
    
    if stats["json_migrated"]:
        print("✅ Prompts JSON migrados")
    else:
        print("⚠️  Migración JSON parcial")
    
    if stats["errors"]:
        print(f"\n⚠️  {len(stats['errors'])} errores encontrados:")
        for error in stats["errors"][:5]:  # Mostrar solo los primeros 5
            print(f"   - {error}")
        if len(stats["errors"]) > 5:
            print(f"   ... y {len(stats['errors']) - 5} errores más")
    
    print("\n🎉 Migración completada!")
    print("\nPróximos pasos:")
    print("1. Verificar que el sistema funciona correctamente")
    print("2. Probar las funciones de fallback")
    print("3. Usar la función 'Reparar' en el frontend si es necesario")
    
    if backup_file:
        print(f"4. El backup está disponible en: {os.path.basename(backup_file)}")


def main():
    """Función principal del script de migración - Versión sin interacción para Railway"""
    print("🚀 Benova Multi-Tenant Prompts Migration Tool")
    print("=" * 50)
    
    # Verificar variables de entorno
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ Error: DATABASE_URL no configurada")
        print("   Configura la variable de entorno DATABASE_URL con la conexión PostgreSQL")
        sys.exit(1)
    
    print(f"📊 Base de datos: {db_url.split('@')[1] if '@' in db_url else 'configurada'}")
    
    # Auto-confirmar migración si se pasa --auto
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        confirm = True
        print("🤖 Modo automático activado - ejecutando migración...")
    else:
        confirm = input("\n¿Proceder con la migración? (y/N): ").lower().strip() == 'y'
    
    if not confirm:
        print("Migración cancelada")
        sys.exit(0)
    
    # Ejecutar migración
    migrator = PromptMigrationManager(db_url)
    
    # Crear backup
    backup_file = migrator.create_backup()
    if backup_file:
        print(f"✅ Backup creado: {os.path.basename(backup_file)}")
    
    # Ejecutar migración completa
    stats = migrator.run_complete_migration()
    
    # Mostrar resultados
    print("\n" + "=" * 50)
    print("📊 RESULTADOS DE MIGRACIÓN")
    print("=" * 50)
    
    duration = 0
    if stats["start_time"] and stats["end_time"]:
        duration = (stats["end_time"] - stats["start_time"]).total_seconds()
    
    print(f"⏱️  Duración: {duration:.2f} segundos")
    print(f"🏢 Empresas procesadas: {stats['companies_processed']}")
    print(f"🤖 Prompts migrados: {stats['prompts_migrated']}")
    
    if stats["schema_created"]:
        print("✅ Schema PostgreSQL creado")
    else:
        print("❌ Error creando schema")
        sys.exit(1)
    
    if stats["defaults_populated"]:
        print("✅ Default prompts poblados")
    else:
        print("❌ Error poblando defaults")
        sys.exit(1)
    
    if stats["json_migrated"]:
        print("✅ Prompts JSON migrados")
    else:
        print("⚠️  Migración JSON parcial")
    
    if stats["errors"]:
        print(f"\n⚠️  {len(stats['errors'])} errores encontrados:")
        for error in stats["errors"][:3]:  # Mostrar solo los primeros 3
            print(f"   - {error}")
        if len(stats["errors"]) > 3:
            print(f"   ... y {len(stats['errors']) - 3} errores más")
    
    print("\n🎉 Migración completada exitosamente!")
    
    if backup_file:
        print(f"💾 Backup disponible en: {os.path.basename(backup_file)}")
    
    # Exit con código 0 para indicar éxito
    sys.exit(0)
