# app/config/company_config.py - MODIFICADO PARA POSTGRESQL-FIRST
"""
Gestión de configuración de empresas multi-tenant
MODIFICADO: PostgreSQL como fuente principal, JSON como fallback
MANTIENE: Misma interfaz pública, mismo comportamiento, mismos nombres de funciones
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CompanyConfig:
    """Configuración básica de empresa - MANTIENE ESTRUCTURA ORIGINAL"""
    company_id: str
    company_name: str
    redis_prefix: str
    vectorstore_index: str
    schedule_service_url: str
    sales_agent_name: str
    services: str
    model_name: str = "gpt-4o-mini"
    max_tokens: int = 1500
    temperature: float = 0.7
    max_context_messages: int = 10
    treatment_durations: Dict[str, int] = None
    schedule_keywords: List[str] = None
    emergency_keywords: List[str] = None
    sales_keywords: List[str] = None
    business_type: str = "general"

    def __post_init__(self):
        if self.treatment_durations is None:
            self.treatment_durations = {}
        if self.schedule_keywords is None:
            self.schedule_keywords = []
        if self.emergency_keywords is None:
            self.emergency_keywords = []
        if self.sales_keywords is None:
            self.sales_keywords = []

class CompanyConfigManager:
    """
    Gestor de configuración de empresas - MODIFICADO PARA POSTGRESQL-FIRST
    
    CAMBIOS INTERNOS:
    - PostgreSQL como fuente principal
    - JSON como fallback únicamente
    - Migración automática JSON → PostgreSQL
    
    MANTIENE:
    - Misma interfaz pública
    - Mismos nombres de funciones  
    - Mismos tipos de retorno
    - Compatibilidad total con código existente
    """
    
    def __init__(self):
        self._configs: Dict[str, CompanyConfig] = {}
        self._extended_configs: Dict[str, Any] = {}
        
        # ✅ NUEVO: Integración con servicio enterprise PostgreSQL
        self._enterprise_service = None
        self._postgresql_available = False
        
        # Cargar configuraciones (ahora PostgreSQL-first)
        self._load_company_configs()
        self._load_extended_configs()
        
        logger.info(f"CompanyConfigManager initialized with {len(self._configs)} companies (PostgreSQL-first mode)")
    
    def _init_enterprise_service(self):
        """Inicializar servicio enterprise si no está disponible"""
        if self._enterprise_service is None:
            try:
                from app.services.company_config_service import get_enterprise_company_service
                self._enterprise_service = get_enterprise_company_service()
                
                # Test de conexión
                db_status = self._enterprise_service.get_db_status()
                self._postgresql_available = db_status.get('postgresql_available', False)
                
                if self._postgresql_available:
                    logger.info("✅ PostgreSQL service available - using as primary source")
                else:
                    logger.warning("⚠️ PostgreSQL service not available - will use JSON fallback")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize enterprise service: {e}")
                self._postgresql_available = False
    
    def _load_company_configs(self):
        """
        Cargar configuraciones - MODIFICADO PARA POSTGRESQL-FIRST
        Orden: PostgreSQL > JSON > Defaults
        """
        try:
            self._init_enterprise_service()
            
            # ✅ PASO 1: CARGAR DESDE POSTGRESQL (FUENTE PRINCIPAL)
            if self._postgresql_available:
                companies_loaded = self._load_from_postgresql()
                if companies_loaded > 0:
                    logger.info(f"✅ Loaded {companies_loaded} companies from PostgreSQL")
                    
                    # ✅ PASO 2: SINCRONIZAR JSON SI HAY DIFERENCIAS
                    self._sync_json_with_postgresql()
                    return
                else:
                    logger.warning("⚠️ No companies found in PostgreSQL, checking JSON")
            
            # ✅ PASO 3: FALLBACK A JSON (solo si PostgreSQL falla)
            companies_loaded = self._load_from_json()
            if companies_loaded > 0:
                logger.info(f"✅ Loaded {companies_loaded} companies from JSON (fallback mode)")
                
                # ✅ PASO 4: MIGRAR JSON → POSTGRESQL si es posible
                if self._postgresql_available:
                    self._migrate_json_to_postgresql()
                return
            
            # ✅ PASO 5: CONFIGURACIÓN DE EMERGENCIA
            logger.warning("⚠️ No companies found, loading emergency defaults")
            self._load_emergency_config()
            
        except Exception as e:
            logger.error(f"❌ Error loading company configs: {e}")
            self._load_emergency_config()
    
    def _load_from_postgresql(self) -> int:
        """Cargar empresas desde PostgreSQL"""
        try:
            if not self._enterprise_service:
                return 0
                
            pg_companies = self._enterprise_service.list_companies()
            loaded_count = 0
            
            for pg_company in pg_companies:
                # Convertir EnterpriseCompanyConfig → CompanyConfig
                legacy_config = pg_company.to_legacy_config()
                self._configs[pg_company.company_id] = legacy_config
                loaded_count += 1
            
            return loaded_count
            
        except Exception as e:
            logger.error(f"❌ Error loading from PostgreSQL: {e}")
            return 0
    
    def _load_from_json(self) -> int:
        """Cargar empresas desde JSON (fallback)"""
        try:
            config_file = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
            
            if not os.path.exists(config_file):
                logger.warning(f"JSON config file not found: {config_file}")
                return 0
            
            with open(config_file, 'r', encoding='utf-8') as f:
                configs_data = json.load(f)
            
            loaded_count = 0
            for company_id, config_data in configs_data.items():
                try:
                    self._configs[company_id] = CompanyConfig(
                        company_id=company_id,
                        **config_data
                    )
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"❌ Error loading company {company_id} from JSON: {e}")
            
            return loaded_count
            
        except Exception as e:
            logger.error(f"❌ Error reading JSON config: {e}")
            return 0
    
    def _sync_json_with_postgresql(self):
        """Sincronizar JSON con PostgreSQL para mantener compatibilidad"""
        try:
            config_file = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
            
            # Crear JSON actualizado desde PostgreSQL
            json_data = {}
            for company_id, config in self._configs.items():
                json_data[company_id] = {
                    "company_name": config.company_name,
                    "business_type": config.business_type,
                    "redis_prefix": config.redis_prefix,
                    "vectorstore_index": config.vectorstore_index,
                    "schedule_service_url": config.schedule_service_url,
                    "sales_agent_name": config.sales_agent_name,
                    "services": config.services,
                    "model_name": config.model_name,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "treatment_durations": config.treatment_durations or {},
                    "_source": "postgresql_sync",
                    "_synced_at": "auto"
                }
            
            # Escribir JSON actualizado
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ JSON config synchronized with PostgreSQL ({len(json_data)} companies)")
            
        except Exception as e:
            logger.warning(f"⚠️ Could not sync JSON with PostgreSQL: {e}")
    
    def _migrate_json_to_postgresql(self):
        """Migrar empresas desde JSON hacia PostgreSQL"""
        try:
            if not self._enterprise_service or not self._postgresql_available:
                return
            
            config_file = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
            
            if not os.path.exists(config_file):
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            migrated_count = 0
            for company_id, company_data in json_data.items():
                try:
                    # Verificar si ya existe en PostgreSQL
                    existing = self._enterprise_service.get_company_config(company_id, use_cache=False)
                    if existing and existing.notes != "Default emergency configuration":
                        continue  # Ya existe, skip
                    
                    # Importar EnterpriseCompanyConfig para crear la migración
                    from app.services.company_config_service import EnterpriseCompanyConfig
                    
                    # Crear configuración enterprise desde JSON
                    enterprise_config = EnterpriseCompanyConfig(
                        company_id=company_id,
                        company_name=company_data.get('company_name', company_id),
                        business_type=company_data.get('business_type', 'general'),
                        services=company_data.get('services', ''),
                        redis_prefix=company_data.get('redis_prefix', f"{company_id}:"),
                        vectorstore_index=company_data.get('vectorstore_index', f"{company_id}_documents"),
                        sales_agent_name=company_data.get('sales_agent_name', f"Asistente de {company_data.get('company_name', company_id)}"),
                        schedule_service_url=company_data.get('schedule_service_url', 'http://127.0.0.1:4040'),
                        model_name=company_data.get('model_name', 'gpt-4o-mini'),
                        max_tokens=company_data.get('max_tokens', 1500),
                        temperature=company_data.get('temperature', 0.7),
                        treatment_durations=company_data.get('treatment_durations'),
                        created_by="json_migration",
                        modified_by="json_migration",
                        notes=f"Auto-migrated from {config_file}"
                    )
                    
                    # Guardar en PostgreSQL
                    success = self._enterprise_service.create_company(enterprise_config, created_by="json_migration")
                    
                    if success:
                        migrated_count += 1
                        logger.info(f"✅ Migrated {company_id} from JSON to PostgreSQL")
                        
                except Exception as e:
                    logger.error(f"❌ Error migrating {company_id}: {e}")
            
            if migrated_count > 0:
                logger.info(f"✅ Migration completed: {migrated_count} companies moved to PostgreSQL")
                # Recargar desde PostgreSQL después de migración
                self._configs.clear()
                self._load_from_postgresql()
            
        except Exception as e:
            logger.error(f"❌ Error during migration: {e}")
    
    def _load_emergency_config(self):
        """Cargar configuración mínima de emergencia - MANTIENE LÓGICA ORIGINAL"""
        default_config = CompanyConfig(
            company_id="benova",
            company_name="Benova",
            business_type="medicina_estetica",
            redis_prefix="benova:",
            vectorstore_index="benova_documents",
            schedule_service_url=os.getenv('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040'),
            sales_agent_name="María, asesora de Benova",
            services="medicina estética y tratamientos de belleza",
            treatment_durations={
                "limpieza facial": 60,
                "masaje": 60,
                "microagujas": 90,
                "botox": 30,
                "rellenos": 45,
                "peeling": 45,
                "radiofrecuencia": 60,
                "depilación": 30,
                "tratamiento general": 60
            }
        )
        
        self._configs["benova"] = default_config
        logger.warning("⚠️ Using emergency configuration with default Benova setup")
    
    def _load_extended_configs(self):
        """Cargar configuraciones extendidas - MANTIENE LÓGICA ORIGINAL"""
        try:
            # Verificar si está habilitada la configuración extendida
            extended_enabled = os.getenv('EXTENDED_CONFIG_ENABLED', 'false').lower() == 'true'
            if not extended_enabled:
                logger.info("Extended configuration disabled via environment variable")
                return
            
            extended_config_file = os.getenv('EXTENDED_CONFIG_FILE', 'extended_companies_config.json')
            
            if os.path.exists(extended_config_file):
                with open(extended_config_file, 'r', encoding='utf-8') as f:
                    extended_data = json.load(f)
                
                # Importar clases de configuración extendida dinámicamente
                try:
                    from .extended_company_config import (
                        ExtendedCompanyConfig, TreatmentConfig, AgendaConfig,
                        load_extended_company_configs
                    )
                    
                    # Cargar usando el loader específico
                    self._extended_configs = load_extended_company_configs(extended_config_file)
                    logger.info(f"Loaded extended configs for {len(self._extended_configs)} companies")
                    
                except ImportError as e:
                    logger.warning(f"Extended configuration classes not available: {e}")
                    # Fallback a configuración JSON simple
                    self._extended_configs = extended_data
                    logger.info(f"Loaded extended configs (simple JSON) for {len(extended_data)} companies")
            else:
                logger.info(f"Extended config file not found: {extended_config_file}")
                
        except Exception as e:
            logger.error(f"Error loading extended configs: {e}")
            self._extended_configs = {}
    
    # ========================================================================
    # MÉTODOS PÚBLICOS - MANTIENEN EXACTAMENTE LA MISMA INTERFAZ
    # ========================================================================
    
    def get_company_config(self, company_id: str) -> Optional[CompanyConfig]:
        """Obtener configuración de empresa - MANTIENE INTERFAZ ORIGINAL"""
        return self._configs.get(company_id)
    
    def get_extended_config(self, company_id: str) -> Optional[Any]:
        """Obtener configuración extendida - MANTIENE INTERFAZ ORIGINAL"""
        return self._extended_configs.get(company_id)
    
    def get_all_companies(self) -> Dict[str, CompanyConfig]:
        """Obtener todas las configuraciones básicas - MANTIENE INTERFAZ ORIGINAL"""
        return self._configs.copy()
    
    def get_all_extended_companies(self) -> Dict[str, Any]:
        """Obtener todas las configuraciones extendidas - MANTIENE INTERFAZ ORIGINAL"""
        return self._extended_configs.copy()
    
    def validate_company_id(self, company_id: str) -> bool:
        """Validar si existe la empresa - MANTIENE INTERFAZ ORIGINAL"""
        return company_id in self._configs
    
    def add_company_config(self, config: CompanyConfig):
        """
        Agregar nueva configuración - MODIFICADO PARA POSTGRESQL-FIRST
        Ahora también guarda en PostgreSQL si está disponible
        """
        self._configs[config.company_id] = config
        logger.info(f"Added company config for: {config.company_id}")
        
        # ✅ NUEVO: También guardar en PostgreSQL si está disponible
        if self._postgresql_available and self._enterprise_service:
            try:
                from app.services.company_config_service import EnterpriseCompanyConfig
                
                # Convertir CompanyConfig → EnterpriseCompanyConfig
                enterprise_config = EnterpriseCompanyConfig(
                    company_id=config.company_id,
                    company_name=config.company_name,
                    business_type=config.business_type,
                    services=config.services,
                    redis_prefix=config.redis_prefix,
                    vectorstore_index=config.vectorstore_index,
                    sales_agent_name=config.sales_agent_name,
                    schedule_service_url=config.schedule_service_url,
                    model_name=config.model_name,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    treatment_durations=config.treatment_durations,
                    created_by="company_manager",
                    modified_by="company_manager",
                    notes="Added via CompanyManager.add_company_config()"
                )
                
                # Verificar si ya existe
                existing = self._enterprise_service.get_company_config(config.company_id, use_cache=False)
                
                if not existing or existing.notes == "Default emergency configuration":
                    success = self._enterprise_service.create_company(enterprise_config, created_by="company_manager")
                    if success:
                        logger.info(f"✅ Company {config.company_id} also saved to PostgreSQL")
                else:
                    logger.info(f"⏭️ Company {config.company_id} already exists in PostgreSQL")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not save {config.company_id} to PostgreSQL: {e}")
    
    def update_company_config(self, company_id: str, **updates):
        """Actualizar configuración existente - MANTIENE INTERFAZ ORIGINAL"""
        if company_id in self._configs:
            config = self._configs[company_id]
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            logger.info(f"Updated company config for: {company_id}")
            
            # ✅ NUEVO: También actualizar en PostgreSQL si está disponible
            if self._postgresql_available and self._enterprise_service:
                try:
                    success = self._enterprise_service.update_company(company_id, updates, updated_by="company_manager")
                    if success:
                        logger.info(f"✅ Company {company_id} also updated in PostgreSQL")
                except Exception as e:
                    logger.warning(f"⚠️ Could not update {company_id} in PostgreSQL: {e}")
        else:
            logger.error(f"Cannot update non-existent company: {company_id}")
    
    def reload_configs(self):
        """Recargar todas las configuraciones - MANTIENE INTERFAZ ORIGINAL"""
        try:
            self._configs.clear()
            self._extended_configs.clear()
            
            # Reinicializar servicio enterprise
            self._enterprise_service = None
            self._postgresql_available = False
            
            # Recargar (PostgreSQL-first)
            self._load_company_configs()
            self._load_extended_configs()
            
            logger.info("✅ All configurations reloaded successfully (PostgreSQL-first)")
            return True
        except Exception as e:
            logger.error(f"❌ Error reloading configurations: {e}")
            return False
    
    # ========================================================================
    # MÉTODOS ESPECÍFICOS PARA COMPATIBILIDAD - MANTIENEN INTERFACES ORIGINALES
    # ========================================================================
    
    def get_schedule_integration_type(self, company_id: str) -> str:
        """Obtener tipo de integración de agendamiento - MANTIENE INTERFAZ ORIGINAL"""
        extended_config = self.get_extended_config(company_id)
        
        if extended_config:
            if hasattr(extended_config, 'integration_type'):
                return extended_config.integration_type
            elif isinstance(extended_config, dict):
                return extended_config.get('integration_type', 'basic')
        
        return 'basic'
    
    def get_treatment_duration(self, company_id: str, treatment_name: str) -> int:
        """Obtener duración de tratamiento - MANTIENE INTERFAZ ORIGINAL"""
        config = self.get_company_config(company_id)
        if config and config.treatment_durations:
            return config.treatment_durations.get(treatment_name, 60)
        return 60
    
    def get_required_booking_fields(self, company_id: str) -> list:
        """Obtener campos requeridos para reservar - MANTIENE INTERFAZ ORIGINAL"""
        extended_config = self.get_extended_config(company_id)
        
        if extended_config:
            if hasattr(extended_config, 'required_booking_fields'):
                return extended_config.required_booking_fields
            elif isinstance(extended_config, dict):
                return extended_config.get('required_booking_fields', [])
        
        return [
            "nombre completo",
            "número de cédula", 
            "fecha de nacimiento",
            "correo electrónico",
            "motivo"
        ]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema - MANTIENE INTERFAZ ORIGINAL + INFO POSTGRESQL"""
        return {
            "basic_configs_loaded": len(self._configs),
            "extended_configs_loaded": len(self._extended_configs),
            "companies_with_extended": list(self._extended_configs.keys()),
            "companies_basic_only": [
                company_id for company_id in self._configs.keys() 
                if company_id not in self._extended_configs
            ],
            "extended_config_enabled": bool(self._extended_configs),
            "integration_types": {
                company_id: self.get_schedule_integration_type(company_id)
                for company_id in self._configs.keys()
            },
            # ✅ NUEVA INFO: Estado PostgreSQL
            "postgresql_available": self._postgresql_available,
            "primary_source": "postgresql" if self._postgresql_available else "json_fallback",
            "enterprise_service_available": self._enterprise_service is not None
        }

