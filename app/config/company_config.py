# app/config/company_config.py - VERSIÓN CORREGIDA PARA SOLUCIONAR ATTRIBUTE ERROR

import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CompanyConfig:
    """Configuración de empresa con métodos para acceso de atributos"""
    company_id: str
    company_name: str
    description: str
    services: List[str] = field(default_factory=list)
    # URLs y configuraciones
    chatwoot_base_url: str = ""
    chatwoot_access_token: str = ""
    schedule_service_url: str = ""
    # Configuración de agentes
    agent_config: Dict[str, Any] = field(default_factory=dict)
    # Elasticsearch/vectorstore
    elasticsearch_index: str = ""
    vectorstore_collection_name: str = ""
    # Metadatos adicionales
    industry: str = ""
    location: str = ""
    contact_info: Dict[str, Any] = field(default_factory=dict)
    business_hours: Dict[str, Any] = field(default_factory=dict)
    # Configuración extendida
    extended_config: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Método get para compatibilidad con dict - SOLUCIONA EL ERROR"""
        return getattr(self, key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Soporte para acceso tipo diccionario"""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Key '{key}' not found in CompanyConfig")
    
    def __contains__(self, key: str) -> bool:
        """Soporte para 'in' operator"""
        return hasattr(self, key)
    
    def keys(self):
        """Retornar keys como dict"""
        return [field.name for field in self.__dataclass_fields__]
    
    def items(self):
        """Retornar items como dict"""
        return [(field.name, getattr(self, field.name)) for field in self.__dataclass_fields__]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            field.name: getattr(self, field.name) 
            for field in self.__dataclass_fields__
        }

