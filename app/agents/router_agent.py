from app.agents.base_agent import BaseAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class RouterAgent(BaseAgent):
    """Agente Router multi-tenant para clasificación de intenciones"""
    
    def _initialize_agent(self):
        """Inicializar configuración del router"""
        self.prompt_template = self._create_prompt_template()
        self.chain = self.prompt_template | self.chat_model | StrOutputParser()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Crear template de prompts personalizado por empresa"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un clasificador de intenciones para {self.company_config.company_name}.
            
Servicios disponibles: {self.company_config.services}

ANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:

1. **EMERGENCY** - Urgencias médicas:
   - Palabras clave: {', '.join(self.company_config.emergency_keywords)}
   - Síntomas post-tratamiento graves
   - Cualquier situación que requiera atención médica inmediata

2. **SALES** - Consultas comerciales:
   - Información sobre tratamientos y servicios
   - Palabras clave: {', '.join(self.company_config.sales_keywords)}
   - Comparación de procedimientos
   - Beneficios y resultados

3. **SCHEDULE** - Gestión de citas:
   - Palabras clave: {', '.join(self.company_config.schedule_keywords)}
   - Modificar, cancelar o consultar citas
   - Verificar disponibilidad

4. **SUPPORT** - Soporte general:
   - Información general de {self.company_config.company_name}
   - Consultas sobre procesos
   - Cualquier otra consulta

RESPONDE SOLO con el formato JSON:
{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación",
    "company_context": "{self.company_config.company_name}"
}}

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar clasificación de intenciones"""
        self._log_agent_activity("classifying_intent", {"question": inputs.get("question", "")[:50]})
        return self.chain.invoke(inputs)
