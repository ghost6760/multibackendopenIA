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
from langchain_community.chat_message_histories import RedisChatMessageHistory  # FIXED: Moved to community
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
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "7")
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
print(f"Account ID: {ACCOUNT_ID}")
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
# Multi-Tenant Architecture Components
# ===============================

class TenantManager:
    """
    Manages tenant-specific configurations and data isolation
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.tenant_cache = {}
        self._load_tenants()
    
    def _load_tenants(self):
        """Load tenant configurations from Redis"""
        try:
            tenant_keys = self.redis_client.keys("tenant:*:config")
            for key in tenant_keys:
                tenant_id = key.split(':')[1]
                config = self.redis_client.hgetall(key)
                if config:
                    self.tenant_cache[tenant_id] = config
            logger.info(f"✅ Loaded {len(self.tenant_cache)} tenant configurations")
        except Exception as e:
            logger.error(f"❌ Error loading tenant configurations: {e}")
    
    def get_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get configuration for a specific tenant"""
        if tenant_id in self.tenant_cache:
            return self.tenant_cache[tenant_id]
        
        try:
            config = self.redis_client.hgetall(f"tenant:{tenant_id}:config")
            if config:
                self.tenant_cache[tenant_id] = config
                return config
        except Exception as e:
            logger.error(f"Error getting tenant config for {tenant_id}: {e}")
        
        return {}
    
    def create_tenant_namespace(self, tenant_id: str, resource_type: str) -> str:
        """Create a namespaced key for tenant resources"""
        return f"tenant:{tenant_id}:{resource_type}"
    
    def get_tenant_from_conversation(self, conversation_id: str) -> Optional[str]:
        """Extract tenant ID from conversation context"""
        try:
            # Try to get tenant from conversation metadata
            tenant_key = f"conversation:{conversation_id}:tenant"
            tenant_id = self.redis_client.get(tenant_key)
            
            if not tenant_id:
                # Fallback: check if tenant is stored in conversation data
                conv_data = self.redis_client.hgetall(f"conversation:{conversation_id}")
                tenant_id = conv_data.get('tenant_id')
            
            return tenant_id
        except Exception as e:
            logger.error(f"Error getting tenant from conversation {conversation_id}: {e}")
            return None
    
    def register_conversation_tenant(self, conversation_id: str, tenant_id: str):
        """Register tenant for a conversation"""
        try:
            tenant_key = f"conversation:{conversation_id}:tenant"
            self.redis_client.set(tenant_key, tenant_id, ex=86400)  # 24 hours TTL
            logger.info(f"✅ Registered conversation {conversation_id} for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Error registering conversation tenant: {e}")

# Initialize Tenant Manager
tenant_manager = TenantManager(redis_client)

# ===============================
# Multi-Tenant LangChain Components Setup
# ===============================

class TenantLangChainManager:
    """
    Manages LangChain components per tenant with isolated configurations
    """
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self.embeddings_cache = {}
        self.chat_models_cache = {}
        self.vectorstores_cache = {}
    
    def get_tenant_embeddings(self, tenant_id: str) -> OpenAIEmbeddings:
        """Get or create embeddings for a specific tenant"""
        if tenant_id not in self.embeddings_cache:
            tenant_config = self.tenant_manager.get_tenant_config(tenant_id)
            
            # Use tenant-specific embedding model if configured
            embedding_model = tenant_config.get('embedding_model', EMBEDDING_MODEL)
            
            self.embeddings_cache[tenant_id] = OpenAIEmbeddings(
                model=embedding_model,
                openai_api_key=OPENAI_API_KEY
            )
            
            logger.info(f"✅ Created embeddings for tenant {tenant_id} with model {embedding_model}")
        
        return self.embeddings_cache[tenant_id]
    
    def get_tenant_chat_model(self, tenant_id: str) -> ChatOpenAI:
        """Get or create chat model for a specific tenant"""
        if tenant_id not in self.chat_models_cache:
            tenant_config = self.tenant_manager.get_tenant_config(tenant_id)
            
            # Use tenant-specific configurations if available
            model_name = tenant_config.get('model_name', MODEL_NAME)
            temperature = float(tenant_config.get('temperature', TEMPERATURE))
            max_tokens = int(tenant_config.get('max_tokens', MAX_TOKENS))
            
            self.chat_models_cache[tenant_id] = ChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=OPENAI_API_KEY
            )
            
            logger.info(f"✅ Created chat model for tenant {tenant_id} with model {model_name}")
        
        return self.chat_models_cache[tenant_id]
    
    def get_tenant_vectorstore(self, tenant_id: str) -> RedisVectorStore:
        """Get or create vector store for a specific tenant"""
        if tenant_id not in self.vectorstores_cache:
            embeddings = self.get_tenant_embeddings(tenant_id)
            tenant_config = self.tenant_manager.get_tenant_config(tenant_id)
            
            # Create tenant-specific index name
            index_name = f"tenant_{tenant_id}_documents"
            vector_dim = int(tenant_config.get('vector_dim', 1536))  # Default for text-embedding-3-small
            
            self.vectorstores_cache[tenant_id] = RedisVectorStore(
                embeddings,
                redis_url=REDIS_URL,
                index_name=index_name,
                vector_dim=vector_dim
            )
            
            logger.info(f"✅ Created vector store for tenant {tenant_id} with index {index_name}")
        
        return self.vectorstores_cache[tenant_id]

