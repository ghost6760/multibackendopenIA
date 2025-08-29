import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CompanyConfig:
    """Configuración específica para cada empresa"""
    company_id: str
    company_name: str
    redis_prefix: str
    vectorstore_index: str
    schedule_service_url: str
    services: str
    sales_agent_name: str
    support_agent_name: str
    emergency_agent_name: str
    schedule_agent_name: str
    industry_type: str
    working_hours: str
    contact_info: Dict[str, str]
    business_rules: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompanyConfig':
        """Crear configuración desde diccionario"""
        return cls(
            company_id=data.get('company_id', ''),
            company_name=data.get('company_name', ''),
            redis_prefix=data.get('redis_prefix', f"{data.get('company_id', 'default')}:"),
            vectorstore_index=data.get('vectorstore_index', f"{data.get('company_id', 'default')}_documents"),
            schedule_service_url=data.get('schedule_service_url', 'http://127.0.0.1:4040'),
            services=data.get('services', 'servicios profesionales'),
            sales_agent_name=data.get('sales_agent_name', 'María'),
            support_agent_name=data.get('support_agent_name', 'María'),
            emergency_agent_name=data.get('emergency_agent_name', 'María'),
            schedule_agent_name=data.get('schedule_agent_name', 'María'),
            industry_type=data.get('industry_type', 'general'),
            working_hours=data.get('working_hours', 'Lunes a Viernes 8:00 AM - 6:00 PM'),
            contact_info=data.get('contact_info', {}),
            business_rules=data.get('business_rules', {})
        )

