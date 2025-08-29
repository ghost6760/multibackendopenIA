from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.models.conversation import ConversationManager
from app.config.company_config import get_company_config, CompanyConfig
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnableLambda
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.schema.output_parser import StrOutputParser
from flask import current_app
import logging
import json
import requests
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """Sistema multi-agente multi-empresa"""
    
    def __init__(self, company_id: str = "default"):
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.openai_service = OpenAIService()
        self.vectorstore_service = VectorstoreService(company_id)
        self.chat_model = self.openai_service.get_chat_model()
        self.retriever = self.vectorstore_service.get_retriever()
        self.conversation_manager = None  # Se inyecta cuando se usa
        
        # Configuración específica de empresa
        self.voice_enabled = current_app.config.get('VOICE_ENABLED', False)
        self.image_enabled = current_app.config.get('IMAGE_ENABLED', False)
        self.schedule_service_url = self.company_config.schedule_service_url
        self.is_local_development = current_app.config.get('ENVIRONMENT') == 'local'
        self.selenium_timeout = 30 if self.is_local_development else 60
        
        # Cache del estado de Selenium por empresa
        self.selenium_service_available = False
        self.selenium_status_last_check = 0
        self.selenium_status_cache_duration = 30
        
        # Inicializar agentes con configuración de empresa
        self.agents = self._initialize_agents()
        
        # Verificar servicio Selenium
        self._initialize_local_selenium_connection()
    
    def _initialize_agents(self):
        """Initialize all specialized agents with company configuration"""
        return {
            'router': self._create_router_agent(),
            'emergency': self._create_emergency_agent(),
            'sales': self._create_sales_agent(),
            'support': self._create_support_agent(),
            'schedule': self._create_enhanced_schedule_agent(),
            'availability': self._create_availability_agent()
        }
    
    def _verify_selenium_service(self, force_check: bool = False) -> bool:
        """Verificar disponibilidad del servicio Selenium específico de empresa con cache inteligente"""
        current_time = time.time()
        
        if not force_check and (current_time - self.selenium_status_last_check) < self.selenium_status_cache_duration:
            return self.selenium_service_available
        
        try:
            response = requests.get(
                f"{self.schedule_service_url}/health",
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
            logger.warning(f"Selenium service verification failed for company {self.company_id}: {e}")
            self.selenium_service_available = False
            self.selenium_status_last_check = current_time
            return False
    
    def _initialize_local_selenium_connection(self):
        """Inicializar y verificar conexión con microservicio específico de empresa"""
        try:
            logger.info(f"Intentando conectar con microservicio de {self.company_config.company_name} en: {self.schedule_service_url}")
            
            is_available = self._verify_selenium_service(force_check=True)
            
            if is_available:
                logger.info(f"✅ Conexión exitosa con microservicio de {self.company_config.company_name}")
            else:
                logger.warning(f"⚠️ Servicio de {self.company_config.company_name} no disponible")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando conexión con Selenium para {self.company_config.company_name}: {e}")
            self.selenium_service_available = False
    
    def _create_router_agent(self):
        """Agente Router: Clasifica la intención del usuario - Dinámico por empresa"""
        
        # Extraer keywords específicos de empresa
        business_rules = self.company_config.business_rules
        emergency_keywords = business_rules.get('emergency_keywords', ['emergencia', 'urgente'])
        sales_keywords = business_rules.get('sales_keywords', ['precio', 'información'])
        schedule_keywords = business_rules.get('schedule_keywords', ['agendar', 'cita'])
        
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un clasificador de intenciones para {self.company_config.company_name} ({self.company_config.industry_type}).

ANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:

1. **EMERGENCY** - Urgencias:
   - Palabras clave: {', '.join(emergency_keywords)}
   - Situaciones que requieren atención inmediata

2. **SALES** - Consultas comerciales:
   - Información sobre {self.company_config.services}
   - Palabras clave: {', '.join(sales_keywords)}
   - Comparación de servicios

3. **SCHEDULE** - Gestión de citas:
   - Palabras clave: {', '.join(schedule_keywords)}
   - Agendar, modificar o cancelar citas
   - Consultar disponibilidad

4. **SUPPORT** - Soporte general:
   - Información general de {self.company_config.company_name}
   - Consultas sobre procesos
   - Cualquier otra consulta

RESPONDE SOLO con el formato JSON:
{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación"
}}

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
        
        return router_prompt | self.chat_model | StrOutputParser()
    
    def _create_emergency_agent(self):
        """Agente de Emergencias: Maneja urgencias - Personalizado por empresa"""
        emergency_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.emergency_agent_name}, especialista en emergencias de {self.company_config.company_name}.

SITUACIÓN DETECTADA: Posible emergencia.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma/problema
3. Indica que el caso será escalado de emergencia
4. Proporciona información de contacto si es necesario:
   - Teléfono: {self.company_config.contact_info.get('phone', 'Contactar directamente')}
   - Email: {self.company_config.contact_info.get('email', 'info@empresa.com')}

TONO: Profesional, empático, tranquilizador pero urgente.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia de {self.company_config.company_name} ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        return emergency_prompt | self.chat_model | StrOutputParser()
    
    def _create_sales_agent(self):
        """Agente de Ventas: Especializado en información comercial - Dinámico por empresa"""
        sales_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, asesor comercial especializado de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
INDUSTRIA: {self.company_config.industry_type}
HORARIOS: {self.company_config.working_hours}

