# app/services/multi_agent_factory.py
from typing import Dict, Any, List, Optional, Tuple
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator
from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.services.chatwoot_service import ChatwootService
from app.services.multimedia_service import MultimediaService
from app.services.calendar_integration_service import CalendarIntegrationService
from app.workflows.tool_executor import ToolExecutor
from app.config.company_config import get_company_manager, get_company_config
from app.config.extended_company_config import ExtendedCompanyConfig
import logging

logger = logging.getLogger(__name__)

class MultiAgentFactory:
    """Factory para crear y gestionar orquestadores multi-agente por empresa"""
    
    def __init__(self):
        self._orchestrators: Dict[str, MultiAgentOrchestrator] = {}
        self._openai_service = None
        self._vectorstore_services: Dict[str, VectorstoreService] = {}
        self._tool_executors: Dict[str, ToolExecutor] = {}
        
        # Servicios compartidos (no específicos por empresa)
        self._multimedia_service = None
        self._chatwoot_services: Dict[str, ChatwootService] = {}
    
    def get_orchestrator(self, company_id: str) -> Optional[MultiAgentOrchestrator]:
        """Obtener o crear orquestador para una empresa"""
        try:
            # Verificar si ya existe
            if company_id in self._orchestrators:
                return self._orchestrators[company_id]
            
            # Validar empresa
            company_manager = get_company_manager()
            if not company_manager.validate_company_id(company_id):
                logger.error(f"Invalid company_id: {company_id}")
                return None
            
            # Crear OpenAI service si no existe
            if not self._openai_service:
                self._openai_service = OpenAIService()
            
            # Crear orquestador
            orchestrator = MultiAgentOrchestrator(
                company_id=company_id,
                openai_service=self._openai_service
            )
            
            # ✅ 1. Inyectar PromptService
            from app.services import get_prompt_service
            prompt_service = get_prompt_service()
            orchestrator.set_prompt_service(prompt_service)
            logger.info(f"  → Prompt service injected for {company_id}")
            
            # ✅ 2. Crear y configurar vectorstore específico
            vectorstore_service = self._get_vectorstore_service(company_id)
            orchestrator.set_vectorstore_service(vectorstore_service)
            
            # ✅ 3. Crear y configurar tool_executor con todos los servicios
            tool_executor = self._create_tool_executor(company_id, vectorstore_service)
            orchestrator.set_tool_executor(tool_executor)
            
            # Guardar en cache
            self._orchestrators[company_id] = orchestrator
            
            logger.info(f"✅ Created orchestrator for {company_id} with all services")
            return orchestrator
    
    def _create_tool_executor(self, company_id: str, vectorstore_service: VectorstoreService) -> ToolExecutor:
        """
        Crear tool executor con todos los servicios inyectados
        """
        try:
            # Verificar cache
            if company_id in self._tool_executors:
                return self._tool_executors[company_id]
            
            # Crear tool executor
            tool_executor = ToolExecutor(company_id=company_id)
            
            # ✅ Inyectar vectorstore (RAG)
            tool_executor.set_vectorstore_service(vectorstore_service)
            logger.info(f"  → Vectorstore injected for {company_id}")
            
            # ✅ Inyectar multimedia service (compartido)
            multimedia_service = self._get_multimedia_service()
            tool_executor.set_multimedia_service(multimedia_service)
            logger.info(f"  → Multimedia service injected for {company_id}")
            
            # ✅ Inyectar chatwoot service (específico por empresa)
            chatwoot_service = self._get_chatwoot_service(company_id)
            tool_executor.set_chatwoot_service(chatwoot_service)
            logger.info(f"  → Chatwoot service injected for {company_id}")
            
            # ✅ Inyectar calendar service (si está configurado)
            calendar_service = self._get_calendar_service(company_id)
            if calendar_service:
                tool_executor.set_calendar_service(calendar_service)
                logger.info(f"  → Calendar service injected for {company_id}")
            else:
                logger.info(f"  → Calendar service not configured for {company_id}")
            
            # Guardar en cache
            self._tool_executors[company_id] = tool_executor
            
            # Log de resumen
            available_tools = tool_executor.get_available_tools()
            ready_count = sum(1 for status in available_tools.values() if status.get('available'))
            logger.info(f"✅ ToolExecutor ready for {company_id}: {ready_count}/{len(available_tools)} tools available")
            
            return tool_executor
            
        except Exception as e:
            logger.error(f"Error creating tool executor for {company_id}: {e}")
            # Retornar tool executor básico sin servicios
            return ToolExecutor(company_id=company_id)
    
    def _get_vectorstore_service(self, company_id: str) -> VectorstoreService:
        """Obtener o crear servicio de vectorstore específico para empresa"""
        try:
            # Verificar cache
            if company_id in self._vectorstore_services:
                return self._vectorstore_services[company_id]
            
            # Crear nuevo servicio de vectorstore con configuración específica
            vectorstore_service = VectorstoreService(company_id=company_id)
            
            # Guardar en cache
            self._vectorstore_services[company_id] = vectorstore_service
            
            logger.info(f"Created vectorstore service for company: {company_id}")
            return vectorstore_service
            
        except Exception as e:
            logger.error(f"Error creating vectorstore service for {company_id}: {e}")
            # Crear servicio básico como fallback
            return VectorstoreService()
    
    def _get_multimedia_service(self) -> MultimediaService:
        """Obtener servicio multimedia (compartido entre empresas)"""
        if not self._multimedia_service:
            self._multimedia_service = MultimediaService()
            logger.info("Created shared multimedia service")
        return self._multimedia_service
    
    def _get_chatwoot_service(self, company_id: str) -> ChatwootService:
        """Obtener o crear servicio de Chatwoot específico para empresa"""
        try:
            # Verificar cache
            if company_id in self._chatwoot_services:
                return self._chatwoot_services[company_id]
            
            # Crear servicio de Chatwoot
            chatwoot_service = ChatwootService(company_id=company_id)
            
            # Guardar en cache
            self._chatwoot_services[company_id] = chatwoot_service
            
            logger.info(f"Created Chatwoot service for company: {company_id}")
            return chatwoot_service
            
        except Exception as e:
            logger.error(f"Error creating Chatwoot service for {company_id}: {e}")
            # Retornar servicio básico
            return ChatwootService(company_id=company_id)
    
    def _get_calendar_service(self, company_id: str) -> Optional[CalendarIntegrationService]:
        """
        Obtener servicio de calendario si está configurado.
        Retorna None si no hay configuración de calendario.
        """
        try:
            # Obtener configuración de la empresa
            company_config = get_company_config(company_id)
            
            # Verificar si hay configuración extendida con calendario
            # (ExtendedCompanyConfig tiene integration_type e integration_config)
            if not hasattr(company_config, 'integration_type'):
                return None
            
            if not company_config.integration_type:
                return None
            
            # Crear extended config si es necesario
            if isinstance(company_config, ExtendedCompanyConfig):
                extended_config = company_config
            else:
                # No hay configuración de calendario
                return None
            
            # Crear servicio de calendario
            calendar_service = CalendarIntegrationService(extended_config)
            
            logger.info(f"Created Calendar service ({extended_config.integration_type}) for {company_id}")
            return calendar_service
            
        except Exception as e:
            logger.warning(f"Calendar service not available for {company_id}: {e}")
            return None
    
    def get_all_companies(self) -> Dict[str, MultiAgentOrchestrator]:
        """Obtener todos los orquestadores activos"""
        return self._orchestrators.copy()
    
    def clear_company_cache(self, company_id: str):
        """Limpiar cache de una empresa específica"""
        if company_id in self._orchestrators:
            del self._orchestrators[company_id]
            logger.info(f"Cleared orchestrator cache for company: {company_id}")
        
        if company_id in self._vectorstore_services:
            del self._vectorstore_services[company_id]
            logger.info(f"Cleared vectorstore cache for company: {company_id}")
        
        if company_id in self._tool_executors:
            del self._tool_executors[company_id]
            logger.info(f"Cleared tool executor cache for company: {company_id}")
        
        if company_id in self._chatwoot_services:
            del self._chatwoot_services[company_id]
            logger.info(f"Cleared Chatwoot cache for company: {company_id}")
    
    def clear_all_cache(self):
        """Limpiar todo el cache"""
        self._orchestrators.clear()
        self._vectorstore_services.clear()
        self._tool_executors.clear()
        self._chatwoot_services.clear()
        logger.info("Cleared all caches")
    
    def health_check_all(self) -> Dict[str, Any]:
        """Health check de todos los orquestadores"""
        results = {}
        company_manager = get_company_manager()
        
        for company_id in company_manager.get_all_companies().keys():
            try:
                orchestrator = self.get_orchestrator(company_id)
                if orchestrator:
                    results[company_id] = orchestrator.health_check()
                else:
                    results[company_id] = {
                        "system_healthy": False,
                        "error": "Could not create orchestrator"
                    }
            except Exception as e:
                results[company_id] = {
                    "system_healthy": False,
                    "error": str(e)
                }
        
        return results

# Instancia global del factory
_multi_agent_factory: Optional[MultiAgentFactory] = None

def get_multi_agent_factory() -> MultiAgentFactory:
    """Obtener instancia global del factory"""
    global _multi_agent_factory
    
    if _multi_agent_factory is None:
        _multi_agent_factory = MultiAgentFactory()
    
    return _multi_agent_factory

def get_orchestrator_for_company(company_id: str) -> Optional[MultiAgentOrchestrator]:
    """Función de conveniencia para obtener orquestador"""
    factory = get_multi_agent_factory()
    return factory.get_orchestrator(company_id)
