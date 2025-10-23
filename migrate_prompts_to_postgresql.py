#!/usr/bin/env python3
"""
migrate_prompts_refactored.py
Migración REFACTORIZADA para soporte de prompts estructurados con LangGraph
Convierte prompts legacy a formato estructurado con system, examples, placeholders, meta
"""

import os
import sys
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class StructuredPromptMigrationManager:
    """Migración para prompts estructurados con LangGraph"""
    
    def __init__(self, db_connection_string: str = None):
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.migration_stats = {
            "schema_created": False,
            "defaults_populated": False,
            "customs_migrated": False,
            "companies_processed": 0,
            "prompts_migrated": 0,
            "structured_prompts": 0,
            "simple_prompts": 0,
            "errors": [],
            "start_time": None,
            "end_time": None
        }
        
        self.valid_companies = ['benova', 'spa_wellness', 'medispa', 'dental_clinic']
        self.valid_agents = ['router_agent', 'sales_agent', 'support_agent', 
                            'emergency_agent', 'schedule_agent']
    
    def run_complete_migration(self) -> Dict[str, Any]:
        """Ejecutar migración completa con soporte estructurado"""
        logger.info("🚀 Iniciando migración con prompts estructurados")
        self.migration_stats["start_time"] = datetime.utcnow()
        
        try:
            # Fase 1: Crear schema
            if self._create_schema():
                self.migration_stats["schema_created"] = True
                logger.info("✅ Fase 1: Schema creado")
            else:
                logger.error("❌ Fase 1: Error creando schema")
                return self.migration_stats
            
            # Fase 2: Poblar default prompts desde JSON
            if self._populate_defaults_from_json():
                self.migration_stats["defaults_populated"] = True
                logger.info("✅ Fase 2: Default prompts poblados")
            else:
                logger.error("❌ Fase 2: Error poblando defaults")
                return self.migration_stats
            
            # Fase 3: Migrar custom prompts
            if self._migrate_custom_prompts():
                self.migration_stats["customs_migrated"] = True
                logger.info("✅ Fase 3: Custom prompts migrados")
            else:
                logger.warning("⚠️ Fase 3: Migración parcial de customs")
            
            # Validación
            self._validate_migration()
            
            self.migration_stats["end_time"] = datetime.utcnow()
            duration = (self.migration_stats["end_time"] - self.migration_stats["start_time"]).total_seconds()
            
            logger.info(f"🎉 Migración completada en {duration:.2f} segundos")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"💥 Error crítico: {e}")
            self.migration_stats["errors"].append(f"Critical error: {str(e)}")
            return self.migration_stats
    
    def _create_schema(self) -> bool:
        """Crear schema con soporte estructurado"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                schema_sql = """
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                
                -- Tabla custom_prompts con soporte estructurado
                CREATE TABLE IF NOT EXISTS custom_prompts (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100) NOT NULL,
                    format VARCHAR(20) DEFAULT 'simple' CHECK (format IN ('simple', 'structured')),
                    template TEXT NOT NULL,
                    structured_template JSONB,
                    is_active BOOLEAN DEFAULT true,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    modified_by VARCHAR(100) DEFAULT 'admin',
                    notes TEXT,
                    CONSTRAINT unique_active_prompt UNIQUE (company_id, agent_name)
                );
                
                -- Tabla prompt_versions con soporte estructurado
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id BIGSERIAL PRIMARY KEY,
                    prompt_id BIGINT,
                    company_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100) NOT NULL,
                    format VARCHAR(20) DEFAULT 'simple',
                    template TEXT NOT NULL,
                    structured_template JSONB,
                    version INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    notes TEXT
                );
                
                -- Tabla default_prompts con soporte estructurado
                CREATE TABLE IF NOT EXISTS default_prompts (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(100) NOT NULL,
                    agent_name VARCHAR(100) NOT NULL,
                    format VARCHAR(20) DEFAULT 'simple' CHECK (format IN ('simple', 'structured')),
                    template TEXT NOT NULL,
                    structured_template JSONB,
                    description TEXT,
                    category VARCHAR(50) DEFAULT 'general',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_default_prompt UNIQUE (company_id, agent_name)
                );
                
                -- Índices
                CREATE INDEX IF NOT EXISTS idx_custom_prompts_company ON custom_prompts(company_id);
                CREATE INDEX IF NOT EXISTS idx_custom_prompts_format ON custom_prompts(format);
                CREATE INDEX IF NOT EXISTS idx_default_prompts_company ON default_prompts(company_id);
                CREATE INDEX IF NOT EXISTS idx_default_prompts_format ON default_prompts(format);
                """
                
                cursor.execute(schema_sql)
                conn.commit()
                logger.info("✅ Schema con soporte estructurado creado")
                return True
                
        except Exception as e:
            logger.error(f"Error creando schema: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _convert_to_structured(
        self, 
        template: str, 
        company_id: str, 
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Convertir prompt legacy a formato estructurado
        
        Returns:
            Dict con: {system, examples, placeholders, meta}
        """
        # Extraer placeholders del template
        placeholders = {}
        if '{context}' in template:
            placeholders['context'] = {'type': 'string', 'description': 'Contexto relevante'}
        if '{chat_history}' in template:
            placeholders['chat_history'] = {'type': 'string', 'description': 'Historial de conversación'}
        if '{question}' in template:
            placeholders['question'] = {'type': 'string', 'description': 'Pregunta del usuario'}
        if '{emergency_protocols}' in template:
            placeholders['emergency_protocols'] = {'type': 'string', 'description': 'Protocolos de emergencia'}
        if '{schedule_context}' in template:
            placeholders['schedule_context'] = {'type': 'string', 'description': 'Contexto de agendamiento'}
        
        # Por ahora, examples vacío (se pueden agregar manualmente después)
        examples = []
        
        # Metadata
        meta = {
            'company_id': company_id,
            'agent_name': agent_name,
            'version': '1.0',
            'migrated_from': 'json',
            'migration_date': datetime.utcnow().isoformat()
        }
        
        return {
            'system': template,
            'examples': examples,
            'placeholders': placeholders,
            'meta': meta
        }
    
    def _populate_defaults_from_json(self) -> bool:
        """Poblar default_prompts desde custom_prompts.json"""
        try:
            json_file = os.path.join(os.path.dirname(__file__), 'custom_prompts.json')
            
            if not os.path.exists(json_file):
                logger.warning("📄 No custom_prompts.json encontrado")
                return False
            
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                for company_id, company_data in json_data.items():
                    if company_id.startswith('_') or company_id not in self.valid_companies:
                        continue
                    
                    for agent_name, agent_data in company_data.items():
                        if agent_name not in self.valid_agents:
                            continue
                        
                        # Obtener default_template
                        default_template = agent_data.get('default_template')
                        
                        if not default_template:
                            logger.warning(f"⚠️ No default_template for {company_id}/{agent_name}")
                            continue
                        
                        # Convertir a estructura
                        structured = self._convert_to_structured(
                            default_template, 
                            company_id, 
                            agent_name
                        )
                        
                        try:
                            cursor.execute("""
                                INSERT INTO default_prompts (
                                    company_id,
                                    agent_name,
                                    format,
                                    template,
                                    structured_template,
                                    description,
                                    category
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                    format = EXCLUDED.format,
                                    template = EXCLUDED.template,
                                    structured_template = EXCLUDED.structured_template,
                                    updated_at = CURRENT_TIMESTAMP
                            """, (
                                company_id,
                                agent_name,
                                'structured',  # Formato estructurado
                                default_template,  # Template legacy para compatibilidad
                                Json(structured),  # JSONB estructurado
                                f"Default prompt para {agent_name}",
                                'default'
                            ))
                            
                            self.migration_stats["prompts_migrated"] += 1
                            self.migration_stats["structured_prompts"] += 1
                            logger.info(f"✅ Default migrado: {company_id}/{agent_name} (structured)")
                            
                        except Exception as e:
                            error_msg = f"Error migrando default {company_id}/{agent_name}: {str(e)}"
                            logger.warning(error_msg)
                            self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"✅ Default prompts migrados: {self.migration_stats['prompts_migrated']}")
                return True
                
        except Exception as e:
            logger.error(f"Error poblando defaults: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _migrate_custom_prompts(self) -> bool:
        """Migrar custom prompts (los que tienen template != null)"""
        try:
            json_file = os.path.join(os.path.dirname(__file__), 'custom_prompts.json')
            
            if not os.path.exists(json_file):
                logger.info("📄 No custom_prompts.json para migrar customs")
                return True
            
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            conn = psycopg2.connect(self.db_connection_string)
            customs_count = 0
            
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
                            # Convertir a estructura
                            structured = self._convert_to_structured(
                                custom_template,
                                company_id,
                                agent_name
                            )
                            
                            try:
                                cursor.execute("""
                                    INSERT INTO custom_prompts (
                                        company_id,
                                        agent_name,
                                        format,
                                        template,
                                        structured_template,
                                        created_by,
                                        modified_by,
                                        notes
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                        format = EXCLUDED.format,
                                        template = EXCLUDED.template,
                                        structured_template = EXCLUDED.structured_template,
                                        modified_by = EXCLUDED.modified_by,
                                        modified_at = CURRENT_TIMESTAMP,
                                        notes = EXCLUDED.notes
                                """, (
                                    company_id,
                                    agent_name,
                                    'structured',
                                    custom_template,
                                    Json(structured),
                                    agent_data.get('modified_by', 'migration'),
                                    agent_data.get('modified_by', 'migration'),
                                    f"Custom prompt migrado desde JSON con estructura"
                                ))
                                
                                customs_count += 1
                                logger.info(f"✅ Custom migrado: {company_id}/{agent_name} (structured)")
                                
                            except Exception as e:
                                error_msg = f"Error migrando custom {company_id}/{agent_name}: {str(e)}"
                                logger.warning(error_msg)
                                self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"✅ Custom prompts migrados: {customs_count}")
                return True
                
        except Exception as e:
            logger.error(f"Error migrando custom prompts: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _validate_migration(self) -> bool:
        """Validar migración"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar prompts poblados
                cursor.execute("SELECT COUNT(*) as count, format FROM default_prompts GROUP BY format")
                defaults_by_format = cursor.fetchall()
                
                cursor.execute("SELECT COUNT(*) as count, format FROM custom_prompts GROUP BY format")
                customs_by_format = cursor.fetchall()
                
                # Verificar structured_template
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM default_prompts 
                    WHERE structured_template IS NOT NULL
                """)
                structured_count = cursor.fetchone()['count']
                
                # Verificar un prompt específico
                cursor.execute("""
                    SELECT 
                        company_id, 
                        agent_name, 
                        format,
                        LEFT(template, 50) as template_preview,
                        structured_template->'system' as system_preview
                    FROM default_prompts 
                    WHERE company_id = 'benova' AND agent_name = 'sales_agent'
                """)
                benova_sales = cursor.fetchone()
                
                logger.info(f"✅ Default prompts por formato: {defaults_by_format}")
                logger.info(f"✅ Custom prompts por formato: {customs_by_format}")
                logger.info(f"✅ Prompts con estructura: {structured_count}")
                
                if benova_sales:
                    logger.info(f"✅ Benova sales format: {benova_sales['format']}")
                    logger.info(f"✅ Template preview: {benova_sales['template_preview']}...")
                    if benova_sales.get('system_preview'):
                        preview = str(benova_sales['system_preview'])[:50]
                        logger.info(f"✅ System preview: {preview}...")
                    
                    # Verificar que sea el prompt específico de María
                    if 'María' in benova_sales['template_preview']:
                        logger.info("✅ Prompts específicos migrados correctamente")
                        return True
                    else:
                        logger.warning("⚠️ Los prompts no parecen ser los específicos del JSON")
                        return False
                
                return structured_count > 0
                
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def create_backup(self) -> str:
        """Crear backup del JSON"""
        try:
            json_file = os.path.join(os.path.dirname(__file__), 'custom_prompts.json')
            
            if os.path.exists(json_file):
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{json_file}.backup.{timestamp}"
                
                import shutil
                shutil.copy2(json_file, backup_file)
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
    
    parser = argparse.ArgumentParser(
        description='Migración refactorizada con prompts estructurados'
    )
    parser.add_argument('--auto', action='store_true', help='Ejecutar automáticamente')
    parser.add_argument('--db-url', type=str, help='URL de PostgreSQL')
    
    args = parser.parse_args()
    
    migration_manager = StructuredPromptMigrationManager(args.db_url)
    
    try:
        # Backup
        migration_manager.create_backup()
        
        # Migración
        results = migration_manager.run_complete_migration()
        
        # Resultados
        print("\n" + "="*60)
        print("📊 RESULTADOS DE MIGRACIÓN ESTRUCTURADA")
        print("="*60)
        duration = (results.get('end_time', datetime.utcnow()) - 
                   results.get('start_time', datetime.utcnow())).total_seconds()
        print(f"⏱️  Duración: {duration:.2f} segundos")
        print(f"🏢 Empresas procesadas: {results['companies_processed']}")
        print(f"🤖 Total prompts migrados: {results['prompts_migrated']}")
        print(f"📦 Prompts estructurados: {results['structured_prompts']}")
        print(f"📝 Prompts simples: {results['simple_prompts']}")
        print(f"✅ Schema: {'OK' if results['schema_created'] else 'ERROR'}")
        print(f"✅ Defaults: {'OK' if results['defaults_populated'] else 'ERROR'}")
        print(f"✅ Customs: {'OK' if results['customs_migrated'] else 'PARCIAL'}")
        
        if results['errors']:
            print(f"\n⚠️  {len(results['errors'])} errores:")
            for error in results['errors'][:5]:
                print(f"    - {error}")
        
        print("\n🎉 Migración estructurada completada!")
        print("✅ Prompts con formato: {system, examples, placeholders, meta}")
        
        return 0 if not results['errors'] else 1
        
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
