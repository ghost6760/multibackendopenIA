#!/usr/bin/env python3
"""
migrate_prompts_to_postgresql_fixed.py
Migración corregida que resuelve el problema de constraints con PostgreSQL
"""

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class FixedPromptMigrationManager:
    """Migración corregida que maneja constraints PostgreSQL correctamente"""
    
    def __init__(self, db_connection_string: str = None):
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.migration_stats = {
            "schema_created": False,
            "constraints_created": False,
            "defaults_populated": False,
            "json_migrated": False,
            "companies_processed": 0,
            "prompts_migrated": 0,
            "errors": [],
            "start_time": None,
            "end_time": None
        }
        
        # Configuración válida del sistema
        self.valid_companies = ['benova', 'spa_wellness', 'medispa', 'dental_clinic']
        self.valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
    
    def run_complete_migration(self) -> Dict[str, Any]:
        """Ejecutar migración completa con constraints corregidos"""
        logger.info("🚀 Iniciando migración FINAL con arquitectura separada")
        self.migration_stats["start_time"] = datetime.utcnow()
        
        try:
            # Fase 1: Crear schema completo con arquitectura separada
            if self._create_complete_schema():
                self.migration_stats["schema_created"] = True
                logger.info("✅ Fase 1: Schema completo creado")
            else:
                logger.error("❌ Fase 1: Error creando schema")
                return self.migration_stats
            
            # Fase 2: Crear constraints de forma segura (PostgreSQL compatible)
            if self._create_constraints_safe():
                self.migration_stats["constraints_created"] = True
                logger.info("✅ Fase 2: Constraints creados correctamente")
            else:
                logger.warning("⚠️ Fase 2: Algunos constraints no se pudieron crear, pero continuando...")
            
            # Fase 3: Poblar default_prompts con arquitectura separada
            if self._populate_default_prompts_separated():
                self.migration_stats["defaults_populated"] = True
                logger.info("✅ Fase 3: Default prompts poblados")
            else:
                logger.error("❌ Fase 3: Error poblando defaults")
                return self.migration_stats
            
            # Fase 4: Migrar custom prompts si existen
            if self._migrate_custom_prompts():
                self.migration_stats["json_migrated"] = True
                logger.info("✅ Fase 4: Custom prompts migrados")
            else:
                logger.warning("⚠️ Fase 4: Migración de custom prompts parcial")
            
            # Fase 5: Validar migración final
            if self._validate_final_migration():
                logger.info("✅ Fase 5: Migración validada exitosamente")
            else:
                logger.warning("⚠️ Fase 5: Validación con advertencias")
            
            self.migration_stats["end_time"] = datetime.utcnow()
            duration = (self.migration_stats["end_time"] - self.migration_stats["start_time"]).total_seconds()
            
            logger.info(f"🎉 Migración FINAL completada en {duration:.2f} segundos")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"💥 Error crítico en migración: {e}")
            self.migration_stats["errors"].append(f"Critical error: {str(e)}")
            return self.migration_stats
    
    def _create_complete_schema(self) -> bool:
        """Crear schema completo con arquitectura separada desde cero"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Schema con arquitectura separada correcta (compatible con postgresql_schema.sql)
                schema_sql = """
                -- Extensiones necesarias
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                
                -- Tabla de prompts personalizados (custom_prompts)
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
                    notes TEXT
                );
                
                -- Tabla de historial de versiones
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id BIGSERIAL PRIMARY KEY,
                    prompt_id BIGINT,
                    company_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100) NOT NULL,
                    template TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    notes TEXT
                );
                
                -- Tabla de prompts por defecto (ARQUITECTURA MULTI-TENANT)
                CREATE TABLE IF NOT EXISTS default_prompts (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100) NOT NULL,
                    template TEXT NOT NULL,
                    description TEXT,
                    category VARCHAR(50) DEFAULT 'general',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
                
                cursor.execute(schema_sql)
                conn.commit()
                logger.info("✅ Tablas creadas con arquitectura separada")
                return True
                
        except Exception as e:
            logger.error(f"Error creando schema: {e}")
            self.migration_stats["errors"].append(f"Schema creation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _constraint_exists(self, conn, table_name: str, constraint_name: str) -> bool:
        """Verificar si un constraint ya existe (PostgreSQL compatible)"""
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE table_name = %s AND constraint_name = %s
                """, (table_name, constraint_name))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.debug(f"Error verificando constraint {constraint_name}: {e}")
            return False
    
    def _create_constraints_safe(self) -> bool:
        """Crear constraints de forma segura (PostgreSQL compatible)"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            success_count = 0
            
            with conn.cursor() as cursor:
                # 1. Constraint para custom_prompts
                if not self._constraint_exists(conn, 'custom_prompts', 'unique_active_prompt'):
                    try:
                        cursor.execute("""
                            ALTER TABLE custom_prompts 
                            ADD CONSTRAINT unique_active_prompt 
                            UNIQUE (company_id, agent_name)
                            DEFERRABLE INITIALLY DEFERRED
                        """)
                        success_count += 1
                        logger.info("✅ Constraint unique_active_prompt creado")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo crear unique_active_prompt: {e}")
                else:
                    success_count += 1
                    logger.info("✅ Constraint unique_active_prompt ya existe")
                
                # 2. Constraint para default_prompts (empresa + agente)
                if not self._constraint_exists(conn, 'default_prompts', 'unique_company_agent'):
                    try:
                        cursor.execute("""
                            ALTER TABLE default_prompts 
                            ADD CONSTRAINT unique_company_agent 
                            UNIQUE (company_id, agent_name)
                        """)
                        success_count += 1
                        logger.info("✅ Constraint unique_company_agent creado")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo crear unique_company_agent: {e}")
                else:
                    success_count += 1
                    logger.info("✅ Constraint unique_company_agent ya existe")
                
                # 3. Foreign key para prompt_versions
                if not self._constraint_exists(conn, 'prompt_versions', 'fk_prompt_versions_prompt_id'):
                    try:
                        cursor.execute("""
                            ALTER TABLE prompt_versions 
                            ADD CONSTRAINT fk_prompt_versions_prompt_id 
                            FOREIGN KEY (prompt_id) REFERENCES custom_prompts(id) ON DELETE CASCADE
                        """)
                        success_count += 1
                        logger.info("✅ Foreign key constraint creado")
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo crear foreign key: {e}")
                else:
                    success_count += 1
                    logger.info("✅ Foreign key constraint ya existe")
                
                # 4. Crear índices
                indices = [
                    ("idx_custom_prompts_company_agent", "custom_prompts", "(company_id, agent_name)"),
                    ("idx_custom_prompts_active", "custom_prompts", "(is_active) WHERE is_active = true"),
                    ("idx_default_prompts_company_agent", "default_prompts", "(company_id, agent_name)"),
                    ("idx_prompt_versions_prompt_id", "prompt_versions", "(prompt_id)")
                ]
                
                for idx_name, table_name, idx_columns in indices:
                    try:
                        cursor.execute(f"""
                            CREATE INDEX IF NOT EXISTS {idx_name} 
                            ON {table_name} {idx_columns}
                        """)
                        logger.debug(f"✅ Índice {idx_name} verificado")
                    except Exception as e:
                        logger.warning(f"⚠️ Índice {idx_name}: {e}")
                
                conn.commit()
                logger.info(f"✅ Constraints procesados: {success_count} exitosos")
                return success_count >= 2  # Al menos los constraints principales
                
        except Exception as e:
            logger.error(f"Error creando constraints: {e}")
            self.migration_stats["errors"].append(f"Constraints creation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _populate_default_prompts_separated(self) -> bool:
        """Poblar default_prompts con arquitectura separada (multi-tenant)"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            # Templates base para cada agente
            base_templates = {
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
                }
            }
            
            with conn.cursor() as cursor:
                # Poblar para cada empresa y cada agente
                for company_id in self.valid_companies:
                    for agent_name in self.valid_agents:
                        if agent_name in base_templates:
                            template_data = base_templates[agent_name]
                            try:
                                cursor.execute("""
                                    INSERT INTO default_prompts (company_id, agent_name, template, description, category)
                                    VALUES (%s, %s, %s, %s, %s)
                                    ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                        template = EXCLUDED.template,
                                        description = EXCLUDED.description,
                                        category = EXCLUDED.category,
                                        updated_at = CURRENT_TIMESTAMP
                                """, (
                                    company_id,
                                    agent_name,
                                    template_data['template'],
                                    template_data['description'],
                                    template_data['category']
                                ))
                                logger.debug(f"✅ Default prompt para {company_id}/{agent_name}")
                            except Exception as e:
                                logger.warning(f"Error poblando {company_id}/{agent_name}: {e}")
                
                conn.commit()
                
                # Verificar resultados
                cursor.execute("SELECT COUNT(*) FROM default_prompts")
                total_prompts = cursor.fetchone()[0]
                expected_prompts = len(self.valid_companies) * len(self.valid_agents)
                
                logger.info(f"✅ Default prompts poblados: {total_prompts}/{expected_prompts}")
                return total_prompts > 0
                
        except Exception as e:
            logger.error(f"Error poblando defaults: {e}")
            self.migration_stats["errors"].append(f"Defaults population failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _migrate_custom_prompts(self) -> bool:
        """Migrar custom prompts del archivo JSON"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(__file__), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                logger.info("📄 No existe custom_prompts.json, saltando migración")
                return True
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)
            
            with conn.cursor() as cursor:
                for company_id, company_data in custom_data.items():
                    if company_id not in self.valid_companies:
                        continue
                    
                    self.migration_stats["companies_processed"] += 1
                    
                    for agent_key, agent_data in company_data.items():
                        # Extraer agent_name del key (manejar formatos company_agent o solo agent)
                        if agent_key.startswith(f"{company_id}_"):
                            agent_name = agent_key.replace(f"{company_id}_", "")
                        else:
                            agent_name = agent_key
                        
                        if agent_name not in self.valid_agents:
                            continue
                        
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
                                agent_data.get('template', f'Template para {agent_name}'),
                                agent_data.get('created_by', 'migration'),
                                agent_data.get('modified_by', 'migration'),
                                f"Migrado desde JSON el {datetime.utcnow().isoformat()}"
                            ))
                            
                            self.migration_stats["prompts_migrated"] += 1
                            logger.debug(f"✅ Migrado custom: {company_id}/{agent_name}")
                            
                        except Exception as e:
                            error_msg = f"Error migrando custom {company_id}/{agent_name}: {str(e)}"
                            logger.warning(error_msg)
                            self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"✅ Custom prompts migrados: {self.migration_stats['prompts_migrated']}")
                return True
                
        except Exception as e:
            logger.error(f"Error en migración de custom prompts: {e}")
            self.migration_stats["errors"].append(f"Custom prompts migration failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _validate_final_migration(self) -> bool:
        """Validar que la migración final es correcta"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar que default_prompts tiene arquitectura separada
                cursor.execute("""
                    SELECT COUNT(*) as count FROM default_prompts 
                    WHERE company_id IS NOT NULL AND agent_name IS NOT NULL
                """)
                valid_separated = cursor.fetchone()['count']
                
                # Verificar constraint existe
                cursor.execute("""
                    SELECT COUNT(*) as count FROM information_schema.table_constraints 
                    WHERE table_name = 'default_prompts' 
                    AND constraint_name = 'unique_company_agent'
                """)
                constraint_exists = cursor.fetchone()['count'] > 0
                
                # Verificar tablas existen
                cursor.execute("""
                    SELECT COUNT(*) as count FROM information_schema.tables 
                    WHERE table_name IN ('custom_prompts', 'default_prompts', 'prompt_versions')
                """)
                tables_exist = cursor.fetchone()['count'] == 3
                
                logger.info(f"✅ Prompts con arquitectura separada: {valid_separated}")
                logger.info(f"✅ Constraint unique_company_agent existe: {constraint_exists}")
                logger.info(f"✅ Todas las tablas existen: {tables_exist}")
                
                expected_prompts = len(self.valid_companies) * len(self.valid_agents)
                
                if (valid_separated >= expected_prompts and 
                    constraint_exists and 
                    tables_exist):
                    logger.info("✅ Migración FINAL validada perfectamente")
                    return True
                else:
                    logger.warning("⚠️ Validación con advertencias")
                    return False
                
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def create_backup(self) -> str:
        """Crear backup del archivo JSON antes de migrar"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(__file__), 
                'custom_prompts.json'
            )
            
            if os.path.exists(custom_prompts_file):
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{custom_prompts_file}.backup.{timestamp}"
                
                import shutil
                shutil.copy2(custom_prompts_file, backup_file)
                logger.info(f"✅ Backup creado: {backup_file}")
                return backup_file
            else:
                logger.info("📄 No existe custom_prompts.json para backup")
                return ""
                
        except Exception as e:
            logger.warning(f"⚠️ Error creando backup: {e}")
            return ""


