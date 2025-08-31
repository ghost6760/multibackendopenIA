# app/config/extended_company_config.py
"""
Configuración extendida para agendamiento multi-empresa con múltiples agendas
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json
import os

@dataclass
class TreatmentConfig:
    """Configuración específica de un tratamiento"""
    name: str
    duration: int  # en minutos
    sessions: int = 1  # número de sesiones por cita
    deposit: float = 0.0  # abono requerido
    category: str = "general"  # categoría del tratamiento
    agenda_id: str = "default"  # ID de la agenda específica
    preparation_time: int = 0  # tiempo de preparación en minutos
    followup_time: int = 0  # tiempo de seguimiento en minutos
    requires_consultation: bool = False  # requiere consulta previa
    consultation_duration: int = 15  # duración de consulta en minutos
    max_advance_days: int = 30  # máximo días de anticipación para agendar
    min_advance_hours: int = 2  # mínimo horas de anticipación
    
@dataclass
class AgendaConfig:
    """Configuración de una agenda específica"""
    agenda_id: str
    name: str
    calendar_id: str  # ID del calendario (Google Calendar, etc.)
    working_hours: Dict[str, Dict[str, str]]  # horarios por día de la semana
    timezone: str = "America/Bogota"
    buffer_time: int = 15  # tiempo de buffer entre citas en minutos
    max_concurrent: int = 1  # máximo citas concurrentes
    categories: List[str] = field(default_factory=list)  # categorías que maneja
    
@dataclass
class ExtendedCompanyConfig:
    """Configuración extendida para empresa con soporte de agendamiento avanzado"""
    company_id: str
    company_name: str
    
    # Configuración básica (heredada)
    redis_prefix: str
    vectorstore_index: str
    schedule_service_url: str
    sales_agent_name: str
    services: str
    
    # Configuración de agendamiento extendida
    treatments: Dict[str, TreatmentConfig] = field(default_factory=dict)
    agendas: Dict[str, AgendaConfig] = field(default_factory=dict)
    
    # Campos requeridos para reservar (configurable por empresa)
    required_booking_fields: List[str] = field(default_factory=lambda: [
        "nombre completo",
        "número de cédula", 
        "fecha de nacimiento",
        "correo electrónico",
        "motivo"
    ])
    
    # Configuración de integración
    integration_type: str = "generic_rest"
    integration_config: Dict[str, Any] = field(default_factory=dict)
    
    # Configuración de notificaciones
    notification_settings: Dict[str, Any] = field(default_factory=lambda: {
        "email_confirmations": True,
        "sms_reminders": False,
        "whatsapp_notifications": False,
        "calendar_invites": True
    })
    
    # Políticas de agendamiento
    booking_policies: Dict[str, Any] = field(default_factory=lambda: {
        "allow_same_day": False,
        "require_deposit": False,
        "auto_confirm": True,
        "cancellation_hours": 24,
        "reschedule_limit": 2
    })
    
    def get_treatment_config(self, treatment_name: str) -> Optional[TreatmentConfig]:
        """Obtener configuración de un tratamiento específico"""
        return self.treatments.get(treatment_name.lower())
    
    def get_agenda_for_treatment(self, treatment_name: str) -> Optional[AgendaConfig]:
        """Obtener la agenda correspondiente a un tratamiento"""
        treatment = self.get_treatment_config(treatment_name)
        if treatment:
            return self.agendas.get(treatment.agenda_id)
        return self.agendas.get("default")
    
    def get_available_agendas(self) -> List[str]:
        """Obtener lista de agendas disponibles"""
        return list(self.agendas.keys())
    
    def validate_booking_data(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validar datos de reserva según configuración de empresa"""
        validation_result = {
            "valid": True,
            "missing_fields": [],
            "invalid_fields": [],
            "warnings": []
        }
        
        # Validar campos requeridos
        for field in self.required_booking_fields:
            field_key = field.lower().replace(" ", "_")
            if field_key not in booking_data or not booking_data[field_key]:
                validation_result["missing_fields"].append(field)
                validation_result["valid"] = False
        
        # Validar tratamiento
        treatment_name = booking_data.get("treatment", "")
        if treatment_name:
            treatment = self.get_treatment_config(treatment_name)
            if not treatment:
                validation_result["warnings"].append(f"Tratamiento '{treatment_name}' no configurado")
        
        return validation_result

