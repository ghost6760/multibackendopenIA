"""Services package initialization - Enhanced for Multi-tenant - FIXED"""

# ========================================================================
# IMPORTS SEGUROS (sin dependencias circulares)
# ========================================================================
from .openai_service import OpenAIService, init_openai
from .redis_service import get_redis_client, init_redis, close_redis
from .vectorstore_service import VectorstoreService, init_vectorstore
from .multimedia_service import MultimediaService
from .vector_auto_recovery import (
    RedisVectorAutoRecovery,
    VectorstoreProtectionMiddleware,
    initialize_auto_recovery_system,
    get_auto_recovery_instance,
    get_system_wide_health
)
from .prompt_service import PromptService, get_prompt_service, init_prompt_service
from .company_config_service import (
    EnterpriseCompanyConfigService,
    get_enterprise_company_service,
    EnterpriseCompanyConfig
)

# ========================================================================
# LAZY IMPORTS para evitar circular dependencies
# ========================================================================
# NO importar ChatwootService ni MultiAgentOrchestrator al nivel del módulo
# Se cargan bajo demanda en las funciones

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
    
    # Multi-agent system (lazy loaded)
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
    'init_prompt_service',
    
    # ✅ FIXED: Added missing comma
    'EnterpriseCompanyConfigService',
    'get_enterprise_company_service', 
    'EnterpriseCompanyConfig',
    
    # Convenience functions
    'get_chatwoot_service',
    'get_vectorstore_service',
    'get_prompt_service_for_company'
]

# ========================================================================
# LAZY LOADERS - Evitan imports circulares
# ========================================================================

def _lazy_import_chatwoot():
    """Lazy import de ChatwootService"""
    from .chatwoot_service import ChatwootService
    return ChatwootService

def _lazy_import_orchestrator():
    """Lazy import de MultiAgentOrchestrator"""
    from .multi_agent_orchestrator import MultiAgentOrchestrator
    return MultiAgentOrchestrator

def _lazy_import_factory():
    """Lazy import de MultiAgentFactory"""
    from .multi_agent_factory import MultiAgentFactory, get_multi_agent_factory, get_orchestrator_for_company
    return MultiAgentFactory, get_multi_agent_factory, get_orchestrator_for_company

# ========================================================================
# PUBLIC API - Funciones que usan lazy loading
# ========================================================================

# Exponer las clases a través de getters dinámicos
def __getattr__(name):
    """
    Lazy loading de módulos problemáticos.
    Se ejecuta solo cuando alguien intenta acceder a estos nombres.
    """
    if name == 'ChatwootService':
        return _lazy_import_chatwoot()
    elif name == 'MultiAgentOrchestrator':
        return _lazy_import_orchestrator()
    elif name == 'MultiAgentFactory':
        factory_class, _, _ = _lazy_import_factory()
        return factory_class
    elif name == 'get_multi_agent_factory':
        _, getter, _ = _lazy_import_factory()
        return getter
    elif name == 'get_orchestrator_for_company':
        _, _, getter = _lazy_import_factory()
        return getter
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# ========================================================================
# Convenience functions for multi-tenant usage
# ========================================================================

def get_chatwoot_service(company_id: str):
    """Get Chatwoot service for specific company (lazy loaded)"""
    ChatwootService = _lazy_import_chatwoot()
    return ChatwootService(company_id=company_id)

def get_vectorstore_service(company_id: str) -> VectorstoreService:
    """Get Vectorstore service for specific company"""
    return VectorstoreService(company_id=company_id)
    
def get_prompt_service_for_company(company_id: str = None) -> PromptService:
    """Get Prompt service (company-agnostic, handles multi-tenancy internally)"""
    return get_prompt_service()