class CompanyManager:
    """Gestor de configuraciones multi-tenant con manejo robusto de errores"""
    
    def __init__(self):
        self.companies: Dict[str, CompanyConfig] = {}
        self.config_file_path = "companies_config.json"
        self.extended_config_file_path = "extended_companies_config.json"
        self.extended_config_enabled = os.getenv('EXTENDED_CONFIG_ENABLED', 'false').lower() == 'true'
        
        # Cargar configuraciones
        self._load_companies_config()
        if self.extended_config_enabled:
            self._load_extended_config()
        
        logger.info(f"CompanyManager initialized with {len(self.companies)} companies")
    
    def _load_companies_config(self):
        """Cargar configuración básica de empresas"""
        try:
            if not os.path.exists(self.config_file_path):
                logger.warning(f"Companies config file not found: {self.config_file_path}")
                self._create_default_config()
                return
            
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            companies_data = config_data.get('companies', {})
            loaded_companies = []
            
            for company_id, company_data in companies_data.items():
                try:
                    # Validar datos requeridos
                    required_fields = ['company_name', 'description']
                    for field in required_fields:
                        if field not in company_data:
                            company_data[field] = f"Default {field} for {company_id}"
                    
                    # Crear configuración de empresa
                    company_config = CompanyConfig(
                        company_id=company_id,
                        company_name=company_data.get('company_name', company_id),
                        description=company_data.get('description', ''),
                        services=company_data.get('services', []),
                        chatwoot_base_url=company_data.get('chatwoot_base_url', ''),
                        chatwoot_access_token=company_data.get('chatwoot_access_token', ''),
                        schedule_service_url=company_data.get('schedule_service_url', 'http://127.0.0.1:4040'),
                        agent_config=company_data.get('agent_config', {}),
                        elasticsearch_index=company_data.get('elasticsearch_index', f"{company_id}_documents"),
                        vectorstore_collection_name=company_data.get('vectorstore_collection_name', f"{company_id}_vectors"),
                        industry=company_data.get('industry', ''),
                        location=company_data.get('location', ''),
                        contact_info=company_data.get('contact_info', {}),
                        business_hours=company_data.get('business_hours', {}),
                        extended_config=company_data.get('extended_config', {})
                    )
                    
                    self.companies[company_id] = company_config
                    loaded_companies.append(company_id)
                    
                except Exception as e:
                    logger.error(f"Error loading company {company_id}: {e}")
                    continue
            
            logger.info(f"Loaded company configs from file: {self.config_file_path}")
            logger.info(f"Loaded configurations for companies: {loaded_companies}")
            
        except Exception as e:
            logger.error(f"Error loading companies config: {e}")
            self._create_default_config()
    
    def _load_extended_config(self):
        """Cargar configuración extendida (Google Calendar, etc.)"""
        try:
            if not os.path.exists(self.extended_config_file_path):
                logger.info(f"Extended config file not found: {self.extended_config_file_path}")
                return
            
            with open(self.extended_config_file_path, 'r', encoding='utf-8') as f:
                extended_data = json.load(f)
            
            extended_count = 0
            for company_id, extended_config in extended_data.items():
                if company_id in self.companies:
                    # Merge extended config
                    self.companies[company_id].extended_config.update(extended_config)
                    extended_count += 1
                else:
                    logger.warning(f"Extended config found for non-existent company: {company_id}")
            
            logger.info(f"Loaded extended configs for {extended_count} companies")
            
        except Exception as e:
            logger.error(f"Error loading extended config: {e}")
    
    def _create_default_config(self):
        """Crear configuración por defecto si no existe"""
        default_companies = {
            "benova": {
                "company_name": "Benova",
                "description": "Centro estético avanzado",
                "services": ["Tratamientos faciales", "Rejuvenecimiento", "Hidratación profunda"],
                "industry": "belleza",
                "location": "Medellín, Colombia"
            },
            "spa_wellness": {
                "company_name": "Wellness Spa & Relax",
                "description": "Spa integral de bienestar",
                "services": ["Masajes terapéuticos", "Relajación", "Aromaterapia"],
                "industry": "bienestar",
                "location": "Medellín, Colombia"
            },
            "medispa": {
                "company_name": "MediSpa Elite",
                "description": "Medicina estética especializada",
                "services": ["Botox", "Rellenos", "Tratamientos láser"],
                "industry": "medicina estética",
                "location": "Medellín, Colombia"
            },
            "clinica_dental": {
                "company_name": "Clínica Dental Sonrisa",
                "description": "Clínica dental integral",
                "services": ["Limpieza dental", "Ortodoncia", "Implantes"],
                "industry": "odontología",
                "location": "Medellín, Colombia"
            }
        }
        
        for company_id, company_data in default_companies.items():
            try:
                company_config = CompanyConfig(
                    company_id=company_id,
                    company_name=company_data['company_name'],
                    description=company_data['description'],
                    services=company_data.get('services', []),
                    industry=company_data.get('industry', ''),
                    location=company_data.get('location', ''),
                    schedule_service_url=f"http://127.0.0.1:{4040 + len(self.companies)}",
                    elasticsearch_index=f"{company_id}_documents",
                    vectorstore_collection_name=f"{company_id}_vectors"
                )
                self.companies[company_id] = company_config
                
            except Exception as e:
                logger.error(f"Error creating default config for {company_id}: {e}")
        
        logger.info(f"Created default configurations for {len(self.companies)} companies")
    
    def get_company_config(self, company_id: str) -> Optional[CompanyConfig]:
        """Obtener configuración de empresa específica"""
        return self.companies.get(company_id)
    
    def get_all_companies(self) -> Dict[str, CompanyConfig]:
        """Obtener todas las configuraciones de empresas"""
        return self.companies.copy()
    
    def validate_company_id(self, company_id: str) -> bool:
        """Validar que el company_id existe"""
        return company_id in self.companies
    
    def get_company_list(self) -> List[Dict[str, Any]]:
        """Obtener lista de empresas para API"""
        companies_list = []
        for company_id, config in self.companies.items():
            companies_list.append({
                "company_id": company_id,
                "company_name": config.company_name,
                "description": config.description,
                "services_count": len(config.services),
                "industry": config.industry,
                "location": config.location,
                "has_extended_config": bool(config.extended_config)
            })
        return companies_list
    
    def reload_config(self) -> bool:
        """Recargar configuraciones desde archivos"""
        try:
            old_companies = list(self.companies.keys())
            self.companies.clear()
            
            self._load_companies_config()
            if self.extended_config_enabled:
                self._load_extended_config()
            
            new_companies = list(self.companies.keys())
            logger.info(f"Config reloaded. Old: {old_companies}, New: {new_companies}")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading config: {e}")
            return False
    
    def update_company_config(self, company_id: str, updates: Dict[str, Any]) -> bool:
        """Actualizar configuración de empresa específica"""
        try:
            if company_id not in self.companies:
                logger.error(f"Company {company_id} not found for update")
                return False
            
            config = self.companies[company_id]
            
            # Actualizar campos permitidos
            allowed_updates = [
                'company_name', 'description', 'services', 'industry', 
                'location', 'contact_info', 'business_hours', 'chatwoot_base_url',
                'chatwoot_access_token', 'schedule_service_url'
            ]
            
            for key, value in updates.items():
                if key in allowed_updates and hasattr(config, key):
                    setattr(config, key, value)
                    logger.info(f"Updated {company_id}.{key}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating company config for {company_id}: {e}")
            return False
    
    def get_company_services(self, company_id: str) -> List[str]:
        """Obtener servicios de una empresa específica"""
        config = self.get_company_config(company_id)
        return config.services if config else []
    
    def get_company_schedule_url(self, company_id: str) -> str:
        """Obtener URL del servicio de agendamiento para una empresa"""
        config = self.get_company_config(company_id)
        return config.schedule_service_url if config else "http://127.0.0.1:4040"
    
    def get_vectorstore_config(self, company_id: str) -> Dict[str, str]:
        """Obtener configuración de vectorstore para una empresa"""
        config = self.get_company_config(company_id)
        if not config:
            return {
                "index": f"{company_id}_documents",
                "collection": f"{company_id}_vectors"
            }
        
        return {
            "index": config.elasticsearch_index or f"{company_id}_documents",
            "collection": config.vectorstore_collection_name or f"{company_id}_vectors"
        }