# Función para cargar configuraciones extendidas
def load_extended_company_configs(config_file: str = "extended_companies_config.json") -> Dict[str, ExtendedCompanyConfig]:
    """Cargar configuraciones extendidas desde archivo JSON"""
    try:
        if not os.path.exists(config_file):
            return create_default_extended_configs()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        configs = {}
        for company_id, company_data in data.items():
            # Procesar tratamientos
            treatments = {}
            if "treatments" in company_data:
                for treatment_name, treatment_data in company_data["treatments"].items():
                    treatments[treatment_name.lower()] = TreatmentConfig(
                        name=treatment_name,
                        **treatment_data
                    )
            
            # Procesar agendas
            agendas = {}
            if "agendas" in company_data:
                for agenda_id, agenda_data in company_data["agendas"].items():
                    agendas[agenda_id] = AgendaConfig(
                        agenda_id=agenda_id,
                        **agenda_data
                    )
            
            # Crear configuración extendida
            config = ExtendedCompanyConfig(
                company_id=company_id,
                treatments=treatments,
                agendas=agendas,
                **{k: v for k, v in company_data.items() if k not in ["treatments", "agendas"]}
            )
            
            configs[company_id] = config
        
        return configs
        
    except Exception as e:
        print(f"Error loading extended configs: {e}")
        return create_default_extended_configs()

def create_default_extended_configs() -> Dict[str, ExtendedCompanyConfig]:
    """Crear configuraciones por defecto para empresas existentes"""
    
    # Configuración para Benova
    benova_treatments = {
        "limpieza facial": TreatmentConfig(
            name="Limpieza Facial",
            duration=60,
            sessions=1,
            category="cosmetologia",
            agenda_id="cosmetologia",
            preparation_time=10
        ),
        "tratamiento corporal": TreatmentConfig(
            name="Tratamiento Corporal",
            duration=60,
            sessions=2,  # 2 sesiones por cita
            category="cosmetologia",
            agenda_id="cosmetologia",
            preparation_time=15
        ),
        "valoración médica": TreatmentConfig(
            name="Valoración Médica",
            duration=15,
            category="medicina",
            agenda_id="medicina",
            requires_consultation=False
        ),
        "valoración + tratamiento": TreatmentConfig(
            name="Valoración + Tratamiento",
            duration=45,
            deposit=100000.0,
            category="medicina", 
            agenda_id="medicina",
            requires_consultation=True,
            consultation_duration=15
        )
    }
    
    benova_agendas = {
        "cosmetologia": AgendaConfig(
            agenda_id="cosmetologia",
            name="Agenda Cosmetología",
            calendar_id="cosmetologia@benova.com",
            working_hours={
                "monday": {"start": "08:00", "end": "18:00"},
                "tuesday": {"start": "08:00", "end": "18:00"},
                "wednesday": {"start": "08:00", "end": "18:00"},
                "thursday": {"start": "08:00", "end": "18:00"},
                "friday": {"start": "08:00", "end": "18:00"},
                "saturday": {"start": "08:00", "end": "14:00"}
            },
            buffer_time=15,
            categories=["cosmetologia"]
        ),
        "medicina": AgendaConfig(
            agenda_id="medicina",
            name="Agenda Medicina Estética",
            calendar_id="medicina@benova.com",
            working_hours={
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                "wednesday": {"start": "09:00", "end": "17:00"},
                "thursday": {"start": "09:00", "end": "17:00"},
                "friday": {"start": "09:00", "end": "17:00"}
            },
            buffer_time=10,
            categories=["medicina"]
        )
    }
    
    benova_config = ExtendedCompanyConfig(
        company_id="benova",
        company_name="Benova",
        redis_prefix="benova:",
        vectorstore_index="benova_documents",
        schedule_service_url="http://127.0.0.1:4040",
        sales_agent_name="María, asesora especializada de Benova",
        services="medicina estética y tratamientos de belleza",
        treatments=benova_treatments,
        agendas=benova_agendas,
        required_booking_fields=[
            "nombre completo",
            "número de cédula", 
            "fecha de nacimiento",
            "correo electrónico",
            "motivo"
        ],
        integration_type="google_calendar",
        integration_config={
            "credentials_path": "/path/to/google_credentials.json",
            "calendar_timezone": "America/Bogota"
        }
    )
    
    # Configuración para MediSpa (ejemplo simplificado)
    medispa_treatments = {
        "consulta dermatológica": TreatmentConfig(
            name="Consulta Dermatológica",
            duration=45,
            category="medicina",
            agenda_id="dermatologia"
        ),
        "tratamiento láser": TreatmentConfig(
            name="Tratamiento Láser",
            duration=90,
            category="medicina",
            agenda_id="laser_room",
            preparation_time=20
        )
    }
    
    medispa_agendas = {
        "dermatologia": AgendaConfig(
            agenda_id="dermatologia",
            name="Consultas Dermatología",
            calendar_id="dermato@medispa.com",
            working_hours={
                "monday": {"start": "08:00", "end": "16:00"},
                "tuesday": {"start": "08:00", "end": "16:00"},
                "wednesday": {"start": "08:00", "end": "16:00"},
                "thursday": {"start": "08:00", "end": "16:00"},
                "friday": {"start": "08:00", "end": "16:00"}
            }
        ),
        "laser_room": AgendaConfig(
            agenda_id="laser_room",
            name="Sala de Láser",
            calendar_id="laser@medispa.com",
            working_hours={
                "tuesday": {"start": "10:00", "end": "18:00"},
                "thursday": {"start": "10:00", "end": "18:00"},
                "friday": {"start": "10:00", "end": "18:00"},
                "saturday": {"start": "08:00", "end": "14:00"}
            }
        )
    }
    
    medispa_config = ExtendedCompanyConfig(
        company_id="medispa",
        company_name="MediSpa Elite", 
        redis_prefix="medispa:",
        vectorstore_index="medispa_documents",
        schedule_service_url="http://127.0.0.1:4041",
        sales_agent_name="Dr. López, especialista de MediSpa Elite",
        services="medicina estética avanzada y bienestar integral",
        treatments=medispa_treatments,
        agendas=medispa_agendas,
        integration_type="calendly",
        integration_config={
            "api_key": "your_calendly_api_key",
            "organization_uri": "https://api.calendly.com/organizations/YOUR_ORG"
        }
    )
    
    return {
        "benova": benova_config,
        "medispa": medispa_config
    }

