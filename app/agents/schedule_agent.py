# app/agents/schedule_agent_hybrid.py - VERSIÓN HÍBRIDA CON LANGGRAPH

"""
ScheduleAgent - Versión Híbrida con LangGraph

Esta versión usa ScheduleAgentGraph internamente pero mantiene
la misma interfaz externa para compatibilidad total.

CAMBIOS vs versión original:
- Usa ScheduleAgentGraph para validaciones paso a paso
- Extracción de información separada de generación de respuesta
- Estado compartido entre pasos (extract → validate → check → respond)
- Mejor debugging y trazabilidad

COMPATIBILIDAD:
- ✅ 100% compatible con API existente
- ✅ Misma interfaz invoke()
- ✅ Mismo set_vectorstore_service()
- ✅ Mismos métodos auxiliares
"""

from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Any, List, Optional, Tuple
import requests
import logging
import re
from datetime import datetime, timedelta
import json

# ✅ IMPORTAR GRAFO DE LANGGRAPH
from app.langgraph_adapters.schedule_agent_graph import ScheduleAgentGraph

logger = logging.getLogger(__name__)


class ScheduleAgent(BaseAgent):
    """
    Agente de agendamiento multi-tenant con integración de calendarios y RAG

    VERSIÓN HÍBRIDA: Usa ScheduleAgentGraph (LangGraph) internamente
    pero mantiene la misma interfaz externa para compatibilidad.
    """

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

        # Crear cadena (para compatibilidad con código que la usa directamente)
        self._create_chain()

        # ✅ NUEVO: Inicializar grafo de LangGraph
        self._initialize_graph()

    def _initialize_graph(self):
        """
        ✅ NUEVO: Inicializar grafo de ScheduleAgentGraph

        Crea el grafo que manejará el flujo de agendamiento paso a paso.
        """
        try:
            # Crear grafo (se pasa self para que pueda usar métodos auxiliares)
            self.graph = ScheduleAgentGraph(
                schedule_agent=self,
                enable_checkpointing=False
            )

            logger.info(
                f"[{self.company_config.company_id}] ScheduleAgentGraph initialized"
            )

        except Exception as e:
            logger.error(
                f"[{self.company_config.company_id}] "
                f"Error initializing ScheduleAgentGraph: {e}"
            )
            # Si falla, el agente puede seguir funcionando sin el grafo
            self.graph = None

    def set_vectorstore_service(self, vectorstore_service):
        """
        Inyectar servicio de vectorstore específico de la empresa

        ✅ ACTUALIZADO: También reinicializa el grafo con RAG
        """
        self.vectorstore_service = vectorstore_service

        # Recrear cadena con RAG (compatibilidad)
        self._create_chain()

        # ✅ Reinicializar grafo para que use RAG
        if hasattr(self, 'graph') and self.graph:
            try:
                self.graph = ScheduleAgentGraph(
                    schedule_agent=self,  # Ahora con RAG
                    enable_checkpointing=False
                )
                logger.info(
                    f"[{self.company_config.company_id}] "
                    f"ScheduleAgentGraph reinitialized with RAG"
                )
            except Exception as e:
                logger.error(
                    f"[{self.company_config.company_id}] "
                    f"Error reinitializing graph with RAG: {e}"
                )

    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        Método invoke compatible con orchestrator

        ✅ ACTUALIZADO: Usa ScheduleAgentGraph si está disponible,
        sino usa implementación directa (chain).

        Args:
            inputs: Diccionario con:
                - question: str
                - chat_history: List
                - context: str (opcional)
                - user_id: str (opcional)

        Returns:
            Respuesta del agente (str)
        """
        try:
            question = inputs.get("question", "")
            chat_history = inputs.get("chat_history", [])
            user_id = inputs.get("user_id", "default_user")

            if not question:
                return (
                    f"No se proporcionó una pregunta válida para "
                    f"{self.company_config.company_name}."
                )

            # ✅ USAR GRAFO SI ESTÁ DISPONIBLE
            if self.graph:
                logger.info(
                    f"[{self.company_config.company_id}] "
                    f"Using ScheduleAgentGraph for scheduling"
                )

                response = self.graph.get_response(
                    question=question,
                    user_id=user_id,
                    chat_history=chat_history
                )

                return response

            else:
                # Fallback a implementación directa (chain)
                logger.warning(
                    f"[{self.company_config.company_id}] "
                    f"ScheduleAgentGraph not available, using direct chain"
                )

                return self.process_message(question, chat_history, "")

        except Exception as e:
            logger.exception(
                f"[{self.company_config.company_id}] "
                f"Error in ScheduleAgent.invoke: {e}"
            )
            return (
                f"Lo siento, estoy experimentando dificultades técnicas. "
                f"Por favor, contacta con {self.company_config.company_name} "
                f"directamente."
            )

    # ============================================================================
    # MÉTODOS AUXILIARES - MANTENER PARA COMPATIBILIDAD Y USO DEL GRAFO
    # ============================================================================
    # El grafo usa estos métodos, así que deben permanecer

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

    def _verify_schedule_service(self, force_check: bool = False) -> bool:
        """Verificar servicio de agendamiento específico de la empresa"""
        import time
        current_time = time.time()

        if not force_check and (current_time - self.schedule_status_last_check) < self.schedule_status_cache_duration:
            return self.schedule_service_available

        try:
            health_endpoint = self._get_health_endpoint()
            response = requests.get(health_endpoint, timeout=5)

            if response.status_code == 200:
                self.schedule_service_available = True
                self.schedule_status_last_check = current_time
                logger.info(
                    f"Schedule service ({self.integration_type}) available for "
                    f"{self.company_config.company_name}"
                )
                return True
            else:
                self.schedule_service_available = False
                self.schedule_status_last_check = current_time
                return False

        except Exception as e:
            logger.warning(
                f"Schedule service verification failed for "
                f"{self.company_config.company_name}: {e}"
            )
            self.schedule_service_available = False
            self.schedule_status_last_check = current_time
            return False

    def _get_health_endpoint(self) -> str:
        """Obtener endpoint de health según tipo de integración"""
        base_url = self.company_config.schedule_service_url

        if self.integration_type == 'google_calendar':
            return f"{base_url}/health"
        elif self.integration_type == 'calendly':
            return f"{base_url}/health"
        elif self.integration_type == 'webhook':
            return f"{base_url}/ping"
        else:
            return f"{base_url}/health"

    def _extract_date_from_question(self, question: str, chat_history: List = None) -> Optional[str]:
        """Extraer fecha de la pregunta"""
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

    def _extract_treatment_from_question(self, question: str) -> str:
        """Extraer tratamiento específico de la empresa"""
        question_lower = question.lower()

        # Buscar en las configuraciones de tratamientos
        schedules_config = self._get_schedules_configuration()
        for treatment in schedules_config.keys():
            if treatment.lower() in question_lower:
                return treatment

        return "tratamiento general"

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
                if len(name.split()) >= 2:
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

    def _get_schedules_configuration(self) -> Dict[str, Any]:
        """Obtener configuración de múltiples agendas por empresa"""
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

    def _get_treatment_configuration(self, treatment: str) -> Dict[str, Any]:
        """Obtener configuración completa del tratamiento"""
        schedules_config = self._get_schedules_configuration()

        for treatment_name, config in schedules_config.items():
            if treatment_name.lower() == treatment.lower():
                return config

        return {
            'duration': self.company_config.treatment_durations.get(treatment, 60),
            'sessions': 1,
            'deposit': 0,
            'category': 'general',
            'agenda_id': 'default'
        }

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

    def _check_calendly_availability(self, date: str, treatment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Verificar disponibilidad en Calendly"""
        try:
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

    # ============================================================================
    # MÉTODOS DE COMPATIBILIDAD - MANTENER PARA NO ROMPER CÓDIGO EXISTENTE
    # ============================================================================
    # Estos métodos se mantienen por si algún código los llama directamente

    def _create_chain(self):
        """Crear cadena híbrida (se mantiene para compatibilidad)"""
        # Implementación simplificada para compatibilidad
        # El grafo manejará la lógica real
        pass

    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Template por defecto para agendamiento"""
        template = f"""Especialista en agendamiento de {self.company_config.company_name}.

OBJETIVO: Ayudar a los usuarios a programar, consultar y gestionar citas.

SERVICIOS DISPONIBLES: {self.company_config.services}

CONTEXTO DE AGENDAMIENTO:
{{schedule_context}}

CAMPOS REQUERIDOS:
{{required_fields}}

INSTRUCCIONES:
1. Si el usuario consulta disponibilidad, proporciona horarios disponibles
2. Si el usuario quiere agendar, solicita la información requerida
3. Sé profesional pero cálido

TONO: Profesional, organizado, servicial.

HISTORIAL:
{{chat_history}}

CONSULTA: {{question}}

Responde de manera clara y organizada."""

        return ChatPromptTemplate.from_messages([
            ("system", template),
            ("human", "{question}")
        ])
