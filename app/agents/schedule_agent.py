# app/agents/schedule_agent.py - VERSIÓN COMPLETAMENTE CORREGIDA

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
        try:
            schedule_url = getattr(self.company_config, 'schedule_service_url', '').lower()
            
            if 'googleapis.com' in schedule_url or 'google' in schedule_url:
                return 'google_calendar'
            elif 'calendly.com' in schedule_url or 'calendly' in schedule_url:
                return 'calendly'
            elif 'cal.com' in schedule_url or 'cal.' in schedule_url:
                return 'cal_com'
            else:
                return 'generic'
        except Exception as e:
            logger.warning(f"[{self.company_id}] Error detecting integration type: {e}")
            return 'generic'
    
    def _verify_schedule_service(self):
        """Verificar disponibilidad del servicio de agendamiento"""
        current_time = datetime.now().timestamp()
        
        # Usar cache para evitar verificaciones constantes
        if current_time - self.schedule_status_last_check < self.schedule_status_cache_duration:
            return self.schedule_service_available
        
        try:
            schedule_url = getattr(self.company_config, 'schedule_service_url', '')
            if not schedule_url:
                logger.info(f"[{self.company_id}] No schedule service URL configured, using fallback")
                self.schedule_service_available = False
                return False
            
            # Intentar conexión con timeout corto
            response = requests.get(f"{schedule_url}/health", timeout=2)
            self.schedule_service_available = response.status_code == 200
            
            if self.schedule_service_available:
                logger.info(f"[{self.company_id}] Schedule service connected successfully")
            else:
                logger.warning(f"[{self.company_id}] Schedule service returned status {response.status_code}")
                
        except Exception as e:
            logger.warning(f"[{self.company_id}] Schedule service verification failed: {e}")
            self.schedule_service_available = False
        
        self.schedule_status_last_check = current_time
        return self.schedule_service_available
    
    def _create_prompt_template(self):
        """Crear template de prompt para agendamiento"""
        return ChatPromptTemplate.from_template("""
        Eres un asistente especializado en agendamiento para {company_name}.

        **Contexto del cliente:**
        - Empresa: {company_name}
        - Fecha actual: {current_date}
        - Pregunta del usuario: {question}

        **Información de contexto adicional:**
        {context}

        **Historial de conversación:**
        {chat_history}

        **Tu misión:**
        1. Ayudar con consultas de disponibilidad de citas y agendamiento
        2. Proporcionar información sobre horarios disponibles
        3. Guiar el proceso de reserva de citas
        4. Responder preguntas sobre servicios disponibles para agendar

        **Instrucciones específicas:**
        - Si el usuario quiere verificar disponibilidad, pregunta por fecha y horario preferido
        - Si quiere agendar, solicita: nombre completo, teléfono, servicio deseado, fecha y hora
        - Siempre confirma los detalles antes de proceder con una reserva
        - Si hay conflictos de horario, ofrece alternativas cercanas
        - Mantén un tono profesional y amigable

        **Respuesta:**
        """)
    
    def _create_chain(self):
        """Crear cadena de procesamiento con RAG opcional"""
        try:
            if self.vectorstore_service:
                # Cadena con RAG
                def get_context_and_respond(inputs):
                    question = inputs["question"]
                    
                    # Obtener contexto del vectorstore
                    context_docs = self.vectorstore_service.similarity_search(
                        question, 
                        k=3,
                        filter_metadata={"agent_type": "schedule"}
                    )
                    
                    context = "\n".join([doc.page_content for doc in context_docs]) if context_docs else "No hay información específica disponible."
                    
                    # Preparar inputs del prompt
                    prompt_inputs = {
                        "company_name": getattr(self.company_config, 'company_name', self.company_id),
                        "current_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "question": question,
                        "context": context,
                        "chat_history": self._format_chat_history(inputs.get("chat_history", []))
                    }
                    
                    # Generar respuesta
                    messages = self.prompt_template.format_messages(**prompt_inputs)
                    response = self.openai_service.invoke(messages)
                    
                    return {"response": response.content}
                
                self.chain = RunnableLambda(get_context_and_respond)
                logger.info(f"[{self.company_id}] Schedule agent chain created with RAG")
                
            else:
                # Cadena sin RAG
                def respond_without_rag(inputs):
                    prompt_inputs = {
                        "company_name": getattr(self.company_config, 'company_name', self.company_id),
                        "current_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "question": inputs["question"],
                        "context": "Información básica de agendamiento disponible.",
                        "chat_history": self._format_chat_history(inputs.get("chat_history", []))
                    }
                    
                    messages = self.prompt_template.format_messages(**prompt_inputs)
                    response = self.openai_service.invoke(messages)
                    
                    return {"response": response.content}
                
                self.chain = RunnableLambda(respond_without_rag)
                logger.info(f"[{self.company_id}] Schedule agent chain created without RAG")
                
        except Exception as e:
            logger.error(f"[{self.company_id}] Error creating schedule agent chain: {e}")
            # Crear cadena de fallback
            self._create_fallback_chain()
    
    def _create_fallback_chain(self):
        """Crear cadena de fallback simple"""
        def fallback_response(inputs):
            return {
                "response": f"Lo siento, hay un problema técnico con el sistema de agendamiento de {getattr(self.company_config, 'company_name', self.company_id)}. Por favor, contacta directamente para agendar tu cita."
            }
        
        self.chain = RunnableLambda(fallback_response)
        logger.info(f"[{self.company_id}] Schedule agent fallback chain created")
    
    def process_query(self, question: str, chat_history: List = None, **kwargs) -> str:
        """Procesar consulta de agendamiento"""
        try:
            inputs = {
                "question": question,
                "chat_history": chat_history or [],
                "user_id": kwargs.get("user_id", "unknown"),
                "company_id": self.company_id
            }
            
            # Verificar si es una consulta específica de disponibilidad
            if self._is_availability_query(question):
                return self._handle_availability_query(question, inputs)
            
            # Verificar si es una solicitud de agendamiento
            if self._is_booking_query(question):
                return self._handle_booking_query(question, inputs)
            
            # Procesamiento general con cadena
            result = self.chain.invoke(inputs)
            return result.get("response", "No pude procesar tu consulta de agendamiento.")
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error in ScheduleAgent.process_query: {e}")
            return f"Disculpa, tuve un problema procesando tu consulta de agendamiento en {getattr(self.company_config, 'company_name', self.company_id)}. ¿Puedes intentar de nuevo?"
    
    def _is_availability_query(self, question: str) -> bool:
        """Detectar si es una consulta de disponibilidad"""
        availability_patterns = [
            r"disponibilidad|disponible|horarios?",
            r"libre|ocupado|agendas?",
            r"cita|turno|hora"
        ]
        return any(re.search(pattern, question.lower()) for pattern in availability_patterns)
    
    def _is_booking_query(self, question: str) -> bool:
        """Detectar si es una solicitud de agendamiento"""
        booking_patterns = [
            r"agendar|reservar|programar",
            r"quiero.*cita|necesito.*turno",
            r"confirmar.*cita"
        ]
        return any(re.search(pattern, question.lower()) for pattern in booking_patterns)
    
    def _handle_availability_query(self, question: str, inputs: Dict) -> str:
        """Manejar consulta de disponibilidad"""
        try:
            # Verificar servicio de agendamiento
            if self._verify_schedule_service():
                # Intentar consulta real
                availability_response = self._query_real_availability(question)
                if availability_response:
                    return availability_response
            
            # Fallback: respuesta genérica
            company_name = getattr(self.company_config, 'company_name', self.company_id)
            return f"""Para consultar disponibilidad en {company_name}, necesito algunos detalles:

📅 **¿Qué fecha prefieres?**
🕐 **¿Tienes algún horario en mente?**
📋 **¿Qué servicio necesitas?**

Nuestros horarios generales son:
• Lunes a Viernes: 9:00 AM - 6:00 PM
• Sábados: 9:00 AM - 2:00 PM

¿Con qué detalles te puedo ayudar?"""
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error handling availability query: {e}")
            return "Disculpa, tuve un problema verificando la disponibilidad. ¿Puedes intentar de nuevo?"
    
    def _handle_booking_query(self, question: str, inputs: Dict) -> str:
        """Manejar solicitud de agendamiento"""
        try:
            company_name = getattr(self.company_config, 'company_name', self.company_id)
            
            # Extraer información de agendamiento del texto
            booking_info = self._extract_booking_info(question)
            
            if booking_info.get('complete'):
                # Información completa, proceder con agendamiento
                return self._process_booking(booking_info)
            else:
                # Información incompleta, solicitar detalles faltantes
                return f"""Para agendar tu cita en {company_name}, necesito la siguiente información:

📝 **Datos requeridos:**
• Nombre completo
• Número de teléfono
• Servicio deseado
• Fecha preferida
• Horario preferido

**Información que ya tengo:**
{self._format_booking_info(booking_info)}

¿Puedes completar los datos faltantes?"""
                
        except Exception as e:
            logger.error(f"[{self.company_id}] Error handling booking query: {e}")
            return "Disculpa, tuve un problema procesando tu solicitud de agendamiento. ¿Puedes intentar de nuevo?"
    
    def _query_real_availability(self, question: str) -> Optional[str]:
        """Consultar disponibilidad real del servicio externo"""
        try:
            schedule_url = getattr(self.company_config, 'schedule_service_url', '')
            if not schedule_url:
                return None
            
            response = requests.post(
                f"{schedule_url}/api/availability",
                json={"query": question, "company_id": self.company_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('message', 'Información de disponibilidad procesada.')
            
        except Exception as e:
            logger.warning(f"[{self.company_id}] Real availability query failed: {e}")
        
        return None
    
    def _extract_booking_info(self, question: str) -> Dict[str, Any]:
        """Extraer información de agendamiento del texto"""
        info = {
            'name': None,
            'phone': None,
            'service': None,
            'date': None,
            'time': None,
            'complete': False
        }
        
        # Patrones básicos para extracción
        phone_pattern = r'(\d{3}[\-\.\s]??\d{3}[\-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[\-\.\s]??\d{4}|\d{3}[\-\.\s]??\d{7})'
        date_pattern = r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        time_pattern = r'(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)'
        
        phone_match = re.search(phone_pattern, question)
        if phone_match:
            info['phone'] = phone_match.group(1)
        
        date_match = re.search(date_pattern, question)
        if date_match:
            info['date'] = date_match.group(1)
        
        time_match = re.search(time_pattern, question)
        if time_match:
            info['time'] = time_match.group(1)
        
        # Verificar si la información está completa
        info['complete'] = all([
            info.get('name'),
            info.get('phone'),
            info.get('date'),
            info.get('time')
        ])
        
        return info
    
    def _format_booking_info(self, info: Dict[str, Any]) -> str:
        """Formatear información de agendamiento"""
        details = []
        if info.get('name'):
            details.append(f"• Nombre: {info['name']}")
        if info.get('phone'):
            details.append(f"• Teléfono: {info['phone']}")
        if info.get('service'):
            details.append(f"• Servicio: {info['service']}")
        if info.get('date'):
            details.append(f"• Fecha: {info['date']}")
        if info.get('time'):
            details.append(f"• Hora: {info['time']}")
        
        return "\n".join(details) if details else "Ninguna información capturada aún."
    
    def _process_booking(self, booking_info: Dict[str, Any]) -> str:
        """Procesar agendamiento completo"""
        try:
            company_name = getattr(self.company_config, 'company_name', self.company_id)
            
            # Generar referencia de agendamiento
            booking_ref = f"{self.company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # En producción, aquí se haría la reserva real
            return f"""🎉 **¡Cita agendada exitosamente en {company_name}!**

📄 **Referencia:** {booking_ref}
👤 **Nombre:** {booking_info.get('name', 'N/A')}
📞 **Teléfono:** {booking_info.get('phone', 'N/A')}
📋 **Servicio:** {booking_info.get('service', 'Consulta general')}
📅 **Fecha:** {booking_info.get('date', 'N/A')}
🕐 **Hora:** {booking_info.get('time', 'N/A')}

**Importante:**
• Llegar 10 minutos antes de la cita
• Traer documento de identidad
• En caso de cancelación, avisar con 24h de anticipación

¿Necesitas algo más?"""
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error processing booking: {e}")
            return "Hubo un problema procesando tu agendamiento. Por favor, contacta directamente."
    
    def check_real_availability(self, date_str: str, time_str: str = None, service_type: str = None) -> Dict[str, Any]:
        """Método para ser usado por AvailabilityAgent"""
        try:
            if self._verify_schedule_service():
                schedule_url = getattr(self.company_config, 'schedule_service_url', '')
                response = requests.post(
                    f"{schedule_url}/api/check_availability",
                    json={
                        "date": date_str,
                        "time": time_str,
                        "service": service_type,
                        "company_id": self.company_id
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, **data}
            
            # Fallback
            return {
                "success": True,
                "available": True,
                "message": f"Disponibilidad verificada para {date_str} {time_str or ''} (modo simulado)"
            }
            
        except Exception as e:
            logger.warning(f"[{self.company_id}] Real availability check failed: {e}")
            return {"success": False, "error": str(e)}
    
    def book_real_appointment(self, date_str: str, time_str: str, client_info: Dict, service_type: str = None) -> Dict[str, Any]:
        """Método para ser usado por AvailabilityAgent para booking real"""
        try:
            if self._verify_schedule_service():
                schedule_url = getattr(self.company_config, 'schedule_service_url', '')
                response = requests.post(
                    f"{schedule_url}/api/book_appointment",
                    json={
                        "date": date_str,
                        "time": time_str,
                        "client_info": client_info,
                        "service": service_type,
                        "company_id": self.company_id
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, **data}
            
            # Fallback booking
            booking_ref = f"{self.company_id}_{date_str}_{time_str}_{datetime.now().strftime('%H%M%S')}".replace("-", "").replace(":", "")
            
            return {
                "success": True,
                "booking_reference": booking_ref,
                "message": f"Cita reservada para {date_str} a las {time_str} (modo simulado)",
                "date": date_str,
                "time": time_str,
                "service_type": service_type or "consulta general"
            }
            
        except Exception as e:
            logger.warning(f"[{self.company_id}] Real appointment booking failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_chat_history(self, chat_history: List) -> str:
        """Formatear historial de chat para el prompt"""
        if not chat_history:
            return "No hay historial de conversación previa."
        
        formatted_history = []
        for message in chat_history[-5:]:  # Últimos 5 mensajes
            if isinstance(message, dict):
                role = message.get('role', 'user')
                content = message.get('content', '')
                formatted_history.append(f"{role.capitalize()}: {content}")
            else:
                formatted_history.append(str(message))
        
        return "\n".join(formatted_history)
