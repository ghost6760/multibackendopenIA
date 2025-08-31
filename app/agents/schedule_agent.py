from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any
import requests
import logging

logger = logging.getLogger(__name__)

class ScheduleAgent(BaseAgent):
    """Agente de agendamiento multi-tenant con integración Selenium y RAG"""
    
    def _initialize_agent(self):
        """Inicializar agente de agendamiento"""
        self.prompt_template = self._create_prompt_template()
        self.selenium_service_available = False
        self.selenium_status_last_check = 0
        self.selenium_status_cache_duration = 30
        self.vectorstore_service = None  # Se inyecta externamente
        
        # Verificar conexión inicial con servicio Selenium específico
        self._verify_selenium_service()
        
        # Crear cadena
        self._create_chain()
    
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore específico de la empresa"""
        self.vectorstore_service = vectorstore_service
        # Recrear cadena con RAG
        self._create_chain()
    
    def _create_chain(self):
        """Crear cadena de agendamiento con RAG opcional"""
        self.chain = (
            {
                "selenium_status": self._get_selenium_status,
                "schedule_context": self._get_schedule_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "user_id": lambda x: x.get("user_id", "default_user"),
                "company_name": lambda x: self.company_config.company_name,
                "services": lambda x: self.company_config.services
            }
            | RunnableLambda(self._process_schedule_request)
        )
    
    def _create_prompt_template(self):
        """No se usa directamente, se procesa en _process_schedule_request"""
        pass
    
    def _get_selenium_status(self, inputs):
        """Obtener estado del servicio Selenium específico de la empresa"""
        if self.selenium_service_available:
            return f"✅ Sistema de agendamiento ACTIVO para {self.company_config.company_name} (Conectado a {self.company_config.schedule_service_url})"
        else:
            return f"⚠️ Sistema de agendamiento NO DISPONIBLE para {self.company_config.company_name} (Verificar conexión: {self.company_config.schedule_service_url})"
    
    def _get_schedule_context(self, inputs):
        """Obtener contexto de agendamiento desde documentos RAG"""
        try:
            question = inputs.get("question", "")
            
            if not self.vectorstore_service:
                return self._get_basic_schedule_info()
            
            # Buscar información relacionada con agendamiento
            schedule_query = f"cita agenda horario duración preparación requisitos {question}"
            docs = self.vectorstore_service.search_by_company(
                schedule_query,
                self.company_config.company_id,
                k=2
            )
            
            if not docs:
                return self._get_basic_schedule_info()
            
            # Extraer información relevante para agendamiento
            context_parts = []
            for doc in docs:
                if hasattr(doc, 'page_content') and doc.page_content:
                    content = doc.page_content.lower()
                    if any(word in content for word in ['cita', 'agenda', 'horario', 'duración', 'preparación', 'requisitos']):
                        context_parts.append(doc.page_content)
                elif isinstance(doc, dict) and 'content' in doc:
                    content = doc['content'].lower()
                    if any(word in content for word in ['cita', 'agenda', 'horario', 'duración', 'preparación', 'requisitos']):
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
        treatment_info = []
        for treatment, duration in self.company_config.treatment_durations.items():
            treatment_info.append(f"- {treatment}: {duration} minutos")
        
        return f"""Información de agendamiento de {self.company_config.company_name}:

Duraciones de tratamientos:
{chr(10).join(treatment_info)}