def save_extended_configs(configs: Dict[str, ExtendedCompanyConfig], 
                         filename: str = "extended_companies_config.json"):
    """Guardar configuraciones extendidas a archivo JSON"""
    try:
        serializable_configs = {}
        
        for company_id, config in configs.items():
            # Serializar tratamientos
            treatments_data = {}
            for treatment_name, treatment in config.treatments.items():
                treatments_data[treatment_name] = {
                    "duration": treatment.duration,
                    "sessions": treatment.sessions,
                    "deposit": treatment.deposit,
                    "category": treatment.category,
                    "agenda_id": treatment.agenda_id,
                    "preparation_time": treatment.preparation_time,
                    "followup_time": treatment.followup_time,
                    "requires_consultation": treatment.requires_consultation,
                    "consultation_duration": treatment.consultation_duration,
                    "max_advance_days": treatment.max_advance_days,
                    "min_advance_hours": treatment.min_advance_hours
                }
            
            # Serializar agendas
            agendas_data = {}
            for agenda_id, agenda in config.agendas.items():
                agendas_data[agenda_id] = {
                    "name": agenda.name,
                    "calendar_id": agenda.calendar_id,
                    "working_hours": agenda.working_hours,
                    "timezone": agenda.timezone,
                    "buffer_time": agenda.buffer_time,
                    "max_concurrent": agenda.max_concurrent,
                    "categories": agenda.categories
                }
            
            # Configuración completa
            serializable_configs[company_id] = {
                "company_name": config.company_name,
                "redis_prefix": config.redis_prefix,
                "vectorstore_index": config.vectorstore_index,
                "schedule_service_url": config.schedule_service_url,
                "sales_agent_name": config.sales_agent_name,
                "services": config.services,
                "treatments": treatments_data,
                "agendas": agendas_data,
                "required_booking_fields": config.required_booking_fields,
                "integration_type": config.integration_type,
                "integration_config": config.integration_config,
                "notification_settings": config.notification_settings,
                "booking_policies": config.booking_policies
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_configs, f, indent=2, ensure_ascii=False)
        
        print(f"Extended configurations saved to {filename}")
        
    except Exception as e:
        print(f"Error saving extended configs: {e}")

# Ejemplo de uso
if __name__ == "__main__":
    # Crear y guardar configuraciones por defecto
    default_configs = create_default_extended_configs()
    save_extended_configs(default_configs)
    
    # Cargar y mostrar configuraciones
    loaded_configs = load_extended_company_configs()
    
    for company_id, config in loaded_configs.items():
        print(f"\n=== {config.company_name} ===")
        print(f"Tratamientos: {len(config.treatments)}")
        print(f"Agendas: {len(config.agendas)}")
        print(f"Campos requeridos: {len(config.required_booking_fields)}")
        print(f"Integración: {config.integration_type}")
