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
    """Gestor de configuraciones de empresas"""
    
    def __init__(self):
        self._configs: Dict[str, CompanyConfig] = {}
        self._load_company_configs()
    
    def _load_company_configs(self):
        """Cargar configuraciones desde archivo JSON o variables de entorno"""
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
        """Obtener configuración de una empresa"""
        config = self._configs.get(company_id)
        
        if not config:
            logger.warning(f"Company config not found for: {company_id}")
            # Intentar con configuración por defecto
            config = self._configs.get("default")
            
        return config
    
    def get_all_companies(self) -> Dict[str, CompanyConfig]:
        """Obtener todas las configuraciones de empresas"""
        return self._configs.copy()
    
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

# Instancia global del gestor
_company_manager: Optional[CompanyConfigManager] = None

def get_company_manager() -> CompanyConfigManager:
    """Obtener instancia global del gestor de empresas"""
    global _company_manager
    
    if _company_manager is None:
        _company_manager = CompanyConfigManager()
    
    return _company_manager

def get_company_config(company_id: str) -> Optional[CompanyConfig]:
    """Función de conveniencia para obtener configuración"""
    manager = get_company_manager()
    return manager.get_company_config(company_id)

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
