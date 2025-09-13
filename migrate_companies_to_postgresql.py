# migrate_companies_to_postgresql.py
#!/usr/bin/env python3
"""
migrate_companies_to_postgresql.py
Migración ESPECÍFICA para configuración de empresas a PostgreSQL
Enfoque exclusivo en tablas: companies, company_config_versions, company_templates, company_runtime_settings
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

class CompanyConfigMigrationManager:
    """Migración específica para configuración de empresas a PostgreSQL"""
    
    def __init__(self, db_connection_string: str = None):
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.migration_stats = {
            "schema_created": False,
            "constraints_created": False,
            "templates_populated": False,
            "companies_migrated": False,
            "companies_processed": 0,
            "templates_created": 0,
            "errors": [],
            "start_time": None,
            "end_time": None
        }
        
        # Empresas válidas del sistema
        self.valid_companies = ['benova', 'spa_wellness', 'medispa', 'dental_clinic']
        
        # Templates de configuración predefinidas
        self.default_templates = {
            'medical_clinic': {
                'business_type': 'healthcare',
                'display_name': 'Clínica Médica',
                'description': 'Plantilla para clínicas médicas generales',
                'default_config': {
                    "business_type": "healthcare",
                    "timezone": "America/Bogota",
                    "language": "es",
                    "currency": "COP",
                    "treatment_durations": {"consulta_general": 30, "procedimiento_basico": 60},
                    "emergency_keywords": ["dolor", "sangrado", "emergencia"],
                    "schedule_keywords": ["agendar", "cita", "reservar"]
                },
                'required_fields': ['company_name', 'services', 'sales_agent_name']
            },
            'dental_clinic': {
                'business_type': 'healthcare',
                'display_name': 'Clínica Dental',
                'description': 'Plantilla para clínicas dentales',
                'default_config': {
                    "business_type": "healthcare",
                    "timezone": "America/Bogota",
                    "language": "es",
                    "currency": "COP",
                    "treatment_durations": {"consulta_dental": 45, "implante": 120, "limpieza": 60},
                    "emergency_keywords": ["dolor_dental", "sangrado_encia", "emergencia_dental"],
                    "schedule_keywords": ["agendar", "cita", "reservar"]
                },
                'required_fields': ['company_name', 'services', 'sales_agent_name']
            },
            'beauty_spa': {
                'business_type': 'beauty',
                'display_name': 'Spa de Belleza',
                'description': 'Plantilla para spas y centros de belleza',
                'default_config': {
                    "business_type": "beauty",
                    "timezone": "America/Bogota",
                    "language": "es",
                    "currency": "COP",
                    "treatment_durations": {"facial": 90, "masaje": 60, "tratamiento_corporal": 120},
                    "sales_keywords": ["precio", "promocion", "tratamiento"],
                    "schedule_keywords": ["agendar", "reservar", "programar"]
                },
                'required_fields': ['company_name', 'services', 'sales_agent_name']
            }
        }
    
    def run_complete_migration(self) -> Dict[str, Any]:
        """Ejecutar migración completa para configuración de empresas"""
        logger.info("🚀 Iniciando migración de configuración de empresas a PostgreSQL")
        self.migration_stats["start_time"] = datetime.utcnow()
        
        try:
            # Fase 1: Crear schema de empresas
            if self._create_company_schema():
                self.migration_stats["schema_created"] = True
                logger.info("✅ Fase 1: Schema de empresas creado")
            else:
                logger.error("❌ Fase 1: Error creando schema de empresas")
                return self.migration_stats
            
            # Fase 2: Crear constraints
            if self._create_constraints_safe():
                self.migration_stats["constraints_created"] = True
                logger.info("✅ Fase 2: Constraints creados")
            else:
                logger.warning("⚠️ Fase 2: Algunos constraints fallaron")
            
            # Fase 3: Poblar templates predefinidas
            if self._populate_company_templates():
                self.migration_stats["templates_populated"] = True
                logger.info("✅ Fase 3: Templates de empresas pobladas")
            else:
                logger.error("❌ Fase 3: Error poblando templates")
                return self.migration_stats
            
            # Fase 4: Migrar configuraciones desde JSON
            if self._migrate_companies_from_json():
                self.migration_stats["companies_migrated"] = True
                logger.info("✅ Fase 4: Configuraciones de empresas migradas")
            else:
                logger.warning("⚠️ Fase 4: Migración parcial de empresas")
            
            # Validación final
            self._validate_company_migration()
            
            self.migration_stats["end_time"] = datetime.utcnow()
            duration = (self.migration_stats["end_time"] - self.migration_stats["start_time"]).total_seconds()
            
            logger.info(f"🎉 Migración de configuración de empresas completada en {duration:.2f} segundos")
            return self.migration_stats
            
        except Exception as e:
            logger.error(f"💥 Error crítico en migración de empresas: {e}")
            self.migration_stats["errors"].append(f"Critical error: {str(e)}")
            return self.migration_stats
    
    def _create_company_schema(self) -> bool:
        """Crear schema específico para tablas de configuración de empresas"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Schema específico para configuración de empresas
                company_schema_sql = """
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                
                -- TABLA PRINCIPAL DE CONFIGURACIÓN DE EMPRESAS
                CREATE TABLE IF NOT EXISTS companies (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(100) UNIQUE NOT NULL,
                    company_name VARCHAR(200) NOT NULL,
                    business_type VARCHAR(100) DEFAULT 'general',
                    services TEXT NOT NULL,
                    
                    -- Configuración Redis/Vector Store
                    redis_prefix VARCHAR(150) NOT NULL,
                    vectorstore_index VARCHAR(150) NOT NULL,
                    
                    -- Configuración de Agentes
                    sales_agent_name VARCHAR(200) NOT NULL,
                    model_name VARCHAR(100) DEFAULT 'gpt-4o-mini',
                    max_tokens INTEGER DEFAULT 1500,
                    temperature DECIMAL(3,2) DEFAULT 0.7,
                    max_context_messages INTEGER DEFAULT 10,
                    
                    -- Configuración de Servicios Externos
                    schedule_service_url VARCHAR(300),
                    schedule_integration_type VARCHAR(50) DEFAULT 'basic',
                    chatwoot_account_id VARCHAR(50),
                    
                    -- Configuración de Negocio
                    treatment_durations JSONB,
                    schedule_keywords TEXT[],
                    emergency_keywords TEXT[],
                    sales_keywords TEXT[],
                    required_booking_fields TEXT[],
                    
                    -- Configuración de Localización
                    timezone VARCHAR(50) DEFAULT 'America/Bogota',
                    language VARCHAR(10) DEFAULT 'es',
                    currency VARCHAR(10) DEFAULT 'COP',
                    
                    -- Estado y Metadatos
                    is_active BOOLEAN DEFAULT true,
                    subscription_tier VARCHAR(50) DEFAULT 'basic',
                    max_documents INTEGER DEFAULT 1000,
                    max_conversations INTEGER DEFAULT 10000,
                    
                    -- Auditoría
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    modified_by VARCHAR(100) DEFAULT 'admin',
                    version INTEGER DEFAULT 1,
                    notes TEXT
                );
                
                -- TABLA DE HISTORIAL DE CONFIGURACIÓN DE EMPRESAS
                CREATE TABLE IF NOT EXISTS company_config_versions (
                    id BIGSERIAL PRIMARY KEY,
                    company_pk BIGINT REFERENCES companies(id) ON DELETE CASCADE,
                    company_id VARCHAR(100) NOT NULL,
                    version INTEGER NOT NULL,
                    action VARCHAR(50) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'ACTIVATE', 'DEACTIVATE')),
                    
                    -- Snapshot completo de la configuración
                    config_snapshot JSONB NOT NULL,
                    changes_summary TEXT,
                    
                    -- Campos específicos que cambiaron
                    changed_fields TEXT[],
                    previous_values JSONB,
                    new_values JSONB,
                    
                    -- Auditoría
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    notes TEXT,
                    
                    -- Metadatos de cambio
                    change_reason VARCHAR(200),
                    change_source VARCHAR(100) DEFAULT 'admin_panel',
                    ip_address INET,
                    user_agent TEXT
                );
                
                -- TABLA DE PLANTILLAS DE CONFIGURACIÓN
                CREATE TABLE IF NOT EXISTS company_templates (
                    id BIGSERIAL PRIMARY KEY,
                    template_name VARCHAR(100) UNIQUE NOT NULL,
                    business_type VARCHAR(100) NOT NULL,
                    display_name VARCHAR(200) NOT NULL,
                    description TEXT,
                    
                    -- Configuración por defecto
                    default_config JSONB NOT NULL,
                    required_fields TEXT[] NOT NULL,
                    optional_fields TEXT[],
                    
                    -- Metadatos
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin'
                );
                
                -- TABLA DE CONFIGURACIÓN DINÁMICA
                CREATE TABLE IF NOT EXISTS company_runtime_settings (
                    id BIGSERIAL PRIMARY KEY,
                    company_id VARCHAR(100) REFERENCES companies(company_id) ON DELETE CASCADE,
                    setting_key VARCHAR(100) NOT NULL,
                    setting_value TEXT,
                    setting_type VARCHAR(50) DEFAULT 'string',
                    setting_category VARCHAR(100) DEFAULT 'general',
                    
                    -- Metadatos
                    is_encrypted BOOLEAN DEFAULT false,
                    last_accessed TIMESTAMP WITH TIME ZONE,
                    access_count INTEGER DEFAULT 0,
                    
                    -- Auditoría
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100) DEFAULT 'admin',
                    modified_by VARCHAR(100) DEFAULT 'admin',
                    
                    UNIQUE(company_id, setting_key)
                );
                """
                
                cursor.execute(company_schema_sql)
                conn.commit()
                logger.info("✅ Tablas de configuración de empresas creadas")
                return True
                
        except Exception as e:
            logger.error(f"Error creando schema de empresas: {e}")
            self.migration_stats["errors"].append(f"Company schema creation failed: {str(e)}")
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
        """Crear constraints específicos para tablas de empresas"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            success_count = 0
            
            with conn.cursor() as cursor:
                # Índices para performance
                indices_sql = """
                -- ÍNDICES PARA CONFIGURACIÓN DE EMPRESAS
                CREATE INDEX IF NOT EXISTS idx_companies_company_id ON companies(company_id);
                CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);
                CREATE INDEX IF NOT EXISTS idx_companies_business_type ON companies(business_type);
                CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies(created_at);
                
                CREATE INDEX IF NOT EXISTS idx_config_versions_company_id ON company_config_versions(company_id);
                CREATE INDEX IF NOT EXISTS idx_config_versions_version ON company_config_versions(version);
                CREATE INDEX IF NOT EXISTS idx_config_versions_action ON company_config_versions(action);
                CREATE INDEX IF NOT EXISTS idx_config_versions_created_at ON company_config_versions(created_at);
                
                CREATE INDEX IF NOT EXISTS idx_runtime_settings_company_id ON company_runtime_settings(company_id);
                CREATE INDEX IF NOT EXISTS idx_runtime_settings_key ON company_runtime_settings(setting_key);
                CREATE INDEX IF NOT EXISTS idx_runtime_settings_category ON company_runtime_settings(setting_category);
                """
                
                cursor.execute(indices_sql)
                success_count += 1
                logger.info("✅ Índices de empresas creados")
                
                # Función para trigger de versionado
                trigger_function_sql = """
                CREATE OR REPLACE FUNCTION create_company_config_version()
                RETURNS TRIGGER AS $$
                DECLARE
                    next_version INTEGER;
                    config_json JSONB;
                    changed_fields_array TEXT[];
                    previous_vals JSONB;
                    new_vals JSONB;
                BEGIN
                    -- Obtener siguiente versión
                    SELECT COALESCE(MAX(version), 0) + 1 
                    INTO next_version 
                    FROM company_config_versions 
                    WHERE company_id = COALESCE(NEW.company_id, OLD.company_id);
                    
                    -- Preparar datos según operación
                    IF TG_OP = 'DELETE' THEN
                        config_json := to_jsonb(OLD);
                        
                        INSERT INTO company_config_versions (
                            company_pk, company_id, version, action, config_snapshot,
                            changes_summary, created_by, notes
                        ) VALUES (
                            OLD.id, OLD.company_id, next_version, 'DELETE', config_json,
                            'Company configuration deleted', OLD.modified_by, 'Company deleted'
                        );
                        
                        RETURN OLD;
                        
                    ELSIF TG_OP = 'INSERT' THEN
                        config_json := to_jsonb(NEW);
                        
                        INSERT INTO company_config_versions (
                            company_pk, company_id, version, action, config_snapshot,
                            changes_summary, created_by, notes
                        ) VALUES (
                            NEW.id, NEW.company_id, next_version, 'CREATE', config_json,
                            'Initial company configuration created', NEW.created_by, 'Company created'
                        );
                        
                        RETURN NEW;
                        
                    ELSIF TG_OP = 'UPDATE' THEN
                        -- Detectar campos que cambiaron
                        changed_fields_array := ARRAY[]::TEXT[];
                        previous_vals := '{}'::JSONB;
                        new_vals := '{}'::JSONB;
                        
                        -- Comparar campos principales
                        IF OLD.company_name != NEW.company_name THEN
                            changed_fields_array := array_append(changed_fields_array, 'company_name');
                            previous_vals := previous_vals || jsonb_build_object('company_name', OLD.company_name);
                            new_vals := new_vals || jsonb_build_object('company_name', NEW.company_name);
                        END IF;
                        
                        IF OLD.services != NEW.services THEN
                            changed_fields_array := array_append(changed_fields_array, 'services');
                            previous_vals := previous_vals || jsonb_build_object('services', OLD.services);
                            new_vals := new_vals || jsonb_build_object('services', NEW.services);
                        END IF;
                        
                        IF OLD.sales_agent_name != NEW.sales_agent_name THEN
                            changed_fields_array := array_append(changed_fields_array, 'sales_agent_name');
                            previous_vals := previous_vals || jsonb_build_object('sales_agent_name', OLD.sales_agent_name);
                            new_vals := new_vals || jsonb_build_object('sales_agent_name', NEW.sales_agent_name);
                        END IF;
                        
                        -- Solo crear versión si hay cambios reales
                        IF array_length(changed_fields_array, 1) > 0 THEN
                            config_json := to_jsonb(NEW);
                            
                            INSERT INTO company_config_versions (
                                company_pk, company_id, version, action, config_snapshot,
                                changed_fields, previous_values, new_values,
                                changes_summary, created_by, notes
                            ) VALUES (
                                NEW.id, NEW.company_id, next_version, 'UPDATE', config_json,
                                changed_fields_array, previous_vals, new_vals,
                                'Configuration updated: ' || array_to_string(changed_fields_array, ', '),
                                NEW.modified_by, 'Configuration modified'
                            );
                        END IF;
                        
                        RETURN NEW;
                    END IF;
                    
                    RETURN NULL;
                END;
                $$ LANGUAGE plpgsql;
                """
                
                cursor.execute(trigger_function_sql)
                success_count += 1
                logger.info("✅ Función de trigger para versionado creada")
                
                # Crear trigger
                trigger_sql = """
                DROP TRIGGER IF EXISTS trigger_company_config_versioning ON companies;
                CREATE TRIGGER trigger_company_config_versioning
                    AFTER INSERT OR UPDATE OR DELETE ON companies
                    FOR EACH ROW
                    EXECUTE FUNCTION create_company_config_version();
                """
                
                cursor.execute(trigger_sql)
                success_count += 1
                logger.info("✅ Trigger de versionado creado")
                
                conn.commit()
                return success_count >= 2
                
        except Exception as e:
            logger.error(f"Error creando constraints de empresas: {e}")
            self.migration_stats["errors"].append(f"Company constraints creation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _populate_company_templates(self) -> bool:
        """Poblar templates predefinidas de configuración"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                templates_added = 0
                
                for template_name, template_data in self.default_templates.items():
                    try:
                        cursor.execute("""
                            INSERT INTO company_templates 
                            (template_name, business_type, display_name, description, default_config, required_fields, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (template_name) DO UPDATE SET
                                business_type = EXCLUDED.business_type,
                                display_name = EXCLUDED.display_name,
                                description = EXCLUDED.description,
                                default_config = EXCLUDED.default_config,
                                required_fields = EXCLUDED.required_fields,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            template_name,
                            template_data['business_type'],
                            template_data['display_name'],
                            template_data['description'],
                            json.dumps(template_data['default_config']),
                            template_data['required_fields'],
                            'migration'
                        ))
                        
                        templates_added += 1
                        logger.info(f"✅ Template poblada: {template_name}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error poblando template {template_name}: {e}")
                        self.migration_stats["errors"].append(f"Error poblando template {template_name}: {str(e)}")
                
                conn.commit()
                
                self.migration_stats["templates_created"] = templates_added
                logger.info(f"✅ Templates pobladas: {templates_added}")
                return templates_added > 0
                
        except Exception as e:
            logger.error(f"Error poblando templates: {e}")
            self.migration_stats["errors"].append(f"Templates population failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _migrate_companies_from_json(self) -> bool:
        """Migrar configuraciones de empresas desde JSON"""
        try:
            companies_config_file = os.path.join(os.path.dirname(__file__), 'companies_config.json')
            
            if not os.path.exists(companies_config_file):
                logger.error("❌ No existe companies_config.json")
                return False
            
            # Cargar JSON
            with open(companies_config_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                for company_id, company_data in json_data.items():
                    if company_id not in self.valid_companies:
                        logger.warning(f"⚠️ Empresa no válida: {company_id}")
                        continue
                    
                    self.migration_stats["companies_processed"] += 1
                    
                    try:
                        # Preparar datos de empresa
                        company_name = company_data.get('company_name', company_id.title())
                        services = company_data.get('services', 'servicios generales')
                        redis_prefix = company_data.get('redis_prefix', f"{company_id}:")
                        vectorstore_index = company_data.get('vectorstore_index', f"{company_id}_documents")
                        sales_agent_name = company_data.get('sales_agent_name', f"Asistente de {company_name}")
                        
                        # Configuración técnica
                        model_name = company_data.get('model_name', 'gpt-4o-mini')
                        max_tokens = company_data.get('max_tokens', 1500)
                        temperature = company_data.get('temperature', 0.7)
                        schedule_service_url = company_data.get('schedule_service_url', 'http://127.0.0.1:4040')
                        
                        # Configuración de negocio
                        treatment_durations = company_data.get('treatment_durations')
                        schedule_keywords = company_data.get('schedule_keywords', [])
                        emergency_keywords = company_data.get('emergency_keywords', [])
                        sales_keywords = company_data.get('sales_keywords', [])
                        
                        cursor.execute("""
                            INSERT INTO companies (
                                company_id, company_name, services, redis_prefix, vectorstore_index,
                                sales_agent_name, model_name, max_tokens, temperature, schedule_service_url,
                                treatment_durations, schedule_keywords, emergency_keywords, sales_keywords,
                                created_by, modified_by, notes
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (company_id) DO UPDATE SET
                                company_name = EXCLUDED.company_name,
                                services = EXCLUDED.services,
                                sales_agent_name = EXCLUDED.sales_agent_name,
                                model_name = EXCLUDED.model_name,
                                max_tokens = EXCLUDED.max_tokens,
                                temperature = EXCLUDED.temperature,
                                schedule_service_url = EXCLUDED.schedule_service_url,
                                treatment_durations = EXCLUDED.treatment_durations,
                                schedule_keywords = EXCLUDED.schedule_keywords,
                                emergency_keywords = EXCLUDED.emergency_keywords,
                                sales_keywords = EXCLUDED.sales_keywords,
                                modified_by = EXCLUDED.modified_by,
                                modified_at = CURRENT_TIMESTAMP,
                                notes = EXCLUDED.notes
                        """, (
                            company_id, company_name, services, redis_prefix, vectorstore_index,
                            sales_agent_name, model_name, max_tokens, temperature, schedule_service_url,
                            json.dumps(treatment_durations) if treatment_durations else None,
                            schedule_keywords, emergency_keywords, sales_keywords,
                            'json_migration', 'json_migration', f'Migrated from companies_config.json'
                        ))
                        
                        logger.info(f"✅ Empresa migrada: {company_id}")
                        
                    except Exception as e:
                        error_msg = f"Error migrando empresa {company_id}: {str(e)}"
                        logger.error(f"❌ {error_msg}")
                        self.migration_stats["errors"].append(error_msg)
                
                conn.commit()
                logger.info(f"✅ Empresas procesadas: {self.migration_stats['companies_processed']}")
                return self.migration_stats['companies_processed'] > 0
                
        except Exception as e:
            logger.error(f"Error migrando empresas desde JSON: {e}")
            self.migration_stats["errors"].append(f"JSON migration failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _validate_company_migration(self) -> bool:
        """Validar migración de configuración de empresas"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar empresas creadas
                cursor.execute("SELECT COUNT(*) as count FROM companies")
                total_companies = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM companies WHERE is_active = true")
                active_companies = cursor.fetchone()['count']
                
                # Verificar templates
                cursor.execute("SELECT COUNT(*) as count FROM company_templates")
                total_templates = cursor.fetchone()['count']
                
                # Verificar algunas empresas específicas
                cursor.execute("""
                    SELECT company_id, company_name, sales_agent_name 
                    FROM companies 
                    WHERE company_id IN ('benova', 'spa_wellness', 'medispa', 'dental_clinic')
                    ORDER BY company_id
                """)
                sample_companies = cursor.fetchall()
                
                logger.info(f"✅ Total empresas: {total_companies}")
                logger.info(f"✅ Empresas activas: {active_companies}")
                logger.info(f"✅ Templates disponibles: {total_templates}")
                
                if sample_companies:
                    logger.info("✅ Empresas migradas exitosamente:")
                    for company in sample_companies:
                        logger.info(f"    - {company['company_id']}: {company['company_name']} ({company['sales_agent_name']})")
                    return True
                else:
                    logger.warning("⚠️ No se encontraron empresas en la migración")
                    return False
                
        except Exception as e:
            logger.error(f"Error en validación de empresas: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def create_backup(self) -> str:
        """Crear backup del archivo de configuración original"""
        try:
            companies_config_file = os.path.join(os.path.dirname(__file__), 'companies_config.json')
            
            if os.path.exists(companies_config_file):
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{companies_config_file}.backup.{timestamp}"
                
                import shutil
                shutil.copy2(companies_config_file, backup_file)
                logger.info(f"✅ Backup de empresas creado: {backup_file}")
                return backup_file
            else:
                logger.info("📄 No companies_config.json para backup")
                return ""
                
        except Exception as e:
            logger.warning(f"⚠️ Error creando backup de empresas: {e}")
            return ""


def main():
    """Función principal para migración de configuración de empresas"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración de configuración de empresas a PostgreSQL')
    parser.add_argument('--auto', action='store_true', help='Ejecutar automáticamente')
    parser.add_argument('--db-url', type=str, help='URL de PostgreSQL')
    
    args = parser.parse_args()
    
    migration_manager = CompanyConfigMigrationManager(args.db_url)
    
    try:
        # Backup
        migration_manager.create_backup()
        
        # Migración
        results = migration_manager.run_complete_migration()
        
        # Resultados
        print("\n" + "="*60)
        print("📊 RESULTADOS DE MIGRACIÓN DE CONFIGURACIÓN DE EMPRESAS")
        print("="*60)
        print(f"⏱️  Duración: {(results.get('end_time', datetime.utcnow()) - results.get('start_time', datetime.utcnow())).total_seconds():.2f} segundos")
        print(f"🏢 Empresas procesadas: {results['companies_processed']}")
        print(f"📋 Templates creadas: {results['templates_created']}")
        print(f"✅ Schema creado" if results['schema_created'] else "❌ Error en schema")
        print(f"✅ Constraints creados" if results['constraints_created'] else "⚠️ Advertencias en constraints")
        print(f"✅ Templates pobladas" if results['templates_populated'] else "❌ Error poblando templates")
        print(f"✅ Empresas migradas" if results['companies_migrated'] else "⚠️ Empresas migradas parcialmente")
        
        if results['errors']:
            print(f"\n⚠️  {len(results['errors'])} errores:")
            for error in results['errors'][:5]:
                print(f"    - {error}")
        
        print("\n🎉 Migración de configuración de empresas completada!")
        print("✅ Tablas: companies, company_config_versions, company_templates, company_runtime_settings")
        print("✅ Source of truth: PostgreSQL con fallback a JSON")
        
        return 0 if not results['errors'] else 1
        
    except Exception as e:
        logger.error(f"💥 Error en migración de empresas: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
