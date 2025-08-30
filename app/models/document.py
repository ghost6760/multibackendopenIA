from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config
from datetime import datetime
import hashlib
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DocumentManager:
    """Manager for document operations multi-tenant"""
    
    def __init__(self, company_id: str = None):
        self.company_id = company_id or "default"
        self.company_config = get_company_config(self.company_id)
        
        # Configurar prefijo específico de empresa
        if self.company_config:
            self.redis_prefix = self.company_config.redis_prefix + "document:"
        else:
            self.redis_prefix = f"{self.company_id}:document:"
        
        self.redis_client = get_redis_client()
        self.change_tracker = DocumentChangeTracker(self.redis_client, self.company_id)
        
        logger.info(f"DocumentManager initialized for company: {self.company_id}")
    
    def add_document(self, content: str, metadata: Dict[str, Any], 
                    vectorstore_service) -> Tuple[str, int]:
        """Add a single document with company isolation"""
        # Generate doc_id with company prefix
        base_doc_id = hashlib.md5(content.encode()).hexdigest()
        doc_id = f"{self.company_id}_{base_doc_id}"
        
        # Enrich metadata with company info
        metadata.update({
            'doc_id': doc_id,
            'company_id': self.company_id,
            'company_name': self.company_config.company_name if self.company_config else self.company_id
        })
        
        # Create chunks
        texts, chunk_metadatas = vectorstore_service.create_chunks
