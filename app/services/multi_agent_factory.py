# multi_agent_factory.py
from typing import Dict, Any, List, Optional, Tuple
from app.services.multi_agent_orchestrator import MultiAgentOrchestrator
from app.services.openai_service import OpenAIService
from app.services.vectorstore_service import VectorstoreService
from app.config.company_config import get_company_manager
import logging

logger = logging.getLogger(__name__)

class MultiAgentFactory:
    """Factory para crear y gestionar orquestadores multi-agente por empresa"""
    
    def __init__(self):
        self._orchestrators: Dict[str, MultiAgentOrchestrator] = {}
        self._openai_service = None
        self._vectorstore_services: Dict[str, VectorstoreService] = {}
    
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
            
            # Crear y configurar vectorstore específico
            vectorstore_service = self._get_vectorstore_service(company_id)
            orchestrator.set_vectorstore_service(vectorstore_service)
            
            # Guardar en cache
            self._orchestrators[company_id] = orchestrator
            
            logger.info(f"Created new orchestrator for company: {company_id}")
            return orchestrator
            
        except Exception as e:
            logger.error(f"Error creating orchestrator for {company_id}: {e}")
            return None
    
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
    
    def clear_all_cache(self):
        """Limpiar todo el cache"""
        self._orchestrators.clear()
        self._vectorstore_services.clear()
        logger.info("Cleared all orchestrator and vectorstore caches")
    
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