INFORMACIÓN DISPONIBLE:
{{context}}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del servicio solicitado
3. Beneficios principales (máximo 3)
4. Información de contacto si aplica
5. Llamada a la acción para agendar

CONTACTO:
- Teléfono: {self.company_config.contact_info.get('phone', 'Consultar')}
- Email: {self.company_config.contact_info.get('email', 'Consultar')}

TONO: Cálido, profesional, persuasivo.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 5 oraciones.

FINALIZA SIEMPRE con: "¿Te gustaría agendar tu cita en {self.company_config.company_name}? 📅"

Historial de conversación:
{{chat_history}}

Pregunta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_sales_context(inputs):
            """Obtener contexto RAG para ventas específico de empresa"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de {self.company_config.company_name}:
- {self.company_config.services}
- {self.company_config.industry_type}
- Atención personalizada
- Profesionales certificados
- Horarios: {self.company_config.working_hours}
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving sales context for company {self.company_id}: {e}")
                return f"Información básica disponible de {self.company_config.company_name}. Te conectaré con un especialista para detalles específicos."
        
        return (
            {
                "context": get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | sales_prompt
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_support_agent(self):
        """Agente de Soporte: Consultas generales y escalación - Personalizado por empresa"""
        support_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.support_agent_name}, especialista en soporte al cliente de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
INDUSTRIA: {self.company_config.industry_type}
HORARIOS: {self.company_config.working_hours}

OBJETIVO: Resolver consultas generales y facilitar navegación.

TIPOS DE CONSULTA:
- Información de {self.company_config.company_name} (ubicación, horarios)
- Procesos y políticas
- Escalación a especialistas
- Consultas generales sobre {self.company_config.services}

INFORMACIÓN DISPONIBLE:
{{context}}

INFORMACIÓN DE CONTACTO:
- Teléfono: {self.company_config.contact_info.get('phone', 'Consultar')}
- Email: {self.company_config.contact_info.get('email', 'Consultar')}
- Sitio web: {self.company_config.contact_info.get('website', 'Consultar')}

PROTOCOLO:
1. Respuesta directa a la consulta
2. Información adicional relevante de {self.company_config.company_name}
3. Opciones de seguimiento

TONO: Profesional, servicial, eficiente.
LONGITUD: Máximo 4 oraciones.
EMOJIS: Máximo 3 por respuesta.

Si no puedes resolver completamente: "Te conectaré con un especialista de {self.company_config.company_name} para resolver tu consulta específica. 👨‍💼"

Historial de conversación:
{{chat_history}}

Consulta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_support_context(inputs):
            """Obtener contexto RAG para soporte específico de empresa"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información general de {self.company_config.company_name}:
- {self.company_config.services}
- Horarios: {self.company_config.working_hours}
- Industria: {self.company_config.industry_type}
- Información institucional
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving support context for company {self.company_id}: {e}")
                return f"Información general de {self.company_config.company_name} disponible. Te conectaré con un especialista para consultas específicas."
        
        return (
            {
                "context": get_support_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | support_prompt
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_availability_agent(self):
        """Agente que verifica disponibilidad - Personalizado por empresa"""
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un agente de disponibilidad de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
HORARIOS LABORALES: {self.company_config.working_hours}

ESTADO DEL SISTEMA:
{{selenium_status}}

PROTOCOLO:
1. Verificar estado del servicio de {self.company_config.company_name}
2. Extraer la fecha (DD-MM-YYYY) y el servicio del mensaje
3. Consultar el RAG para obtener la duración del servicio (en minutos)
4. Llamar al endpoint /check-availability con la fecha
5. Filtrar los slots disponibles que puedan acomodar la duración
6. Devolver los horarios en formato legible

Ejemplo de respuesta:
"Horarios disponibles en {self.company_config.company_name} para {{fecha}} (servicio de {{duracion}} min):
- 09:00 - 10:00
- 10:30 - 11:30
- 14:00 - 15:00"

Si no hay disponibilidad: "No hay horarios disponibles en {self.company_config.company_name} para {{fecha}} con duración de {{duracion}} minutos."
Si hay error del sistema: "Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista."

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
        
        def get_availability_selenium_status(inputs):
            """Obtener estado del sistema Selenium para availability específico de empresa"""
            is_available = self._verify_selenium_service()
            
            if is_available:
                return f"✅ Sistema de {self.company_config.company_name} ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de {self.company_config.company_name} NO DISPONIBLE (Verificar conexión: {self.schedule_service_url})"
        
        def process_availability(inputs):
            """Procesar consulta de disponibilidad específica de empresa"""
            try:
                question = inputs.get("question", "")
                chat_history = inputs.get("chat_history", [])
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"=== AVAILABILITY AGENT {self.company_config.company_name} - PROCESANDO ===")
                logger.info(f"Pregunta: {question}")
                logger.info(f"Estado Selenium: {selenium_status}")
                
                if not self._verify_selenium_service():
                    logger.error(f"Servicio Selenium no disponible para {self.company_config.company_name}")
                    return f"Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista para verificar horarios. 👨‍💼"
                
                date = self._extract_date_from_question(question, chat_history)
                service = self._extract_service_from_question(question)
                
                if not date:
                    return f"Por favor especifica la fecha en formato DD-MM-YYYY para consultar disponibilidad en {self.company_config.company_name}."
                
                logger.info(f"Fecha extraída: {date}, Servicio: {service}")
                
                duration = self._get_service_duration(service)
                logger.info(f"Duración del servicio: {duration} minutos")
                
                availability_data = self._call_check_availability(date)
                
                if not availability_data:
                    logger.warning("No se obtuvieron datos de disponibilidad")
                    return f"Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista."
                
if not availability_data.get("available_slots"):
                    logger.info("No hay slots disponibles para la fecha solicitada")
                    return f"No hay horarios disponibles en {self.company_config.company_name} para {date}."
                
                filtered_slots = self._filter_slots_by_duration(
                    availability_data["available_slots"], 
                    duration
                )
                
                logger.info(f"Slots filtrados: {filtered_slots}")
                
                response = self._format_slots_response(filtered_slots, date, duration)
                logger.info(f"=== AVAILABILITY AGENT {self.company_config.company_name} - RESPUESTA GENERADA ===")
                return response
                
            except Exception as e:
                logger.error(f"Error en agente de disponibilidad para {self.company_config.company_name}: {e}")
                logger.exception("Stack trace completo:")
                return f"Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista."
    
        return (
            {
                "selenium_status": get_availability_selenium_status,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | RunnableLambda(process_availability)
        )
    
    def _create_enhanced_schedule_agent(self):
        """Agente de Schedule mejorado con integración de disponibilidad - Personalizado por empresa"""
        schedule_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.schedule_agent_name}, especialista en gestión de citas de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
HORARIOS: {self.company_config.working_hours}
INDUSTRIA: {self.company_config.industry_type}

OBJETIVO: Facilitar la gestión completa de citas y horarios usando herramientas avanzadas.

INFORMACIÓN DISPONIBLE:
{{context}}

ESTADO DEL SISTEMA DE AGENDAMIENTO:
{{selenium_status}}

DISPONIBILIDAD CONSULTADA:
{{available_slots}}

FUNCIONES PRINCIPALES:
- Agendar nuevas citas (con automatización completa via sistema de {self.company_config.company_name})
- Modificar citas existentes
- Cancelar citas
- Consultar disponibilidad
- Verificar citas programadas
- Reagendar citas

PROCESO DE AGENDAMIENTO AUTOMATIZADO:
1. SIEMPRE verificar disponibilidad PRIMERO
2. Mostrar horarios disponibles al usuario
3. Extraer información del cliente del contexto
4. Validar datos requeridos
5. Solo usar herramienta de sistema después de confirmar disponibilidad
6. Confirmar resultado al cliente

DATOS REQUERIDOS PARA AGENDAR:
- Nombre completo del cliente
- Número de cédula
- Teléfono de contacto
- Fecha deseada
- Hora preferida (que esté disponible)
- Fecha de nacimiento (opcional)
- Género (opcional)

REGLAS IMPORTANTES:
- NUNCA agendar sin mostrar disponibilidad primero
- Si no hay disponibilidad, sugerir fechas alternativas
- Si el horario solicitado no está disponible, mostrar opciones cercanas
- Confirmar todos los datos antes de proceder

ESTRUCTURA DE RESPUESTA:
1. Confirmación de la solicitud
2. Verificación de disponibilidad (OBLIGATORIO)
3. Información relevante o solicitud de datos faltantes
4. Resultado de la acción o siguiente paso

TONO: Profesional, eficiente, servicial.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 6 oraciones.

Historial de conversación:
{{chat_history}}

Solicitud del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_schedule_context(inputs):
            """Obtener contexto RAG para agenda específico de empresa"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de agenda {self.company_config.company_name}:
- Horarios: {self.company_config.working_hours}
- Servicios agendables: {self.company_config.services}
- Políticas de cancelación: 24 horas de anticipación
- Reagendamiento disponible sin costo
- Sistema de agendamiento automático disponible
- Datos requeridos: Nombre, cédula, teléfono, fecha y hora deseada"""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving schedule context for company {self.company_id}: {e}")
                return f"Información básica de agenda de {self.company_config.company_name} disponible. Sistema de agendamiento automático disponible."
        
        def get_selenium_status(inputs):
            """Obtener estado del sistema Selenium específico de empresa usando cache"""
            if self.selenium_service_available:
                return f"✅ Sistema de agendamiento de {self.company_config.company_name} ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de agendamiento de {self.company_config.company_name} NO DISPONIBLE (Verificar conexión)"
        
        def process_schedule_with_selenium(inputs):
            """Procesar solicitud de agenda con integración de disponibilidad específica de empresa"""
            try:
                question = inputs.get("question", "")
                user_id = inputs.get("user_id", "default_user")
                chat_history = inputs.get("chat_history", [])
                context = inputs.get("context", "")
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"Procesando solicitud de agenda para {self.company_config.company_name}: {question}")
                
                available_slots = ""
                if self._contains_schedule_intent(question):
                    logger.info("Detectado intent de agendamiento - verificando disponibilidad")
                    try:
                        availability_response = self.agents['availability'].invoke({"question": question})
                        available_slots = availability_response
                        logger.info(f"Disponibilidad obtenida: {available_slots}")
                    except Exception as e:
                        logger.error(f"Error verificando disponibilidad: {e}")
                        available_slots = "Error consultando disponibilidad. Verificaré manualmente."
                
                base_inputs = {
                    "question": question,
                    "chat_history": chat_history,
                    "context": context,
                    "selenium_status": selenium_status,
                    "available_slots": available_slots
                }
                
                logger.info("Generando respuesta base con disponibilidad")
                base_response = (schedule_prompt | self.chat_model | StrOutputParser()).invoke(base_inputs)
                
                should_proceed_selenium = (
                    self._contains_schedule_intent(question) and 
                    self._should_use_selenium(question, chat_history) and
                    self._has_available_slots_confirmation(available_slots) and
                    not self._is_just_availability_check(question)
                )
                
                logger.info(f"¿Proceder con Selenium para {self.company_config.company_name}? {should_proceed_selenium}")
                
                if should_proceed_selenium:
                    logger.info(f"Procediendo con agendamiento automático via sistema de {self.company_config.company_name}")
                    selenium_result = self._call_local_schedule_microservice(question, user_id, chat_history)
                    
                    if selenium_result.get('success'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    elif selenium_result.get('requires_more_info'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    else:
                        return f"{available_slots}\n\n{base_response}\n\nNota: Te conectaré con un especialista de {self.company_config.company_name} para completar el agendamiento."
                
                return base_response
                
            except Exception as e:
                logger.error(f"Error en agendamiento para {self.company_config.company_name}: {e}")
                return f"Error procesando tu solicitud de {self.company_config.company_name}. Conectando con especialista..."
        
        return (
            {
                "context": get_schedule_context,
                "selenium_status": get_selenium_status,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "user_id": lambda x: x.get("user_id", "default_user")
            }
            | RunnableLambda(process_schedule_with_selenium)
        )
    
    def get_response(self, question: str, user_id: str, conversation_manager: ConversationManager,
                     media_type: str = "text", media_context: str = None) -> Tuple[str, str]:
        """Método principal para obtener respuesta del sistema multi-agente específico de empresa"""
        self.conversation_manager = conversation_manager
        
        if media_type == "image" and media_context:
            processed_question = f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            processed_question = f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        else:
            processed_question = question
        
        if not processed_question or not processed_question.strip():
            return f"Por favor, envía un mensaje específico para poder ayudarte con {self.company_config.company_name}.", "support"
        
        if not user_id or not user_id.strip():
            return "Error interno: ID de usuario inválido.", "error"
        
        try:
            chat_history = conversation_manager.get_chat_history(user_id, format_type="messages")
            
            inputs = {
                "question": processed_question.strip(), 
                "chat_history": chat_history,
                "user_id": user_id,
                "company_id": self.company_id
            }
            
            might_need_rag = self._might_need_rag(processed_question)
            
            logger.info(f"🔍 CONSULTA INICIADA {self.company_config.company_name} - User: {user_id}, Pregunta: {processed_question[:100]}...")
            if might_need_rag:
                logger.info("   → Posible consulta RAG detectada")
            
            response = self._orchestrate(inputs)
            
            logger.info(f"🤖 RESPUESTA GENERADA {self.company_config.company_name} - Agente: {self._determine_agent_used(response)}")
            logger.info(f"   → Longitud respuesta: {len(response)} caracteres")
            
            conversation_manager.add_message(user_id, "user", processed_question)
            conversation_manager.add_message(user_id, "assistant", response)
            
            agent_used = self._determine_agent_used(response)
            
            logger.info(f"Multi-agent response generated for {self.company_config.company_name} user {user_id} using {agent_used}")
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"Error en sistema multi-agente de {self.company_config.company_name} (User: {user_id})")
            return f"Disculpa, tuve un problema técnico en {self.company_config.company_name}. Por favor intenta de nuevo.", "error"
    
    def _orchestrate(self, inputs):
        """Orquestador principal que coordina los agentes específicos de empresa"""
        try:
            router_response = self.agents['router'].invoke(inputs)
            
            try:
                classification = json.loads(router_response)
                intent = classification.get("intent", "SUPPORT")
                confidence = classification.get("confidence", 0.5)
                
                logger.info(f"Intent classified for {self.company_config.company_name}: {intent} (confidence: {confidence})")
                
            except json.JSONDecodeError:
                intent = "SUPPORT"
                confidence = 0.3
                logger.warning(f"Router response was not valid JSON for {self.company_config.company_name}, defaulting to SUPPORT")
            
            inputs["user_id"] = inputs.get("user_id", "default_user")
            inputs["company_id"] = self.company_id
            
            if intent == "EMERGENCY" or confidence > 0.8:
                if intent == "EMERGENCY":
                    return self.agents['emergency'].invoke(inputs)
                elif intent == "SALES":
                    return self.agents['sales'].invoke(inputs)
                elif intent == "SCHEDULE":
                    return self.agents['schedule'].invoke(inputs)
                else:
                    return self.agents['support'].invoke(inputs)
            else:
                return self.agents['support'].invoke(inputs)
                
        except Exception as e:
            logger.error(f"Error in orchestrator for {self.company_config.company_name}: {e}")
            return self.agents['support'].invoke(inputs)
    
    def _extract_date_from_question(self, question, chat_history=None):
        """Extract date from question or chat history"""
        import re
        
        date_str = self._find_date_in_text(question)
        if date_str:
            return date_str
        
        if chat_history:
            history_text = " ".join([
                msg.content if hasattr(msg, 'content') else str(msg) 
                for msg in chat_history
            ])
            date_str = self._find_date_in_text(history_text)
            if date_str:
                return date_str
        
        return None
    
    def _find_date_in_text(self, text):
        """Helper to find date in text"""
        import re
        from datetime import datetime, timedelta
        
        match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', text)
        if match:
            return match.group(0).replace('/', '-')
        
        text_lower = text.lower()
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
    
    def _extract_service_from_question(self, question):
        """Extraer servicio del mensaje usando reglas específicas de empresa"""
        question_lower = question.lower()
        
        # Usar business rules específicas de empresa
        business_rules = self.company_config.business_rules
        
        # Para Benova (centro estético)
        if self.company_config.industry_type == "estética":
            treatments_keywords = business_rules.get("treatment_durations", {})
            
            for treatment, duration in treatments_keywords.items():
                keywords = [treatment.lower()]
                if treatment == "limpieza facial":
                    keywords.extend(["limpieza", "facial"])
                elif treatment == "microagujas":
                    keywords.extend(["micro agujas", "microneedling"])
                elif treatment == "rellenos":
                    keywords.extend(["relleno", "ácido hialurónico"])
                elif treatment == "radiofrecuencia":
                    keywords.extend(["rf"])
                elif treatment == "depilación":
                    keywords.extend(["láser"])
                
                if any(keyword in question_lower for keyword in keywords):
                    return treatment
                    
            return "tratamiento general"
        
        # Para otras empresas, usar reglas generales
        else:
            service_durations = business_rules.get("service_durations", {})
            for service, duration in service_durations.items():
                if service.lower() in question_lower:
                    return service
                    
            return "servicio_general"
    
    def _get_service_duration(self, service):
        """Obtener duración del servicio desde RAG o configuración específica de empresa"""
        try:
            docs = self.retriever.invoke(f"duración tiempo {service}")
            
            for doc in docs:
                content = doc.page_content.lower()
                if "duración" in content or "tiempo" in content:
                    import re
                    duration_match = re.search(r'(\d+)\s*(?:minutos?|min)', content)
                    if duration_match:
                        return int(duration_match.group(1))
            
            # Usar business rules específicas de empresa
            business_rules = self.company_config.business_rules
            
            if self.company_config.industry_type == "estética":
                default_durations = business_rules.get("treatment_durations", {
                    "limpieza facial": 60,
                    "masaje": 60,
                    "microagujas": 90,
                    "botox": 30,
                    "rellenos": 45,
                    "peeling": 45,
                    "radiofrecuencia": 60,
                    "depilación": 30,
                    "tratamiento general": 60
                })
            else:
                default_durations = business_rules.get("service_durations", {
                    "consulta": 30,
                    "servicio_basico": 45,
                    "servicio_premium": 60,
                    "servicio_general": 45
                })
           
            return default_durations.get(service, 60)
           
        except Exception as e:
            logger.error(f"Error obteniendo duración del servicio para {self.company_config.company_name}: {e}")
            return 60
    
    def _call_check_availability(self, date):
        """Llamar al endpoint de disponibilidad específico de empresa"""
        try:
            if not self._verify_selenium_service():
                logger.warning(f"Servicio de {self.company_config.company_name} no disponible para availability check")
                return None
            
            logger.info(f"Consultando disponibilidad en {self.company_config.company_name}: {self.schedule_service_url}/check-availability para fecha: {date}")
            
            response = requests.post(
                f"{self.schedule_service_url}/check-availability",
                json={"date": date, "company_id": self.company_id},
                headers={"Content-Type": "application/json"},
                timeout=self.selenium_timeout
            )
            
            logger.info(f"Respuesta de availability endpoint de {self.company_config.company_name} - Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Datos de disponibilidad de {self.company_config.company_name} obtenidos exitosamente: {result.get('success', False)}")
                return result.get("data", {})
            else:
                logger.warning(f"Endpoint de disponibilidad de {self.company_config.company_name} retornó código {response.status_code}")
                logger.warning(f"Respuesta: {response.text}")
                self.selenium_service_available = False
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando con endpoint de disponibilidad de {self.company_config.company_name} ({self.selenium_timeout}s)")
            self.selenium_service_available = False
            return None
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"No se pudo conectar con endpoint de disponibilidad de {self.company_config.company_name}: {self.schedule_service_url}")
            logger.error(f"Error de conexión: {e}")
            self.selenium_service_available = False
            return None
            
        except Exception as e:
            logger.error(f"Error llamando endpoint de disponibilidad de {self.company_config.company_name}: {e}")
            self.selenium_service_available = False
            return None
    
    def _filter_slots_by_duration(self, available_slots, required_duration):
        """Filtrar slots que pueden acomodar la duración requerida"""
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
            logger.error(f"Error filtrando slots para {self.company_config.company_name}: {e}")
            return []
    
    def _are_consecutive_times(self, times):
        """Verificar si los horarios son consecutivos (diferencia de 30 min)"""
        for i in range(len(times) - 1):
            current_minutes = self._time_to_minutes(times[i])
            next_minutes = self._time_to_minutes(times[i + 1])
            if next_minutes - current_minutes != 30:
                return False
        return True
    
    def _time_to_minutes(self, time_str):
        """Convertir hora a minutos desde medianoche"""
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
        """Sumar minutos a una hora y retornar en formato HH:MM"""
        try:
            total_minutes = self._time_to_minutes(time_str) + minutes_to_add
            hours = (total_minutes // 60) % 24
            minutes = total_minutes % 60
            return f"{hours:02d}:{minutes:02d}"
        except:
            return time_str
    
    def _format_slots_response(self, slots, date, duration):
        """Formatear respuesta con horarios disponibles específico de empresa"""
        if not slots:
            return f"No hay horarios disponibles en {self.company_config.company_name} para {date} (servicio de {duration} min)."
        
        slots_text = "\n".join(f"- {slot}" for slot in slots)
        return f"Horarios disponibles en {self.company_config.company_name} para {date} (servicio de {duration} min):\n{slots_text}"
    
    def _call_local_schedule_microservice(self, question: str, user_id: str, chat_history: list) -> Dict[str, Any]:
        """Llamar al microservicio de schedule específico de empresa"""
        try:
            logger.info(f"Llamando a microservicio de {self.company_config.company_name} en: {self.schedule_service_url}")
            
            response = requests.post(
                f"{self.schedule_service_url}/schedule-request",
                json={
                    "message": question,
                    "user_id": user_id,
                    "company_id": self.company_id,
                    "company_name": self.company_config.company_name,
                    "chat_history": [
                        {
                            "content": msg.content if hasattr(msg, 'content') else str(msg),
                            "type": getattr(msg, 'type', 'user')
                        } for msg in chat_history
                    ]
                },
                timeout=self.selenium_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success') and result.get('appointment_data'):
                    self._notify_appointment_success(user_id, result.get('appointment_data'))
                
                logger.info(f"Respuesta exitosa del microservicio de {self.company_config.company_name}: {result.get('success', False)}")
                return result
            else:
                logger.warning(f"Microservicio de {self.company_config.company_name} retornó código {response.status_code}")
                self.selenium_service_available = False
                return {"success": False, "message": f"Servicio de {self.company_config.company_name} no disponible"}
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando con microservicio de {self.company_config.company_name} ({self.selenium_timeout}s)")
            self.selenium_service_available = False
            return {"success": False, "message": f"Timeout del servicio de {self.company_config.company_name}"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"No se pudo conectar con microservicio de {self.company_config.company_name}: {self.schedule_service_url}")
            self.selenium_service_available = False
            return {"success": False, "message": f"Servicio de {self.company_config.company_name} no disponible"}
        
        except Exception as e:
            logger.error(f"Error llamando microservicio de {self.company_config.company_name}: {e}")
            self.selenium_service_available = False
            return {"success": False, "message": f"Error del servicio de {self.company_config.company_name}"}
    
    def _contains_schedule_intent(self, question: str) -> bool:
        """Detectar si la pregunta contiene intención de agendamiento usando keywords específicos de empresa"""
        business_rules = self.company_config.business_rules
        schedule_keywords = business_rules.get('schedule_keywords', ['agendar', 'cita'])
        return any(keyword in question.lower() for keyword in schedule_keywords)
    
    def _has_available_slots_confirmation(self, availability_response: str) -> bool:
        """Verificar si la respuesta de disponibilidad contiene slots válidos"""
        if not availability_response:
            return False
        
        availability_lower = availability_response.lower()
        
        text_indicators = [
            "horarios disponibles",
            "disponible para",
            f"horarios disponibles en {self.company_config.company_name.lower()}"
        ]
        
        has_text_indicators = any(indicator in availability_lower for indicator in text_indicators)
        has_list_format = "- " in availability_response
        has_time_format = ":" in availability_response and "-" in availability_response
        
        negative_indicators = [
            "no hay horarios disponibles",
            "no hay disponibilidad", 
            "error consultando disponibilidad"
        ]
        
        has_negative = any(indicator in availability_lower for indicator in negative_indicators)
        has_positive = has_text_indicators or has_list_format or has_time_format
        
        return has_positive and not has_negative
    
    def _is_just_availability_check(self, question: str) -> bool:
        """Determinar si solo se está consultando disponibilidad sin agendar"""
        availability_only_keywords = [
            "disponibilidad para", "horarios disponibles", "qué horarios",
            "cuándo hay", "hay disponibilidad", "ver horarios"
        ]
        
        schedule_confirmation_keywords = [
            "agendar", "reservar", "procede", "proceder", "confirmar",
            "quiero la cita", "agenda la cita"
        ]
        
        has_availability_check = any(keyword in question.lower() for keyword in availability_only_keywords)
        has_schedule_confirmation = any(keyword in question.lower() for keyword in schedule_confirmation_keywords)
        
        return has_availability_check and not has_schedule_confirmation
    
    def _should_use_selenium(self, question: str, chat_history: list) -> bool:
        """Determinar si se debe usar el microservicio de Selenium"""
        question_lower = question.lower()
        
        business_rules = self.company_config.business_rules
        schedule_keywords = business_rules.get('schedule_keywords', ['agendar', 'cita'])
        
        has_schedule_intent = any(keyword in question_lower for keyword in schedule_keywords)
        has_patient_info = self._extract_patient_info_from_history(chat_history)
        
        return has_schedule_intent and (has_patient_info or self._has_complete_info_in_message(question))
    
    def _extract_patient_info_from_history(self, chat_history: list) -> bool:
        """Extraer información del paciente del historial"""
        history_text = " ".join([msg.content if hasattr(msg, 'content') else str(msg) for msg in chat_history])
        
        has_name = any(word in history_text.lower() for word in ["nombre", "llamo", "soy"])
        has_phone = any(char.isdigit() for char in history_text) and len([c for c in history_text if c.isdigit()]) >= 7
        has_date = any(word in history_text.lower() for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name and (has_phone or has_date)
    
    def _has_complete_info_in_message(self, message: str) -> bool:
        """Verificar si el mensaje tiene información completa"""
        message_lower = message.lower()
        
        has_name_indicator = any(word in message_lower for word in ["nombre", "llamo", "soy"])
        has_phone_indicator = any(char.isdigit() for char in message) and len([c for c in message if c.isdigit()]) >= 7
        has_date_indicator = any(word in message_lower for word infrom app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.models.conversation import ConversationManager
from app.config.company_config import get_company_config, CompanyConfig
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnableLambda
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.schema.output_parser import StrOutputParser
from flask import current_app
import logging
import json
import requests
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """Sistema multi-agente multi-empresa"""
    
    def __init__(self, company_id: str = "default"):
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.openai_service = OpenAIService()
        self.vectorstore_service = VectorstoreService(company_id)
        self.chat_model = self.openai_service.get_chat_model()
        self.retriever = self.vectorstore_service.get_retriever()
        self.conversation_manager = None  # Se inyecta cuando se usa
        
        # Configuración específica de empresa
        self.voice_enabled = current_app.config.get('VOICE_ENABLED', False)
        self.image_enabled = current_app.config.get('IMAGE_ENABLED', False)
        self.schedule_service_url = self.company_config.schedule_service_url
        self.is_local_development = current_app.config.get('ENVIRONMENT') == 'local'
        self.selenium_timeout = 30 if self.is_local_development else 60
        
        # Cache del estado de Selenium por empresa
        self.selenium_service_available = False
        self.selenium_status_last_check = 0
        self.selenium_status_cache_duration = 30
        
        # Inicializar agentes con configuración de empresa
        self.agents = self._initialize_agents()
        
        # Verificar servicio Selenium
        self._initialize_local_selenium_connection()
    
    def _initialize_agents(self):
        """Initialize all specialized agents with company configuration"""
        return {
            'router': self._create_router_agent(),
            'emergency': self._create_emergency_agent(),
            'sales': self._create_sales_agent(),
            'support': self._create_support_agent(),
            'schedule': self._create_enhanced_schedule_agent(),
            'availability': self._create_availability_agent()
        }
    
    def _verify_selenium_service(self, force_check: bool = False) -> bool:
        """Verificar disponibilidad del servicio Selenium específico de empresa con cache inteligente"""
        current_time = time.time()
        
        if not force_check and (current_time - self.selenium_status_last_check) < self.selenium_status_cache_duration:
            return self.selenium_service_available
        
        try:
            response = requests.get(
                f"{self.schedule_service_url}/health",
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
            logger.warning(f"Selenium service verification failed for company {self.company_id}: {e}")
            self.selenium_service_available = False
            self.selenium_status_last_check = current_time
            return False
    
    def _initialize_local_selenium_connection(self):
        """Inicializar y verificar conexión con microservicio específico de empresa"""
        try:
            logger.info(f"Intentando conectar con microservicio de {self.company_config.company_name} en: {self.schedule_service_url}")
            
            is_available = self._verify_selenium_service(force_check=True)
            
            if is_available:
                logger.info(f"✅ Conexión exitosa con microservicio de {self.company_config.company_name}")
            else:
                logger.warning(f"⚠️ Servicio de {self.company_config.company_name} no disponible")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando conexión con Selenium para {self.company_config.company_name}: {e}")
            self.selenium_service_available = False
    
    def _create_router_agent(self):
        """Agente Router: Clasifica la intención del usuario - Dinámico por empresa"""
        
        # Extraer keywords específicos de empresa
        business_rules = self.company_config.business_rules
        emergency_keywords = business_rules.get('emergency_keywords', ['emergencia', 'urgente'])
        sales_keywords = business_rules.get('sales_keywords', ['precio', 'información'])
        schedule_keywords = business_rules.get('schedule_keywords', ['agendar', 'cita'])
        
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un clasificador de intenciones para {self.company_config.company_name} ({self.company_config.industry_type}).

ANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:

1. **EMERGENCY** - Urgencias:
   - Palabras clave: {', '.join(emergency_keywords)}
   - Situaciones que requieren atención inmediata

2. **SALES** - Consultas comerciales:
   - Información sobre {self.company_config.services}
   - Palabras clave: {', '.join(sales_keywords)}
   - Comparación de servicios

3. **SCHEDULE** - Gestión de citas:
   - Palabras clave: {', '.join(schedule_keywords)}
   - Agendar, modificar o cancelar citas
   - Consultar disponibilidad

4. **SUPPORT** - Soporte general:
   - Información general de {self.company_config.company_name}
   - Consultas sobre procesos
   - Cualquier otra consulta

RESPONDE SOLO con el formato JSON:
{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación"
}}

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
        
        return router_prompt | self.chat_model | StrOutputParser()
    
    def _create_emergency_agent(self):
        """Agente de Emergencias: Maneja urgencias - Personalizado por empresa"""
        emergency_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.emergency_agent_name}, especialista en emergencias de {self.company_config.company_name}.

SITUACIÓN DETECTADA: Posible emergencia.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma/problema
3. Indica que el caso será escalado de emergencia
4. Proporciona información de contacto si es necesario:
   - Teléfono: {self.company_config.contact_info.get('phone', 'Contactar directamente')}
   - Email: {self.company_config.contact_info.get('email', 'info@empresa.com')}

TONO: Profesional, empático, tranquilizador pero urgente.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia de {self.company_config.company_name} ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        return emergency_prompt | self.chat_model | StrOutputParser()
    
    def _create_sales_agent(self):
        """Agente de Ventas: Especializado en información comercial - Dinámico por empresa"""
        sales_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, asesor comercial especializado de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
INDUSTRIA: {self.company_config.industry_type}
HORARIOS: {self.company_config.working_hours}

INFORMACIÓN DISPONIBLE:
{{context}}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del servicio solicitado
3. Beneficios principales (máximo 3)
4. Información de contacto si aplica
5. Llamada a la acción para agendar

CONTACTO:
- Teléfono: {self.company_config.contact_info.get('phone', 'Consultar')}
- Email: {self.company_config.contact_info.get('email', 'Consultar')}

TONO: Cálido, profesional, persuasivo.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 5 oraciones.

FINALIZA SIEMPRE con: "¿Te gustaría agendar tu cita en {self.company_config.company_name}? 📅"

Historial de conversación:
{{chat_history}}

Pregunta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_sales_context(inputs):
            """Obtener contexto RAG para ventas específico de empresa"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de {self.company_config.company_name}:
- {self.company_config.services}
- {self.company_config.industry_type}
- Atención personalizada
- Profesionales certificados
- Horarios: {self.company_config.working_hours}
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving sales context for company {self.company_id}: {e}")
                return f"Información básica disponible de {self.company_config.company_name}. Te conectaré con un especialista para detalles específicos."
        
        return (
            {
                "context": get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | sales_prompt
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_support_agent(self):
        """Agente de Soporte: Consultas generales y escalación - Personalizado por empresa"""
        support_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.support_agent_name}, especialista en soporte al cliente de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
INDUSTRIA: {self.company_config.industry_type}
HORARIOS: {self.company_config.working_hours}

OBJETIVO: Resolver consultas generales y facilitar navegación.

TIPOS DE CONSULTA:
- Información de {self.company_config.company_name} (ubicación, horarios)
- Procesos y políticas
- Escalación a especialistas
- Consultas generales sobre {self.company_config.services}

INFORMACIÓN DISPONIBLE:
{{context}}

INFORMACIÓN DE CONTACTO:
- Teléfono: {self.company_config.contact_info.get('phone', 'Consultar')}
- Email: {self.company_config.contact_info.get('email', 'Consultar')}
- Sitio web: {self.company_config.contact_info.get('website', 'Consultar')}

PROTOCOLO:
1. Respuesta directa a la consulta
2. Información adicional relevante de {self.company_config.company_name}
3. Opciones de seguimiento

TONO: Profesional, servicial, eficiente.
LONGITUD: Máximo 4 oraciones.
EMOJIS: Máximo 3 por respuesta.

Si no puedes resolver completamente: "Te conectaré con un especialista de {self.company_config.company_name} para resolver tu consulta específica. 👨‍💼"

Historial de conversación:
{{chat_history}}

Consulta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_support_context(inputs):
            """Obtener contexto RAG para soporte específico de empresa"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información general de {self.company_config.company_name}:
- {self.company_config.services}
- Horarios: {self.company_config.working_hours}
- Industria: {self.company_config.industry_type}
- Información institucional
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving support context for company {self.company_id}: {e}")
                return f"Información general de {self.company_config.company_name} disponible. Te conectaré con un especialista para consultas específicas."
        
        return (
            {
                "context": get_support_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | support_prompt
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_availability_agent(self):
        """Agente que verifica disponibilidad - Personalizado por empresa"""
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un agente de disponibilidad de {self.company_config.company_name}.

EMPRESA: {self.company_config.company_name}
SERVICIOS: {self.company_config.services}
HORARIOS LABORALES: {self.company_config.working_hours}

ESTADO DEL SISTEMA:
{{selenium_status}}

PROTOCOLO:
1. Verificar estado del servicio de {self.company_config.company_name}
2. Extraer la fecha (DD-MM-YYYY) y el servicio del mensaje
3. Consultar el RAG para obtener la duración del servicio (en minutos)
4. Llamar al endpoint /check-availability con la fecha
5. Filtrar los slots disponibles que puedan acomodar la duración
6. Devolver los horarios en formato legible

Ejemplo de respuesta:
"Horarios disponibles en {self.company_config.company_name} para {{fecha}} (servicio de {{duracion}} min):
- 09:00 - 10:00
- 10:30 - 11:30
- 14:00 - 15:00"

Si no hay disponibilidad: "No hay horarios disponibles en {self.company_config.company_name} para {{fecha}} con duración de {{duracion}} minutos."
Si hay error del sistema: "Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista."

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
        
        def get_availability_selenium_status(inputs):
            """Obtener estado del sistema Selenium para availability específico de empresa"""
            is_available = self._verify_selenium_service()
            
            if is_available:
                return f"✅ Sistema de {self.company_config.company_name} ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de {self.company_config.company_name} NO DISPONIBLE (Verificar conexión: {self.schedule_service_url})"
        
        def process_availability(inputs):
            """Procesar consulta de disponibilidad específica de empresa"""
            try:
                question = inputs.get("question", "")
                chat_history = inputs.get("chat_history", [])
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"=== AVAILABILITY AGENT {self.company_config.company_name} - PROCESANDO ===")
                logger.info(f"Pregunta: {question}")
                logger.info(f"Estado Selenium: {selenium_status}")
                
                if not self._verify_selenium_service():
                    logger.error(f"Servicio Selenium no disponible para {self.company_config.company_name}")
                    return f"Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista para verificar horarios. 👨‍💼"
                
                date = self._extract_date_from_question(question, chat_history)
                service = self._extract_service_from_question(question)
                
                if not date:
                    return f"Por favor especifica la fecha en formato DD-MM-YYYY para consultar disponibilidad en {self.company_config.company_name}."
                
                logger.info(f"Fecha extraída: {date}, Servicio: {service}")
                
                duration = self._get_service_duration(service)
                logger.info(f"Duración del servicio: {duration} minutos")
                
                availability_data = self._call_check_availability(date)
                
                if not availability_data:
                    logger.warning("No se obtuvieron datos de disponibilidad")
                    return f"Error consultando disponibilidad de {self.company_config.company_name}. Te conectaré con un especialista."
                
                if not availability_data.get("available_slots"):
                    logger.info("No hay slots disponibles para la fecha solicitada")
                    return f
