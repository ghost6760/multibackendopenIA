# app/services/company_config_service.py
"""
Enterprise Company Configuration Service
========================================

Maneja configuración de empresas en PostgreSQL como source of truth
Con fallback automático a JSON y caching en Redis para performance

Arquitectura de 3 niveles:
1. PostgreSQL (source of truth) 
2. JSON File (fallback/bootstrap)
3. Redis Cache (performance)
"""

import os
import json
import logging
import psycopg2
import psycopg2.extras
from psycopg2 import sql 
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from app.services.redis_service import get_redis_client
from app.config.company_config import CompanyConfig  # Mantener compatibilidad

logger = logging.getLogger(__name__)

@dataclass
class EnterpriseCompanyConfig:
    """Configuración empresa extendida para PostgreSQL"""
    company_id: str
    company_name: str
    business_type: str = 'general'
    services: str = ''
    
    # Redis/Vector Store
    redis_prefix: str = ''
    vectorstore_index: str = ''
    
    # Agentes IA
    sales_agent_name: str = ''
    model_name: str = 'gpt-4o-mini'
    max_tokens: int = 1500
    temperature: float = 0.7
    max_context_messages: int = 10
    
    # Servicios Externos
    schedule_service_url: str = 'http://127.0.0.1:4040'
    schedule_integration_type: str = 'basic'
    chatwoot_account_id: Optional[str] = None
    
    # Configuración de Negocio
    treatment_durations: Optional[Dict[str, int]] = None
    schedule_keywords: Optional[List[str]] = None
    emergency_keywords: Optional[List[str]] = None
    sales_keywords: Optional[List[str]] = None
    required_booking_fields: Optional[List[str]] = None
    
    # Localización
    timezone: str = 'America/Bogota'
    language: str = 'es'
    currency: str = 'COP'
    
    # Estado y Límites
    is_active: bool = True
    subscription_tier: str = 'basic'
    max_documents: int = 1000
    max_conversations: int = 10000
    
    # Metadatos
    version: int = 1
    created_by: str = 'admin'
    modified_by: str = 'admin'
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Auto-completar campos derivados"""
        if not self.redis_prefix:
            self.redis_prefix = f"{self.company_id}:"
        if not self.vectorstore_index:
            self.vectorstore_index = f"{self.company_id}_documents"
        if not self.sales_agent_name:
            self.sales_agent_name = f"Asistente de {self.company_name}"
    
    def to_legacy_config(self) -> CompanyConfig:
        """Convertir a formato legacy para compatibilidad"""
        return CompanyConfig(
            company_id=self.company_id,
            company_name=self.company_name,
            redis_prefix=self.redis_prefix,
            vectorstore_index=self.vectorstore_index,
            schedule_service_url=self.schedule_service_url,
            sales_agent_name=self.sales_agent_name,
            services=self.services,
            model_name=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            max_context_messages=self.max_context_messages,
            treatment_durations=self.treatment_durations or {},
            schedule_keywords=self.schedule_keywords or [],
            emergency_keywords=self.emergency_keywords or [],
            sales_keywords=self.sales_keywords or []
        )

class EnterpriseCompanyConfigService:
    """Servicio de configuración empresarial con PostgreSQL"""
    
    def __init__(self):
        self.db_connection_string = os.getenv('DATABASE_URL')
        self.redis_client = get_redis_client()
        self.cache_ttl = 300  # 5 minutos cache
        self._db_status = "unknown"
        
        # Cache en memoria para performance
        self._memory_cache: Dict[str, EnterpriseCompanyConfig] = {}
        self._cache_timestamp = 0
        
        logger.info("EnterpriseCompanyConfigService initialized")
    
    def get_company_config(self, company_id: str, use_cache: bool = True) -> Optional[EnterpriseCompanyConfig]:
        """
        Obtener configuración con fallback automático:
        1. Memory Cache (performance)
        2. Redis Cache (distributed)
        3. PostgreSQL (source of truth)
        4. JSON File (fallback)
        5. Default Config (emergency)
        """
        try:
            # 1. Memory Cache
            if use_cache and self._is_memory_cache_valid() and company_id in self._memory_cache:
                logger.debug(f"Company config from memory cache: {company_id}")
                return self._memory_cache[company_id]
            
            # 2. Redis Cache
            if use_cache:
                config = self._get_config_from_redis_cache(company_id)
                if config:
                    self._memory_cache[company_id] = config
                    return config
            
            # 3. PostgreSQL
            config = self._get_config_from_postgresql(company_id)
            if config:
                self._cache_config(company_id, config)
                return config
            
            # 4. JSON Fallback
            config = self._get_config_from_json_fallback(company_id)
            if config:
                logger.warning(f"Using JSON fallback for company {company_id}")
                return config
            
            # 5. Default Emergency Config
            logger.warning(f"Creating emergency default config for {company_id}")
            return self._create_default_config(company_id)
            
        except Exception as e:
            logger.error(f"Error getting company config for {company_id}: {e}")
            return self._create_default_config(company_id)
    
    def create_company(self, config: EnterpriseCompanyConfig, created_by: str = "admin") -> bool:
        """Crear nueva empresa en PostgreSQL"""
        if not self.db_connection_string:
            logger.error("PostgreSQL not available for company creation")
            return False
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Verificar que no existe
                    cursor.execute("SELECT company_id FROM companies WHERE company_id = %s", (config.company_id,))
                    if cursor.fetchone():
                        logger.error(f"Company {config.company_id} already exists")
                        return False
                    
                    # Preparar datos para inserción
                    insert_data = asdict(config)
                    insert_data['created_by'] = created_by
                    insert_data['modified_by'] = created_by
                    
                    # Convertir listas/dicts a formato PostgreSQL
                    if config.treatment_durations:
                        insert_data['treatment_durations'] = json.dumps(config.treatment_durations)
                    if config.schedule_keywords:
                        insert_data['schedule_keywords'] = config.schedule_keywords
                    if config.emergency_keywords:
                        insert_data['emergency_keywords'] = config.emergency_keywords
                    if config.sales_keywords:
                        insert_data['sales_keywords'] = config.sales_keywords
                    if config.required_booking_fields:
                        insert_data['required_booking_fields'] = config.required_booking_fields
                    
                    # Construir query de inserción
                    columns = list(insert_data.keys())
                    placeholders = [f"%({col})s" for col in columns]
                    
                    insert_query = f"""
                        INSERT INTO companies ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING id, version
                    """
                    
                    cursor.execute(insert_query, insert_data)
                    result = cursor.fetchone()
                    
                    conn.commit()
                    
                    # Limpiar cache
                    self._invalidate_cache(config.company_id)
                    
                    logger.info(f"Company {config.company_id} created successfully (ID: {result['id']}, Version: {result['version']})")
                    return True
                    
        except Exception as e:
            logger.error(f"Error creating company {config.company_id}: {e}")
            return False
    ###
    def update_company(self, company_id: str, updates: Dict[str, Any], modified_by: str = "admin") -> bool:
        """Actualizar configuración de empresa"""
        if not self.db_connection_string:
            logger.error("PostgreSQL not available for company update")
            return False
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Verificar que existe
                    cursor.execute("SELECT id FROM companies WHERE company_id = %s AND is_active = true", (company_id,))
                    if not cursor.fetchone():
                        logger.error(f"Company {company_id} not found or inactive")
                        return False
                    
                    # Preparar datos de actualización (SIN version)
                    updates['modified_by'] = modified_by
                    updates['modified_at'] = datetime.now(timezone.utc)
                    
                    # Construir query de actualización
                    set_clauses = []
                    values = {}
                    
                    for key, value in updates.items():
                        set_clauses.append(f"{key} = %({key})s")
                        values[key] = value
                    
                    # 🔧 AGREGAR version increment directamente al SQL
                    set_clauses.append("version = version + 1")
                    
                    update_query = f"""
                        UPDATE companies 
                        SET {', '.join(set_clauses)}
                        WHERE company_id = %(company_id)s
                        RETURNING version
                    """
                    
                    values['company_id'] = company_id
                    cursor.execute(update_query, values)
                    result = cursor.fetchone()
                    
                    conn.commit()
                    
                    # Limpiar cache
                    self._invalidate_cache(company_id)
                    
                    logger.info(f"Company {company_id} updated successfully (Version: {result['version']})")
                    return True
                    
        except Exception as e:
            logger.error(f"Error updating company {company_id}: {e}")
            return False
    
    def list_companies(self, active_only: bool = True, business_type: Optional[str] = None) -> List[EnterpriseCompanyConfig]:
        """Listar todas las empresas"""
        companies = []
        
        if self.db_connection_string:
            try:
                with psycopg2.connect(self.db_connection_string) as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                        query = "SELECT * FROM companies WHERE 1=1"
                        params = []
                        
                        if active_only:
                            query += " AND is_active = %s"
                            params.append(True)
                        
                        if business_type:
                            query += " AND business_type = %s"
                            params.append(business_type)
                        
                        query += " ORDER BY company_name"
                        
                        cursor.execute(query, params)
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            try:
                                config = self._row_to_config(row)
                                companies.append(config)
                            except Exception as e:
                                logger.warning(f"Error parsing company {row.get('company_id')}: {e}")
                                
            except Exception as e:
                logger.error(f"Error listing companies: {e}")
        
        # Fallback a JSON si PostgreSQL falla
        if not companies:
            companies = self._list_companies_from_json()
        
        return companies
    
    def migrate_from_json(self, json_file_path: str = "companies_config.json") -> Dict[str, Any]:
        """Migrar configuraciones desde JSON a PostgreSQL"""
        migration_stats = {
            "companies_migrated": 0,
            "companies_updated": 0,
            "errors": [],
            "success": False
        }
        
        try:
            if not os.path.exists(json_file_path):
                migration_stats["errors"].append(f"JSON file not found: {json_file_path}")
                return migration_stats
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            for company_id, company_data in json_data.items():
                try:
                    # Convertir JSON a EnterpriseCompanyConfig
                    config = EnterpriseCompanyConfig(
                        company_id=company_id,
                        company_name=company_data.get('company_name', company_id),
                        services=company_data.get('services', ''),
                        redis_prefix=company_data.get('redis_prefix', f"{company_id}:"),
                        vectorstore_index=company_data.get('vectorstore_index', f"{company_id}_documents"),
                        sales_agent_name=company_data.get('sales_agent_name', f"Asistente de {company_data.get('company_name', company_id)}"),
                        model_name=company_data.get('model_name', 'gpt-4o-mini'),
                        max_tokens=company_data.get('max_tokens', 1500),
                        temperature=company_data.get('temperature', 0.7),
                        schedule_service_url=company_data.get('schedule_service_url', 'http://127.0.0.1:4040'),
                        treatment_durations=company_data.get('treatment_durations'),
                        created_by="json_migration",
                        modified_by="json_migration",
                        notes=f"Migrated from {json_file_path} on {datetime.now().isoformat()}"
                    )
                    
                    # Verificar si existe
                    existing = self._get_config_from_postgresql(company_id)
                    
                    if existing:
                        # Actualizar existente
                        updates = {
                            'company_name': config.company_name,
                            'services': config.services,
                            'sales_agent_name': config.sales_agent_name
                        }
                        if self.update_company(company_id, updates, "json_migration"):
                            migration_stats["companies_updated"] += 1
                    else:
                        # Crear nuevo
                        if self.create_company(config, "json_migration"):
                            migration_stats["companies_migrated"] += 1
                    
                except Exception as e:
                    error_msg = f"Error migrating {company_id}: {str(e)}"
                    logger.error(error_msg)
                    migration_stats["errors"].append(error_msg)
            
            migration_stats["success"] = len(migration_stats["errors"]) == 0
            logger.info(f"Migration completed: {migration_stats}")
            
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            logger.error(error_msg)
            migration_stats["errors"].append(error_msg)
        
        return migration_stats
    
    def get_db_status(self) -> Dict[str, Any]:
        """Verificar estado de la base de datos"""
        if not self.db_connection_string:
            return {
                "postgresql_available": False,
                "connection_status": "no_connection_string",
                "fallback_mode": "json_only"
            }
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Verificar tablas
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables
                        WHERE table_schema = 'public' 
                        AND table_name IN ('companies', 'company_config_versions', 'company_templates')
                    """)
                    tables = [row['table_name'] for row in cursor.fetchall()]
                    
                    # Contar registros
                    total_companies = 0
                    active_companies = 0
                    
                    if 'companies' in tables:
                        cursor.execute("SELECT COUNT(*) as count FROM companies")
                        total_companies = cursor.fetchone()['count']
                        
                        cursor.execute("SELECT COUNT(*) as count FROM companies WHERE is_active = true")
                        active_companies = cursor.fetchone()['count']
                    
                    self._db_status = "connected"
                    return {
                        "postgresql_available": True,
                        "connection_status": "connected",
                        "tables_exist": len(tables) >= 2,  # Mínimo companies y versions
                        "tables_found": tables,
                        "total_companies": total_companies,
                        "active_companies": active_companies,
                        "fallback_mode": "none"
                    }
        
        except Exception as e:
            logger.error(f"Database status check failed: {e}")
            self._db_status = f"error: {str(e)}"
            return {
                "postgresql_available": False,
                "connection_status": "error",
                "error": str(e),
                "fallback_mode": "json_required"
            }
    
    # ========== MÉTODOS PRIVADOS ==========
    
    def _get_config_from_postgresql(self, company_id: str) -> Optional[EnterpriseCompanyConfig]:
        """Obtener configuración desde PostgreSQL"""
        if not self.db_connection_string:
            return None
        
        try:
            with psycopg2.connect(self.db_connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM companies WHERE company_id = %s AND is_active = true",
                        (company_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return self._row_to_config(row)
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting config from PostgreSQL for {company_id}: {e}")
            return None
    
    def _row_to_config(self, row: Dict[str, Any]) -> EnterpriseCompanyConfig:
        """Convertir fila de DB a EnterpriseCompanyConfig"""
        # Parsear JSON fields
        treatment_durations = None
        if row.get('treatment_durations'):
            if isinstance(row['treatment_durations'], str):
                treatment_durations = json.loads(row['treatment_durations'])
            else:
                treatment_durations = row['treatment_durations']
        
        return EnterpriseCompanyConfig(
            company_id=row['company_id'],
            company_name=row['company_name'],
            business_type=row.get('business_type', 'general'),
            services=row['services'],
            redis_prefix=row['redis_prefix'],
            vectorstore_index=row['vectorstore_index'],
            sales_agent_name=row['sales_agent_name'],
            model_name=row.get('model_name', 'gpt-4o-mini'),
            max_tokens=row.get('max_tokens', 1500),
            temperature=float(row.get('temperature', 0.7)),
            max_context_messages=row.get('max_context_messages', 10),
            schedule_service_url=row.get('schedule_service_url', 'http://127.0.0.1:4040'),
            schedule_integration_type=row.get('schedule_integration_type', 'basic'),
            chatwoot_account_id=row.get('chatwoot_account_id'),
            treatment_durations=treatment_durations,
            schedule_keywords=row.get('schedule_keywords'),
            emergency_keywords=row.get('emergency_keywords'),
            sales_keywords=row.get('sales_keywords'),
            required_booking_fields=row.get('required_booking_fields'),
            timezone=row.get('timezone', 'America/Bogota'),
            language=row.get('language', 'es'),
            currency=row.get('currency', 'COP'),
            is_active=row.get('is_active', True),
            subscription_tier=row.get('subscription_tier', 'basic'),
            max_documents=row.get('max_documents', 1000),
            max_conversations=row.get('max_conversations', 10000),
            version=row.get('version', 1),
            created_by=row.get('created_by', 'admin'),
            modified_by=row.get('modified_by', 'admin'),
            notes=row.get('notes')
        )
    
    def _get_config_from_redis_cache(self, company_id: str) -> Optional[EnterpriseCompanyConfig]:
        """Obtener configuración desde cache Redis"""
        try:
            cache_key = f"company_config:{company_id}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                config_dict = json.loads(cached_data)
                return EnterpriseCompanyConfig(**config_dict)
            
            return None
            
        except Exception as e:
            logger.debug(f"Redis cache miss for {company_id}: {e}")
            return None
    
    def _cache_config(self, company_id: str, config: EnterpriseCompanyConfig):
        """Cachear configuración en Redis y memoria"""
        try:
            # Redis cache
            cache_key = f"company_config:{company_id}"
            config_dict = asdict(config)
            self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                json.dumps(config_dict, default=str)
            )
            
            # Memory cache
            self._memory_cache[company_id] = config
            self._cache_timestamp = datetime.now().timestamp()
            
        except Exception as e:
            logger.warning(f"Error caching config for {company_id}: {e}")
    
    def _invalidate_cache(self, company_id: str):
        """Invalidar cache para empresa específica"""
        try:
            # Redis
            cache_key = f"company_config:{company_id}"
            self.redis_client.delete(cache_key)
            
            # Memory
            if company_id in self._memory_cache:
                del self._memory_cache[company_id]
                
        except Exception as e:
            logger.warning(f"Error invalidating cache for {company_id}: {e}")
    
    def _is_memory_cache_valid(self) -> bool:
        """Verificar si cache en memoria es válido"""
        return (datetime.now().timestamp() - self._cache_timestamp) < self.cache_ttl
    
    def _get_config_from_json_fallback(self, company_id: str) -> Optional[EnterpriseCompanyConfig]:
        """Fallback a archivo JSON"""
        try:
            json_file = "companies_config.json"
            if not os.path.exists(json_file):
                return None
            
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            company_data = json_data.get(company_id)
            if not company_data:
                return None
            
            return EnterpriseCompanyConfig(
                company_id=company_id,
                company_name=company_data.get('company_name', company_id),
                services=company_data.get('services', ''),
                redis_prefix=company_data.get('redis_prefix', f"{company_id}:"),
                vectorstore_index=company_data.get('vectorstore_index', f"{company_id}_documents"),
                sales_agent_name=company_data.get('sales_agent_name', f"Asistente de {company_data.get('company_name', company_id)}"),
                model_name=company_data.get('model_name', 'gpt-4o-mini'),
                max_tokens=company_data.get('max_tokens', 1500),
                temperature=company_data.get('temperature', 0.7),
                schedule_service_url=company_data.get('schedule_service_url', 'http://127.0.0.1:4040'),
                notes="Loaded from JSON fallback"
            )
            
        except Exception as e:
            logger.error(f"Error loading JSON config for {company_id}: {e}")
            return None
    
    def _list_companies_from_json(self) -> List[EnterpriseCompanyConfig]:
        """Listar empresas desde JSON como fallback"""
        companies = []
        try:
            json_file = "companies_config.json"
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                for company_id in json_data.keys():
                    config = self._get_config_from_json_fallback(company_id)
                    if config:
                        companies.append(config)
        
        except Exception as e:
            logger.error(f"Error listing companies from JSON: {e}")
        
        return companies
    
    def _create_default_config(self, company_id: str) -> EnterpriseCompanyConfig:
        """Crear configuración por defecto de emergencia"""
        return EnterpriseCompanyConfig(
            company_id=company_id,
            company_name=f"Empresa {company_id.title()}",
            services="servicios generales",
            notes="Default emergency configuration"
        )


# ========== INSTANCIA GLOBAL ==========
_enterprise_company_service: Optional[EnterpriseCompanyConfigService] = None

def get_enterprise_company_service() -> EnterpriseCompanyConfigService:
    """Obtener instancia global del servicio enterprise"""
    global _enterprise_company_service
    
    if _enterprise_company_service is None:
        _enterprise_company_service = EnterpriseCompanyConfigService()
    
    return _enterprise_company_service
