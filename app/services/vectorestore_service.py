from langchain_redis import RedisVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from app.services.redis_service import get_redis_client
from app.services.openai_service import OpenAIService
from app.config.company_config import get_company_config, CompanyConfig
from flask import current_app
import logging
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def init_vectorstore(app):
    """Initialize vectorstore configuration"""
    try:
        # This is mainly for validation at startup
        redis_url = app.config.get('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL not found in configuration")
        
        logger.info("✅ Vectorstore configuration validated")
        return True
    except Exception as e:
        logger.error(f"❌ Vectorstore initialization failed: {e}")
        raise

class VectorstoreService:
    """Service for managing vector storage and retrieval - Multi-Company"""
    
    def __init__(self, company_id:
