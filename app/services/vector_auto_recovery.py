from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config
from flask import current_app
import logging
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RedisVectorAutoRecovery:
    """
    Sistema de auto-recuperación para vectorstore Redis - Multi-tenant
    """
    
    def __init__(self, company_id: str = "default"):
        self.company_id = company_id
        self.company_config = get_company_config(company_id)
        
        if self.company_config:
            self.index_name = self.company_config.vectorstore_index
            self.redis_prefix = self.company_config.redis_prefix
        else:
            self.index_name = f"{company_id}_documents"
            self.redis_prefix = f"{company_id}:"
        
        self.redis_client = get_redis_client()
        self.metadata_key = f"__recovery_metadata__{self.index_name}"
        self.backup_key = f"__backup_docs__{self.index_name}"
        self.documents_pattern = f"{self.index_name}:*"
        self.health_cache = {"last_check": 0, "status": None}
        self._recovery_lock = threading.Lock()
        
        # Configuration from app config
        self.health_check_interval = current_app.config.get('VECTORSTORE_HEALTH_CHECK_INTERVAL', 30)
        self.recovery_timeout = current_app.config.get('VECTORSTORE_RECOVERY_TIMEOUT', 60)
        self.auto_recovery_enabled = current_app.config.get('VECTORSTORE_AUTO_RECOVERY', True)
        
        logger.info(f"Auto-recovery initialized for company: {company_id} (index: {self.index_name})")
    
    def verify_index_health(self) -> Dict[str, Any]:
        """Verificar estado del índice con cache inteligente multi-tenant"""
        current_time = time.time()
        
        # Cache for health_check_interval seconds
        if (current_time - self.health_cache["last_check"]) < self.health_check_interval and self.health_cache["status"]:
            return self.health_cache["status"]
        
        try:
            # Verificar índice específico de empresa
            info = self.redis_client.ft(self.index_name).info()
            doc_count = info.get('num_docs', 0)
            
            # Contar documentos almacenados específicos de empresa
            stored_keys = list(self.redis_client.scan_iter(match=self.documents_pattern))
            stored_count = len(stored_keys)
            
            health_status = {
                "company_id": self.company_id,
                "index_name": self.index_name,
                "index_exists": True,
                "index_functional": doc_count > 0,
                "stored_documents": stored_count,
                "index_doc_count": doc_count,
                "needs_recovery": doc_count == 0 and stored_count > 0,
                "healthy": doc_count > 0 and stored_count > 0,
                "timestamp": current_time
            }
            
            self.health_cache = {"last_check": current_time, "status": health_status}
            return health_status
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error checking index health: {e}")
            health_status = {
                "company_id": self.company_id,
                "index_name": self.index_name,
                "index_exists": False,
                "index_functional": False,
                "stored_documents": 0,
                "needs_recovery": True,
                "healthy": False,
                "error": str(e),
                "timestamp": current_time
            }
            self.health_cache = {"last_check": current_time, "status": health_status}
            return health_status
    
    def reconstruct_index_from_stored_data(self) -> bool:
        """Reconstruir índice desde datos almacenados específico de empresa"""
        if not self.auto_recovery_enabled:
            logger.warning(f"[{self.company_id}] Auto-recovery is disabled")
            return False
            
        with self._recovery_lock:
            try:
                logger.info(f"[{self.company_id}] Starting index reconstruction...")
                
                # Obtener documentos almacenados de esta empresa
                stored_docs = self._get_stored_documents()
                if not stored_docs:
                    logger.warning(f"[{self.company_id}] No stored documents found")
                    return False
                
                # Eliminar índice corrupto específico de empresa
                try:
                    self.redis_client.ft(self.index_name).dropindex(delete_documents=False)
                    logger.info(f"[{self.company_id}] Dropped corrupted index: {self.index_name}")
                except:
                    pass
                
                time.sleep(1)
                
                # Recrear índice usando VectorstoreService específico de empresa
                try:
                    from app.services.vectorstore_service import VectorstoreService
                    vectorstore_service = VectorstoreService(company_id=self.company_id)
                    vectorstore_service._initialize_vectorstore()
                    
                    # Limpiar cache
                    self.health_cache = {"last_check": 0, "status": None}
                    
                    logger.info(f"[{self.company_id}] Index reconstructed: {len(stored_docs)} docs available")
                    return True
                    
                except Exception as e:
                    logger.error(f"[{self.company_id}] Error recreating index: {e}")
                    return False
                
            except Exception as e:
                logger.error(f"[{self.company_id}] Error in reconstruction: {e}")
                return False
    
    def _get_stored_documents(self) -> List[Dict]:
        """Obtener documentos almacenados específicos de empresa"""
        try:
            docs = []
            keys = list(self.redis_client.scan_iter(match=self.documents_pattern))
            
            for key in keys:
                try:
                    doc_data = self.redis_client.hgetall(key)
                    if doc_data:
                        doc = {}
                        for k, v in doc_data.items():
                            key_str = k.decode() if isinstance(k, bytes) else k
                            val_str = v.decode() if isinstance(v, bytes) else v
                            doc[key_str] = val_str
                        
                        # Verificar que pertenece a esta empresa
                        doc_company_id = doc.get('company_id', '')
                        if doc_company_id == self.company_id or not doc_company_id:
                            docs.append(doc)
                        
                except Exception as e:
                    logger.warning(f"[{self.company_id}] Error processing document {key}: {e}")
                    continue
            
            return docs
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting stored documents: {e}")
            return []
    
    def ensure_index_healthy(self) -> bool:
        """Método principal de recuperación específico de empresa"""
        try:
            health = self.verify_index_health()
            
            if health["needs_recovery"] and self.auto_recovery_enabled:
                logger.warning(f"[{self.company_id}] Index needs recovery, attempting reconstruction...")
                return self.reconstruct_index_from_stored_data()
            
            return health["healthy"]
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error ensuring index health: {e}")
            return False
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Get protection status específico de empresa"""
        health = self.verify_index_health()
        
        return {
            "company_id": self.company_id,
            "index_name": self.index_name,
            "vectorstore_healthy": health.get("healthy", False),
            "index_exists": health.get("index_exists", False),
            "needs_recovery": health.get("needs_recovery", False),
            "protection_active": True,
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "auto_recovery_available": True,
            "health_check_interval": self.health_check_interval,
            "last_health_check": self.health_cache.get("last_check", 0)
        }


class VectorstoreProtectionMiddleware:
    """
    Middleware para proteger operaciones del vectorstore - Multi-tenant
    """
    
    def __init__(self, auto_recovery: RedisVectorAutoRecovery):
        self.auto_recovery = auto_recovery
        self._original_methods = {}
        self.company_id = auto_recovery.company_id
        
    def apply_protection(self, vectorstore_service) -> bool:
        """Aplicar protección automática a métodos críticos multi-tenant"""
        try:
            # Proteger vectorstore.add_texts
            if hasattr(vectorstore_service.vectorstore, 'add_texts'):
                original_add_texts = vectorstore_service.vectorstore.add_texts
                
                def protected_add_texts(texts, metadatas=None, **kwargs):
                    try:
                        # Verificar salud antes de agregar
                        if self.auto_recovery.auto_recovery_enabled:
                            self.auto_recovery.ensure_index_healthy()
                        
                        result = original_add_texts(texts, metadatas, **kwargs)
                        logger.debug(f"[{self.company_id}] Protected add_texts: {len(texts)} texts")
                        return result
                        
                    except Exception as e:
                        logger.error(f"[{self.company_id}] Protected add_texts failed: {e}")
                        
                        # Recovery y retry
                        if self.auto_recovery.ensure_index_healthy():
                            try:
                                return original_add_texts(texts, metadatas, **kwargs)
                            except Exception as retry_error:
                                logger.error(f"[{self.company_id}] Retry failed: {retry_error}")
                        
                        raise e
                
                vectorstore_service.vectorstore.add_texts = protected_add_texts
                self._original_methods['add_texts'] = original_add_texts
                logger.info(f"[{self.company_id}] Vectorstore add_texts protected")
            
            # Proteger retriever.invoke
            if hasattr(vectorstore_service, 'get_retriever'):
                retriever = vectorstore_service.get_retriever()
                if hasattr(retriever, 'invoke'):
                    original_invoke = retriever.invoke
                    
                    def protected_retriever_invoke(input_query, config=None, **kwargs):
                        try:
                            # Verificar salud antes de buscar
                            if self.auto_recovery.auto_recovery_enabled:
                                health = self.auto_recovery.verify_index_health()
                                if not health["healthy"] and health["stored_documents"] > 0:
                                    self.auto_recovery.ensure_index_healthy()
                            
                            return original_invoke(input_query, config, **kwargs)
                            
                        except Exception as e:
                            logger.error(f"[{self.company_id}] Protected retriever failed: {e}")
                            
                            # Recovery y retry
                            if self.auto_recovery.reconstruct_index_from_stored_data():
                                try:
                                    return original_invoke(input_query, config, **kwargs)
                                except:
                                    logger.error(f"[{self.company_id}] Final retry failed")
                            
                            # Retornar vacío para no romper
                            logger.warning(f"[{self.company_id}] Returning empty results due to failure")
                            return []
                    
                    retriever.invoke = protected_retriever_invoke
                    self._original_methods['retriever_invoke'] = original_invoke
                    logger.info(f"[{self.company_id}] Retriever invoke protected")
            
            return True
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error applying protection: {e}")
            return False
    
    def remove_protection(self, vectorstore_service) -> bool:
        """Remover protección y restaurar métodos originales"""
        try:
            if 'add_texts' in self._original_methods:
                vectorstore_service.vectorstore.add_texts = self._original_methods['add_texts']
                
            if 'retriever_invoke' in self._original_methods:
                retriever = vectorstore_service.get_retriever()
                retriever.invoke = self._original_methods['retriever_invoke']
                
            self._original_methods.clear()
            logger.info(f"[{self.company_id}] Vectorstore protection removed")
            return True
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error removing protection: {e}")
            return False


# Multi-tenant global instances
_auto_recovery_instances: Dict[str, RedisVectorAutoRecovery] = {}
_protection_middlewares: Dict[str, VectorstoreProtectionMiddleware] = {}


def initialize_auto_recovery_system() -> bool:
    """Inicializar sistema de auto-recovery global multi-tenant"""
    global _auto_recovery_instances, _protection_middlewares
    
    try:
        from app.config.company_config import get_company_manager
        
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        for company_id in companies.keys():
            try:
                if company_id not in _auto_recovery_instances:
                    _auto_recovery_instances[company_id] = RedisVectorAutoRecovery(company_id)
                    logger.info(f"Auto-recovery initialized for company: {company_id}")
                
                if company_id not in _protection_middlewares:
                    _protection_middlewares[company_id] = VectorstoreProtectionMiddleware(
                        _auto_recovery_instances[company_id]
                    )
                    logger.info(f"Protection middleware initialized for company: {company_id}")
                    
            except Exception as e:
                logger.error(f"Error initializing auto-recovery for company {company_id}: {e}")
                continue
        
        logger.info(f"Multi-tenant auto-recovery system initialized for {len(_auto_recovery_instances)} companies")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing multi-tenant auto-recovery: {e}")
        return False


def apply_vectorstore_protection(vectorstore_service, company_id: str = None) -> bool:
    """Aplicar protección a un servicio de vectorstore específico de empresa"""
    global _protection_middlewares
    
    target_company_id = company_id or getattr(vectorstore_service, 'company_id', 'default')
    
    if target_company_id not in _protection_middlewares:
        logger.error(f"Protection middleware not initialized for company: {target_company_id}")
        return False
    
    return _protection_middlewares[target_company_id].apply_protection(vectorstore_service)


def get_auto_recovery_instance(company_id: str = None) -> Optional[RedisVectorAutoRecovery]:
    """Obtener instancia de auto-recovery específica de empresa"""
    global _auto_recovery_instances
    
    if company_id is None:
        company_id = 'default'
    
    if company_id not in _auto_recovery_instances:
        # Crear instancia bajo demanda
        try:
            _auto_recovery_instances[company_id] = RedisVectorAutoRecovery(company_id)
            logger.info(f"Created auto-recovery instance on-demand for company: {company_id}")
        except Exception as e:
            logger.error(f"Error creating auto-recovery instance for company {company_id}: {e}")
            return None
    
    return _auto_recovery_instances.get(company_id)


def get_all_auto_recovery_instances() -> Dict[str, RedisVectorAutoRecovery]:
    """Obtener todas las instancias de auto-recovery"""
    return _auto_recovery_instances.copy()


def clear_auto_recovery_cache(company_id: str = None):
    """Limpiar cache de auto-recovery para una empresa específica o todas"""
    global _auto_recovery_instances, _protection_middlewares
    
    if company_id:
        # Clear específico de empresa
        if company_id in _auto_recovery_instances:
            _auto_recovery_instances[company_id].health_cache = {"last_check": 0, "status": None}
            logger.info(f"Auto-recovery cache cleared for company: {company_id}")
    else:
        # Clear todas las empresas
        for company_id, instance in _auto_recovery_instances.items():
            instance.health_cache = {"last_check": 0, "status": None}
        logger.info("Auto-recovery cache cleared for all companies")


def get_health_recommendations(health: Dict) -> List[str]:
    """Generar recomendaciones de salud multi-tenant"""
    recommendations = []
    company_id = health.get("company_id", "unknown")
    
    if health.get("needs_recovery"):
        recommendations.append(f"Index for {company_id} needs reconstruction - will auto-repair on next operation")
    
    if not health.get("index_exists"):
        recommendations.append(f"Index missing for {company_id} - will be recreated from stored documents")
    
    if health.get("healthy"):
        recommendations.append(f"System is healthy for {company_id} - no action required")
    
    if not recommendations:
        recommendations.append(f"System status unclear for {company_id} - manual inspection recommended")
    
    return recommendations


def get_system_wide_health() -> Dict[str, Any]:
    """Obtener salud de todo el sistema multi-tenant"""
    try:
        from app.config.company_config import get_company_manager
        
        company_manager = get_company_manager()
        companies = company_manager.get_all_companies()
        
        system_health = {
            "total_companies": len(companies),
            "companies_health": {},
            "overall_healthy": True,
            "timestamp": time.time()
        }
        
        for company_id in companies.keys():
            try:
                instance = get_auto_recovery_instance(company_id)
                if instance:
                    health = instance.verify_index_health()
                    system_health["companies_health"][company_id] = health
                    
                    if not health.get("healthy", False):
                        system_health["overall_healthy"] = False
                else:
                    system_health["companies_health"][company_id] = {
                        "healthy": False,
                        "error": "Auto-recovery instance not available"
                    }
                    system_health["overall_healthy"] = False
                    
            except Exception as e:
                system_health["companies_health"][company_id] = {
                    "healthy": False,
                    "error": str(e)
                }
                system_health["overall_healthy"] = False
        
        return system_health
        
    except Exception as e:
        return {
            "total_companies": 0,
            "companies_health": {},
            "overall_healthy": False,
            "error": str(e),
            "timestamp": time.time()
        }