class CompanyConfigManager:
    """Gestor de configuraciones de empresas"""
    
    def __init__(self):
        self._companies_config = self._load_companies_config()
        self._default_config = self._load_default_config()
    
    def _load_companies_config(self) -> Dict[str, CompanyConfig]:
        """Cargar configuraciones de empresas desde archivo o variables de entorno"""
        companies = {}
        
        # Intentar cargar desde archivo JSON
        config_file = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                for company_id, company_data in config_data.items():
                    companies[company_id] = CompanyConfig.from_dict({
                        'company_id': company_id,
                        **company_data
                    })
                    
                logger.info(f"Loaded {len(companies)} company configurations from file")
                return companies
                
            except Exception as e:
                logger.error(f"Error loading companies config from file: {e}")
        
        # Cargar configuraciones por defecto si no hay archivo
        companies = self._load_default_companies()
        logger.info(f"Using default company configurations: {len(companies)} companies")
        return companies
    
    def _load_default_companies(self) -> Dict[str, CompanyConfig]:
        """Configuraciones por defecto para empresas conocidas"""
        default_companies = {
            "benova": {
                "company_name": "Benova",
                "redis_prefix": "benova:",
                "vectorstore_index": "benova_documents",
                "schedule_service_url": os.getenv('BENOVA_SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040'),
                "services": "tratamientos estéticos y bienestar",
                "sales_agent_name": "María",
                "support_agent_name": "María",
                "emergency_agent_name": "María",
                "schedule_agent_name": "María",
                "industry_type": "estética",
                "working_hours": "Lunes a Viernes 8:00 AM - 6:00 PM, Sábados 8:00 AM - 4:00 PM",
                "contact_info": {
                    "phone": "+57 300 123 4567",
                    "email": "info@benova.com",
                    "address": "Medellín, Colombia"
                },
                "business_rules": {
                    "treatment_durations": {
                        "limpieza facial": 60,
                        "masaje": 60,
                        "microagujas": 90,
                        "botox": 30,
                        "rellenos": 45,
                        "peeling": 45,
                        "radiofrecuencia": 60,
                        "depilación": 30,
                        "tratamiento general": 60
                    },
                    "schedule_keywords": [
                        "agendar", "reservar", "programar", "cita", "appointment",
                        "agenda", "disponibilidad", "horario", "fecha", "hora",
                        "procede", "proceder", "confirmar cita"
                    ],
                    "emergency_keywords": [
                        "dolor intenso", "sangrado", "emergencia", 
                        "reacción alérgica", "inflamación severa"
                    ],
                    "sales_keywords": [
                        "precio", "costo", "inversión", "promoción",
                        "tratamiento", "procedimiento", "beneficio"
                    ]
                }
            },
            "example_company": {
                "company_name": "Empresa Ejemplo",
                "redis_prefix": "example:",
                "vectorstore_index": "example_documents",
                "schedule_service_url": os.getenv('EXAMPLE_SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4041'),
                "services": "servicios profesionales",
                "sales_agent_name": "Ana",
                "support_agent_name": "Carlos",
                "emergency_agent_name": "Dr. López",
                "schedule_agent_name": "Patricia",
                "industry_type": "general",
                "working_hours": "Lunes a Viernes 9:00 AM - 5:00 PM",
                "contact_info": {
                    "phone": "+57 300 987 6543",
                    "email": "contacto@ejemplo.com",
                    "website": "https://ejemplo.com"
                },
                "business_rules": {
                    "service_durations": {
                        "consulta": 30,
                        "servicio_basico": 45,
                        "servicio_premium": 60,
                        "servicio_general": 45
                    },
                    "schedule_keywords": [
                        "agendar", "reservar", "programar", "cita",
                        "agenda", "disponibilidad", "horario"
                    ],
                    "emergency_keywords": [
                        "urgente", "emergencia", "problema grave"
                    ],
                    "sales_keywords": [
                        "precio", "costo", "información", "servicio"
                    ]
                }
            }
        }
        
        companies = {}
        for company_id, company_data in default_companies.items():
            companies[company_id] = CompanyConfig.from_dict({
                'company_id': company_id,
                **company_data
            })
        
        return companies
    
    def _load_default_config(self) -> CompanyConfig:
        """Configuración por defecto para empresas no encontradas"""
        return CompanyConfig.from_dict({
            'company_id': 'default',
            'company_name': 'Empresa',
            'redis_prefix': 'default:',
            'vectorstore_index': 'default_documents',
            'schedule_service_url': 'http://127.0.0.1:4040',
            'services': 'servicios profesionales',
            'sales_agent_name': 'Agente de Ventas',
            'support_agent_name': 'Agente de Soporte',
            'emergency_agent_name': 'Agente de Emergencia',
            'schedule_agent_name': 'Agente de Agenda',
            'industry_type': 'general',
            'working_hours': 'Lunes a Viernes 9:00 AM - 5:00 PM',
            'contact_info': {},
            'business_rules': {}
        })
    
    def get_company_config(self, company_id: str) -> CompanyConfig:
        """Obtener configuración de empresa por ID"""
        if not company_id:
            logger.warning("No company_id provided, using default config")
            return self._default_config
        
        company_id = company_id.lower().strip()
        
        if company_id in self._companies_config:
            return self._companies_config[company_id]
        
        logger.warning(f"Company '{company_id}' not found, using default config")
        return self._default_config
    
    def get_all_companies(self) -> Dict[str, CompanyConfig]:
        """Obtener todas las configuraciones de empresas"""
        return self._companies_config.copy()
    
    def add_company(self, company_id: str, company_data: Dict[str, Any]) -> bool:
        """Agregar nueva configuración de empresa"""
        try:
            company_config = CompanyConfig.from_dict({
                'company_id': company_id,
                **company_data
            })
            
            self._companies_config[company_id.lower()] = company_config
            logger.info(f"Added new company configuration: {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding company configuration: {e}")
            return False
    
    def extract_company_id_from_webhook(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """Extraer company_id desde datos del webhook"""
        # Métodos de extracción en orden de prioridad
        extraction_methods = [
            # Método 1: Campo company_id directo
            lambda: webhook_data.get("company_id"),
            
            # Método 2: Desde conversation.meta
            lambda: webhook_data.get("conversation", {}).get("meta", {}).get("company_id"),
            
            # Método 3: Desde account (para Chatwoot)
            lambda: webhook_data.get("conversation", {}).get("account", {}).get("name", "").lower(),
            
            # Método 4: Desde custom attributes
            lambda: webhook_data.get("conversation", {}).get("custom_attributes", {}).get("company_id"),
            
            # Método 5: Desde URL del webhook si está disponible
            lambda: self._extract_company_from_webhook_url(webhook_data),
            
            # Método 6: Desde account_id mapping
            lambda: self._map_account_id_to_company(webhook_data)
        ]
        
        for method in extraction_methods:
            try:
                company_id = method()
                if company_id and str(company_id).strip():
                    company_id = str(company_id).lower().strip()
                    if company_id in self._companies_config:
                        logger.info(f"✅ Company ID extracted: {company_id}")
                        return company_id
            except Exception as e:
                logger.debug(f"Extraction method failed: {e}")
                continue
        
        # Fallback: usar configuración por defecto
        logger.warning("Could not extract company_id from webhook, using default")
        return "default"
    
    def _extract_company_from_webhook_url(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """Extraer company desde URL del webhook si está disponible"""
        # Esta función puede ser implementada si el webhook contiene información de URL
        return None
    
    def _map_account_id_to_company(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """Mapear account_id a company_id para sistemas como Chatwoot"""
        account_id = webhook_data.get("conversation", {}).get("account", {}).get("id")
        
        # Mapeo configurable de account_id a company_id
        account_to_company_mapping = {
            "7": "benova",  # Account ID 7 = Benova
            # Agregar más mapeos según sea necesario
        }
        
        if account_id and str(account_id) in account_to_company_mapping:
            return account_to_company_mapping[str(account_id)]
        
        return None
    
    def validate_company_config(self, company_id: str) -> bool:
        """Validar que la configuración de una empresa sea válida"""
        try:
            config = self.get_company_config(company_id)
            
            # Validaciones básicas
            required_fields = ['company_id', 'company_name', 'redis_prefix', 'vectorstore_index']
            
            for field in required_fields:
                if not getattr(config, field, None):
                    logger.error(f"Missing required field '{field}' for company '{company_id}'")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating company config for '{company_id}': {e}")
            return False

# Instancia global del gestor de configuraciones
_company_config_manager: Optional[CompanyConfigManager] = None

def get_company_config_manager() -> CompanyConfigManager:
    """Obtener instancia global del gestor de configuraciones"""
    global _company_config_manager
    
    if _company_config_manager is None:
        _company_config_manager = CompanyConfigManager()
    
    return _company_config_manager

def get_company_config(company_id: str) -> CompanyConfig:
    """Función de conveniencia para obtener configuración de empresa"""
    return get_company_config_manager().get_company_config(company_id)