# Instancia global del manager
_company_manager = None

def get_company_manager() -> CompanyManager:
    """Obtener instancia global del CompanyManager"""
    global _company_manager
    if _company_manager is None:
        _company_manager = CompanyManager()
    return _company_manager

def reload_companies_config() -> bool:
    """Función de utilidad para recargar configuraciones"""
    return get_company_manager().reload_config()

# Funciones de utilidad para compatibilidad
def get_company_config(company_id: str) -> Optional[CompanyConfig]:
    """Función de utilidad para obtener configuración de empresa"""
    return get_company_manager().get_company_config(company_id)

def validate_company_id(company_id: str) -> bool:
    """Función de utilidad para validar company_id"""
    return get_company_manager().validate_company_id(company_id)

def get_all_companies() -> Dict[str, CompanyConfig]:
    """Función de utilidad para obtener todas las empresas"""
    return get_company_manager().get_all_companies()

# ============================================================================
# FUNCIONES DE WEBHOOK MULTI-TENANT (REQUERIDAS POR webhook.py)
# ============================================================================

def extract_company_id_from_webhook(data: Dict[str, Any]) -> str:
    """Extraer company_id del payload de webhook de Chatwoot"""
    try:
        # Método 1: Desde conversation.meta
        conversation = data.get("conversation", {})
        meta = conversation.get("meta", {})
        
        if "company_id" in meta:
            logger.debug(f"Company ID found in conversation meta: {meta['company_id']}")
            return meta["company_id"]
        
        # Método 2: Desde account_id (mapeo predefinido)
        account_id = conversation.get("account", {}).get("id") or conversation.get("account_id")
        
        if account_id:
            # Mapeo de account_id a company_id (configurar según tu setup de Chatwoot)
            account_mapping = {
                "7": "benova",      # Benova Chatwoot account
                "8": "medispa",     # MediSpa account
                "9": "spa_wellness", # Spa Wellness account
                "10": "clinica_dental" # Clínica Dental account
            }
            
            company_id = account_mapping.get(str(account_id))
            if company_id:
                logger.debug(f"Company ID mapped from account_id {account_id}: {company_id}")
                return company_id
        
        # Método 3: Desde inbox personalizado (si está configurado)
        inbox = conversation.get("inbox", {})
        inbox_name = inbox.get("name", "").lower()
        
        # Mapeo basado en nombres de inbox
        if "benova" in inbox_name:
            return "benova"
        elif "medispa" in inbox_name:
            return "medispa"
        elif "wellness" in inbox_name or "spa" in inbox_name:
            return "spa_wellness"
        elif "dental" in inbox_name or "clinica" in inbox_name:
            return "clinica_dental"
        
        # Método 4: Desde URL del webhook (si incluye company_id)
        # Este método requeriría que el webhook URL tenga formato: /webhook/chatwoot/{company_id}
        from flask import request
        if hasattr(request, 'view_args') and request.view_args:
            webhook_company_id = request.view_args.get('company_id')
            if webhook_company_id:
                logger.debug(f"Company ID from webhook URL: {webhook_company_id}")
                return webhook_company_id
        
        # Método 5: Por defecto basado en configuración de entorno
        default_company = os.getenv('DEFAULT_COMPANY_ID', 'benova')
        logger.warning(f"Could not extract company_id from webhook data, using default: {default_company}")
        return default_company
        
    except Exception as e:
        logger.error(f"Error extracting company_id from webhook: {e}")
        # Fallback seguro
        return os.getenv('DEFAULT_COMPANY_ID', 'benova')

