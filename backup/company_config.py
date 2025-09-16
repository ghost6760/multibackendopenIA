# app/config/company_config.py
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from flask import current_app
import logging

logger = logging.getLogger(__name__)

@dataclass
class CompanyConfig:
    """Configuración centralizada por empresa"""
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
    
    # Configuraciones específicas de servicios
    treatment_durations: Dict[str, int] = None
    schedule_keywords: list = None
    emergency_keywords: list = None
    sales_keywords: list = None
    
    def __post_init__(self):
        """Inicializar valores por defecto después de la creación"""
        if self.treatment_durations is None:
            self.treatment_durations = {
                "consulta general": 30,
                "procedimiento estetico": 60,
                "tratamiento facial": 90,
                "masaje": 60,
                "cirugia menor": 120
            }
        
        if self.schedule_keywords is None:
            self.schedule_keywords = [
                "agendar", "reservar", "programar", "cita", "appointment",
                "agenda", "disponibilidad", "horario", "fecha", "hora",
                "procede", "proceder", "confirmar cita"
            ]
        
        if self.emergency_keywords is None:
            self.emergency_keywords = [
                "dolor intenso", "sangrado", "emergencia", 
                "reacción alérgica", "inflamación severa", "urgencia"
            ]
        
        if self.sales_keywords is None:
            self.sales_keywords = [
                "precio", "costo", "inversión", "promoción",
                "tratamiento", "procedimiento", "beneficio", "servicio"
            ]

class CompanyConfigManager:
    """Gestor de configuraciones de empresas - Enhanced con soporte extendido"""
    
    def __init__(self):
        self._configs: Dict[str, CompanyConfig] = {}
        self._extended_configs: Dict[str, Any] = {}  # Para configuraciones extendidas
        self._load_company_configs()
        self._load_extended_configs()
    
    def _load_company_configs(self):
        """Cargar configuraciones básicas desde archivo JSON o variables de entorno"""
        try:
            # Intenta cargar desde archivo JSON
            config_file = os.getenv('COMPANIES_CONFIG_FILE', 'companies_config.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    configs_data = json.load(f)
                logger.info(f"Loaded company configs from file: {config_file}")
            else:
                # Configuración por defecto desde variables de entorno
                configs_data = self._get_default_configs()
                logger.info("Using default company configurations")
            
            # Crear objetos CompanyConfig
            for company_id, config_data in configs_data.items():
                self._configs[company_id] = CompanyConfig(
                    company_id=company_id,
                    **config_data
                )
            
            logger.info(f"Loaded configurations for companies: {list(self._configs.keys())}")
            
        except Exception as e:
            logger.error(f"Error loading company configs: {e}")
            # Cargar configuración mínima de emergencia
            self._load_emergency_config()
    
    def _load_extended_configs(self):
        """Cargar configuraciones extendidas para agendamiento avanzado"""
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
    
    def _get_default_configs(self) -> Dict[str, Any]:
        """Configuración por defecto basada en variables de entorno"""
        return {
            "benova": {
                "company_name": "Benova",
                "redis_prefix": "benova:",
                "vectorstore_index": "benova_documents",
                "schedule_service_url": os.getenv('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040'),
                "sales_agent_name": "María, asesora de Benova",
                "services": "medicina estética y tratamientos de belleza",
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
                }
            },
            "medispa": {
                "company_name": "MediSpa Elite",
                "redis_prefix": "medispa:",
                "vectorstore_index": "medispa_documents",
                "schedule_service_url": os.getenv('MEDISPA_SCHEDULE_URL', 'http://127.0.0.1:4041'),
                "sales_agent_name": "Dr. López, especialista de MediSpa",
                "services": "medicina estética avanzada y bienestar integral",
                "treatment_durations": {
                    "consulta dermatológica": 45,
                    "tratamiento laser": 90,
                    "hidrafacial": 75,
                    "mesoterapia": 60,
                    "plasma rico": 120
                }
            }
        }
    
    def _load_emergency_config(self):
        """Cargar configuración mínima en caso de error"""
        self._configs["default"] = CompanyConfig(
            company_id="default",
            company_name="Sistema de Atención",
            redis_prefix="default:",
            vectorstore_index="default_documents",
            schedule_service_url="http://127.0.0.1:4040",
            sales_agent_name="Asistente Virtual",
            services="atención al cliente"
        )
        logger.warning("Emergency config loaded for 'default' company")
    
    def get_company_config(self, company_id: str) -> Optional[CompanyConfig]:
        """Obtener configuración básica de una empresa"""
        config = self._configs.get(company_id)
        
        if not config:
            logger.warning(f"Company config not found for: {company_id}")
            # Intentar con configuración por defecto
            config = self._configs.get("default")
            
        return config
    
    def get_extended_config(self, company_id: str) -> Optional[Any]:
        """Obtener configuración extendida de una empresa para agendamiento avanzado"""
        extended_config = self._extended_configs.get(company_id)
        
        if not extended_config:
            logger.debug(f"Extended config not found for: {company_id}")
            return None
            
        return extended_config
    
    def has_extended_config(self, company_id: str) -> bool:
        """Verificar si una empresa tiene configuración extendida"""
        return company_id in self._extended_configs
    
    def get_schedule_integration_type(self, company_id: str) -> str:
        """Obtener tipo de integración de agendamiento para una empresa"""
        extended_config = self.get_extended_config(company_id)
        
        if extended_config:
            # Si es objeto ExtendedCompanyConfig
            if hasattr(extended_config, 'integration_type'):
                return extended_config.integration_type
            # Si es diccionario
            elif isinstance(extended_config, dict):
                return extended_config.get('integration_type', 'generic_rest')
        
        # Fallback basado en URL del servicio
        basic_config = self.get_company_config(company_id)
        if basic_config:
            url = basic_config.schedule_service_url.lower()
            if 'google' in url or 'googleapis.com' in url:
                return 'google_calendar'
            elif 'calendly.com' in url:
                return 'calendly'
            elif 'webhook.site' in url or 'zapier.com' in url:
                return 'webhook'
        
        return 'generic_rest'
    
    def get_treatment_config(self, company_id: str, treatment_name: str) -> Optional[Dict[str, Any]]:
        """Obtener configuración específica de un tratamiento"""
        extended_config = self.get_extended_config(company_id)
        
        if extended_config:
            # Si es objeto ExtendedCompanyConfig
            if hasattr(extended_config, 'get_treatment_config'):
                return extended_config.get_treatment_config(treatment_name)
            # Si es diccionario con tratamientos
            elif isinstance(extended_config, dict) and 'treatments' in extended_config:
                treatments = extended_config['treatments']
                return treatments.get(treatment_name.lower())
        
        # Fallback a configuración básica
        basic_config = self.get_company_config(company_id)
        if basic_config and basic_config.treatment_durations:
            duration = basic_config.treatment_durations.get(treatment_name.lower(), 60)
            return {
                "name": treatment_name,
                "duration": duration,
                "sessions": 1,
                "deposit": 0,
                "category": "general",
                "agenda_id": "default"
            }
        
        return None
    
    def get_required_booking_fields(self, company_id: str) -> list:
        """Obtener campos requeridos para reservar en una empresa"""
        extended_config = self.get_extended_config(company_id)
        
        if extended_config:
            # Si es objeto ExtendedCompanyConfig
            if hasattr(extended_config, 'required_booking_fields'):
                return extended_config.required_booking_fields
            # Si es diccionario
            elif isinstance(extended_config, dict):
                return extended_config.get('required_booking_fields', [])
        
        # Campos por defecto
        return [
            "nombre completo",
            "número de cédula", 
            "fecha de nacimiento",
            "correo electrónico",
            "motivo"
        ]
    
    def get_all_companies(self) -> Dict[str, CompanyConfig]:
        """Obtener todas las configuraciones básicas de empresas"""
        return self._configs.copy()
    
    def get_all_extended_companies(self) -> Dict[str, Any]:
        """Obtener todas las configuraciones extendidas de empresas"""
        return self._extended_configs.copy()
    
    def add_company_config(self, config: CompanyConfig):
        """Agregar nueva configuración de empresa"""
        self._configs[config.company_id] = config
        logger.info(f"Added company config for: {config.company_id}")
    
    def update_company_config(self, company_id: str, **updates):
        """Actualizar configuración existente"""
        if company_id in self._configs:
            config = self._configs[company_id]
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            logger.info(f"Updated company config for: {company_id}")
        else:
            logger.error(f"Cannot update non-existent company: {company_id}")
    
    def validate_company_id(self, company_id: str) -> bool:
        """Validar si existe la empresa"""
        return company_id in self._configs
    
    def reload_configs(self):
        """Recargar todas las configuraciones"""
        try:
            self._configs.clear()
            self._extended_configs.clear()
            self._load_company_configs()
            self._load_extended_configs()
            logger.info("All configurations reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error reloading configurations: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema de configuración"""
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
            }
        }