# ========================================================================
# FUNCIONES GLOBALES - MANTIENEN EXACTAMENTE LAS MISMAS INTERFACES
# ========================================================================

# Instancia global del gestor - MANTIENE VARIABLE ORIGINAL
_company_manager: Optional[CompanyConfigManager] = None

def get_company_manager() -> CompanyConfigManager:
    """Obtener instancia global del gestor - MANTIENE INTERFAZ ORIGINAL"""
    global _company_manager
    
    if _company_manager is None:
        _company_manager = CompanyConfigManager()
    
    return _company_manager

def get_company_config(company_id: str) -> Optional[CompanyConfig]:
    """Función de conveniencia para obtener configuración básica - MANTIENE INTERFAZ ORIGINAL"""
    manager = get_company_manager()
    return manager.get_company_config(company_id)

def get_extended_company_config(company_id: str) -> Optional[Any]:
    """Función de conveniencia para obtener configuración extendida - MANTIENE INTERFAZ ORIGINAL"""
    manager = get_company_manager()
    return manager.get_extended_config(company_id)

def extract_company_id_from_webhook(data: Dict[str, Any]) -> str:
    """Extraer company_id del payload de webhook - MANTIENE INTERFAZ ORIGINAL"""
    try:
        # Método 1: Desde conversation.meta
        conversation = data.get("conversation", {})
        meta = conversation.get("meta", {})
        
        if "company_id" in meta:
            return meta["company_id"]
        
        # Método 2: Desde account_id (mapeo)
        account_id = data.get("account", {}).get("id") or conversation.get("account_id")
        
        if account_id:
            account_mapping = {
                "7": "benova",
                "8": "medispa", 
                "9": "dental_clinic",
                "10": "spa_wellness"
            }
            
            mapped_company = account_mapping.get(str(account_id))
            if mapped_company:
                logger.info(f"Mapped account_id {account_id} to company {mapped_company}")
                return mapped_company
        
        # Método 3: Empresa por defecto
        default_company = os.getenv('DEFAULT_COMPANY_ID', 'benova')
        logger.info(f"Using default company: {default_company}")
        return default_company
        
    except Exception as e:
        logger.error(f"Error extracting company_id from webhook: {e}")
        return os.getenv('DEFAULT_COMPANY_ID', 'benova')


def validate_company_context(company_id: str) -> bool:
    """Validar contexto de empresa antes de procesar - MANTIENE INTERFAZ ORIGINAL"""
    try:
        manager = get_company_manager()
        
        if not manager.validate_company_id(company_id):
            logger.error(f"Invalid company_id: {company_id}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating company context for {company_id}: {e}")
        return False

def create_calendar_integration_service(company_id: str):
    """Crear servicio de integración de calendario - MANTIENE INTERFAZ ORIGINAL"""
    try:
        # Importar dinámicamente para evitar dependencias circulares
        from app.services.calendar_integration_service import create_calendar_service
        
        manager = get_company_manager()
        extended_config = manager.get_extended_config(company_id)
        
        if extended_config:
            return create_calendar_service(extended_config)
        else:
            logger.warning(f"No extended config found for {company_id}, calendar integration not available")
            return None
            
    except ImportError:
        logger.warning("Calendar integration service not available")
        return None
    except Exception as e:
        logger.error(f"Error creating calendar service for {company_id}: {e}")
        return None
