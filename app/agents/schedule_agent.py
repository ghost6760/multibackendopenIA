from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any, List, Optional, Tuple
import requests
import logging
import re
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ScheduleAgent(BaseAgent):
    """Agente de agendamiento multi-tenant con integración de calendarios y RAG"""
    
    def _initialize_agent(self):
        """Inicializar agente de agendamiento"""
        self.prompt_template = self._create_prompt_template()
        self.schedule_service_available = False
        self.schedule_status_last_check = 0
        self.schedule_status_cache_duration = 30
        self.vectorstore_service = None  # Se inyecta externamente
        
        # Configuración de integraciones de calendario
        self.integration_type = self._detect_integration_type()
        
        # Verificar conexión inicial con servicio de agendamiento
        self._verify_schedule_service()
        
        # Crear cadena
        self._create_chain()
    
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore específico de la empresa"""
        self.vectorstore_service = vectorstore_service
        # Recrear cadena con RAG
        self._create_chain()
    
    def _detect_integration_type(self) -> str:
        """Detectar tipo de integración basado en configuración"""
        schedule_url = self.company_config.schedule_service_url.lower()
        
        if 'googleapis.com' in schedule_url or 'google' in schedule_url:
            return 'google_calendar'
        elif 'calendly.com' in schedule_url or 'calendly' in schedule_url:
            return 'calendly'
        elif 'cal.com' in schedule_url or 'cal.' in schedule_url:
            return 'cal_com'
        elif 'zapier.com' in schedule_url or 'integromat' in schedule_url or 'make.com' in schedule_url:
            return 'webhook'
        else:
            return 'generic_rest'
    
    def _create_chain(self):
        """Crear cadena de agendamiento con RAG opcional"""
        self.chain = (
            {
                "schedule_status": self._get_schedule_status,
                "schedule_context": self._get_schedule_context,
                "required_fields": self._get_required_booking_fields,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "user_id": lambda x: x.get("user_id", "default_user"),
                "company_name": lambda x: self.company_config.company_name,
                "services": lambda x: self.company_config.services
            }
            | RunnableLambda(self._process_schedule_request)
        )

    ###
    def _create_default_prompt_template(self):
        """
        Template por defecto para agendamiento.
        
        NOTA: Este prompt se guarda en default_prompts pero el ScheduleAgent
        actualmente usa _process_schedule_request() para su lógica.
        Se mantiene este formato para compatibilidad con el sistema.
        """
        template = f"""Especialista en agendamiento de {self.company_config.company_name}.
    
    OBJETIVO: Ayudar a los usuarios a programar, consultar y gestionar citas para los servicios de la empresa.
    
    SERVICIOS DISPONIBLES: {self.company_config.services}
    
    INFORMACIÓN DEL SISTEMA:
    {{schedule_status}}
    
    CONTEXTO DE AGENDAMIENTO:
    {{schedule_context}}
    
    CAMPOS REQUERIDOS PARA AGENDAR:
    {{required_fields}}
    
    INSTRUCCIONES:
    1. Si el usuario consulta disponibilidad, proporciona horarios disponibles
    2. Si el usuario quiere agendar, solicita la información requerida de forma amigable
    3. Usa el contexto de agendamiento para proporcionar información específica sobre duraciones, preparaciones y requisitos
    4. Sé profesional pero cálido en tus respuestas
    5. Si hay información adicional en el contexto (abonos, recomendaciones), menciónala apropiadamente
    
    TONO: Profesional, organizado, servicial y claro.
    LONGITUD: Máximo 4-5 oraciones, a menos que se requiera información detallada.
    
    HISTORIAL DE CONVERSACIÓN:
    {{chat_history}}
    
    CONSULTA DEL USUARIO: {{question}}
    
    Responde de manera clara y organizada, priorizando la experiencia del usuario."""
    
        return ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "{question}")
        ])

    
    def _get_schedule_status(self, inputs):
        """Obtener estado del servicio de agendamiento específico de la empresa"""
        integration_name = self.integration_type.replace('_', ' ').title()
        
        if self.schedule_service_available:
            return f"✅ Sistema de agendamiento ACTIVO para {self.company_config.company_name} ({integration_name})"
        else:
            return f"⚠️ Sistema de agendamiento NO DISPONIBLE para {self.company_config.company_name} (Verificar: {self.company_config.schedule_service_url})"
    
    def _get_schedule_context(self, inputs):
        """Obtener contexto de agendamiento desde documentos RAG"""
        try:
            question = inputs.get("question", "")
            
            if not self.vectorstore_service:
                return self._get_basic_schedule_info()
            
            # Buscar información relacionada con agendamiento
            schedule_query = f"cita agenda horario duración preparación requisitos abono {question}"
            docs = self.vectorstore_service.search_by_company(
                schedule_query,
                self.company_config.company_id,
                k=3
            )
            
            if not docs:
                return self._get_basic_schedule_info()
            
            # Extraer información relevante para agendamiento
            context_parts = []
            for doc in docs:
                if hasattr(doc, 'page_content') and doc.page_content:
                    content = doc.page_content.lower()
                    if any(word in content for word in ['cita', 'agenda', 'horario', 'duración', 'preparación', 'requisitos', 'abono', 'valoración']):
                        context_parts.append(doc.page_content)
                elif isinstance(doc, dict) and 'content' in doc:
                    content = doc['content'].lower()
                    if any(word in content for word in ['cita', 'agenda', 'horario', 'duración', 'preparación', 'requisitos', 'abono', 'valoración']):
                        context_parts.append(doc['content'])
            
            if context_parts:
                basic_info = self._get_basic_schedule_info()
                rag_info = "\n\nInformación adicional específica:\n" + "\n".join(context_parts)
                return basic_info + rag_info
            else:
                return self._get_basic_schedule_info()
                
        except Exception as e:
            logger.error(f"Error retrieving schedule context: {e}")
            return self._get_basic_schedule_info()
    
    def _get_basic_schedule_info(self):
        """Información básica de agendamiento desde configuración"""
        # Obtener configuración de agendas múltiples si existe
        schedules_info = self._get_schedules_configuration()
        
        treatment_info = []
        for treatment, config in schedules_info.items():
            duration = config.get('duration', 60)
            sessions = config.get('sessions', 1)
            deposit = config.get('deposit', 0)
            
            info_line = f"- {treatment}: {duration} min"
            if sessions > 1:
                info_line += f" ({sessions} sesiones)"
            if deposit > 0:
                info_line += f" - Abono: ${deposit:,}"
            
            treatment_info.append(info_line)
        
        return f"""Información de agendamiento de {self.company_config.company_name}:

Duraciones y configuraciones:
{chr(10).join(treatment_info)}

Servicios: {self.company_config.services}
Sistema: {self.integration_type.replace('_', ' ').title()}"""
    
    def _get_schedules_configuration(self) -> Dict[str, Any]:
        """Obtener configuración de múltiples agendas por empresa"""
        # Configuración extendida que puede venir del company_config
        if hasattr(self.company_config, 'schedules_config'):
            return self.company_config.schedules_config
        
        # Convertir treatment_durations básico a configuración extendida
        extended_config = {}
        for treatment, duration in self.company_config.treatment_durations.items():
            extended_config[treatment] = {
                'duration': duration,
                'sessions': 1,
                'deposit': 0,
                'category': 'general',
                'agenda_id': 'default'
            }
        
        return extended_config
    
    def _get_required_booking_fields(self, inputs):
        """Obtener campos requeridos configurables por empresa"""
        # Campos por defecto
        default_fields = [
            "nombre completo",
            "número de cédula", 
            "fecha de nacimiento",
            "correo electrónico",
            "motivo"
        ]
        
        # Verificar si la empresa tiene campos personalizados
        if hasattr(self.company_config, 'required_booking_fields'):
            return self.company_config.required_booking_fields
        
        return default_fields
    
    def _verify_schedule_service(self, force_check: bool = False) -> bool:
        """Verificar servicio de agendamiento específico de la empresa"""
        import time
        current_time = time.time()
        
        if not force_check and (current_time - self.schedule_status_last_check) < self.schedule_status_cache_duration:
            return self.schedule_service_available
        
        try:
            # Diferentes endpoints según el tipo de integración
            health_endpoint = self._get_health_endpoint()
            
            response = requests.get(health_endpoint, timeout=5)
            
            if response.status_code == 200:
                self.schedule_service_available = True
                self.schedule_status_last_check = current_time
                logger.info(f"Schedule service ({self.integration_type}) available for {self.company_config.company_name}")
                return True
            else:
                self.schedule_service_available = False
                self.schedule_status_last_check = current_time
                return False
                
        except Exception as e:
            logger.warning(f"Schedule service verification failed for {self.company_config.company_name}: {e}")
            self.schedule_service_available = False
            self.schedule_status_last_check = current_time
            return False
    
    def _get_health_endpoint(self) -> str:
        """Obtener endpoint de health según tipo de integración"""
        base_url = self.company_config.schedule_service_url
        
        if self.integration_type == 'google_calendar':
            return f"{base_url}/health"  # Nuestro microservicio de Google Calendar
        elif self.integration_type == 'calendly':
            return f"{base_url}/health"  # Proxy a Calendly API
        elif self.integration_type == 'webhook':
            return f"{base_url}/ping"    # Webhook endpoint básico
        else:
            return f"{base_url}/health"  # Generic REST
    
    def _process_schedule_request(self, inputs):
        """Procesar solicitud de agendamiento con lógica específica de empresa y RAG"""
        try:
            question = inputs.get("question", "")
            user_id = inputs.get("user_id", "default_user")
            chat_history = inputs.get("chat_history", [])
            schedule_context = inputs.get("schedule_context", "")
            required_fields = inputs.get("required_fields", [])
            
            self._log_agent_activity("processing_schedule", {
                "question": question[:50],
                "rag_enabled": self.vectorstore_service is not None,
                "integration_type": self.integration_type
            })
            
            # Verificar si es una consulta de disponibilidad
            if self._is_availability_check(question):
                return self._handle_availability_check(question, chat_history, schedule_context)
            
            # Verificar si es agendamiento completo
            if self._should_use_schedule_api(question, chat_history):
                return self._handle_api_scheduling(question, user_id, chat_history, required_fields)
            
            # Respuesta base para solicitudes de agendamiento con contexto RAG
            return self._generate_base_schedule_response(question, inputs, schedule_context, required_fields)
            
        except Exception as e:
            logger.error(f"Error in schedule processing for {self.company_config.company_name}: {e}")
            return f"Error procesando tu solicitud de agenda en {self.company_config.company_name}. Te conectaré con un especialista... 📋"
    
    def _is_availability_check(self, question: str) -> bool:
        """Verificar si solo consulta disponibilidad"""
        availability_keywords = [
            "disponibilidad para", "horarios disponibles", "qué horarios",
            "cuándo hay", "hay disponibilidad", "ver horarios", "agenda libre"
        ]
        return any(keyword in question.lower() for keyword in availability_keywords)
    
    def _should_use_schedule_api(self, question: str, chat_history: list) -> bool:
        """Determinar si usar API de agendamiento para reservar"""
        question_lower = question.lower()
        
        # Verificar keywords de agendamiento
        has_schedule_intent = any(keyword in question_lower for keyword in self.company_config.schedule_keywords)
        
        # Verificar información disponible del paciente
        has_patient_info = self._extract_patient_info_from_history(chat_history)
        
        return has_schedule_intent and self.schedule_service_available and has_patient_info
    
    def _handle_availability_check(self, question: str, chat_history: list, schedule_context: str):
        """Manejar consulta de disponibilidad con contexto RAG"""
        try:
            date = self._extract_date_from_question(question, chat_history)
            treatment = self._extract_treatment_from_question(question)
            
            if not date:
                context_info = ""
                if schedule_context and "duración" in schedule_context.lower():
                    context_info = f"\n\nInformación sobre tratamientos:\n{schedule_context}"
                
                return f"""Para consultar disponibilidad en {self.company_config.company_name}, necesito:

📅 Fecha específica (DD-MM-YYYY)
🩺 Tipo de {self.company_config.services.lower()} que te interesa{context_info}

¿Puedes proporcionarme estos datos?"""
            
            # Obtener configuración del tratamiento
            treatment_config = self._get_treatment_configuration(treatment)
            availability_data = self._call_check_availability(date, treatment)
            
            if not availability_data or not availability_data.get("available_slots"):
                return f"No hay horarios disponibles para {date} en {self.company_config.company_name}."
            
            filtered_slots = self._filter_slots_by_configuration(
                availability_data["available_slots"], 
                treatment_config
            )
            
            return self._format_slots_response(filtered_slots, date, treatment_config)
            
        except Exception as e:
            logger.error(f"Error checking availability for {self.company_config.company_name}: {e}")
            return f"Error consultando disponibilidad en {self.company_config.company_name}. Te conectaré con un especialista."
    
    def _handle_api_scheduling(self, question: str, user_id: str, chat_history: list, required_fields: list):
        """Manejar agendamiento con API de calendario"""
        try:
            # Validar información requerida
            patient_info = self._validate_required_information(chat_history, required_fields)
            
            if not patient_info['complete']:
                missing_fields = patient_info['missing_fields']
                return f"""Para completar tu reserva en {self.company_config.company_name}, necesito:

{chr(10).join([f'• {field}' for field in missing_fields])}

