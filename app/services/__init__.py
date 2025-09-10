"""Services package initialization - Enhanced for Multi-tenant"""
from .chatwoot_service import ChatwootService
from .openai_service import OpenAIService, init_openai
from .redis_service import get_redis_client, init_redis, close_redis
from .vectorstore_service import VectorstoreService, init_vectorstore
from .multimedia_service import MultimediaService
from .multi_agent_orchestrator import MultiAgentOrchestrator
from .multi_agent_factory import MultiAgentFactory, get_multi_agent_factory, get_orchestrator_for_company
from .vector_auto_recovery import (
    RedisVectorAutoRecovery,
    VectorstoreProtectionMiddleware,
    initialize_auto_recovery_system,
    get_auto_recovery_instance,
    get_system_wide_health
)
from .prompt_service import PromptService, get_prompt_service, init_prompt_service

__all__ = [
    # Basic services
    'ChatwootService',
    'OpenAIService',
    'init_openai',
    'get_redis_client',
    'init_redis', 
    'close_redis',
    'VectorstoreService',
    'init_vectorstore',
    'MultimediaService',
    
    # Multi-agent system
    'MultiAgentOrchestrator',
    'MultiAgentFactory',
    'get_multi_agent_factory',
    'get_orchestrator_for_company',
    
    # Auto-recovery system
    'RedisVectorAutoRecovery',
    'VectorstoreProtectionMiddleware', 
    'initialize_auto_recovery_system',
    'get_auto_recovery_instance',
    'get_system_wide_health',
    
    # Prompt service
    'PromptService',
    'get_prompt_service',
    'init_prompt_service'
]

# Convenience functions for multi-tenant usage
def get_chatwoot_service(company_id: str) -> ChatwootService:
    """Get Chatwoot service for specific company"""
    return ChatwootService(company_id=company_id)

def get_vectorstore_service(company_id: str) -> VectorstoreService:
    """Get Vectorstore service for specific company"""
    return VectorstoreService(company_id=company_id)
    
def get_prompt_service_for_company(company_id: str = None) -> PromptService:
    """Get Prompt service (company-agnostic, handles multi-tenancy internally)"""
    return get_prompt_service()