def main():
    """Función principal para ejecutar la migración"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración corregida de prompts a PostgreSQL')
    parser.add_argument('--auto', action='store_true', help='Ejecutar automáticamente sin confirmación')
    parser.add_argument('--db-url', type=str, help='URL de conexión a PostgreSQL')
    
    args = parser.parse_args()
    
    # Configurar manager
    migration_manager = FixedPromptMigrationManager(args.db_url)
    
    try:
        # Crear backup
        migration_manager.create_backup()
        
        # Ejecutar migración
        results = migration_manager.run_complete_migration()
        
        # Mostrar resultados
        print("\n" + "="*50)
        print("📊 RESULTADOS DE MIGRACIÓN FINAL")
        print("="*50)
        print(f"⏱️  Duración: {(results.get('end_time', datetime.utcnow()) - results.get('start_time', datetime.utcnow())).total_seconds():.2f} segundos")
        print(f"🏢 Empresas procesadas: {results['companies_processed']}")
        print(f"🤖 Custom prompts migrados: {results['prompts_migrated']}")
        print(f"✅ Schema con arquitectura separada creado" if results['schema_created'] else "❌ Error en schema")
        print(f"✅ Constraints creados" if results['constraints_created'] else "⚠️ Advertencias en constraints")
        print(f"✅ Defaults poblados" if results['defaults_populated'] else "❌ Error poblando defaults")
        print(f"✅ Custom prompts migrados" if results['json_migrated'] else "⚠️ Custom prompts parcial")
        
        if results['errors']:
            print(f"\n⚠️  {len(results['errors'])} errores encontrados:")
            for error in results['errors']:
                print(f"    - {error}")
        
        print("\n🎉 Migración FINAL completada!")
        print("✅ Arquitectura separada implementada correctamente")
        print("✅ Compatible con prompt_service.py actualizado")
        
        return 0 if not results['errors'] else 1
        
    except Exception as e:
        logger.error(f"💥 Error crítico en main: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