# Initialize Tenant LangChain Manager
langchain_manager = TenantLangChainManager(tenant_manager)

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

def classify_chunk_metadata(chunk, chunk_text: str, tenant_id: str) -> Dict[str, Any]:
    """Clasificar automáticamente metadata de chunks con información del tenant"""
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
        "tenant_id": tenant_id,  # Agregar tenant_id a los metadatos
        "treatment": treatment,
        "type": metadata_type,
        "section": section,
        "chunk_length": len(chunk_text),
        "has_headers": str(bool(chunk.metadata)).lower(),  # "true" o "false"
        "processed_at": datetime.utcnow().isoformat()
    }
    
    return metadata

def advanced_chunk_processing(text: str, tenant_id: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Procesar texto usando sistema de chunking avanzado con información del tenant
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
                metadata = classify_chunk_metadata(chunk, chunk.page_content, tenant_id)
                metadatas.append(metadata)
        
        logger.info(f"Processed {len(processed_texts)} chunks using advanced chunking for tenant {tenant_id}")
        
        return processed_texts, metadatas
        
    except Exception as e:
        logger.error(f"Error in advanced chunk processing for tenant {tenant_id}: {e}")
        return [], []

# ===============================
# Multi-Tenant BOT ACTIVATION LOGIC
# ===============================

BOT_ACTIVE_STATUSES = ["open"]
BOT_INACTIVE_STATUSES = ["pending", "resolved", "snoozed"]

status_lock = threading.Lock()

def update_bot_status(conversation_id, conversation_status, tenant_id: str):
    """Update bot status for a specific conversation in Redis with tenant isolation"""
    with status_lock:
        is_active = conversation_status in BOT_ACTIVE_STATUSES
        
        # Store in Redis with tenant namespace
        status_key = tenant_manager.create_tenant_namespace(tenant_id, f"bot_status:{conversation_id}")
        status_data = {
            'active': str(is_active),
            'status': conversation_status,
            'tenant_id': tenant_id,
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
            logger.error(f"Error updating bot status in Redis for tenant {tenant_id}: {e}")

def should_bot_respond(conversation_id, conversation_status, tenant_id: str):
    """Determine if bot should respond based on conversation status and tenant"""
    update_bot_status(conversation_id, conversation_status, tenant_id)
    is_active = conversation_status in BOT_ACTIVE_STATUSES
    
    if is_active:
        logger.info(f"✅ Tenant {tenant_id} - Bot WILL respond to conversation {conversation_id} (status: {conversation_status})")
    else:
        if conversation_status == "pending":
            logger.info(f"⏸️ Tenant {tenant_id} - Bot will NOT respond to conversation {conversation_id} (status: pending - INACTIVE)")
        else:
            logger.info(f"🚫 Tenant {tenant_id} - Bot will NOT respond to conversation {conversation_id} (status: {conversation_status})")
    
    return is_active

def is_message_already_processed(message_id, conversation_id, tenant_id: str):
    """Check if message has already been processed using Redis with tenant isolation"""
    if not message_id:
        return False
    
    key = tenant_manager.create_tenant_namespace(tenant_id, f"processed_message:{conversation_id}:{message_id}")
    
    try:
        if redis_client.exists(key):
            logger.info(f"🔄 Tenant {tenant_id} - Message {message_id} already processed, skipping")
            return True
        
        redis_client.set(key, "1", ex=3600)  # 1 hour TTL
        logger.info(f"✅ Tenant {tenant_id} - Message {message_id} marked as processed")
        return False
        
    except Exception as e:
        logger.error(f"Error checking processed message in Redis for tenant {tenant_id}: {e}")
        return False

# ===============================
# Multi-Tenant Modern Conversation Manager
# ===============================

class MultiTenantConversationManager:
    """
    Multi-Tenant Conversation Manager con aislamiento completo de datos por tenant
    
    CARACTERÍSTICAS MULTI-TENANT:
    - Aislamiento completo de datos por tenant usando namespaces
    - Configuraciones específicas por tenant
    - Gestión independiente de historiales de chat
    - Compatibilidad con código existente mantenida
    """
    
    def __init__(self, redis_client, tenant_manager: TenantManager, max_messages: int = 10):
        self.redis_client = redis_client
        self.tenant_manager = tenant_manager
        self.max_messages = max_messages
        self.conversations = {}
        self.message_histories = {}
        self.load_conversations_from_redis()
        
    
    def _get_tenant_conversation_key(self, tenant_id: str, user_id: str) -> str:
        """Generate tenant-specific conversation key"""
        return self.tenant_manager.create_tenant_namespace(tenant_id, f"conversation:{user_id}")
    
    def _get_tenant_message_history_key(self, tenant_id: str, user_id: str) -> str:
        """Generate tenant-specific message history key for Redis"""
        return self.tenant_manager.create_tenant_namespace(tenant_id, f"chat_history:{user_id}")
    
    def _create_tenant_user_id(self, tenant_id: str, contact_id: str) -> str:
        """Generate tenant-specific user ID"""
        if not contact_id.startswith("chatwoot_contact_"):
            contact_id = f"chatwoot_contact_{contact_id}"
        return f"{tenant_id}:{contact_id}"
    
    def _get_redis_connection_params(self) -> Dict[str, Any]:
        """
        Extract Redis connection parameters from client
        MEJORADO: Maneja diferentes tipos de configuraciones de Redis
        """
        try:
            # Opción 1: Usar URL directamente (más simple y robusto)
            if hasattr(self.redis_client, 'connection_pool'):
                pool = self.redis_client.connection_pool
                connection_kwargs = pool.connection_kwargs
                
                return {
                    "url": REDIS_URL,  # Usar URL directamente
                    "ttl": 604800  # 7 días
                }
            
            # Opción 2: Fallback a parámetros por defecto
            return {
                "url": REDIS_URL,
                "ttl": 604800
            }
            
        except Exception as e:
            logger.warning(f"Could not extract Redis params, using defaults: {e}")
            return {
                "url": REDIS_URL,
                "ttl": 604800
            }
    
    def _get_or_create_redis_history(self, tenant_id: str, user_id: str) -> BaseChatMessageHistory:
        """
        Método interno para crear/obtener RedisChatMessageHistory con aislamiento por tenant
        """
        tenant_user_id = self._create_tenant_user_id(tenant_id, user_id)
        
        if not tenant_user_id:
            raise ValueError("tenant_user_id cannot be empty")
        
        # Usar caché en memoria para evitar recrear objetos
        if tenant_user_id not in self.message_histories:
            try:
                redis_params = self._get_redis_connection_params()
                
                # Crear session_id específico para el tenant
                session_id = self._get_tenant_message_history_key(tenant_id, user_id)
                
                # Crear RedisChatMessageHistory con parámetros mejorados
                self.message_histories[tenant_user_id] = RedisChatMessageHistory(
                    session_id=session_id,
                    url=redis_params["url"],
                    key_prefix="",  # Ya incluido en session_id
                    ttl=redis_params["ttl"]
                )
                
                logger.info(f"✅ Created Redis message history for tenant {tenant_id}, user {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Error creating Redis message history for tenant {tenant_id}, user {user_id}: {e}")
                # Crear una historia en memoria como fallback
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self.message_histories[tenant_user_id] = InMemoryChatMessageHistory()
                logger.warning(f"⚠️ Using in-memory fallback for tenant {tenant_id}, user {user_id}")
            
            # Aplicar límite de mensajes (ventana deslizante)
            self._apply_message_window(tenant_id, user_id)
        
        return self.message_histories[tenant_user_id]
    
    def get_chat_history(self, tenant_id: str, user_id: str, format_type: str = "dict") -> Any:
        """
        Método unificado para obtener chat history en diferentes formatos con aislamiento por tenant
        
        Args:
            tenant_id: ID del tenant
            user_id: ID del usuario
            format_type: Formato de salida
                - "dict": Lista de diccionarios con role/content (DEFAULT - compatibilidad)
                - "langchain": Objeto BaseChatMessageHistory nativo de LangChain
                - "messages": Lista de objetos BaseMessage de LangChain
        
        Returns:
            Chat history en el formato especificado
        """
        if not tenant_id or not user_id:
            if format_type == "dict":
                return []
            elif format_type == "langchain":
                from langchain_core.chat_history import InMemoryChatMessageHistory
                return InMemoryChatMessageHistory()
            elif format_type == "messages":
                return []
            else:
                return []
        
        try:
            # Obtener el objeto Redis history (centralizado)
            redis_history = self._get_or_create_redis_history(tenant_id, user_id)
            
            # Retornar según el formato solicitado
            if format_type == "langchain":
                # Formato nativo LangChain - para uso con RunnableWithMessageHistory
                return redis_history
            
            elif format_type == "messages":
                # Lista de objetos BaseMessage - para casos avanzados
                return redis_history.messages
            
            elif format_type == "dict":
                # Formato diccionario - para compatibilidad con código existente
                messages = redis_history.messages
                
                chat_history = []
                for msg in messages:
                    if isinstance(msg, HumanMessage):
                        chat_history.append({
                            "role": "user",
                            "content": msg.content
                        })
                    elif isinstance(msg, AIMessage):
                        chat_history.append({
                            "role": "assistant", 
                            "content": msg.content
                        })
                
                return chat_history
            
            else:
                logger.warning(f"Unknown format_type: {format_type}, defaulting to dict")
                return self.get_chat_history(tenant_id, user_id, "dict")
                
        except Exception as e:
            logger.error(f"Error getting chat history for tenant {tenant_id}, user {user_id}: {e}")
            # Retornar valores por defecto según el formato
            if format_type == "dict":
                return []
            elif format_type == "langchain":
                from langchain_core.chat_history import InMemoryChatMessageHistory
                return InMemoryChatMessageHistory()
            elif format_type == "messages":
                return []
            else:
                return []
    
    def _apply_message_window(self, tenant_id: str, user_id: str):
        """
        Aplica ventana deslizante de mensajes para mantener solo los últimos N mensajes
        """
        try:
            tenant_user_id = self._create_tenant_user_id(tenant_id, user_id)
            history = self.message_histories[tenant_user_id]
            messages = history.messages
            
            # Obtener configuración específica del tenant para max_messages
            tenant_config = self.tenant_manager.get_tenant_config(tenant_id)
            max_messages = int(tenant_config.get('max_context_messages', self.max_messages))
            
            if len(messages) > max_messages:
                # Mantener solo los últimos max_messages
                messages_to_keep = messages[-max_messages:]
                
                # Limpiar el historial existente
                history.clear()
                
                # Agregar solo los mensajes que queremos mantener
                for message in messages_to_keep:
                    history.add_message(message)
                
                logger.info(f"✅ Applied message window for tenant {tenant_id}, user {user_id}: kept {len(messages_to_keep)} messages")
        
        except Exception as e:
            logger.error(f"❌ Error applying message window for tenant {tenant_id}, user {user_id}: {e}")
    
    def add_message(self, tenant_id: str, user_id: str, role: str, content: str) -> bool:
        """
        Add message with automatic window management and tenant isolation
        """
        if not tenant_id or not user_id or not content.strip():
            logger.warning("Invalid tenant_id, user_id or content for message")
            return False
        
        try:
            # Usar el método unificado para obtener history
            history = self.get_chat_history(tenant_id, user_id, format_type="langchain")
            
            # Add message to history
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            else:
                logger.warning(f"Unknown role: {role}")
                return False
            
            # Update cache and apply window management
            tenant_user_id = self._create_tenant_user_id(tenant_id, user_id)
            if tenant_user_id in self.message_histories:
                self._apply_message_window(tenant_id, user_id)
            
            # Update metadata
            self._update_conversation_metadata(tenant_id, user_id)
            
            logger.info(f"✅ Message added for tenant {tenant_id}, user {user_id} (role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding message for tenant {tenant_id}, user {user_id}: {e}")
            return False
    
    def _update_conversation_metadata(self, tenant_id: str, user_id: str):
        """Update conversation metadata in Redis with tenant isolation"""
        try:
            conversation_key = self._get_tenant_conversation_key(tenant_id, user_id)
            metadata = {
                'last_updated': str(time.time()),
                'tenant_id': tenant_id,
                'user_id': user_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)  # 7 días TTL
            
        except Exception as e:
            logger.error(f"Error updating metadata for tenant {tenant_id}, user {user_id}: {e}")
    
    def load_conversations_from_redis(self):
        """
        Load conversations from Redis with multi-tenant support
        """
        try:
            # Buscar claves de conversación por tenant
            tenant_conversation_keys = self.redis_client.keys("tenant:*:conversation:*")
            tenant_chat_history_keys = self.redis_client.keys("tenant:*:chat_history:*")
            
            loaded_count = 0
            
            # Migrar datos existentes si es necesario
            for key in tenant_conversation_keys:
                try:
                    # Extraer tenant_id y user_id del key
                    key_parts = key.split(':')
                    if len(key_parts) >= 4:
                        tenant_id = key_parts[1]
                        user_id = ':'.join(key_parts[3:])  # En caso de que user_id tenga ':'
                        
                        context_data = self.redis_client.hgetall(key)
                        
                        if context_data and 'messages' in context_data:
                            # Migrar mensajes antiguos al nuevo formato
                            old_messages = json.loads(context_data['messages'])
                            history = self.get_chat_history(tenant_id, user_id, format_type="langchain")
                            
                            # Verificar si ya migró
                            if len(history.messages) == 0 and old_messages:
                                for msg in old_messages:
                                    if msg.get('role') == 'user':
                                        history.add_user_message(msg['content'])
                                    elif msg.get('role') == 'assistant':
                                        history.add_ai_message(msg['content'])
                                
                                self._apply_message_window(tenant_id, user_id)
                                loaded_count += 1
                                logger.info(f"✅ Migrated conversation for tenant {tenant_id}, user {user_id}")
                
                except Exception as e:
                    logger.warning(f"Failed to migrate conversation {key}: {e}")
                    continue
            
            # Contar conversaciones ya en nuevo formato
            for key in tenant_chat_history_keys:
                key_parts = key.split(':')
                if len(key_parts) >= 4 and key not in [self._get_tenant_message_history_key(key_parts[1], ':'.join(key_parts[3:])) for conv_key in tenant_conversation_keys]:
                    loaded_count += 1
            
            logger.info(f"✅ Loaded {loaded_count} multi-tenant conversation contexts from Redis")
            
        except Exception as e:
            logger.error(f"❌ Error loading multi-tenant contexts from Redis: {e}")
    
    def get_message_count(self, tenant_id: str, user_id: str) -> int:
        """Get total message count for a user in a specific tenant"""
        try:
            history = self.get_chat_history(tenant_id, user_id, format_type="langchain")
            return len(history.messages)
        except Exception as e:
            logger.error(f"Error getting message count for tenant {tenant_id}, user {user_id}: {e}")
            return 0
    
    def clear_conversation(self, tenant_id: str, user_id: str) -> bool:
        """Clear conversation history for a user in a specific tenant"""
        try:
            history = self.get_chat_history(tenant_id, user_id, format_type="langchain")
            history.clear()
            
            # Limpiar metadata
            conversation_key = self._get_tenant_conversation_key(tenant_id, user_id)
            self.redis_client.delete(conversation_key)
            
            # Limpiar caché
            tenant_user_id = self._create_tenant_user_id(tenant_id, user_id)
            if tenant_user_id in self.message_histories:
                del self.message_histories[tenant_user_id]
            
            logger.info(f"✅ Cleared conversation for tenant {tenant_id}, user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing conversation for tenant {tenant_id}, user {user_id}: {e}")
            return False
    
    def get_tenant_conversation_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a specific tenant"""
        try:
            # Buscar todas las conversaciones del tenant
            pattern = self.tenant_manager.create_tenant_namespace(tenant_id, "conversation:*")
            conversation_keys = self.redis_client.keys(pattern)
            
            stats = {
                'tenant_id': tenant_id,
                'total_conversations': len(conversation_keys),
                'active_conversations': 0,
                'total_messages': 0,
                'last_activity': None
            }
            
            latest_timestamp = 0
            
            for key in conversation_keys:
                try:
                    conv_data = self.redis_client.hgetall(key)
                    if conv_data:
                        # Extraer user_id del key
                        user_id = key.split(':')[-1]
                        message_count = self.get_message_count(tenant_id, user_id)
                        stats['total_messages'] += message_count
                        
                        if message_count > 0:
                            stats['active_conversations'] += 1
                        
                        # Actualizar último timestamp
                        last_updated = float(conv_data.get('last_updated', 0))
                        if last_updated > latest_timestamp:
                            latest_timestamp = last_updated
                
                except Exception as e:
                    logger.warning(f"Error processing conversation stats for {key}: {e}")
                    continue
            
            if latest_timestamp > 0:
                stats['last_activity'] = datetime.fromtimestamp(latest_timestamp).isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting tenant conversation stats for {tenant_id}: {e}")
            return {
                'tenant_id': tenant_id,
                'total_conversations': 0,
                'active_conversations': 0,
                'total_messages': 0,
                'last_activity': None,
                'error': str(e)
            }

# Initialize Multi-Tenant Conversation Manager
conversation_manager = MultiTenantConversationManager(redis_client, tenant_manager, MAX_CONTEXT_MESSAGES)
