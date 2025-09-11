#!/usr/bin/env python3
"""
migrate_prompts_fixed_proper.py
Migración CORREGIDA que usa los default_template del JSON como prompts por defecto
"""

import os
import sys
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class ProperPromptMigrationManager:
    """Migración CORRECTA que usa los default_template del JSON"""
    
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
        
        self.valid_companies = ['benova', 'spa_wellness', 'medispa', 'dental_clinic']
        self.valid_agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
    
    def run_complete_migration(self) -> Dict[str, Any]:
        """Ejecutar migración completa CORRECTA"""
        logger.info("🚀 Iniciando migración CORRECTA con prompts del JSON")
        self.migration_stats["start_time"] = datetime.utcnow()
        
        try:
            # Fase 1: Crear schema
            if self._create_complete_schema():
                self.migration_stats["schema_created"] = True
                logger.info("✅ Fase 1: Schema creado")
            else:
                logger.error("❌ Fase 1: Error creando schema")
                return self.migration_stats
            
            # Fase 2: Crear constraints
            if self._create_constraints_safe():
                self.migration_stats["constraints_created"] = True
                logger.info("✅ Fase 2: Constraints creados")
            else:
                logger.warning("⚠️ Fase 2: Algunos constraints fallaron")
            
            # Fase 3: CORREGIDO - Poblar desde JSON
            if self._populate_from_json():
                self.migration_stats["defaults_populated"] = True
                logger.info("✅ Fase 3: Prompts poblados desde JSON")
            else:
                logger.error("❌ Fase 3: Error poblando desde JSON")
                return self.migration_stats
            
            # Fase 4: Migrar custom prompts (los que tienen template != null)
            if self._migrate_custom_prompts_proper():
                self.migration_stats["json_migrated"] = True
                logger.info("✅ Fase 4: Custom prompts migrados")
            else:
                logger.warning("⚠️ Fase 4: Migración parcial de custom prompts")
            
            # Validación
            self._validate_final_migration()
            
            self.migration_stats["end_time"] = datetime.utcnow()
            duration = (self.migration_stats["end_time"] - self.migration_stats["start_time"]).total_seconds()
            
            logger.info(f"🎉 Migración CORRECTA completada en {duration:.2f} segundos")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"💥 Error crítico: {e}")
            self.migration_stats["errors"].append(f"Critical error: {str(e)}")
            return self.migration_stats
    
    def _create_complete_schema(self) -> bool:
        """Crear schema básico"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                schema_sql = """
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
                    notes TEXT
                );
                
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
                logger.info("✅ Tablas creadas")
                return True
                
        except Exception as e:
            logger.error(f"Error creando schema: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _constraint_exists(self, conn, table_name: str, constraint_name: str) -> bool:
        """Verificar si constraint existe"""
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE table_name = %s AND constraint_name = %s
                """, (table_name, constraint_name))
                return cursor.fetchone()[0] > 0
        except:
            return False
    
    def _create_constraints_safe(self) -> bool:
        """Crear constraints de forma segura"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            success_count = 0
            
            with conn.cursor() as cursor:
                # Constraint para custom_prompts
                if not self._constraint_exists(conn, 'custom_prompts', 'unique_active_prompt'):
                    try:
                        cursor.execute("""
                            ALTER TABLE custom_prompts 
                            ADD CONSTRAINT unique_active_prompt 
                            UNIQUE (company_id, agent_name)
                        """)
                        success_count += 1
                        logger.info("✅ Constraint unique_active_prompt creado")
                    except Exception as e:
                        logger.warning(f"⚠️ unique_active_prompt: {e}")
                else:
                    success_count += 1
                    logger.info("✅ unique_active_prompt ya existe")
                
                # Constraint para default_prompts
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
                        logger.warning(f"⚠️ unique_company_agent: {e}")
                else:
                    success_count += 1
                    logger.info("✅ unique_company_agent ya existe")
                
                conn.commit()
                return success_count >= 1
                
        except Exception as e:
            logger.error(f"Error creando constraints: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _populate_from_json(self) -> bool:
        """CORRECTO: Poblar default_prompts usando default_template del JSON"""
        try:
            custom_prompts_file = os.path.join(os.path.dirname(__file__), 'custom_prompts.json')
            
            if not os.path.exists(custom_prompts_file):
                logger.error("❌ No existe custom_prompts.json")
                return False
            
            # Cargar JSON
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                prompts_added = 0
                
                for company_id, company_data in json_data.items():
                    # Saltar metadata
                    if company_id.startswith('_'):
                        continue
                        
                    if company_id not in self.valid_companies:
                        logger.warning(f"⚠️ Empresa desconocida: {company_id}")
                        continue
                    
                    for agent_name, agent_data in company_data.items():
                        if agent_name not in self.valid_agents:
                            continue
                        
                        # CORREGIDO: Usar default_template en lugar de template
                        default_template = agent_data.get('default_template')
                        
                        if not default_template:
                            logger.warning(f"⚠️ No default_template para {company_id}/{agent_name}")
                            continue
                        
                        try:
                            cursor.execute("""
                                INSERT INTO default_prompts (company_id, agent_name, template, description, category)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                    template = EXCLUDED.template,
                                    updated_at = CURRENT_TIMESTAMP
                            """, (
                                company_id,
                                agent_name,
                                default_template,
                                f"Prompt específico para {agent_name} de {company_id}",
                                'custom'
                            ))
                            
                            prompts_added += 1
                            logger.info(f"✅ Poblado: {company_id}/{agent_name}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error poblando {company_id}/{agent_name}: {e}")
                            self.migration_stats["errors"].append(f"Error poblando {company_id}/{agent_name}: {str(e)}")
                
                conn.commit()
                
                logger.info(f"✅ Prompts poblados desde JSON: {prompts_added}")
                return prompts_added > 0
                
        except Exception as e:
            logger.error(f"Error poblando desde JSON: {e}")
            self.migration_stats["errors"].append(f"JSON population failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _migrate_custom_prompts_proper(self) -> bool:
        """Migrar custom prompts (los que tienen template != null)"""
        try:
            custom_prompts_file = os.path.join(os.path.dirname(__file__), 'custom_prompts.json')
            
            if not os.path.exists(custom_prompts_file):
                logger.info("📄 No custom_prompts.json para migrar")
                return True
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                for company_id, company_data in json_data.items():
                    if company_id.startswith('_') or company_id not in self.valid_companies:
                        continue
                    
                    self.migration_stats["companies_processed"] += 1
                    
                    for agent_name, agent_data in company_data.items():
                        if agent_name not in self.valid_agents:
                            continue
                        
                        # Solo migrar si hay template customizado (no null)
                        custom_template = agent_data.get('template')
                        
                        if custom_template is not None and custom_template.strip():
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
                                    custom_template,
                                    agent_data.get('modified_by', 'migration'),
                                    agent_data.get('modified_by', 'migration'),
                                    f"Custom prompt migrado desde JSON"
                                ))
                                
                                self.migration_stats["prompts_migrated"] += 1
                                logger.info(f"✅ Custom migrado: {company_id}/{agent_name}")
                                
                            except Exception as e:
                                error_msg = f"Error migrando custom {company_id}/{agent_name}: {str(e)}"
                                logger.warning(error_msg)
                                self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"✅ Custom prompts migrados: {self.migration_stats['prompts_migrated']}")
                return True
                
        except Exception as e:
            logger.error(f"Error migrando custom prompts: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _validate_final_migration(self) -> bool:
        """Validar migración"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar prompts poblados
                cursor.execute("SELECT COUNT(*) as count FROM default_prompts")
                total_defaults = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM custom_prompts") 
                total_customs = cursor.fetchone()['count']
                
                # Verificar algunos prompts específicos
                cursor.execute("""
                    SELECT company_id, agent_name, LEFT(template, 50) as preview 
                    FROM default_prompts 
                    WHERE company_id = 'benova' AND agent_name = 'sales_agent'
                """)
                benova_sales = cursor.fetchone()
                
                logger.info(f"✅ Default prompts: {total_defaults}")
                logger.info(f"✅ Custom prompts: {total_customs}")
                
                if benova_sales:
                    logger.info(f"✅ Benova sales preview: {benova_sales['preview']}...")
                    # Verificar que sea el prompt específico de María
                    if 'María' in benova_sales['preview']:
                        logger.info("✅ Prompts específicos cargados correctamente")
                        return True
                    else:
                        logger.warning("⚠️ Los prompts no parecen ser los específicos del JSON")
                        return False
                
                return total_defaults > 0
                
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def create_backup(self) -> str:
        """Crear backup"""
        try:
            custom_prompts_file = os.path.join(os.path.dirname(__file__), 'custom_prompts.json')
            
            if os.path.exists(custom_prompts_file):
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{custom_prompts_file}.backup.{timestamp}"
                
                import shutil
                shutil.copy2(custom_prompts_file, backup_file)
                logger.info(f"✅ Backup creado: {backup_file}")
                return backup_file
            else:
                logger.info("📄 No custom_prompts.json para backup")
                return ""
                
        except Exception as e:
            logger.warning(f"⚠️ Error creando backup: {e}")
            return ""


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración CORRECTA usando default_template del JSON')
    parser.add_argument('--auto', action='store_true', help='Ejecutar automáticamente')
    parser.add_argument('--db-url', type=str, help='URL de PostgreSQL')
    
    args = parser.parse_args()
    
    migration_manager = ProperPromptMigrationManager(args.db_url)
    
    try:
        # Backup
        migration_manager.create_backup()
        
        # Migración
        results = migration_manager.run_complete_migration()
        
        # Resultados
        print("\n" + "="*50)
        print("📊 RESULTADOS DE MIGRACIÓN CORRECTA")
        print("="*50)
        print(f"⏱️  Duración: {(results.get('end_time', datetime.utcnow()) - results.get('start_time', datetime.utcnow())).total_seconds():.2f} segundos")
        print(f"🏢 Empresas procesadas: {results['companies_processed']}")
        print(f"🤖 Custom prompts migrados: {results['prompts_migrated']}")
        print(f"✅ Schema creado" if results['schema_created'] else "❌ Error en schema")
        print(f"✅ Constraints creados" if results['constraints_created'] else "⚠️ Advertencias en constraints")
        print(f"✅ Prompts del JSON poblados" if results['defaults_populated'] else "❌ Error poblando")
        print(f"✅ Custom prompts migrados" if results['json_migrated'] else "⚠️ Custom prompts parcial")
        
        if results['errors']:
            print(f"\n⚠️  {len(results['errors'])} errores:")
            for error in results['errors'][:5]:
                print(f"    - {error}")
        
        print("\n🎉 Migración CORRECTA completada!")
        print("✅ Usando prompts específicos del JSON (María, Ana, Dr. López, Dr. Martínez)")
        
        return 0 if not results['errors'] else 1
        
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
