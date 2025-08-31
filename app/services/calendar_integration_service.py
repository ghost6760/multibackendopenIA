# app/services/calendar_integration_service.py
"""
Servicio de integración con sistemas de calendario (Google Calendar, Calendly, etc.)
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import pytz
import logging
from dataclasses import asdict

# Google Calendar
try:
    from google.oauth2.credentials import Credentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials  
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Otras integraciones
import requests

from app.config.extended_company_config import ExtendedCompanyConfig, TreatmentConfig, AgendaConfig

logger = logging.getLogger(__name__)

class CalendarIntegrationService:
    """Servicio base para integraciones de calendario"""
    
    def __init__(self, company_config: ExtendedCompanyConfig):
        self.company_config = company_config
        self.integration_type = company_config.integration_type
        self.integration_config = company_config.integration_config
        
        # Inicializar servicio específico
        self._initialize_service()
    
    def _initialize_service(self):
        """Inicializar servicio según tipo de integración"""
        if self.integration_type == "google_calendar" and GOOGLE_AVAILABLE:
            self._initialize_google_calendar()
        elif self.integration_type == "calendly":
            self._initialize_calendly()
        elif self.integration_type == "webhook":
            self._initialize_webhook()
        else:
            self._initialize_generic_rest()
    
    def _initialize_google_calendar(self):
        """Inicializar Google Calendar API"""
        try:
            credentials_path = self.integration_config.get("credentials_path")
            if not credentials_path or not os.path.exists(credentials_path):
                raise ValueError(f"Google credentials file not found: {credentials_path}")
            
            # Usar Service Account para autenticación
            credentials = ServiceAccountCredentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            self.calendar_service = build('calendar', 'v3', credentials=credentials)
            self.timezone = pytz.timezone(self.integration_config.get("calendar_timezone", "America/Bogota"))
            
            logger.info(f"Google Calendar initialized for {self.company_config.company_id}")
            
        except Exception as e:
            logger.error(f"Error initializing Google Calendar: {e}")
            self.calendar_service = None
    
    def _initialize_calendly(self):
        """Inicializar Calendly API"""
        try:
            self.calendly_api_key = self.integration_config.get("api_key")
            self.calendly_org_uri = self.integration_config.get("organization_uri")
            
            if not self.calendly_api_key:
                raise ValueError("Calendly API key not configured")
            
            self.calendly_headers = {
                "Authorization": f"Bearer {self.calendly_api_key}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Calendly initialized for {self.company_config.company_id}")
            
        except Exception as e:
            logger.error(f"Error initializing Calendly: {e}")
            self.calendly_api_key = None
    
    def _initialize_webhook(self):
        """Inicializar webhook integration"""
        self.webhook_url = self.company_config.schedule_service_url
        self.webhook_secret = self.integration_config.get("webhook_secret", "")
        logger.info(f"Webhook integration initialized for {self.company_config.company_id}")
    
    def _initialize_generic_rest(self):
        """Inicializar API REST genérica"""
        self.api_base_url = self.company_config.schedule_service_url
        self.api_headers = self.integration_config.get("headers", {})
        logger.info(f"Generic REST API initialized for {self.company_config.company_id}")
    
    def check_availability(self, date_str: str, treatment_name: str) -> Dict[str, Any]:
        """Verificar disponibilidad según tipo de integración"""
        try:
            treatment_config = self.company_config.get_treatment_config(treatment_name)
            if not treatment_config:
                return {"available_slots": [], "error": "Treatment not configured"}
            
            if self.integration_type == "google_calendar":
                return self._check_google_availability(date_str, treatment_config)
            elif self.integration_type == "calendly":
                return self._check_calendly_availability(date_str, treatment_config)
            elif self.integration_type == "webhook":
                return self._check_webhook_availability(date_str, treatment_config)
            else:
                return self._check_generic_availability(date_str, treatment_config)
                
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {"available_slots": [], "error": str(e)}
    
    def _check_google_availability(self, date_str: str, treatment_config: TreatmentConfig) -> Dict[str, Any]:
        """Verificar disponibilidad en Google Calendar"""
        try:
            if not self.calendar_service:
                return {"available_slots": [], "error": "Google Calendar not initialized"}
            
            # Obtener agenda correspondiente
            agenda_config = self.company_config.get_agenda_for_treatment(treatment_config.name)
            if not agenda_config:
                return {"available_slots": [], "error": "No agenda configured for treatment"}
            
            # Parsear fecha
            date_obj = datetime.strptime(date_str, "%d-%m-%Y").date()
            day_name = date_obj.strftime("%A").lower()
            
            # Verificar si el día tiene horario configurado
            if day_name not in agenda_config.working_hours:
                return {"available_slots": [], "message": f"No working hours configured for {day_name}"}
            
            working_hours = agenda_config.working_hours[day_name]
            start_time = datetime.strptime(working_hours["start"], "%H:%M").time()
            end_time = datetime.strptime(working_hours["end"], "%H:%M").time()
            
            # Crear datetime objects para el día específico
            start_datetime = datetime.combine(date_obj, start_time)
            end_datetime = datetime.combine(date_obj, end_time)
            
            # Convertir a UTC para Google Calendar
            start_datetime = self.timezone.localize(start_datetime).astimezone(pytz.UTC)
            end_datetime = self.timezone.localize(end_datetime).astimezone(pytz.UTC)
            
            # Obtener eventos existentes
            events_result = self.calendar_service.events().list(
                calendarId=agenda_config.calendar_id,
                timeMin=start_datetime.isoformat(),
                timeMax=end_datetime.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Calcular slots disponibles
            available_slots = self._calculate_available_slots(
                start_datetime, end_datetime, events, treatment_config, agenda_config
            )
            
            return {
                "available_slots": available_slots,
                "date": date_str,
                "treatment": treatment_config.name,
                "agenda": agenda_config.name
            }
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return {"available_slots": [], "error": f"Calendar API error: {e}"}
        except Exception as e:
            logger.error(f"Error checking Google Calendar availability: {e}")
            return {"available_slots": [], "error": str(e)}
    
    def _calculate_available_slots(self, start_datetime: datetime, end_datetime: datetime,
                                 existing_events: List[Dict], treatment_config: TreatmentConfig,
                                 agenda_config: AgendaConfig) -> List[str]:
        """Calcular slots disponibles considerando eventos existentes"""
        try:
            slots = []
            slot_duration = 30  # slots de 30 minutos
            treatment_duration = treatment_config.duration
            buffer_time = agenda_config.buffer_time
            
            # Crear lista de intervalos ocupados
            busy_intervals = []
            for event in existing_events:
                event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
                
                # Agregar buffer time
                event_start = event_start - timedelta(minutes=buffer_time)
                event_end = event_end + timedelta(minutes=buffer_time)
                
                busy_intervals.append((event_start, event_end))
            
            # Generar slots de 30 minutos
            current_time = start_datetime
            while current_time + timedelta(minutes=treatment_duration) <= end_datetime:
                slot_end = current_time + timedelta(minutes=treatment_duration)
                
                # Verificar si el slot está libre
                is_free = True
                for busy_start, busy_end in busy_intervals:
                    if (current_time < busy_end and slot_end > busy_start):
                        is_free = False
                        break
                
                if is_free:
                    # Convertir de vuelta a timezone local
                    local_time = current_time.astimezone(self.timezone)
                    slots.append(local_time.strftime("%H:%M"))
                
                current_time += timedelta(minutes=slot_duration)
            
            return slots
            
        except Exception as e:
            logger.error(f"Error calculating available slots: {e}")
            return []
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear reserva según tipo de integración"""
        try:
            if self.integration_type == "google_calendar":
                return self._create_google_booking(booking_data)
            elif self.integration_type == "calendly":
                return self._create_calendly_booking(booking_data)
            elif self.integration_type == "webhook":
                return self._create_webhook_booking(booking_data)
            else:
                return self._create_generic_booking(booking_data)
                
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_google_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear evento en Google Calendar"""
        try:
            if not self.calendar_service:
                return {"success": False, "error": "Google Calendar not initialized"}
            
            patient_info = booking_data.get("patient_info", {})
            treatment_name = patient_info.get("motivo", "Consulta general")
            
            treatment_config = self.company_config.get_treatment_config(treatment_name)
            if not treatment_config:
                return {"success": False, "error": "Treatment configuration not found"}
            
            agenda_config = self.company_config.get_agenda_for_treatment(treatment_name)
            if not agenda_config:
                return {"success": False, "error": "No agenda configured for treatment"}
            
            # Extraer información de fecha y hora del mensaje o historial
            date_time_info = self._extract_datetime_from_booking(booking_data)
            if not date_time_info:
                return {"success": False, "error": "Date and time information not found"}
            
            start_datetime = date_time_info["start"]
            end_datetime = start_datetime + timedelta(minutes=treatment_config.duration)
            
            # Crear evento
            event = {
                'summary': f'{treatment_config.name} - {patient_info.get("nombre_completo", "Cliente")}',
                'description': self._create_event_description(patient_info, treatment_config),
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': str(self.timezone)
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': str(self.timezone)
                },
                'attendees': [
                    {
                        'email': patient_info.get("correo_electronico", ""),
                        'displayName': patient_info.get("nombre_completo", "")
                    }
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 24 horas antes
                        {'method': 'popup', 'minutes': 60}  # 1 hora antes
                    ]
                }
            }
            
            # Crear evento en Google Calendar
            created_event = self.calendar_service.events().insert(
                calendarId=agenda_config.calendar_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "calendar_link": created_event.get('htmlLink'),
                "confirmation_number": created_event['id'][-8:],
                "message": f"Cita agendada para {start_datetime.strftime('%d/%m/%Y a las %H:%M')}"
            }
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return {"success": False, "error": f"Calendar API error: {e}"}
        except Exception as e:
            logger.error(f"Error creating Google Calendar event: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_event_description(self, patient_info: Dict[str, Any], 
                                treatment_config: TreatmentConfig) -> str:
        """Crear descripción del evento"""
        description_parts = [
            f"Tratamiento: {treatment_config.name}",
            f"Duración: {treatment_config.duration} minutos",
            f"Paciente: {patient_info.get('nombre_completo', 'N/A')}",
            f"Teléfono: {patient_info.get('telefono', 'N/A')}",
            f"Email: {patient_info.get('correo_electronico', 'N/A')}",
            f"Cédula: {patient_info.get('numero_de_cedula', 'N/A')}"
        ]
        
        if treatment_config.deposit > 0:
            description_parts.append(f"Abono requerido: ${treatment_config.deposit:,.0f}")
        
        if treatment_config.requires_consultation:
            description_parts.append("Incluye consulta previa")
        
        return "\n".join(description_parts)
    
    def _extract_datetime_from_booking(self, booking_data: Dict[str, Any]) -> Optional[Dict[str, datetime]]:
        """Extraer fecha y hora de los datos de reserva"""
        try:
            # Buscar en el mensaje principal
            message = booking_data.get("message", "")
            chat_history = booking_data.get("chat_history", [])
            
            # Combinar todo el texto para buscar fecha y hora
            all_text = message + " " + " ".join([
                msg.get("content", "") for msg in chat_history
            ])
            
            # Buscar fecha
            import re
            date_match = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', all_text)
            if not date_match:
                return None
            
            day, month, year = date_match.groups()
            date_obj = datetime(int(year), int(month), int(day))
            
            # Buscar hora
            time_match = re.search(r'\b(\d{1,2}):(\d{2})\b', all_text)
            if time_match:
                hour, minute = time_match.groups()
                time_obj = datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
                
                # Combinar fecha y hora
                start_datetime = datetime.combine(date_obj.date(), time_obj)
                start_datetime = self.timezone.localize(start_datetime)
                
                return {"start": start_datetime}
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting datetime from booking: {e}")
            return None
    
    def _check_calendly_availability(self, date_str: str, treatment_config: TreatmentConfig) -> Dict[str, Any]:
        """Verificar disponibilidad en Calendly"""
        try:
            if not self.calendly_api_key:
                return {"available_slots": [], "error": "Calendly not configured"}
            
            # Llamar a Calendly API para obtener slots disponibles
            # (Implementación específica según documentación de Calendly)
            
            return {"available_slots": [], "message": "Calendly integration pending"}
            
        except Exception as e:
            logger.error(f"Error checking Calendly availability: {e}")
            return {"available_slots": [], "error": str(e)}
    
    def _create_calendly_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear reserva en Calendly"""
        try:
            # Implementar según API de Calendly
            return {"success": False, "message": "Calendly booking pending implementation"}
            
        except Exception as e:
            logger.error(f"Error creating Calendly booking: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_webhook_availability(self, date_str: str, treatment_config: TreatmentConfig) -> Dict[str, Any]:
        """Verificar disponibilidad vía webhook"""
        try:
            webhook_data = {
                "action": "check_availability",
                "company_id": self.company_config.company_id,
                "date": date_str,
                "treatment": asdict(treatment_config),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                self.webhook_url,
                json=webhook_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"available_slots": [], "error": f"Webhook returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error with webhook availability: {e}")
            return {"available_slots": [], "error": str(e)}
    
    def _create_webhook_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear reserva vía webhook"""
        try:
            webhook_data = {
                "action": "create_booking",
                "company_id": self.company_config.company_id,
                **booking_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                self.webhook_url,
                json=webhook_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "webhook_response": result,
                    "message": "Reserva procesada vía webhook"
                }
            else:
                return {"success": False, "error": f"Webhook returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error with webhook booking: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_generic_availability(self, date_str: str, treatment_config: TreatmentConfig) -> Dict[str, Any]:
        """Verificar disponibilidad con API REST genérica"""
        try:
            response = requests.post(
                f"{self.api_base_url}/check-availability",
                json={
                    "company_id": self.company_config.company_id,
                    "date": date_str,
                    "treatment": asdict(treatment_config)
                },
                headers=self.api_headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {"available_slots": []})
            else:
                return {"available_slots": [], "error": f"API returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error with generic API availability: {e}")
            return {"available_slots": [], "error": str(e)}
    
    def _create_generic_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear reserva con API REST genérica"""
        try:
            response = requests.post(
                f"{self.api_base_url}/create-booking",
                json={
                    "company_id": self.company_config.company_id,
                    **booking_data
                },
                headers=self.api_headers,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"API returned {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error with generic API booking: {e}")
            return {"success": False, "error": str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio de calendario"""
        try:
            if self.integration_type == "google_calendar":
                return {
                    "integration_type": "google_calendar",
                    "service_available": self.calendar_service is not None,
                    "calendar_count": len(self.company_config.agendas),
                    "timezone": str(self.timezone)
                }
            elif self.integration_type == "calendly":
                return {
                    "integration_type": "calendly",
                    "service_available": self.calendly_api_key is not None,
                    "organization": self.calendly_org_uri
                }
            else:
                return {
                    "integration_type": self.integration_type,
                    "service_available": True,
                    "endpoint": self.company_config.schedule_service_url
                }
                
        except Exception as e:
            return {
                "integration_type": self.integration_type,
                "service_available": False,
                "error": str(e)
            }

# Factory para crear servicios de calendario
def create_calendar_service(company_config: ExtendedCompanyConfig) -> CalendarIntegrationService:
    """Factory para crear servicio de calendario según configuración"""
    return CalendarIntegrationService(company_config)
