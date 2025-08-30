from app.agents.base_agent import BaseAgent

class EmergencyAgent(BaseAgent):
    """Agente de emergencias médicas multi-tenant"""
    
    def _initialize_agent(self):
        """Inicializar configuración de emergencias"""
        self.prompt_template = self._create_prompt_template()
        self.chain = self.prompt_template | self.chat_model | StrOutputParser()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Template personalizado para emergencias"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres un especialista en emergencias médicas de {self.company_config.company_name}.

SITUACIÓN DETECTADA: Posible emergencia médica.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma
3. Indica que el caso será escalado de emergencia a {self.company_config.company_name}
4. Proporciona información de contacto directo si es necesario

SERVICIOS DE EMERGENCIA: {self.company_config.services}

TONO: Profesional, empático, tranquilizador pero urgente.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia en {self.company_config.company_name} ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar protocolo de emergencia"""
        self._log_agent_activity("handling_emergency", {
            "user_id": inputs.get("user_id", "unknown"),
            "urgency": "high"
        })
        return self.chain.invoke(inputs)