¿Puedes proporcionarme esta información?"""
            
            # Procesar reserva según tipo de integración
            booking_result = self._call_booking_api(question, user_id, chat_history, patient_info['data'])
            
            if booking_result.get('success'):
                return self._format_booking_success(booking_result)
            elif booking_result.get('requires_more_info'):
                return booking_result.get('response', f"Necesito más información para agendar tu cita en {self.company_config.company_name}.")
            else:
                return f"No pude completar el agendamiento automático en {self.company_config.company_name}. Te conectaré con un especialista para completar tu cita."
                
        except Exception as e:
            logger.error(f"Error in API scheduling for {self.company_config.company_name}: {e}")
            return f"Error en el agendamiento automático. Te conectaré con un especialista de {self.company_config.company_name}."
    
    def _validate_required_information(self, chat_history: list, required_fields: list) -> Dict[str, Any]:
        """Validar que se tenga toda la información requerida para reservar"""
        history_text = " ".join([
            msg.content if hasattr(msg, 'content') else str(msg) 
            for msg in chat_history
        ]).lower()
        
        extracted_info = {}
        missing_fields = []
        
        # Validar cada campo requerido
        for field in required_fields:
            field_lower = field.lower()
            value = None
            
            if 'nombre' in field_lower:
                value = self._extract_name(history_text)
            elif 'cédula' in field_lower or 'cedula' in field_lower:
                value = self._extract_cedula(history_text)
            elif 'fecha de nacimiento' in field_lower or 'nacimiento' in field_lower:
                value = self._extract_birth_date(history_text)
            elif 'correo' in field_lower or 'email' in field_lower:
                value = self._extract_email(history_text)
            elif 'teléfono' in field_lower or 'telefono' in field_lower:
                value = self._extract_phone(history_text)
            elif 'motivo' in field_lower:
                value = self._extract_reason(history_text)
            
            if value:
                extracted_info[field] = value
            else:
                missing_fields.append(field)
        
        return {
            'complete': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'data': extracted_info
        }
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extraer nombre del texto"""
        patterns = [
            r'mi nombre es ([a-záéíóúñ\s]+)',
            r'me llamo ([a-záéíóúñ\s]+)',
            r'soy ([a-záéíóúñ\s]+)',
            r'nombre:?\s*([a-záéíóúñ\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip().title()
                if len(name.split()) >= 2:  # Al menos nombre y apellido
                    return name
        
        return None
    
    def _extract_cedula(self, text: str) -> Optional[str]:
        """Extraer número de cédula del texto"""
        patterns = [
            r'cédula:?\s*(\d{7,10})',
            r'cedula:?\s*(\d{7,10})',
            r'documento:?\s*(\d{7,10})',
            r'cc:?\s*(\d{7,10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_birth_date(self, text: str) -> Optional[str]:
        """Extraer fecha de nacimiento"""
        patterns = [
            r'nací el (\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'fecha de nacimiento:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'nacimiento:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).replace('/', '-')
        
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extraer correo electrónico"""
        pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extraer teléfono"""
        patterns = [
            r'teléfono:?\s*(\+?\d{10,})',
            r'celular:?\s*(\+?\d{10,})',
            r'móvil:?\s*(\+?\d{10,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_reason(self, text: str) -> Optional[str]:
        """Extraer motivo de la consulta"""
        # Buscar en el contexto general de la conversación
        treatments = list(self.company_config.treatment_durations.keys())
        
        for treatment in treatments:
            if treatment.lower() in text:
                return treatment
        
        # Buscar palabras clave genéricas
        reasons = ['consulta', 'valoración', 'revisión', 'tratamiento', 'procedimiento']
        for reason in reasons:
            if reason in text:
                return reason.title()
        
        return None
    
    def _get_treatment_configuration(self, treatment: str) -> Dict[str, Any]:
        """Obtener configuración completa del tratamiento"""
        schedules_config = self._get_schedules_configuration()
        
        # Buscar configuración específica
        for treatment_name, config in schedules_config.items():
            if treatment_name.lower() == treatment.lower():
                return config
        
        # Configuración por defecto
        return {
            'duration': self.company_config.treatment_durations.get(treatment, 60),
            'sessions': 1,
            'deposit': 0,
            'category': 'general',
            'agenda_id': 'default'
        }
    
    def _call_check_availability(self, date: str, treatment: str = "general") -> Dict[str, Any]:
        """Llamar al endpoint de disponibilidad según tipo de integración"""
        try:
            treatment_config = self._get_treatment_configuration(treatment)
            
            if self.integration_type == 'google_calendar':
                return self._check_google_calendar_availability(date, treatment_config)
            elif self.integration_type == 'calendly':
                return self._check_calendly_availability(date, treatment_config)
            elif self.integration_type == 'webhook':
                return self._check_webhook_availability(date, treatment_config)
            else:
                return self._check_generic_availability(date, treatment_config)
                
        except Exception as e:
            logger.error(f"Error calling availability endpoint: {e}")
            return None
    
    def _check_google_calendar_availability(self, date: str, treatment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verificar disponibilidad en Google Calendar"""
        try:
            response = requests.post(
                f"{self.company_config.schedule_service_url}/calendar/availability",
                json={
                    "date": date,
                    "duration": treatment_config['duration'],
                    "calendar_id": treatment_config.get('agenda_id', 'primary'),
                    "company_id": self.company_config.company_id
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logger.warning(f"Google Calendar API returned {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error with Google Calendar API: {e}")
            return None
    
    def _check_generic_availability(self, date: str, treatment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verificar disponibilidad con API genérica"""
        try:
            response = requests.post(
                f"{self.company_config.schedule_service_url}/check-availability",
                json={
                    "date": date,
                    "treatment": treatment_config,
                    "company_id": self.company_config.company_id
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logger.warning(f"Availability endpoint returned {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling generic availability endpoint: {e}")
            return None
    
    def _call_booking_api(self, question: str, user_id: str, chat_history: list, patient_info: Dict[str, Any]) -> Dict[str, Any]:
        """Llamar a la API de reserva según tipo de integración"""
        try:
            booking_data = {
                "message": question,
                "user_id": user_id,
                "company_id": self.company_config.company_id,
                "company_name": self.company_config.company_name,
                "patient_info": patient_info,
                "chat_history": self._format_chat_history(chat_history),
                "integration_type": self.integration_type
            }
            
            if self.integration_type == 'google_calendar':
                return self._book_google_calendar(booking_data)
            elif self.integration_type == 'calendly':
                return self._book_calendly(booking_data)
            elif self.integration_type == 'webhook':
                return self._book_webhook(booking_data)
            else:
                return self._book_generic_api(booking_data)
                
        except Exception as e:
            logger.error(f"Error calling booking API: {e}")
            return {"success": False, "message": "Error del servicio"}
    
    def _book_google_calendar(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear evento en Google Calendar"""
        try:
            response = requests.post(
                f"{self.company_config.schedule_service_url}/calendar/book",
                json=booking_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "booking_id": result.get("event_id"),
                    "calendar_link": result.get("calendar_link"),
                    "response": result.get("message", "Cita agendada exitosamente")
                }
            else:
                logger.warning(f"Google Calendar booking returned {response.status_code}")
                return {"success": False, "message": "Error creando evento"}
                
        except Exception as e:
            logger.error(f"Error booking Google Calendar: {e}")
            return {"success": False, "message": "Error del servicio"}
    
    def _book_generic_api(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reservar con API genérica"""
        try:
            response = requests.post(
                f"{self.company_config.schedule_service_url}/schedule-request",
                json=booking_data,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Generic booking API returned {response.status_code}")
                return {"success": False, "message": "Servicio no disponible"}
                
        except Exception as e:
            logger.error(f"Error with generic booking API: {e}")
            return {"success": False, "message": "Error del servicio"}
    
    def _format_booking_success(self, booking_result: Dict[str, Any]) -> str:
        """Formatear mensaje de éxito de reserva"""
        base_message = f"✅ ¡Cita agendada exitosamente en {self.company_config.company_name}!"
        
        details = []
        if booking_result.get('booking_id'):
            details.append(f"📋 ID de reserva: {booking_result['booking_id']}")
        
        if booking_result.get('calendar_link'):
            details.append(f"📅 Enlace al calendario: {booking_result['calendar_link']}")
        
        if booking_result.get('confirmation_email'):
            details.append("📧 Recibirás confirmación por email")
        
        if details:
            base_message += "\n\n" + "\n".join(details)
        
        return base_message + f"\n\n{booking_result.get('response', '')}"
    
    def _format_chat_history(self, chat_history: list) -> List[Dict[str, str]]:
        """Formatear historial de chat para APIs"""
        return [
            {
                "content": msg.content if hasattr(msg, 'content') else str(msg),
                "type": getattr(msg, 'type', 'user')
            } for msg in chat_history
        ]
    
    def _generate_base_schedule_response(self, question: str, inputs: Dict[str, Any], 
                                       schedule_context: str, required_fields: List[str]) -> str:
        """Generar respuesta base para agendamiento con contexto RAG"""
        fields_text = "\n".join([f"- {field.title()}" for field in required_fields])
        
        basic_response = f"""Perfecto, te ayudo con tu cita en {self.company_config.company_name}.

Para agendar necesito:
{fields_text}

¿Puedes proporcionarme esta información? 📅"""

        # Agregar información específica del RAG si está disponible
        if schedule_context and len(schedule_context) > 100:
            context_lines = schedule_context.split('\n')
            relevant_info = []
            for line in context_lines:
                if any(word in line.lower() for word in ['preparación', 'requisitos', 'recomendación', 'antes', 'abono', 'valoración']):
                    relevant_info.append(line.strip())
            
            if relevant_info:
                basic_response += f"\n\nInformación adicional:\n" + "\n".join(relevant_info[:3])
        
        return basic_response
    
    # Métodos auxiliares mantenidos del código original
    def _extract_date_from_question(self, question, chat_history=None):
        """Extraer fecha de la pregunta o historial"""
        import re
        from datetime import datetime, timedelta
        
        # Buscar formato DD-MM-YYYY
        match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', question)
        if match:
            return match.group(0).replace('/', '-')
        
        # Palabras relativas
        text_lower = question.lower()
        today = datetime.now()
        
        if "hoy" in text_lower:
            return today.strftime("%d-%m-%Y")
        elif "mañana" in text_lower:
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime("%d-%m-%Y")
        elif "pasado mañana" in text_lower:
            day_after = today + timedelta(days=2)
            return day_after.strftime("%d-%m-%Y")
        
        return None
    
    def _extract_treatment_from_question(self, question):
        """Extraer tratamiento específico de la empresa"""
        question_lower = question.lower()
        
        # Buscar en las configuraciones de tratamientos
        schedules_config = self._get_schedules_configuration()
        for treatment in schedules_config.keys():
            if treatment.lower() in question_lower:
                return treatment
        
        return "tratamiento general"
    
    def _extract_patient_info_from_history(self, chat_history: list) -> bool:
        """Extraer información del paciente del historial"""
        if not chat_history:
            return False
            
        history_text = " ".join([msg.content if hasattr(msg, 'content') else str(msg) for msg in chat_history])
        
        # Verificar presencia de información clave
        has_name = any(word in history_text.lower() for word in ["nombre", "llamo", "soy"])
        has_contact = any(char.isdigit() for char in history_text) and len([c for c in history_text if c.isdigit()]) >= 7
        has_date_or_time = any(word in history_text.lower() for word in ["fecha", "día", "mañana", "hoy", "hora"])
        
        return has_name and (has_contact or has_date_or_time)
    
    def _filter_slots_by_configuration(self, available_slots, treatment_config):
        """Filtrar slots por configuración del tratamiento"""
        try:
            if not available_slots:
                return []
            
            required_duration = treatment_config['duration']
            sessions = treatment_config.get('sessions', 1)
            
            # Para múltiples sesiones, necesitamos más tiempo o slots consecutivos
            if sessions > 1:
                required_duration = required_duration * sessions
            
            required_slots = max(1, required_duration // 30)
            
            times = []
            for slot in available_slots:
                if isinstance(slot, dict) and "time" in slot:
                    times.append(slot["time"])
                elif isinstance(slot, str):
                    times.append(slot)
            
            times.sort()
            filtered = []
            
            if required_slots == 1:
                return [f"{time} - {self._add_minutes_to_time(time, required_duration)}" for time in times]
            
            # Para tratamientos que requieren múltiples slots
            for i in range(len(times) - required_slots + 1):
                consecutive_times = times[i:i + required_slots]
                if self._are_consecutive_times(consecutive_times):
                    start_time = consecutive_times[0]
                    end_time = self._add_minutes_to_time(start_time, required_duration)
                    filtered.append(f"{start_time} - {end_time}")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering slots: {e}")
            return []
    
    def _are_consecutive_times(self, times):
        """Verificar tiempos consecutivos"""
        for i in range(len(times) - 1):
            current_minutes = self._time_to_minutes(times[i])
            next_minutes = self._time_to_minutes(times[i + 1])
            if next_minutes - current_minutes != 30:
                return False
        return True
    
    def _time_to_minutes(self, time_str):
        """Convertir hora a minutos"""
        try:
            time_clean = time_str.strip()
            if ':' in time_clean:
                parts = time_clean.split(':')
                hours = int(parts[0])
                minutes = int(parts[1])
                return hours * 60 + minutes
            return 0
        except (ValueError, IndexError):
            return 0
    
    def _add_minutes_to_time(self, time_str, minutes_to_add):
        """Sumar minutos a hora"""
        try:
            total_minutes = self._time_to_minutes(time_str) + minutes_to_add
            hours = (total_minutes // 60) % 24
            minutes = total_minutes % 60
            return f"{hours:02d}:{minutes:02d}"
        except:
            return time_str
    
    def _format_slots_response(self, slots, date, treatment_config):
        """Formatear respuesta de horarios con información del tratamiento"""
        if not slots:
            treatment_name = "tratamiento"
            duration = treatment_config.get('duration', 60)
            return f"No hay horarios disponibles para {date} en {self.company_config.company_name} (tratamiento de {duration} min)."
        
        # Información adicional del tratamiento
        duration = treatment_config.get('duration', 60)
        sessions = treatment_config.get('sessions', 1)
        deposit = treatment_config.get('deposit', 0)
        
        slots_text = "\n".join(f"- {slot}" for slot in slots)
        
        response = f"Horarios disponibles para {date} en {self.company_config.company_name}:\n{slots_text}"
        
        # Agregar información adicional si es relevante
        if sessions > 1:
            response += f"\n\n⏱️ Duración: {duration} min ({sessions} sesiones)"
        else:
            response += f"\n\n⏱️ Duración: {duration} minutos"
        
        if deposit > 0:
            response += f"\n💰 Abono requerido: ${deposit:,}"
        
        return response
    
    # Métodos específicos para integraciones que no se implementaron en _call_check_availability
    def _check_calendly_availability(self, date: str, treatment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verificar disponibilidad en Calendly"""
        try:
            # Implementar integración con Calendly API
            response = requests.get(
                f"{self.company_config.schedule_service_url}/calendly/availability",
                params={
                    "date": date,
                    "duration": treatment_config['duration'],
                    "event_type": treatment_config.get('calendly_event_type', 'default')
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            return None
            
        except Exception as e:
            logger.error(f"Error with Calendly API: {e}")
            return None
    
    def _check_webhook_availability(self, date: str, treatment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verificar disponibilidad vía webhook"""
        try:
            # Enviar webhook para consultar disponibilidad
            webhook_data = {
                "action": "check_availability",
                "date": date,
                "treatment": treatment_config,
                "company_id": self.company_config.company_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                self.company_config.schedule_service_url,
                json=webhook_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            return None
            
        except Exception as e:
            logger.error(f"Error with webhook availability: {e}")
            return None
    
    def _book_calendly(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reservar cita en Calendly"""
        try:
            # Implementar booking con Calendly
            response = requests.post(
                f"{self.company_config.schedule_service_url}/calendly/book",
                json=booking_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "booking_url": result.get("booking_url"),
                    "response": "Cita programada en Calendly. Revisa tu email para confirmar."
                }
            return {"success": False, "message": "Error con Calendly"}
            
        except Exception as e:
            logger.error(f"Error booking Calendly: {e}")
            return {"success": False, "message": "Error del servicio"}
    
    def _book_webhook(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reservar cita vía webhook"""
        try:
            webhook_data = {
                "action": "create_booking",
                **booking_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                self.company_config.schedule_service_url,
                json=webhook_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "webhook_response": result,
                    "response": "Solicitud de cita enviada exitosamente"
                }
            return {"success": False, "message": "Error procesando webhook"}
            
        except Exception as e:
            logger.error(f"Error with webhook booking: {e}")
            return {"success": False, "message": "Error del servicio"}
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar cadena del agente"""
        return self.chain.invoke(inputs)

    
    def check_availability(self, question: str, chat_history: list, schedule_context: Dict[str, Any]) -> str:
        """
        Verifica disponibilidad basándose en la lógica actual o devuelve un mensaje por defecto.
        """
        try:
            company_name = schedule_context.get("company_name", "la empresa")
            services = schedule_context.get("services", [])
            formatted_services = self._format_services(services)
    
            # Lógica simple: responder con instrucciones
            return (
                f"Actualmente no tengo acceso a la agenda en tiempo real para {company_name}, "
                f"pero puedo ayudarte a programar una cita.\n\n"
                f"Por favor indícame:\n"
                f"📅 Fecha deseada (DD-MM-YYYY)\n"
                f"🩺 Tipo de servicio ({formatted_services})"
            )
        except Exception as e:
            logger.error(f"Error en check_availability para {company_name}: {e}")
            return f"❌ No pude verificar disponibilidad en {company_name}. ¿Deseas que te conecte con un asesor?"


    def get_integration_status(self) -> Dict[str, Any]:
        """Obtener estado de la integración de agendamiento"""
        return {
            "integration_type": self.integration_type,
            "service_available": self.schedule_service_available,
            "service_url": self.company_config.schedule_service_url,
            "last_check": self.schedule_status_last_check,
            "company_id": self.company_config.company_id,
            "schedules_configured": len(self._get_schedules_configuration())
        }

    # Agregar este método al ScheduleAgent (app/agents/schedule_agent.py)
    
    def _format_services(self, services) -> str:
        """Convierte services en un string legible, sin errores - Método requerido por AvailabilityAgent"""
        try:
            if isinstance(services, dict):
                return ", ".join(services.keys())
            elif isinstance(services, list):
                return ", ".join(str(s) for s in services)
            elif isinstance(services, str):
                return services
            else:
                return "servicios disponibles"  # Fallback seguro
        except Exception as e:
            logger.warning(f"Error formatting services for {self.company_config.company_id}: {e}")
            return "servicios disponibles"
    
    def check_availability(self, question: str, chat_history: list, schedule_context: Dict[str, Any]) -> str:
        """
        Método mejorado para verificar disponibilidad - llamado por AvailabilityAgent
        """
        try:
            company_name = schedule_context.get("company_name", self.company_config.company_name)
            services = schedule_context.get("services", self.company_config.services)
            
            # Usar el método _format_services local
            formatted_services = self._format_services(services)
            
            # Extraer fecha de la pregunta
            date = self._extract_date_from_question(question, chat_history)
            treatment = self._extract_treatment_from_question(question)
            
            if date and treatment:
                # Intentar verificar disponibilidad real si tenemos API
                try:
                    availability_data = self._call_check_availability(date, treatment)
                    if availability_data and availability_data.get("available_slots"):
                        slots = availability_data["available_slots"]
                        return self._format_availability_response(slots, date, treatment, company_name)
                except Exception as api_error:
                    logger.warning(f"API availability check failed: {api_error}")
            
            # Respuesta por defecto con servicios formateados
            return (
                f"Para consultar disponibilidad en {company_name}, necesito:\n\n"
                f"📅 Fecha específica (DD-MM-YYYY)\n"
                f"🩺 Tipo de servicio ({formatted_services})\n\n"
                f"¿Puedes proporcionarme estos datos?"
            )
            
        except Exception as e:
            logger.error(f"Error en check_availability para {schedule_context.get('company_name', 'empresa')}: {e}")
            return f"❌ No pude verificar disponibilidad. Te conectaré con un asesor."
    
    def _format_availability_response(self, slots: list, date: str, treatment: str, company_name: str) -> str:
        """Formatea la respuesta de disponibilidad"""
        if not slots:
            return f"No hay horarios disponibles para {treatment} el {date} en {company_name}."
        
        slots_text = "\n".join([f"• {slot}" for slot in slots[:5]])  # Máximo 5 slots
        
        return (
            f"✅ Horarios disponibles para {treatment} el {date} en {company_name}:\n\n"
            f"{slots_text}\n\n"
            f"¿Te gustaría reservar alguno de estos horarios?"
        )
    
    def _extract_date_from_question(self, question: str, chat_history: list) -> str:
        """Extrae fecha de la pregunta con patrones mejorados"""
        import re
        from datetime import datetime, timedelta
        
        # Patrones de fecha
        date_patterns = [
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',  # DD/MM/YYYY o DD-MM-YYYY
            r'\b(\d{2,4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD o YYYY-MM-DD
        ]
        
        # Buscar en la pregunta actual
        text_to_search = question.lower()
        
        for pattern in date_patterns:
            match = re.search(pattern, text_to_search)
            if match:
                try:
                    # Intentar parsear la fecha
                    groups = match.groups()
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        year, month, day = groups
                    else:  # DD-MM-YYYY
                        day, month, year = groups
                    
                    # Crear fecha válida
                    if len(year) == 2:
                        year = f"20{year}"
                    
                    parsed_date = datetime(int(year), int(month), int(day))
                    return parsed_date.strftime("%d-%m-%Y")
                except (ValueError, TypeError):
                    continue
        
        # Palabras relativas comunes
        today = datetime.now()
        relative_dates = {
            'hoy': today,
            'mañana': today + timedelta(days=1),
            'pasado mañana': today + timedelta(days=2),
            'lunes': today + timedelta(days=(7-today.weekday()) % 7),
            'martes': today + timedelta(days=(8-today.weekday()) % 7),
            'miércoles': today + timedelta(days=(9-today.weekday()) % 7),
            'jueves': today + timedelta(days=(10-today.weekday()) % 7),
            'viernes': today + timedelta(days=(11-today.weekday()) % 7),
        }
        
        for word, date_obj in relative_dates.items():
            if word in text_to_search:
                return date_obj.strftime("%d-%m-%Y")
        
        return None
    
    def _extract_treatment_from_question(self, question: str) -> str:
        """Extrae el tipo de tratamiento de la pregunta"""
        question_lower = question.lower()
        
        # Obtener tratamientos de la configuración
        if hasattr(self.company_config, 'treatment_durations') and self.company_config.treatment_durations:
            for treatment in self.company_config.treatment_durations.keys():
                if treatment.lower() in question_lower:
                    return treatment
        
        # Palabras clave genéricas de tratamientos
        treatment_keywords = [
            'limpieza', 'consulta', 'revisión', 'tratamiento', 'terapia',
            'botox', 'relleno', 'facial', 'dental', 'implante', 'ortodoncia'
        ]
        
        for keyword in treatment_keywords:
            if keyword in question_lower:
                return keyword
        
        return "consulta general"
    
    def _call_check_availability(self, date: str, treatment: str) -> Dict[str, Any]:
        """Llama al API de disponibilidad si está configurado"""
        if not self.schedule_service_available:
            return None
        
        try:
            treatment_config = self._get_treatment_configuration(treatment)
            
            if self.integration_type == 'google_calendar':
                return self._check_google_calendar_availability(date, treatment_config)
            elif self.integration_type == 'calendly':
                return self._check_calendly_availability(date, treatment_config)
            elif self.integration_type == 'webhook':
                return self._check_webhook_availability(date, treatment_config)
            else:
                return self._check_generic_availability(date, treatment_config)
                
        except Exception as e:
            logger.error(f"Error calling availability endpoint: {e}")
            return None
