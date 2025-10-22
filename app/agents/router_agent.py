# app/agents/router_agent.py
# Mantiene BaseAgent - NO migrar a cognitivo (es clasificación simple)

from app.agents.base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class RouterAgent(BaseAgent):
    """
    Agente Router multi-tenant para clasificación de intenciones.
    
    IMPORTANTE: NO migrar a CognitiveAgentBase
    - Es un agente simple de clasificación
    - Solo necesita LLM para categorizar
    - No requiere razonamiento multi-paso
    - Mantiene BaseAgent como padre
    """
    
    def _initialize_agent(self):
        """Inicializar configuración del router"""
        self.prompt_template = self._create_prompt_template()
        self.chain = self.prompt_template | self.chat_model | StrOutputParser()
    
    def _create_default_prompt_template(self) -> ChatPromptTemplate:
        """Crear template de prompts por defecto"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un clasificador de intenciones para {self.company_config.company_name}.

SERVICIOS: {self.company_config.services}

ANALIZA el mensaje y clasifica en UNA categoría:

**EMERGENCY** - Urgencias médicas:
- Keywords: {', '.join(self.company_config.emergency_keywords)}
- Síntomas graves, dolor intenso
- Cualquier situación urgente

**SALES** - Consultas comerciales:
- Keywords: {', '.join(self.company_config.sales_keywords)}
- Información de servicios, precios
- Comparaciones, beneficios

**SCHEDULE** - Gestión de citas:
- Keywords: {', '.join(self.company_config.schedule_keywords)}
- Agendar, cancelar, consultar citas
- Verificar disponibilidad

**SUPPORT** - Soporte general:
- Información general
- Dudas, preguntas
- Cualquier otra consulta

RESPONDE SOLO en formato JSON:
{{{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación"
}}}}

Mensaje: {{question}}"""),
            ("human", "{question}")
        ])
    
    def invoke(self, inputs: Dict[str, Any]) -> str:
        """
        Clasificar intención del mensaje.
        
        Args:
            inputs: Dict con question, chat_history, user_id
        
        Returns:
            JSON string con clasificación
        """
        try:
            question = inputs.get("question", "")
            
            if not question:
                return json.dumps({
                    "intent": "SUPPORT",
                    "confidence": 0.3,
                    "keywords": [],
                    "reasoning": "Empty question"
                })
            
            # Ejecutar clasificación
            response = self.chain.invoke({
                "question": question,
                "company_name": self.company_config.company_name,
                "services": self.company_config.services
            })
            
            # Validar JSON
            try:
                json.loads(response)
                return response
            except json.JSONDecodeError:
                # Si no es JSON válido, extraer y corregir
                logger.warning(f"Router response not valid JSON: {response[:100]}")
                return json.dumps({
                    "intent": "SUPPORT",
                    "confidence": 0.5,
                    "keywords": [],
                    "reasoning": "Fallback classification"
                })
            
        except Exception as e:
            logger.error(f"Error in RouterAgent.invoke(): {e}")
            return json.dumps({
                "intent": "SUPPORT",
                "confidence": 0.3,
                "keywords": [],
                "reasoning": f"Error: {str(e)}"
            })