def validate_company_context(company_id: str) -> bool:
    """Validar que el contexto de empresa sea válido antes de procesar webhook"""
    try:
        if not company_id or not isinstance(company_id, str):
            logger.error("Company ID is empty or not a string")
            return False
        
        # Validar que la empresa exista en la configuración
        manager = get_company_manager()
        
        if not manager.validate_company_id(company_id):
            available_companies = list(manager.get_all_companies().keys())
            logger.error(f"Invalid company_id: {company_id}. Available companies: {available_companies}")
            return False
        
        # Verificación adicional: asegurar que la empresa tenga configuración mínima
        company_config = manager.get_company_config(company_id)
        if not company_config:
            logger.error(f"No configuration found for company_id: {company_id}")
            return False
        
        # Verificar que tenga nombre de empresa (configuración mínima válida)
        if not hasattr(company_config, 'company_name') or not company_config.company_name:
            logger.error(f"Company {company_id} has invalid configuration (missing company_name)")
            return False
        
        logger.debug(f"Company context validated for: {company_id} ({company_config.company_name})")
        return True
        
    except Exception as e:
        logger.error(f"Error validating company context for {company_id}: {e}")
        return False

# ============================================================================
# FUNCIONES DE UTILIDAD PARA SERVICIOS INTEGRADOS
# ============================================================================

def get_company_chatwoot_config(company_id: str) -> Dict[str, str]:
    """Obtener configuración de Chatwoot para una empresa específica"""
    try:
        company_config = get_company_config(company_id)
        if not company_config:
            return {}
        
        return {
            "base_url": getattr(company_config, 'chatwoot_base_url', ''),
            "access_token": getattr(company_config, 'chatwoot_access_token', ''),
            "company_id": company_id,
            "company_name": getattr(company_config, 'company_name', company_id)
        }
    except Exception as e:
        logger.error(f"Error getting Chatwoot config for {company_id}: {e}")
        return {}

def get_company_vectorstore_config(company_id: str) -> Dict[str, str]:
    """Obtener configuración de vectorstore para una empresa específica"""
    try:
        company_config = get_company_config(company_id)
        if not company_config:
            return {
                "index": f"{company_id}_documents",
                "collection": f"{company_id}_vectors"
            }
        
        return {
            "index": getattr(company_config, 'elasticsearch_index', f"{company_id}_documents"),
            "collection": getattr(company_config, 'vectorstore_collection_name', f"{company_id}_vectors"),
            "company_id": company_id,
            "company_name": getattr(company_config, 'company_name', company_id)
        }
    except Exception as e:
        logger.error(f"Error getting vectorstore config for {company_id}: {e}")
        return {
            "index": f"{company_id}_documents",
            "collection": f"{company_id}_vectors"
        }

def create_calendar_integration_service(company_id: str):
    """Crear servicio de integración de calendario para una empresa"""
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
