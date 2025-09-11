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
            "constraint_fixed": False,
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
        """
        Ejecutar migración completa del sistema de prompts
        
        FASES:
        1. Crear schema PostgreSQL
        2. Remover constraint problemático
        3. Poblar default_prompts desde agentes del repositorio
        4. Migrar custom_prompts.json existente
        5. Validar migración
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
            
            # Fase 2: Remover constraint problemático
            if self._remove_constraint_if_exists():
                self.migration_stats["constraint_fixed"] = True
                logger.info("✅ Fase 2: Constraint de nombres removido")
            else:
                logger.warning("⚠️ Fase 2: Error removiendo constraint (puede que no exista)")
            
            # Fase 3: Poblar defaults
            if self._populate_default_prompts():
                self.migration_stats["defaults_populated"] = True
                logger.info("✅ Fase 3: Default prompts poblados")
            else:
                logger.error("❌ Fase 3: Error poblando defaults")
                return self.migration_stats
            
            # Fase 4: Migrar JSON existente
            if self._migrate_custom_prompts_file():
                self.migration_stats["json_migrated"] = True
                logger.info("✅ Fase 4: Prompts JSON migrados")
            else:
                logger.warning("⚠️ Fase 4: Migración JSON parcial o sin datos")
            
            # Fase 5: Validar
            if self._validate_migration():
                logger.info("✅ Fase 5: Migración validada exitosamente")
            else:
                logger.warning("⚠️ Fase 5: Validación con advertencias")
            
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
        """Crear schema PostgreSQL si no existe (INTELIGENTE)"""
        logger.info("Verificando schema PostgreSQL...")
        
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Verificar si las tablas ya existen
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('custom_prompts', 'default_prompts', 'prompt_versions')
                """)
                
                existing_tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"Tablas existentes encontradas: {existing_tables}")
                
                if len(existing_tables) == 3:
                    logger.info("✅ Todas las tablas ya existen, verificando arquitectura...")
                    # Verificar si default_prompts tiene la arquitectura correcta
                    if self._verify_and_update_architecture():
                        logger.info("✅ Arquitectura verificada/actualizada")
                    else:
                        logger.warning("⚠️ Problemas actualizando arquitectura")
                    return True
                
                # Solo ejecutar schema si las tablas no existen
                schema_file = os.path.join(os.path.dirname(__file__), 'postgresql_schema.sql')
                
                if os.path.exists(schema_file):
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # Modificar SQL para usar CREATE TABLE IF NOT EXISTS
                    schema_sql = schema_sql.replace('CREATE TABLE custom_prompts', 'CREATE TABLE IF NOT EXISTS custom_prompts')
                    schema_sql = schema_sql.replace('CREATE TABLE prompt_versions', 'CREATE TABLE IF NOT EXISTS prompt_versions')
                    schema_sql = schema_sql.replace('CREATE TABLE default_prompts', 'CREATE TABLE IF NOT EXISTS default_prompts')
                    
                    cursor.execute(schema_sql)
                else:
                    # Usar schema embebido con IF NOT EXISTS
                    cursor.execute(self._get_embedded_schema_sql_safe())
                
                conn.commit()
                logger.info("✅ Schema PostgreSQL verificado/creado exitosamente")
                return True
                
        except Exception as e:
            logger.error(f"Error verificando/creando schema: {e}")
            self.migration_stats["errors"].append(f"Schema creation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _verify_and_update_architecture(self) -> bool:
        """Verificar y actualizar arquitectura de default_prompts para company_id separado"""
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Verificar si company_id ya existe
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'default_prompts' 
                    AND column_name = 'company_id'
                """)
                company_id_exists = cursor.fetchone() is not None
                
                if not company_id_exists:
                    logger.info("🔧 Actualizando arquitectura: agregando company_id")
                    
                    # Agregar columna company_id
                    cursor.execute("""
                        ALTER TABLE default_prompts 
                        ADD COLUMN company_id VARCHAR(100)
                    """)
                    
                    # Remover constraint único en agent_name si existe
                    cursor.execute("""
                        ALTER TABLE default_prompts 
                        DROP CONSTRAINT IF EXISTS default_prompts_agent_name_key
                    """)
                    
                    logger.info("✅ Columna company_id agregada y constraints actualizados")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error actualizando arquitectura: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _remove_constraint_if_exists(self) -> bool:
        """Remover constraint de agent_name que impide nombres como benova_sales_agent"""
        logger.info("Removiendo constraint de nombres de agentes...")
        
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Verificar si el constraint existe
                cursor.execute("""
                    SELECT constraint_name FROM information_schema.table_constraints 
                    WHERE table_name = 'default_prompts' 
                    AND constraint_type = 'CHECK' 
                    AND constraint_name = 'valid_agent_name'
                """)
                
                constraint_exists = cursor.fetchone()
                
                if constraint_exists:
                    # Remover el constraint
                    cursor.execute("""
                        ALTER TABLE default_prompts DROP CONSTRAINT IF EXISTS valid_agent_name
                    """)
                    logger.info("✅ Constraint 'valid_agent_name' removido exitosamente")
                else:
                    logger.info("ℹ️ Constraint 'valid_agent_name' no existe, no es necesario removerlo")
                
                # También remover constraint único de agent_name si existe
                cursor.execute("""
                    ALTER TABLE default_prompts 
                    DROP CONSTRAINT IF EXISTS default_prompts_agent_name_key
                """)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.warning(f"Error removiendo constraint: {e}")
            self.migration_stats["errors"].append(f"Constraint removal failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _get_embedded_schema_sql_safe(self) -> str:
        """Schema SQL embebido con company_id separado - ARQUITECTURA CORREGIDA"""
        return """
        -- Schema con arquitectura corregida: company_id + agent_name separados
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
            company_id VARCHAR(100) NOT NULL,
            agent_name VARCHAR(100) NOT NULL,
            template TEXT NOT NULL,
            description TEXT,
            category VARCHAR(50) DEFAULT 'general',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_company_agent UNIQUE (company_id, agent_name)
        );
        
        -- Índices optimizados para nueva arquitectura
        CREATE INDEX IF NOT EXISTS idx_custom_prompts_company_agent ON custom_prompts(company_id, agent_name);
        CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompt_versions(prompt_id);
        CREATE INDEX IF NOT EXISTS idx_default_prompts_company_agent ON default_prompts(company_id, agent_name);
        """
    
    def _populate_default_prompts(self) -> bool:
        """Poblar default_prompts con arquitectura company_id + agent_name separados (CORREGIDO)"""
        logger.info("Poblando prompts con arquitectura separada desde custom_prompts.json...")
        
        try:
            conn = psycopg2.connect(self.db_connection_string)
            
            with conn.cursor() as cursor:
                # Verificar si ya hay prompts por defecto
                cursor.execute("SELECT COUNT(*) as count FROM default_prompts")
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    logger.info(f"Ya existen {existing_count} default prompts, LIMPIANDO para migración correcta...")
                    # LIMPIAR COMPLETAMENTE para empezar correcto
                    cursor.execute("DELETE FROM default_prompts")
                    logger.info("✅ Tabla default_prompts limpiada")
                
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
                
                prompts_count = 0
                
                # Extraer SOLO default_template de cada empresa/agente válido
                for company_id, agents in custom_prompts.items():
                    # FILTRO 1: Saltar metadata
                    if company_id.startswith('_') or company_id == 'metadata':
                        logger.debug(f"Saltando metadata: {company_id}")
                        continue
                    
                    # FILTRO 2: Solo empresas válidas
                    if company_id not in self.valid_companies:
                        logger.warning(f"Empresa no válida: {company_id}")
                        continue
                    
                    # FILTRO 3: Solo objetos válidos
                    if not isinstance(agents, dict):
                        logger.warning(f"Datos de empresa no válidos: {company_id}")
                        continue
                    
                    logger.info(f"Procesando empresa: {company_id}")
                    
                    for agent_name, agent_data in agents.items():
                        # FILTRO 4: Solo agentes válidos
                        if agent_name not in self.valid_agents:
                            logger.debug(f"Agente no válido: {agent_name}")
                            continue
                        
                        # FILTRO 5: Solo datos de agente válidos
                        if not isinstance(agent_data, dict):
                            logger.debug(f"Datos de agente no válidos: {company_id}/{agent_name}")
                            continue
                        
                        # EXTRAER DEFAULT_TEMPLATE
                        default_template = agent_data.get('default_template')
                        if not default_template or len(default_template.strip()) == 0:
                            logger.debug(f"Sin default_template: {company_id}/{agent_name}")
                            continue
                        
                        # ARQUITECTURA CORREGIDA: company_id y agent_name separados
                        description = f"Prompt personalizado para {agent_name} de {company_id}"
                        
                        # Determinar categoría
                        category_mapping = {
                            'router_agent': 'routing',
                            'sales_agent': 'sales', 
                            'support_agent': 'support',
                            'emergency_agent': 'emergency',
                            'schedule_agent': 'scheduling',
                            'availability_agent': 'availability'
                        }
                        category = category_mapping.get(agent_name, 'general')
                        
                        # INSERTAR CON ARQUITECTURA SEPARADA
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
                        logger.info(f"Migrado default_template: {company_id}/{agent_name}")
                
                conn.commit()
                
                # Validar resultado
                expected_prompts = len(self.valid_companies) * len(self.valid_agents)
                if prompts_count == expected_prompts:
                    logger.info(f"✅ Migración PERFECTA: {prompts_count}/{expected_prompts} prompts específicos por empresa")
                else:
                    logger.warning(f"⚠️ Migración parcial: {prompts_count}/{expected_prompts} prompts")
                
                return prompts_count > 0
                
        except Exception as e:
            logger.error(f"Error poblando default prompts desde JSON: {e}")
            self.migration_stats["errors"].append(f"Default prompts population failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def _migrate_custom_prompts_file(self) -> bool:
        """Migrar custom_prompts.json existente a PostgreSQL (CORREGIDO - FILTRA METADATA)"""
        logger.info("Migrando custom_prompts.json...")
        
        custom_prompts_file = os.path.join(
            os.path.dirname(__file__), 
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
                    # FILTRO AGREGADO: Saltar metadata
                    if company_id.startswith('_') or company_id == 'metadata':
                        logger.debug(f"Saltando metadata en custom_prompts: {company_id}")
                        continue
                    
                    if not isinstance(company_data, dict):
                        continue
                    
                    # FILTRO AGREGADO: Solo empresas válidas
                    if company_id not in self.valid_companies:
                        logger.warning(f"Empresa no válida en custom_prompts: {company_id}")
                        continue
                    
                    self.migration_stats["companies_processed"] += 1
                    logger.info(f"Migrando empresa: {company_id}")
                    
                    for agent_name, agent_data in company_data.items():
                        if not isinstance(agent_data, dict):
                            continue
                        
                        # FILTRO AGREGADO: Solo agentes válidos
                        if agent_name not in self.valid_agents:
                            logger.debug(f"Agente no válido en custom_prompts: {agent_name}")
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
        """Validar que la migración fue exitosa con arquitectura separada (MEJORADO)"""
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
                
                # Verificar que default_prompts tiene company_id
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'default_prompts' 
                    AND column_name = 'company_id'
                """)
                company_id_exists = cursor.fetchone() is not None
                
                if not company_id_exists:
                    logger.error("❌ FALLO: default_prompts no tiene columna company_id")
                    return False
                else:
                    logger.info("✅ Arquitectura separada: company_id existe")
                
                # Verificar conteos
                cursor.execute("SELECT COUNT(*) as count FROM default_prompts")
                default_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM custom_prompts WHERE is_active = true")
                custom_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM prompt_versions")
                version_count = cursor.fetchone()['count']
                
                # Verificar que NO hay prompts con formato combinado
                cursor.execute("""
                    SELECT COUNT(*) as count FROM default_prompts 
                    WHERE agent_name LIKE '%_%'
                """)
                combined_format_count = cursor.fetchone()['count']
                
                # Verificar que todos los prompts tienen company_id y agent_name válidos
                cursor.execute("""
                    SELECT COUNT(*) as count FROM default_prompts 
                    WHERE company_id IS NOT NULL AND agent_name IS NOT NULL
                    AND company_id IN ('benova', 'spa_wellness', 'medispa', 'dental_clinic')
                    AND agent_name IN ('router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent')
                """)
                valid_separated_count = cursor.fetchone()['count']
                
                # Verificar funciones (opcional, no crítico si fallan)
                try:
                    cursor.execute("""
                        SELECT routine_name FROM information_schema.routines 
                        WHERE routine_schema = 'public' 
                        AND routine_name IN ('get_prompt_with_fallback', 'repair_prompts_from_repository')
                    """)
                    functions = [row['routine_name'] for row in cursor.fetchall()]
                    function_count = len(functions)
                except:
                    function_count = 0
                
                # Log de validación
                logger.info(f"✅ Tablas creadas: {len(tables)}/3")
                logger.info(f"✅ Default prompts: {default_count}")
                logger.info(f"✅ Custom prompts: {custom_count}")
                logger.info(f"✅ Version records: {version_count}")
                logger.info(f"✅ Funciones: {function_count}/2")
                
                # VALIDACIONES DE ARQUITECTURA SEPARADA
                if combined_format_count > 0:
                    logger.error(f"❌ FALLO: {combined_format_count} prompts con formato combinado encontrados (deberían ser 0)")
                    return False
                else:
                    logger.info(f"✅ Sin formato combinado: {combined_format_count}")
                
                if valid_separated_count != default_count:
                    logger.error(f"❌ FALLO: No todos los prompts tienen formato separado válido")
                    logger.info(f"   Válidos: {valid_separated_count}, Total: {default_count}")
                    return False
                else:
                    logger.info(f"✅ Todos los prompts tienen arquitectura separada: {valid_separated_count}")
                
                expected_prompts = len(self.valid_companies) * len(self.valid_agents)
                if default_count == expected_prompts:
                    logger.info(f"✅ Cantidad perfecta: {default_count}/{expected_prompts} prompts")
                else:
                    logger.warning(f"⚠️ Cantidad diferente a la esperada: {default_count}/{expected_prompts}")
                
                # Validación básica: verificar que hay defaults
                if default_count > 0:
                    logger.info("✅ Migración validada: hay prompts por defecto con arquitectura separada")
                    return True
                else:
                    logger.warning("⚠️ Migración parcial: no hay prompts por defecto")
                    return False
                
        except Exception as e:
            logger.error(f"Error en validación: {e}")
            self.migration_stats["errors"].append(f"Validation failed: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _get_embedded_schema_sql(self) -> str:
        """Schema SQL embebido como fallback con arquitectura separada"""
        return """
        -- Schema básico embebido con arquitectura separada
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
            company_id VARCHAR(100) NOT NULL,
            agent_name VARCHAR(100) NOT NULL,
            template TEXT NOT NULL,
            description TEXT,
            category VARCHAR(50) DEFAULT 'general',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_company_agent UNIQUE (company_id, agent_name)
        );
        
        -- Índices básicos optimizados
        CREATE INDEX IF NOT EXISTS idx_custom_prompts_company_agent ON custom_prompts(company_id, agent_name);
        CREATE INDEX IF NOT EXISTS idx_prompt_versions_prompt_id ON prompt_versions(prompt_id);
        CREATE INDEX IF NOT EXISTS idx_default_prompts_company_agent ON default_prompts(company_id, agent_name);
        """
    
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
    
    if stats.get("constraint_fixed"):
        print("✅ Constraint de nombres removido")
    else:
        print("⚠️ Constraint de nombres no removido")
    
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


if __name__ == "__main__":
    main()
