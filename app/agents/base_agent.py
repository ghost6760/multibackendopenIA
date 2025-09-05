# app/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.schema.output_parser import StrOutputParser
from app.config.company_config import CompanyConfig
from app.services.openai_service import OpenAIService
import logging

# 🆕 AGREGAR ESTOS IMPORTS
import json
import os
from datetime import datetime


logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Clase base para todos los agentes del sistema multi-tenant"""
    
    def __init__(self, company_config: CompanyConfig, openai_service: OpenAIService):
        self.company_config = company_config
        self.openai_service = openai_service
        self.chat_model = openai_service.get_chat_model()
        self.agent_name = self.__class__.__name__
        
        # Inicializar el agente específico
        self._initialize_agent()
    
    @abstractmethod
    def _initialize_agent(self):
        """Inicializar configuración específica del agente"""
        pass
    
    @abstractmethod
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crear el template de prompts para el agente"""
        pass
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """Método principal para invocar el agente"""
        try:
            # Agregar contexto de empresa
            inputs = self._enhance_inputs_with_company_context(inputs)
            
            # Ejecutar cadena del agente
            result = self._execute_agent_chain(inputs)
            
            # Post-procesar respuesta
            return self._post_process_response(result, inputs)
            
        except Exception as e:
            logger.error(f"Error in {self.agent_name} for company {self.company_config.company_id}: {e}")
            return self._get_fallback_response()
    
    def _enhance_inputs_with_company_context(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquecer inputs con contexto de empresa"""
        enhanced_inputs = inputs.copy()
        enhanced_inputs.update({
            "company_name": self.company_config.company_name,
            "services": self.company_config.services,
            "agent_name": self.company_config.sales_agent_name,
            "company_id": self.company_config.company_id
        })
        return enhanced_inputs
    
    @abstractmethod
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar la cadena específica del agente"""
        pass
    
    def _post_process_response(self, response: str, inputs: Dict[str, Any]) -> str:
        """Post-procesar respuesta del agente"""
        return response
    
    def _get_fallback_response(self) -> str:
        """Respuesta de respaldo en caso de error"""
        return f"Disculpa, tuve un problema técnico. Por favor intenta de nuevo o contacta con {self.company_config.company_name}."
    
    def _log_agent_activity(self, action: str, details: Dict[str, Any] = None):
        """Log de actividad del agente con contexto de empresa"""
        log_data = {
            "agent": self.agent_name,
            "company_id": self.company_config.company_id,
            "action": action
        }
        if details:
            log_data.update(details)
        
        logger.info(f"[{self.company_config.company_id}] {self.agent_name}: {action}", extra=log_data)