Servicios: {self.company_config.services}"""
    
    def _verify_selenium_service(self, force_check: bool = False) -> bool:
        """Verificar servicio Selenium específico de la empresa"""
        import time
        current_time = time.time()
        
        if not force_check and (current_time - self.selenium_status_last_check) < self.selenium_status_cache_duration:
            return self.selenium_service_available
        
        try:
            response = requests.get(
                f"{self.company_config.schedule_service_url}/health",
                timeout=3
            )
            
            if response.status_code == 200:
                self.selenium_service_available = True
                self.selenium_status_last_check = current_time
                return True
            else:
                self.selenium_service_available = False
                self.selenium_status_last_check = current_time
                return False
                
        except Exception as e:
            logger.warning(f"Selenium service verification failed for {self.company_config.company_name}: {e}")
            self.selenium_service_available = False
            self.selenium_status_last_check = current_time
            return False
    
    def _process_schedule_request(self, inputs):
        """Procesar solicitud de agendamiento con lógica específica de empresa y RAG"""
        try:
            question = inputs.get("question", "")
            user_id = inputs.get("user_id", "default_user")
            chat_history = inputs.get("chat_history", [])
            schedule_context = inputs.get("schedule_context", "")
            
            self._log_agent_activity("processing_schedule", {
                "question": question[:50],
                "rag_enabled": self.vectorstore_service is not None
            })
            
            # Verificar si es una consulta de disponibilidad
            if self._is_availability_check(question):
                return self._handle_availability_check(question, chat_history, schedule_context)
            
            # Verificar si es agendamiento completo
            if self._should_use_selenium(question, chat_history):
                return self._handle_selenium_scheduling(question, user_id, chat_history)
            
            # Respuesta base para solicitudes de agendamiento con contexto RAG
            return self._generate_base_schedule_response(question, inputs, schedule_context)
            
        except Exception as e:
            logger.error(f"Error in schedule processing for {self.company_config.company_name}: {e}")
            return f"Error procesando tu solicitud de agenda en {self.company_config.company_name}. Te conectaré con un especialista... 📋"
    
    def _is_availability_check(self, question: str) -> bool:
        """Verificar si solo consulta disponibilidad"""
        availability_keywords = [
            "disponibilidad para", "horarios disponibles", "qué horarios",
            "cuándo hay", "hay disponibilidad", "ver horarios"
        ]
        return any(keyword in question.lower() for keyword in availability_keywords)
    
    def _should_use_selenium(self, question: str, chat_history: list) -> bool:
        """Determinar si usar Selenium para agendamiento"""
        question_lower = question.lower()
        
        # Verificar keywords de agendamiento
        has_schedule_intent = any(keyword in question_lower for keyword in self.company_config.schedule_keywords)
        
        # Verificar información disponible
        has_patient_info = self._extract_patient_info_from_history(chat_history)
        
        return has_schedule_intent and self.selenium_service_available and has_patient_info
    
    def _handle_availability_check(self, question: str, chat_history: list, schedule_context: str):
        """Manejar consulta de disponibilidad con contexto RAG"""
        try:
            date = self._extract_date_from_question(question, chat_history)
            treatment = self._extract_treatment_from_question(question)
            
            if not date:
                # Usar información del RAG si está disponible
                context_info = ""
                if schedule_context and "duración" in schedule_context.lower():
                    context_info = f"\n\nInformación sobre tratamientos:\n{schedule_context}"
                
                return f"""Para consultar disponibilidad en {self.company_config.company_name}, necesito:

📅 Fecha específica (DD-MM-YYYY)
🩺 Tipo de {self.company_config.services.lower()} que te interesa{context_info}

¿Puedes proporcionarme estos datos?"""
            
            duration = self._get_treatment_duration(treatment)
            availability_data = self._call_check_availability(date)
            
            if not availability_data or not availability_data.get("available_slots"):
                return f"No hay horarios disponibles para {date} en {self.company_config.company_name}."
            
            filtered_slots = self._filter_slots_by_duration(
                availability_data["available_slots"], 
                duration
            )
            
            return self._format_slots_response(filtered_slots, date, duration)
            
        except Exception as e:
            logger.error(f"Error checking availability for {self.company_config.company_name}: {e}")
            return f"Error consultando disponibilidad en {self.company_config.company_name}. Te conectaré con un especialista."
    
    def _handle_selenium_scheduling(self, question: str, user_id: str, chat_history: list):
        """Manejar agendamiento con Selenium"""
        try:
            selenium_result = self._call_schedule_microservice(question, user_id, chat_history)
            
            if selenium_result.get('success'):
                return f"✅ ¡Cita agendada exitosamente en {self.company_config.company_name}! {selenium_result.get('response', '')}"
            elif selenium_result.get('requires_more_info'):
                return selenium_result.get('response', f"Necesito más información para agendar tu cita en {self.company_config.company_name}.")
            else:
                return f"No pude completar el agendamiento automático en {self.company_config.company_name}. Te conectaré con un especialista para completar tu cita."
                
        except Exception as e:
            logger.error(f"Error in Selenium scheduling for {self.company_config.company_name}: {e}")
            return f"Error en el agendamiento automático. Te conectaré con un especialista de {self.company_config.company_name}."
    
    def _generate_base_schedule_response(self, question: str, inputs: Dict[str, Any], schedule_context: str):
        """Generar respuesta base para agendamiento con contexto RAG"""
        basic_response = f"""Perfecto, te ayudo con tu cita en {self.company_config.company_name}.

