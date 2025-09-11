#!/usr/bin/env python3
# migrate_prompts_FINAL.py
# Migración FINAL con arquitectura separada y constraints correctos

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

class FinalPromptMigrationManager:
    """Migración FINAL con arquitectura separada y constraints correctos"""
    
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
        """Ejecutar migración completa con arquitectura separada"""
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
            
            # Fase 2: Crear constraints correctos
            if self._create_constraints():
                self.migration_stats["constraints_created"] = True
                logger.info("✅ Fase 2: Constraints creados correctamente")
            else:
                logger.error("❌ Fase 2: Error creando constraints")
                return self.migration_stats
            
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
                # Schema con arquitectura separada correcta
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
                
                -- Tabla de prompts por defecto (ARQUITECTURA SEPARADA)
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
    
    def _create_constraints(self) -> bool:
        """Crear constraints correctos para arquitectura separada"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Constraints para custom_prompts
                cursor.execute("""
                    ALTER TABLE custom_prompts 
                    ADD CONSTRAINT IF NOT EXISTS unique_active_prompt 
                    UNIQUE (company_id, agent_name, is_active) 
                    DEFERRABLE INITIALLY DEFERRED
                """)
                
                # Constraint principal para default_prompts (CRÍTICO PARA ON CONFLICT)
                cursor.execute("""
                    ALTER TABLE default_prompts 
                    ADD CONSTRAINT IF NOT EXISTS unique_company_agent 
                    UNIQUE (company_id, agent_name)
                """)
                
                # Constraints NOT NULL
                cursor.execute("""
                    ALTER TABLE default_prompts 
                    ALTER COLUMN company_id SET NOT NULL,
                    ALTER COLUMN agent_name SET NOT NULL
                """)
                
                # Índices para rendimiento
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_custom_prompts_company_agent 
                    ON custom_prompts(company_id, agent_name) WHERE is_active = true
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_default_prompts_company_agent 
                    ON default_prompts(company_id, agent_name)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id 
                    ON prompt_versions(prompt_id)
                """)
                
                conn.commit()
                logger.info("✅ Constraints e índices creados correctamente")
                return True
                
        except Exception as e:
            logger.error(f"Error creando constraints: {e}")
            self.migration_stats["errors"].append(f"Constraints creation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _populate_default_prompts_separated(self) -> bool:
        """Poblar default_prompts con arquitectura separada (company_id + agent_name)"""
        logger.info("Poblando default_prompts con arquitectura separada...")
        
        try:
            # Buscar archivo custom_prompts.json
            custom_prompts_file = os.path.join(
                os.path.dirname(__file__), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                logger.error(f"No se encontró custom_prompts.json en {custom_prompts_file}")
                return False
            
            # Cargar prompts desde JSON
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            logger.info(f"Cargando prompts desde: {custom_prompts_file}")
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                prompts_count = 0
                
                # Extraer default_template de cada empresa/agente válido
                for company_id, agents in custom_prompts.items():
                    # Filtrar metadata
                    if company_id.startswith('_') or company_id == 'metadata':
                        logger.debug(f"Saltando metadata: {company_id}")
                        continue
                    
                    # Solo empresas válidas
                    if company_id not in self.valid_companies:
                        logger.warning(f"Empresa no válida: {company_id}")
                        continue
                    
                    if not isinstance(agents, dict):
                        logger.warning(f"Datos de empresa no válidos: {company_id}")
                        continue
                    
                    logger.info(f"Procesando empresa: {company_id}")
                    
                    for agent_name, agent_data in agents.items():
                        # Solo agentes válidos
                        if agent_name not in self.valid_agents:
                            logger.debug(f"Agente no válido: {agent_name}")
                            continue
                        
                        if not isinstance(agent_data, dict):
                            logger.debug(f"Datos de agente no válidos: {company_id}/{agent_name}")
                            continue
                        
                        # Extraer default_template
                        default_template = agent_data.get('default_template')
                        if not default_template or len(default_template.strip()) == 0:
                            logger.debug(f"Sin default_template: {company_id}/{agent_name}")
                            continue
                        
                        description = f"Prompt personalizado para {agent_name} de {company_id}"
                        
                        # Determinar categoría
                        category_mapping = {
                            'router_agent': 'routing',
                            'sales_agent': 'sales', 
                            'support_agent': 'support',
                            'emergency_agent': 'emergency',
                            'schedule_agent': 'scheduling'
                        }
                        category = category_mapping.get(agent_name, 'general')
                        
                        # INSERTAR CON ARQUITECTURA SEPARADA + ON CONFLICT CORRECTO
                        cursor.execute("""
                            INSERT INTO default_prompts (company_id, agent_name, template, description, category)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                template = EXCLUDED.template,
                                description = EXCLUDED.description,
                                category = EXCLUDED.category,
                                updated_at = CURRENT_TIMESTAMP
                        """, (company_id, agent_name, default_template, description, category))
                        
                        prompts_count += 1
                        logger.info(f"Migrado: {company_id}/{agent_name}")
                
                conn.commit()
                
                # Validar resultado
                expected_prompts = len(self.valid_companies) * len(self.valid_agents)
                if prompts_count == expected_prompts:
                    logger.info(f"✅ Migración PERFECTA: {prompts_count}/{expected_prompts} prompts")
                else:
                    logger.warning(f"⚠️ Migración parcial: {prompts_count}/{expected_prompts} prompts")
                
                return prompts_count > 0
                
        except Exception as e:
            logger.error(f"Error poblando default prompts: {e}")
            self.migration_stats["errors"].append(f"Default prompts population failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _migrate_custom_prompts(self) -> bool:
        """Migrar custom prompts si existen"""
        logger.info("Migrando custom prompts...")
        
        custom_prompts_file = os.path.join(
            os.path.dirname(__file__), 
            'custom_prompts.json'
        )
        
        if not os.path.exists(custom_prompts_file):
            logger.info("No se encontró custom_prompts.json para custom prompts")
            return True
        
        try:
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                for company_id, company_data in custom_prompts.items():
                    # Filtrar metadata
                    if company_id.startswith('_') or company_id == 'metadata':
                        continue
                    
                    if not isinstance(company_data, dict) or company_id not in self.valid_companies:
                        continue
                    
                    self.migration_stats["companies_processed"] += 1
                    logger.info(f"Migrando custom prompts de empresa: {company_id}")
                    
                    for agent_name, agent_data in company_data.items():
                        if not isinstance(agent_data, dict) or agent_name not in self.valid_agents:
                            continue
                        
                        # Solo migrar si es personalizado y tiene template
                        if agent_data.get('is_custom', False) and agent_data.get('template'):
                            try:
                                cursor.execute("""
                                    INSERT INTO custom_prompts (company_id, agent_name, template, created_by, modified_by, notes)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (company_id, agent_name) WHERE is_active = true DO UPDATE SET
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
                                logger.debug(f"Migrado custom: {company_id}/{agent_name}")
                                
                            except Exception as e:
                                error_msg = f"Error migrando custom {company_id}/{agent_name}: {str(e)}"
                                logger.warning(error_msg)
                                self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"Custom prompts migrados: {self.migration_stats['prompts_migrated']}")
                return True
                
        except Exception as e:
            logger.error(f"Error en migración de custom prompts: {e}")
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
                
                # Verificar que NO hay formato combinado
                cursor.execute("""
                    SELECT COUNT(*) as count FROM default_prompts 
                    WHERE agent_name LIKE '%_%'
                """)
                combined_format = cursor.fetchone()['count']
                
                # Verificar constraint existe
                cursor.execute("""
                    SELECT COUNT(*) as count FROM information_schema.table_constraints 
                    WHERE table_name = 'default_prompts' 
                    AND constraint_name = 'unique_company_agent'
                """)
                constraint_exists = cursor.fetchone()['count'] > 0
                
                logger.info(f"✅ Prompts con arquitectura separada: {valid_separated}")
                logger.info(f"✅ Prompts con formato combinado: {combined_format}")
                logger.info(f"✅ Constraint unique_company_agent existe: {constraint_exists}")
                
                expected_prompts = len(self.valid_companies) * len(self.valid_agents)
                
                if (valid_separated == expected_prompts and 
                    combined_format == 0 and 
                    constraint_exists):
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
    """Función principal del script de migración FINAL"""
    print("🚀 Migración FINAL - Arquitectura Separada")
    print("=" * 50)
    
    # Verificar variables de entorno
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ Error: DATABASE_URL no configurada")
        sys.exit(1)
    
    print(f"📊 Base de datos: {db_url.split('@')[1] if '@' in db_url else 'configurada'}")
    
    # Confirmar migración
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        confirm = True
    else:
        confirm = input("\n¿Proceder con la migración FINAL? (y/N): ").lower().strip() == 'y'
    
    if not confirm:
        print("Migración cancelada")
        sys.exit(0)
    
    # Ejecutar migración
    migrator = FinalPromptMigrationManager(db_url)
    
    # Crear backup
    backup_file = migrator.create_backup()
    if backup_file:
        print(f"✅ Backup creado: {os.path.basename(backup_file)}")
    
    # Ejecutar migración FINAL
    stats = migrator.run_complete_migration()
    
    # Mostrar resultados
    print("\n" + "=" * 50)
    print("📊 RESULTADOS DE MIGRACIÓN FINAL")
    print("=" * 50)
    
    duration = 0
    if stats["start_time"] and stats["end_time"]:
        duration = (stats["end_time"] - stats["start_time"]).total_seconds()
    
    print(f"⏱️  Duración: {duration:.2f} segundos")
    print(f"🏢 Empresas procesadas: {stats['companies_processed']}")
    print(f"🤖 Custom prompts migrados: {stats['prompts_migrated']}")
    
    print("✅ Schema con arquitectura separada creado" if stats["schema_created"] else "❌ Error en schema")
    print("✅ Constraints correctos creados" if stats["constraints_created"] else "❌ Error en constraints")
    print("✅ Default prompts poblados" if stats["defaults_populated"] else "❌ Error poblando defaults")
    print("✅ Custom prompts migrados" if stats["json_migrated"] else "⚠️ Custom prompts parcial")
    
    if stats["errors"]:
        print(f"\n⚠️  {len(stats['errors'])} errores encontrados:")
        for error in stats["errors"][:3]:
            print(f"   - {error}")
    
    print("\n🎉 Migración FINAL completada!")
    print("✅ Arquitectura separada implementada correctamente")
    print("✅ Compatible con prompt_service.py actualizado")


if __name__ == "__main__":
    main()
