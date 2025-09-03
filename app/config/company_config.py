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
