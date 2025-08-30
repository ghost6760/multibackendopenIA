from app.agents.base_agent import BaseAgent
from langchain.schema.runnable import RunnableLambda

class SalesAgent(BaseAgent):
    """Agente de ventas multi-tenant con RAG personalizado"""
    
    def _initialize_agent(self):
        """Inicializar agente de ventas con RAG"""
        self.prompt_template = self._create_prompt_template()
        self.vectorstore_service = None  # Se inyecta externamente
        
    def set_vectorstore_service(self, vectorstore_service):
        """Inyectar servicio de vectorstore específico de la empresa"""
        self.vectorstore_service = vectorstore_service
        self._create_chain()
    
    def _create_chain(self):
        """Crear cadena con RAG personalizado"""
        self.chain = (
            {
                "context": self._get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "company_name": lambda x: self.company_config.company_name,
                "services": lambda x: self.company_config.services,
                "agent_name": lambda x: self.company_config.sales_agent_name
            }
            | self.prompt_template
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Template personalizado para ventas"""
        return ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, especializada en {self.company_config.services}.

OBJETIVO: Proporcionar información comercial precisa y persuasiva para {self.company_config.company_name}.

INFORMACIÓN DISPONIBLE:
{{context}}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del tratamiento/servicio solicitado
3. Beneficios principales (máximo 3)
4. Inversión (si disponible en contexto)
5. Llamada a la acción para agendar

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
    
    def _get_sales_context(self, inputs):
        """Obtener contexto RAG filtrado por empresa"""
        try:
            question = inputs.get("question", "")
            self._log_agent_activity("retrieving_context", {"query": question[:50]})
            
            if not self.vectorstore_service:
                return f"""Información básica de {self.company_config.company_name}:
- Servicios: {self.company_config.services}
- Atención personalizada y profesional
- Tratamientos de calidad certificados
Para información específica, te conectaré con un especialista."""
            
            # Buscar documentos con filtro de empresa
            docs = self.vectorstore_service.search_by_company(question, self.company_config.company_id)
            
            if not docs:
                return f"""Información general de {self.company_config.company_name}:
- Centro especializado en {self.company_config.services}
- Atención personalizada de calidad
- Profesionales certificados
Para información específica de tratamientos, te conectaré con un especialista."""
            
            return "\n\n".join(doc.page_content for doc in docs)
            
        except Exception as e:
            logger.error(f"Error retrieving sales context: {e}")
            return f"Información básica disponible de {self.company_config.company_name}. Te conectaré con un especialista para detalles específicos."
    
    def _execute_agent_chain(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar cadena de ventas"""
        if not hasattr(self, 'chain'):
            # Chain no creado, usar respuesta básica
            return f"Hola, soy {self.company_config.sales_agent_name}. Estamos especializados en {self.company_config.services}. ¿En qué puedo ayudarte? 😊"
        
        return self.chain.invoke(inputs)
