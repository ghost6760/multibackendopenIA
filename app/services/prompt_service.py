# app/services/prompt_service.py
# Servicio refactorizado para gestión de prompts con PostgreSQL y fallbacks

import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.company_config import get_company_manager

logger = logging.getLogger(__name__)

class PromptService:
    """Servicio para gestión de prompts con PostgreSQL, fallbacks y versionado"""
    
    def __init__(self, db_connection_string: str = None):
        """
        Inicializar servicio de prompts
        
        Args:
            db_connection_string: String de conexión PostgreSQL
        """
        self.db_connection_string = db_connection_string or os.getenv('DATABASE_URL')
        self.last_fallback_level = None
        self.repair_summary = []
        
        # Información de último fallback usado
        self._last_fallback_info = {"level": "none", "source": "postgresql"}
        self._db_status = "connected"
        
        # Cache para prompts hardcodeados (fallback nivel 3)
        self._hardcoded_prompts = {
            'router_agent': 'Eres un asistente especializado en clasificar intenciones. Responde con: VENTAS, SOPORTE, EMERGENCIA, AGENDAMIENTO, o DISPONIBILIDAD.',
            'sales_agent': 'Eres un especialista en ventas. Proporciona información comercial y promueve la reserva de citas.',
            'support_agent': 'Eres un asistente de soporte. Ayuda a resolver dudas y proporciona información sobre servicios.',
            'emergency_agent': 'Eres un asistente para emergencias médicas. Proporciona primeros auxilios básicos y recomienda atención médica.',
            'schedule_agent': 'Eres un asistente de agendamiento. Ayuda a programar, modificar o cancelar citas médicas.',
            'availability_agent': 'Eres un asistente de disponibilidad. Proporciona información sobre horarios y disponibilidad de servicios.'
        }
    
    def get_last_fallback_info(self) -> dict:
        """Obtener información del último fallback usado"""
        return self._last_fallback_info
    
    def get_db_connection(self) -> Optional[psycopg2.extensions.connection]:
        """Obtener conexión a PostgreSQL con manejo de errores"""
        try:
            if not self.db_connection_string:
                logger.warning("No database connection string provided")
                return None
                
            conn = psycopg2.connect(
                self.db_connection_string,
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None

    # ========================================================================
    # NUEVO MÉTODO: get_prompt_payload
    # Devuelve estructura con system, examples, placeholders, meta
    # ========================================================================
    
    def get_prompt_payload(
        self, 
        company_id: str, 
        agent_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtener payload estructurado de prompt para un agente.
        
        NUEVO: Devuelve estructura completa con system, examples, placeholders.
        Reemplaza la necesidad de construir ChatPromptTemplate manualmente.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente (ej. 'sales_agent', 'router_agent')
        
        Returns:
            Dict con estructura:
            {
                'system': str,              # Prompt del sistema
                'examples': List[Dict],     # Ejemplos de conversación
                'placeholders': Dict,       # Variables para interpolación
                'meta': Dict                # Metadata (source, version, etc)
            }
        """
        conn = self.get_db_connection()
        if not conn:
            logger.warning(
                f"No DB connection, using hardcoded fallback for {company_id}/{agent_key}"
            )
            return self._get_fallback_prompt_payload(agent_key)
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 1. Intentar obtener custom prompt (personalizado)
                cursor.execute("""
                    SELECT 
                        template, 
                        structured_template,
                        version,
                        modified_at,
                        modified_by
                    FROM custom_prompts 
                    WHERE company_id = %s 
                      AND agent_name = %s 
                      AND is_active = true
                """, (company_id, agent_key))
                
                custom_result = cursor.fetchone()
                
                if custom_result:
                    # Si tiene structured_template (JSONB), usar ese
                    if custom_result.get('structured_template'):
                        structured = custom_result['structured_template']
                        
                        # Asegurar que tiene la estructura esperada
                        payload = {
                            'system': structured.get('system', custom_result['template']),
                            'examples': structured.get('examples', []),
                            'placeholders': structured.get('placeholders', {}),
                            'meta': {
                                'source': 'postgresql_custom_structured',
                                'version': custom_result['version'],
                                'modified_at': str(custom_result['modified_at']),
                                'modified_by': custom_result['modified_by']
                            }
                        }
                        
                        logger.debug(
                            f"Loaded structured custom prompt for {company_id}/{agent_key}"
                        )
                        return payload
                    else:
                        # Solo tiene template string (legacy)
                        return {
                            'system': custom_result['template'],
                            'examples': [],
                            'placeholders': {},
                            'meta': {
                                'source': 'postgresql_custom_legacy',
                                'version': custom_result['version'],
                                'modified_at': str(custom_result['modified_at']),
                                'modified_by': custom_result['modified_by']
                            }
                        }
                
                # 2. Intentar obtener default prompt
                cursor.execute("""
                    SELECT 
                        template,
                        structured_template,
                        description,
                        updated_at
                    FROM default_prompts 
                    WHERE company_id = %s 
                      AND agent_name = %s
                """, (company_id, agent_key))
                
                default_result = cursor.fetchone()
                
                if default_result:
                    # Si tiene structured_template, usar ese
                    if default_result.get('structured_template'):
                        structured = default_result['structured_template']
                        
                        return {
                            'system': structured.get('system', default_result['template']),
                            'examples': structured.get('examples', []),
                            'placeholders': structured.get('placeholders', {}),
                            'meta': {
                                'source': 'postgresql_default_structured',
                                'description': default_result['description'],
                                'updated_at': str(default_result['updated_at'])
                            }
                        }
                    else:
                        # Solo tiene template string
                        return {
                            'system': default_result['template'],
                            'examples': [],
                            'placeholders': {},
                            'meta': {
                                'source': 'postgresql_default_legacy',
                                'description': default_result['description'],
                                'updated_at': str(default_result['updated_at'])
                            }
                        }
                
                # 3. No se encontró nada, usar fallback
                logger.info(
                    f"No prompt found in DB for {company_id}/{agent_key}, using fallback"
                )
                return self._get_fallback_prompt_payload(agent_key)
                
        except Exception as e:
            logger.error(
                f"Error getting prompt payload for {company_id}/{agent_key}: {e}",
                exc_info=True
            )
            return self._get_fallback_prompt_payload(agent_key)
        finally:
            conn.close()
    
    def _get_fallback_prompt_payload(self, agent_key: str) -> Dict[str, Any]:
        """
        Obtener payload de fallback desde prompts hardcodeados.
        
        Args:
            agent_key: Key del agente
        
        Returns:
            Dict con estructura de prompt básica
        """
        system_prompt = self._hardcoded_prompts.get(
            agent_key,
            f"Eres un asistente para {agent_key}."
        )
        
        return {
            'system': system_prompt,
            'examples': [],
            'placeholders': {},
            'meta': {
                'source': 'hardcoded_fallback',
                'agent_key': agent_key
            }
        }
    
    # ========================================================================
    # NUEVO MÉTODO: save_custom_prompt_payload
    # Guarda payload estructurado en JSONB
    # ========================================================================
    
    def save_custom_prompt_payload(
        self,
        company_id: str,
        agent_key: str,
        prompt_payload: Dict[str, Any],
        modified_by: str = "admin"
    ) -> bool:
        """
        Guardar payload estructurado de prompt personalizado.
        
        NUEVO: Guarda estructura completa en campo JSONB structured_template.
        Permite guardar system, examples, placeholders de forma estructurada.
        
        Args:
            company_id: ID de la empresa
            agent_key: Key del agente
            prompt_payload: Dict con estructura:
                {
                    'system': str,
                    'examples': List[Dict],
                    'placeholders': Dict,
                    'meta': Dict (opcional)
                }
            modified_by: Usuario que modifica
        
        Returns:
            bool: True si se guardó exitosamente
        """
        conn = self.get_db_connection()
        if not conn:
            logger.error(
                f"Cannot save prompt payload - No DB connection for {company_id}/{agent_key}"
            )
            return False
        
        try:
            # Validar estructura mínima
            if not prompt_payload.get('system'):
                logger.error(
                    f"Invalid prompt payload - missing 'system' field for {company_id}/{agent_key}"
                )
                return False
            
            # Extraer template string (para compatibilidad)
            template_string = prompt_payload['system']
            
            # Preparar structured_template JSONB
            structured_template = {
                'system': prompt_payload.get('system', ''),
                'examples': prompt_payload.get('examples', []),
                'placeholders': prompt_payload.get('placeholders', {}),
                'meta': prompt_payload.get('meta', {})
            }
            
            with conn.cursor() as cursor:
                # Verificar si ya existe custom prompt
                cursor.execute("""
                    SELECT version FROM custom_prompts 
                    WHERE company_id = %s AND agent_name = %s AND is_active = true
                """, (company_id, agent_key))
                
                existing = cursor.fetchone()
                
                if existing:
                    # UPDATE con incremento de versión
                    new_version = existing[0] + 1
                    
                    cursor.execute("""
                        UPDATE custom_prompts 
                        SET template = %s,
                            structured_template = %s,
                            version = %s,
                            modified_at = CURRENT_TIMESTAMP,
                            modified_by = %s
                        WHERE company_id = %s 
                          AND agent_name = %s 
                          AND is_active = true
                    """, (
                        template_string,
                        json.dumps(structured_template),
                        new_version,
                        modified_by,
                        company_id,
                        agent_key
                    ))
                    
                    logger.info(
                        f"✅ Updated custom prompt payload for {company_id}/{agent_key} "
                        f"(v{new_version})"
                    )
                else:
                    # INSERT nuevo
                    cursor.execute("""
                        INSERT INTO custom_prompts (
                            company_id,
                            agent_name,
                            template,
                            structured_template,
                            version,
                            is_active,
                            created_at,
                            modified_at,
                            modified_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
                    """, (
                        company_id,
                        agent_key,
                        template_string,
                        json.dumps(structured_template),
                        1,
                        True,
                        modified_by
                    ))
                    
                    logger.info(
                        f"✅ Created new custom prompt payload for {company_id}/{agent_key}"
                    )
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(
                f"Error saving prompt payload for {company_id}/{agent_key}: {e}",
                exc_info=True
            )
            if conn:
                conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========================================================================
    # MÉTODOS EXISTENTES (MANTENIDOS PARA COMPATIBILIDAD)
    # ========================================================================
    
    def _get_prompts_from_json_fallback(self, company_id: str, agents: List[str]) -> Optional[Dict[str, Dict]]:
        """Fallback a custom_prompts.json para compatibilidad temporal"""
        try:
            custom_prompts_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'custom_prompts.json'
            )
            
            if not os.path.exists(custom_prompts_file):
                return None
            
            with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                custom_prompts = json.load(f)
            
            company_prompts = custom_prompts.get(company_id, {})
            agents_data = {}
            
            for agent_name in agents:
                agent_data = company_prompts.get(agent_name, {})
                
                if isinstance(agent_data, dict):
                    # Priorizar template personalizado, luego default_template
                    template = agent_data.get('template')
                    if not template or template == "null":
                        template = agent_data.get('default_template') or self._hardcoded_prompts.get(agent_name)
                    
                    agents_data[agent_name] = {
                        "current_prompt": template,
                        "is_custom": agent_data.get('is_custom', False),
                        "last_modified": agent_data.get('modified_at'),
                        "version": 1,
                        "source": "json_file",
                        "fallback_level": "json_compatibility",
                        # NUEVO: Incluir structured_template si existe
                        "structured_template": agent_data.get('structured_template'),
                        "format": "structured" if agent_data.get('structured_template') else "string"
                    }
                else:
                    agents_data[agent_name] = {
                        "current_prompt": self._hardcoded_prompts.get(agent_name, f"Default prompt for {agent_name}"),
                        "is_custom": False,
                        "last_modified": None,
                        "version": 0,
                        "source": "hardcoded",
                        "fallback_level": "json_hardcoded",
                        "structured_template": None,
                        "format": "string"
                    }
            
            return agents_data
            
        except Exception as e:
            logger.error(f"Error reading JSON prompts: {e}")
            return None


    def get_company_prompts(self, company_id: str, agents: List[str] = None) -> Optional[Dict[str, Dict]]:
        """
        Obtener prompts de una empresa con arquitectura separada.
        MODIFICADO: Incluye structured_template y format para compatibilidad.
        
        Returns:
            Dict con datos de prompts para cada agente, incluyendo:
            - current_prompt (str)
            - structured_template (dict, si existe)
            - format ('string' o 'structured')
        """
        if agents is None:
            agents = ['router_agent', 'sales_agent', 'support_agent', 'emergency_agent', 'schedule_agent']
        
        conn = self.get_db_connection()
        if not conn:
            # Fallback a JSON si no hay PostgreSQL
            return self._get_prompts_from_json_fallback(company_id, agents)
        
        try:
            agents_data = {}
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                for agent_name in agents:
                    # Buscar custom prompt (personalizado)
                    cursor.execute("""
                        SELECT 
                            template, 
                            structured_template,
                            is_active, 
                            version, 
                            modified_at, 
                            modified_by, 
                            notes
                        FROM custom_prompts 
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (company_id, agent_name))
                    
                    custom_result = cursor.fetchone()
                    
                    if custom_result:
                        # Tiene prompt personalizado
                        agents_data[agent_name] = {
                            "current_prompt": custom_result['template'],
                            "is_custom": True,
                            "last_modified": custom_result['modified_at'],
                            "modified_by": custom_result['modified_by'],
                            "version": custom_result['version'],
                            "source": "postgresql_custom",
                            "notes": custom_result['notes'],
                            # NUEVO: Incluir structured_template
                            "structured_template": custom_result.get('structured_template'),
                            "format": "structured" if custom_result.get('structured_template') else "string"
                        }
                    else:
                        # Buscar default prompt (por defecto)
                        cursor.execute("""
                            SELECT 
                                template,
                                structured_template, 
                                description, 
                                category, 
                                updated_at
                            FROM default_prompts 
                            WHERE company_id = %s AND agent_name = %s
                        """, (company_id, agent_name))
                        
                        default_result = cursor.fetchone()
                        
                        if default_result:
                            # Tiene prompt por defecto
                            agents_data[agent_name] = {
                                "current_prompt": default_result['template'],
                                "is_custom": False,
                                "last_modified": default_result['updated_at'],
                                "version": 1,
                                "source": "postgresql_default",
                                "description": default_result['description'],
                                "category": default_result['category'],
                                # NUEVO: Incluir structured_template
                                "structured_template": default_result.get('structured_template'),
                                "format": "structured" if default_result.get('structured_template') else "string"
                            }
                        else:
                            # No tiene ni custom ni default, usar hardcoded
                            agents_data[agent_name] = {
                                "current_prompt": self._hardcoded_prompts.get(agent_name, f"Default prompt for {agent_name}"),
                                "is_custom": False,
                                "last_modified": None,
                                "version": 0,
                                "source": "hardcoded",
                                "fallback_level": "hardcoded",
                                "structured_template": None,
                                "format": "string"
                            }
            
            return agents_data
            
        except Exception as e:
            logger.error(f"Error getting company prompts: {e}")
            # Fallback a JSON
            return self._get_prompts_from_json_fallback(company_id, agents)
        finally:
            conn.close()

    def save_custom_prompt(self, company_id: str, agent_name: str, template: str, modified_by: str = "admin") -> bool:
        """
        MANTENIDO: Guardar custom prompt (compatibilidad con endpoints existentes).
        
        Nota: Este método guarda solo el template string.
        Para guardar estructura completa, usar save_custom_prompt_payload.
        """
        conn = self.get_db_connection()
        if not conn:
            logger.error(f"❌ [{company_id}] Cannot save custom prompt - No DB connection")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Verificar si ya existe
                cursor.execute("""
                    SELECT version FROM custom_prompts 
                    WHERE company_id = %s AND agent_name = %s AND is_active = true
                """, (company_id, agent_name))
                
                existing = cursor.fetchone()
                
                if existing:
                    # UPDATE con incremento de versión
                    new_version = existing[0] + 1
                    
                    cursor.execute("""
                        UPDATE custom_prompts 
                        SET template = %s,
                            version = %s,
                            modified_at = CURRENT_TIMESTAMP,
                            modified_by = %s
                        WHERE company_id = %s AND agent_name = %s AND is_active = true
                    """, (template, new_version, modified_by, company_id, agent_name))
                    
                    logger.info(f"✅ [{company_id}] Updated custom prompt for {agent_name} (v{new_version})")
                else:
                    # INSERT nuevo
                    cursor.execute("""
                        INSERT INTO custom_prompts (
                            company_id, agent_name, template, version, is_active,
                            created_at, modified_at, modified_by
                        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
                    """, (company_id, agent_name, template, 1, True, modified_by))
                    
                    logger.info(f"✅ [{company_id}] Created new custom prompt for {agent_name}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ [{company_id}] Error saving custom prompt for {agent_name}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_custom_prompt(self, company_id: str, agent_name: str) -> bool:
        """Eliminar custom prompt (soft delete)"""
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE custom_prompts 
                    SET is_active = false,
                        modified_at = CURRENT_TIMESTAMP
                    WHERE company_id = %s AND agent_name = %s
                """, (company_id, agent_name))
                
                conn.commit()
                logger.info(f"✅ [{company_id}] Deleted custom prompt for {agent_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting custom prompt: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_db_status(self) -> Dict[str, Any]:
        """Obtener estado de la base de datos"""
        conn = self.get_db_connection()
        
        if not conn:
            return {
                "postgresql_available": False,
                "status": "disconnected",
                "fallback_active": True
            }
        
        try:
            with conn.cursor() as cursor:
                # Verificar tablas
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND table_name IN ('custom_prompts', 'default_prompts')
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                has_custom = 'custom_prompts' in tables
                has_default = 'default_prompts' in tables
                
                return {
                    "postgresql_available": True,
                    "status": "connected",
                    "tables": {
                        "custom_prompts": has_custom,
                        "default_prompts": has_default
                    },
                    "fallback_active": not (has_custom and has_default)
                }
                
        except Exception as e:
            logger.error(f"Error checking DB status: {e}")
            return {
                "postgresql_available": False,
                "status": "error",
                "error": str(e),
                "fallback_active": True
            }
        finally:
            conn.close()

    def get_prompt_history(self, company_id: str, agent_name: str, limit: int = 10) -> List[Dict]:
        """Obtener historial de cambios de un prompt"""
        conn = self.get_db_connection()
        if not conn:
            return []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT version, template, modified_at, modified_by, notes
                    FROM custom_prompts 
                    WHERE company_id = %s AND agent_name = %s
                    ORDER BY version DESC
                    LIMIT %s
                """, (company_id, agent_name, limit))
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting prompt history: {e}")
            return []
        finally:
            conn.close()

    def get_default_prompt(self, company_id: str, agent_name: str) -> Optional[str]:
        """Obtener default prompt de un agente"""
        conn = self.get_db_connection()
        if not conn:
            return self._hardcoded_prompts.get(agent_name)
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT template 
                    FROM default_prompts 
                    WHERE company_id = %s AND agent_name = %s
                """, (company_id, agent_name))
                
                result = cursor.fetchone()
                
                if result:
                    return result[0]
                else:
                    logger.debug(f"No default prompt found for {company_id}/{agent_name}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting default prompt for {company_id}/{agent_name}: {e}")
            return None
        finally:
            conn.close()



    
    # Agregar al final de la clase PromptService en app/services/prompt_service.py
    
    def initialize_default_prompts_for_company(self, company_id: str, company_config=None) -> Dict[str, Any]:
        """
        Inicializar prompts default para una nueva empresa usando los métodos existentes de cada agente
        ✅ Usa _create_default_prompt_template() que ya existe en cada agente
        ✅ NO duplica código ni lógica
        
        Args:
            company_id: ID de la empresa
            company_config: CompanyConfig object (opcional, se obtiene si no se provee)
        
        Returns:
            Dict con estadísticas de inicialización
        """
        stats = {
            "company_id": company_id,
            "prompts_created": 0,
            "agents_initialized": [],
            "errors": [],
            "success": False
        }
        
        conn = self.get_db_connection()
        if not conn:
            stats["errors"].append("No database connection available")
            logger.error(f"❌ [{company_id}] Cannot initialize prompts - No DB connection")
            return stats
        
        try:
            # 1. Obtener configuración de la empresa si no se provee
            if company_config is None:
                from app.config.company_config import get_company_manager
                company_manager = get_company_manager()
                company_config = company_manager.get_company_config(company_id)
                
                if not company_config:
                    stats["errors"].append(f"Company config not found for {company_id}")
                    logger.error(f"❌ [{company_id}] Cannot find company config")
                    return stats
            
            # 2. Obtener OpenAI service (necesario para instanciar agentes)
            from app.services.openai_service import OpenAIService
            openai_service = OpenAIService()
            
            # 3. Importar clases de agentes
            from app.agents.router_agent import RouterAgent
            from app.agents.sales_agent import SalesAgent
            from app.agents.support_agent import SupportAgent
            from app.agents.emergency_agent import EmergencyAgent
            from app.agents.schedule_agent import ScheduleAgent
            from app.agents.availability_agent import AvailabilityAgent
            
            # 4. Mapeo de agentes
            agent_classes = {
                "router_agent": RouterAgent,
                "sales_agent": SalesAgent,
                "support_agent": SupportAgent,
                "emergency_agent": EmergencyAgent,
                "schedule_agent": ScheduleAgent,
                "availability_agent": AvailabilityAgent
            }
            
            logger.info(f"🔄 [{company_id}] Initializing {len(agent_classes)} default prompts using agent methods...")
            
            with conn.cursor() as cursor:
                for agent_name, agent_class in agent_classes.items():
                    try:
                        # ✅ Instanciar temporalmente el agente (ligero, solo para obtener prompt)
                        temp_agent = agent_class(company_config, openai_service)
                        
                        # ✅ Llamar al método que YA EXISTE en el agente
                        prompt_template = temp_agent._create_default_prompt_template()
                        
                        # ✅ Extraer el contenido del system message
                        # NOTA: Este código maneja ChatPromptTemplate SOLO aquí, en este método legacy
                        # para compatibilidad con agentes que aún no migraron
                        system_message = prompt_template.messages[0]
                        
                        # Obtener el template string del system message
                        if hasattr(system_message, 'prompt'):
                            # Es un SystemMessagePromptTemplate
                            prompt_string = system_message.prompt.template
                        elif hasattr(system_message, 'content'):
                            # Es un mensaje directo
                            prompt_string = system_message.content
                        else:
                            # Fallback: convertir a string
                            prompt_string = str(system_message)
                        
                        # ✅ Insertar en default_prompts
                        cursor.execute("""
                            INSERT INTO default_prompts (
                                company_id, 
                                agent_name, 
                                template, 
                                description,
                                category,
                                created_at,
                                updated_at
                            )
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            ON CONFLICT (company_id, agent_name) DO UPDATE SET
                                template = EXCLUDED.template,
                                updated_at = CURRENT_TIMESTAMP,
                                description = EXCLUDED.description
                        """, (
                            company_id,
                            agent_name,
                            prompt_string,
                            f"Default prompt for {agent_name} - Extracted from agent class",
                            "default"
                        ))
                        
                        stats["prompts_created"] += 1
                        stats["agents_initialized"].append(agent_name)
                        logger.info(f"✅ [{company_id}] Initialized {agent_name} (length: {len(prompt_string)})")
                        
                        # Limpiar referencia temporal
                        del temp_agent
                        
                    except Exception as e:
                        error_msg = f"Error initializing {agent_name}: {str(e)}"
                        stats["errors"].append(error_msg)
                        logger.error(f"❌ [{company_id}] {error_msg}")
                
                conn.commit()
                
                if stats["prompts_created"] > 0:
                    stats["success"] = True
                    logger.info(f"🎉 [{company_id}] Successfully initialized {stats['prompts_created']}/{len(agent_classes)} prompts")
                else:
                    logger.warning(f"⚠️ [{company_id}] No prompts were initialized")
            
        except Exception as e:
            error_msg = f"Critical error initializing prompts: {str(e)}"
            stats["errors"].append(error_msg)
            logger.error(f"💥 [{company_id}] {error_msg}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
        
        return stats
# ============================================================================
# FACTORY FUNCTION
# ============================================================================

_prompt_service_instance = None

def get_prompt_service() -> PromptService:
    """Factory function para obtener instancia singleton del servicio"""
    global _prompt_service_instance
    
    if _prompt_service_instance is None:
        _prompt_service_instance = PromptService()
    
    return _prompt_service_instance

def init_prompt_service(db_connection_string: str = None) -> PromptService:
    """Inicializar servicio de prompts con configuración específica"""
    global _prompt_service_instance
    _prompt_service_instance = PromptService(db_connection_string)
    return _prompt_service_instance
