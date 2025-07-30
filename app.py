import os
import sys
import time
import logging
import requests
import json
from typing import List, Dict, Any, Optional, Tuple
from flask import Flask, request, jsonify, send_file, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
import threading
import numpy as np
from datetime import datetime, timedelta
import hashlib
import redis

# LangChain imports - ACTUALIZADOS Y CORREGIDOS
from langchain.schema import Document as LangChainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_redis import RedisVectorStore

# Nuevas importaciones para el sistema moderno - CORREGIDAS
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch, RunnableLambda
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.text_splitter import MarkdownHeaderTextSplitter

# Load environment variables
load_dotenv()

# ===============================
# Environment Setup
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHATWOOT_API_KEY = os.getenv("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://chatwoot-production-0f1d.up.railway.app")
PORT = int(os.getenv("PORT", 8080))

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1500))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.7))
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", 10))

# Embedding configuration
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.7))
MAX_RETRIEVED_DOCS = int(os.getenv("MAX_RETRIEVED_DOCS", 3))

if not OPENAI_API_KEY or not CHATWOOT_API_KEY:
    print("ERROR: Missing required environment variables")
    print("Required: OPENAI_API_KEY, CHATWOOT_API_KEY")
    sys.exit(1)

print("Environment loaded successfully")
print(f"Chatwoot URL: {CHATWOOT_BASE_URL}")
print(f"Model: {MODEL_NAME}")
print(f"Embedding Model: {EMBEDDING_MODEL}")
print(f"Redis URL: {REDIS_URL}")

# Initialize Flask
app = Flask(__name__, static_url_path='', static_folder='.')

# Initialize Redis - MEJORADO
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    print("✅ Redis connection successful")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    sys.exit(1)

# Logging configuration
log_level = logging.INFO if os.getenv("ENVIRONMENT") == "production" else logging.DEBUG
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ===============================
# Tenant-Aware Vector Store Factory
# ===============================

class TenantVectorStore:
    """Factory para crear vector stores específicos por tenant"""
    
    _vectorstores = {}
    
    @classmethod
    def get_vectorstore(cls, tenant_id: str) -> RedisVectorStore:
        """Obtener o crear vector store para un tenant específico"""
        if tenant_id not in cls._vectorstores:
            index_name = f"tenant_{tenant_id}_documents"
            cls._vectorstores[tenant_id] = RedisVectorStore(
                OpenAIEmbeddings(
                    model=EMBEDDING_MODEL,
                    openai_api_key=OPENAI_API_KEY
                ),
                redis_url=REDIS_URL,
                index_name=index_name,
                vector_dim=1536
            )
            logger.info(f"✅ Created vector store for tenant: {tenant_id}")
        return cls._vectorstores[tenant_id]

# ===============================
# LangChain Components Setup
# ===============================

# Initialize LangChain components
chat_model = ChatOpenAI(
    model_name=MODEL_NAME,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    openai_api_key=OPENAI_API_KEY
)

def create_advanced_chunking_system():
    """
    Crear sistema de chunking avanzado con MarkdownHeaderTextSplitter
    """
    # Headers para dividir el contenido
    headers_to_split_on = [
        ("##", "treatment"),  # Nivel 1: Tratamientos
        ("###", "detail"),  # Detalles importantes
    ]
    
    # Crear splitter principal
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,       # Mantener el texto del header en cada chunk
        return_each_line=False     # Agrupar todo bajo el mismo header
    
    )
    
    # Fallback para textos largos sin headers
    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,       # ≈250 tokens
        chunk_overlap=200,     # ≈20% de solapamiento
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len
    )
    
    return markdown_splitter, fallback_splitter

def normalize_text(text: str) -> str:
    """Normalizar texto preservando estructura de líneas"""
    if not text or not text.strip():
        return ""
    
    # Split into lines and normalize each line
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        line = line.strip()
        if line:  # Skip empty lines
            # Lowercase and collapse internal spaces
            line = line.lower()
            line = ' '.join(line.split())
            normalized_lines.append(line)
    
    # Join lines back with newlines
    return '\n'.join(normalized_lines)

def classify_chunk_metadata(chunk, chunk_text: str) -> Dict[str, Any]:
    """Clasificar automáticamente metadata de chunks"""
    section = chunk.metadata.get("section", "").lower()
    treatment = chunk.metadata.get("treatment", "general")
    
    # Clasificación automática
    if any(word in section for word in ["funciona", "beneficio", "detalle", "procedimiento", "resultado"]):
        metadata_type = "general"
    elif any(word in section for word in ["precio", "oferta", "horario", "costo", "inversión", "promoción"]):
        metadata_type = "específico"
    elif any(word in section for word in ["contraindicación", "cuidado", "post", "recomendación"]):
        metadata_type = "cuidados"
    else:
        metadata_type = "otro"
    
    # Convertir booleano a string
    metadata = {
        "treatment": treatment,
        "type": metadata_type,
        "section": section,
        "chunk_length": len(chunk_text),
        "has_headers": str(bool(chunk.metadata)).lower(),  # "true" o "false"
        "processed_at": datetime.utcnow().isoformat()
    }
    
    return metadata

def advanced_chunk_processing(text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Procesar texto usando sistema de chunking avanzado
    """
    if not text or not text.strip():
        return [], []
    
    try:
        # Crear splitters
        markdown_splitter, fallback_splitter = create_advanced_chunking_system()
        
        # Normalizar texto
        normalized_text = normalize_text(text)
        
        # Intentar chunking con headers primero
        try:
            chunks = markdown_splitter.split_text(normalized_text)
            
            # Si no se encontraron headers, usar fallback
            if not chunks or all(not chunk.metadata for chunk in chunks):
                logger.info("No headers found, using fallback chunking")
                text_chunks = fallback_splitter.split_text(normalized_text)
                
                # Crear chunks simples para fallback
                chunks = []
                for i, chunk_text in enumerate(text_chunks):
                    chunk_obj = type('Chunk', (), {
                        'page_content': chunk_text,
                        'metadata': {'section': f'chunk_{i}', 'treatment': 'general'}
                    })()
                    chunks.append(chunk_obj)
            
        except Exception as e:
            logger.warning(f"Error in markdown chunking, using fallback: {e}")
            text_chunks = fallback_splitter.split_text(normalized_text)
            
            # Crear chunks simples para fallback
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                chunk_obj = type('Chunk', (), {
                    'page_content': chunk_text,
                    'metadata': {'section': f'chunk_{i}', 'treatment': 'general'}
                })()
                chunks.append(chunk_obj)
        
        # Procesar chunks y generar metadatas
        processed_texts = []
        metadatas = []
        
        for chunk in chunks:
            if chunk.page_content and chunk.page_content.strip():
                processed_texts.append(chunk.page_content)
                metadata = classify_chunk_metadata(chunk, chunk.page_content)
                metadatas.append(metadata)
        
        logger.info(f"Processed {len(processed_texts)} chunks using advanced chunking")
        
        return processed_texts, metadatas
        
    except Exception as e:
        logger.error(f"Error in advanced chunk processing: {e}")
        return [], []

# ===============================
# BOT ACTIVATION LOGIC (Tenant-Aware)
# ===============================

BOT_ACTIVE_STATUSES = ["open"]
BOT_INACTIVE_STATUSES = ["pending", "resolved", "snoozed"]

status_lock = threading.Lock()

def update_bot_status(tenant_id: str, conversation_id: str, conversation_status: str):
    """Update bot status for a specific conversation in Redis"""
    with status_lock:
        is_active = conversation_status in BOT_ACTIVE_STATUSES
        
        # Store in Redis with tenant namespace
        status_key = f"tenant:{tenant_id}:bot_status:{conversation_id}"
        status_data = {
            'active': str(is_active),
            'status': conversation_status,
            'updated_at': str(time.time())
        }
        
        try:
            old_status = redis_client.hget(status_key, 'active')
            redis_client.hset(status_key, mapping=status_data)
            redis_client.expire(status_key, 86400)  # 24 hours TTL
            
            if old_status != str(is_active):
                status_text = "ACTIVO" if is_active else "INACTIVO"
                logger.info(f"🔄 Tenant {tenant_id} - Conversation {conversation_id}: Bot {status_text} (status: {conversation_status})")
                
        except Exception as e:
            logger.error(f"Error updating bot status in Redis: {e}")

def should_bot_respond(tenant_id: str, conversation_id: str, conversation_status: str) -> bool:
    """Determine if bot should respond based on conversation status"""
    update_bot_status(tenant_id, conversation_id, conversation_status)
    is_active = conversation_status in BOT_ACTIVE_STATUSES
    
    if is_active:
        logger.info(f"✅ Tenant {tenant_id} - Bot WILL respond to conversation {conversation_id} (status: {conversation_status})")
    else:
        if conversation_status == "pending":
            logger.info(f"⏸️ Tenant {tenant_id} - Bot will NOT respond to conversation {conversation_id} (status: pending - INACTIVE)")
        else:
            logger.info(f"🚫 Tenant {tenant_id} - Bot will NOT respond to conversation {conversation_id} (status: {conversation_status})")
    
    return is_active

def is_message_already_processed(tenant_id: str, message_id: str, conversation_id: str) -> bool:
    """Check if message has already been processed using Redis"""
    if not message_id:
        return False
    
    key = f"tenant:{tenant_id}:processed_message:{conversation_id}:{message_id}"
    
    try:
        if redis_client.exists(key):
            logger.info(f"🔄 Tenant {tenant_id} - Message {message_id} already processed, skipping")
            return True
        
        redis_client.set(key, "1", ex=3600)  # 1 hour TTL
        logger.info(f"✅ Tenant {tenant_id} - Message {message_id} marked as processed")
        return False
        
    except Exception as e:
        logger.error(f"Error checking processed message in Redis: {e}")
        return False

# ===============================
# REFACTORED Modern Conversation Manager - UNIFIED CHAT HISTORY (Tenant-Aware)
# ===============================

class ModernConversationManager:
    """
    REFACTORED: Conversation Manager moderno con multi-tenant
    CAMBIOS PRINCIPALES:
    - Soporte para multi-tenant mediante namespaces en Redis
    - Identificación de tenant en todas las operaciones
    - Aislamiento de datos entre empresas
    """
    
    def __init__(self, redis_client, max_messages: int = 10):
        self.redis_client = redis_client
        self.max_messages = max_messages
        self.message_histories = {}
        
    def _get_conversation_key(self, tenant_id: str, user_id: str) -> str:
        """Generate standardized conversation key with tenant namespace"""
        return f"tenant:{tenant_id}:conversation:{user_id}"
    
    def _get_message_history_key(self, tenant_id: str, user_id: str) -> str:
        """Generate standardized message history key with tenant namespace"""
        return f"tenant:{tenant_id}:chat_history:{user_id}"
    
    def _create_user_id(self, contact_id: str) -> str:
        """Generate standardized user ID"""
        if not contact_id.startswith("chatwoot_contact_"):
            return f"chatwoot_contact_{contact_id}"
        return contact_id
    
    def _get_redis_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters"""
        return {
            "url": REDIS_URL,
            "ttl": 604800  # 7 días
        }
    
    def _get_or_create_redis_history(self, tenant_id: str, user_id: str) -> BaseChatMessageHistory:
        """Crear/obtener RedisChatMessageHistory con namespace de tenant"""
        cache_key = f"{tenant_id}:{user_id}"
        
        if cache_key not in self.message_histories:
            try:
                redis_params = self._get_redis_connection_params()
                
                self.message_histories[cache_key] = RedisChatMessageHistory(
                    session_id=user_id,
                    url=redis_params["url"],
                    key_prefix=f"tenant:{tenant_id}:chat_history:",
                    ttl=redis_params["ttl"]
                )
                
                logger.info(f"✅ Created Redis message history for tenant:{tenant_id} user:{user_id}")
                
            except Exception as e:
                logger.error(f"❌ Error creating Redis message history: {e}")
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self.message_histories[cache_key] = InMemoryChatMessageHistory()
                logger.warning(f"⚠️ Using in-memory fallback for tenant:{tenant_id} user:{user_id}")
            
            self._apply_message_window(tenant_id, user_id)
        
        return self.message_histories[cache_key]
    
    def get_chat_history(self, tenant_id: str, user_id: str, format_type: str = "dict") -> Any:
        """Obtener historial de chat con identificación de tenant"""
        if not tenant_id or not user_id:
            return [] if format_type == "dict" else []
        
        try:
            redis_history = self._get_or_create_redis_history(tenant_id, user_id)
            
            if format_type == "langchain":
                return redis_history
            
            elif format_type == "messages":
                return redis_history.messages
            
            elif format_type == "dict":
                chat_history = []
                for msg in redis_history.messages:
                    if isinstance(msg, HumanMessage):
                        chat_history.append({"role": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        chat_history.append({"role": "assistant", "content": msg.content})
                return chat_history
            
            else:
                return self.get_chat_history(tenant_id, user_id, "dict")
                
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return [] if format_type == "dict" else []
    
    def _apply_message_window(self, tenant_id: str, user_id: str):
        """Mantener solo los últimos N mensajes"""
        try:
            cache_key = f"{tenant_id}:{user_id}"
            history = self.message_histories[cache_key]
            messages = history.messages
            
            if len(messages) > self.max_messages:
                messages_to_keep = messages[-self.max_messages:]
                history.clear()
                for message in messages_to_keep:
                    history.add_message(message)
                
                logger.info(f"✅ Applied message window for tenant:{tenant_id} user:{user_id}")
        
        except Exception as e:
            logger.error(f"Error applying message window: {e}")
    
    def add_message(self, tenant_id: str, user_id: str, role: str, content: str) -> bool:
        """Agregar mensaje con gestión de tenant"""
        if not tenant_id or not user_id or not content.strip():
            return False
        
        try:
            history = self._get_or_create_redis_history(tenant_id, user_id)
            
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            else:
                return False
            
            self._apply_message_window(tenant_id, user_id)
            self._update_conversation_metadata(tenant_id, user_id)
            return True
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def _update_conversation_metadata(self, tenant_id: str, user_id: str):
        """Actualizar metadatos con namespace de tenant"""
        try:
            conversation_key = self._get_conversation_key(tenant_id, user_id)
            metadata = {
                'last_updated': str(time.time()),
                'user_id': user_id,
                'tenant_id': tenant_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)
            
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
    
    def get_message_count(self, tenant_id: str, user_id: str) -> int:
        """Obtener conteo de mensajes por tenant"""
        try:
            history = self._get_or_create_redis_history(tenant_id, user_id)
            return len(history.messages)
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            return 0
    
    def clear_conversation(self, tenant_id: str, user_id: str) -> bool:
        """Limpiar conversación con identificación de tenant"""
        try:
            cache_key = f"{tenant_id}:{user_id}"
            if cache_key in self.message_histories:
                history = self.message_histories[cache_key]
                history.clear()
                del self.message_histories[cache_key]
            
            conversation_key = self._get_conversation_key(tenant_id, user_id)
            self.redis_client.delete(conversation_key)
            
            logger.info(f"✅ Cleared conversation for tenant:{tenant_id} user:{user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            return False

# Inicializar conversation manager
conversation_manager = ModernConversationManager(redis_client, max_messages=MAX_CONTEXT_MESSAGES)