# Instancia global del gestor
_company_manager: Optional[CompanyConfigManager] = None

def get_company_manager() -> CompanyConfigManager:
    """Obtener instancia global del gestor de empresas"""
    global _company_manager
    
    if _company_manager is None:
        _company_manager = CompanyConfigManager()
    
    return _company_manager

def get_company_config(company_id: str) -> Optional[CompanyConfig]:
    """Función de conveniencia para obtener configuración básica"""
    manager = get_company_manager()
    return manager.get_company_config(company_id)

def get_extended_company_config(company_id: str) -> Optional[Any]:
    """Función de conveniencia para obtener configuración extendida"""
    manager = get_company_manager()
    return manager.get_extended_config(company_id)

def extract_company_id_from_webhook(data: Dict[str, Any]) -> str:
    """Extraer company_id del payload de webhook"""
    try:
        # Método 1: Desde conversation.meta
        conversation = data.get("conversation", {})
        meta = conversation.get("meta", {})
        
        if "company_id" in meta:
            return meta["company_id"]
        
        # Método 2: Desde account_id (mapeo)
        account_id = data.get("account", {}).get("id") or conversation.get("account_id")
        
        if account_id:
            # Mapeo de account_id a company_id
            account_mapping = {
                "7": "benova",  # Benova Chatwoot account
                "8": "medispa", # MediSpa account
            }
            
            company_id = account_mapping.get(str(account_id))
            if company_id:
                return company_id
        
        # Método 3: Desde inbox (si está configurado)
        inbox = conversation.get("inbox", {})
        if "company_id" in inbox:
            return inbox["company_id"]
        
        # Método 4: Por defecto basado en configuración
        default_company = os.getenv('DEFAULT_COMPANY_ID', 'benova')
        logger.warning(f"Using default company_id: {default_company}")
        return default_company
        
    except Exception as e:
        logger.error(f"Error extracting company_id: {e}")
        return os.getenv('DEFAULT_COMPANY_ID', 'benova')

def validate_company_context(company_id: str) -> bool:
    """Validar contexto de empresa antes de procesar"""
    manager = get_company_manager()
    
    if not manager.validate_company_id(company_id):
        logger.error(f"Invalid company_id: {company_id}")
        return False
    
    return True

# Función de utilidad para crear servicio de calendario
def create_calendar_integration_service(company_id: str):
    """Crear servicio de integración de calendario para una empresa"""
    try:
        # Importar dinámicamente para evitar dependencias circulares
        from ..services.calendar_integration_service import create_calendar_service
        
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