Para agendar necesito:
- Nombre completo
- Número de cédula  
- Teléfono de contacto
- Fecha y hora preferida
- Tipo de {self.company_config.services.lower()} que te interesa"""

        # Agregar información específica del RAG si está disponible
        if schedule_context and len(schedule_context) > 100:
            # Extraer información relevante para el usuario
            context_lines = schedule_context.split('\n')
            relevant_info = []
            for line in context_lines:
                if any(word in line.lower() for word in ['preparación', 'requisitos', 'recomendación', 'antes']):
                    relevant_info.append(line.strip())
            
            if relevant_info:
                basic_response += f"\n\nInformación adicional:\n" + "\n".join(relevant_info[:3])
        
        basic_response += f"\n\n¿Puedes proporcionarme esta información? 📅"
        return basic_response
    
    # Métodos auxiliares (mantienen la misma implementación)
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
        
        # Buscar en las duraciones configuradas para esta empresa
        for treatment in self.company_config.treatment_durations.keys():
            if treatment.lower() in question_lower:
                return treatment
        
        return "tratamiento general"
    
    def _get_treatment_duration(self, treatment):
        """Obtener duración del tratamiento desde configuración de empresa"""
        return self.company_config.treatment_durations.get(treatment, 60)
    
    def _call_check_availability(self, date):
        """Llamar al endpoint de disponibilidad específico de la empresa"""
        try:
            response = requests.post(
                f"{self.company_config.schedule_service_url}/check-availability",
                json={
                    "date": date,
                    "company_id": self.company_config.company_id
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logger.warning(f"Availability endpoint returned {response.status_code} for {self.company_config.company_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling availability endpoint for {self.company_config.company_name}: {e}")
            return None
    
    def _call_schedule_microservice(self, question: str, user_id: str, chat_history: list):
        """Llamar al microservicio de agendamiento específico"""
        try:
            response = requests.post(
                f"{self.company_config.schedule_service_url}/schedule-request",
                json={
                    "message": question,
                    "user_id": user_id,
                    "company_id": self.company_config.company_id,
                    "company_name": self.company_config.company_name,
                    "chat_history": [
                        {
                            "content": msg.content if hasattr(msg, 'content') else str(msg),
                            "type": getattr(msg, 'type', 'user')
                        } for msg in chat_history
                    ]
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Schedule microservice returned {response.status_code} for {self.company_config.company_name}")
                return {"success": False, "message": "Servicio no disponible"}
                
        except Exception as e:
            logger.error(f"Error calling schedule microservice for {self.company_config.company_name}: {e}")
            return {"success": False, "message": "Error del servicio"}
    
    def _extract_patient_info_from_history(self, chat_history: list) -> bool:
        """Extraer información del paciente del historial"""
        if not chat_history:
            return False
            
        history_text = " ".join([msg.content if hasattr(msg, 'content') else str(msg) for msg in chat_history])
        
        has_name = any(word in history_text.lower() for word in ["nombre", "llamo", "soy"])
        has_phone = any(char.isdigit() for char in history_text) and len([c for c in history_text if c.isdigit()]) >= 7
        has_date = any(word in history_text.lower() for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name and (has_phone or has_date)
    
    def _filter_slots_by_duration(self, available_slots, required_duration):
        """Filtrar slots por duración requerida"""
        try:
            if not available_slots:
                return []
            
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
    
    def _format_slots_response(self, slots, date, duration):
        """Formatear respuesta de horarios"""
        if not slots:
            return f"No hay horarios disponibles para {date} en {self.company_config.company_name} (tratamiento de {duration} min)."
        
        slots_text = "\n".join(f"- {slot}" for slot in slots)
        return f"Horarios disponibles para {date} en {self.company_config.company_name} (tratamiento de {duration} min):\n{slots_text}"
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar cadena del agente"""
        return self.chain.invoke(inputs)
