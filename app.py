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
from functools import wraps
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
# LangChain Components Setup
# ===============================

# Initialize LangChain components
embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL,
    openai_api_key=OPENAI_API_KEY
)

chat_model = ChatOpenAI(
    model_name=MODEL_NAME,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    openai_api_key=OPENAI_API_KEY
)

# Vectorstore se inicializará dinámicamente por tenant
def get_vectorstore(tenant_id: str) -> RedisVectorStore:
    """Obtener vectorstore específico para cada tenant"""
    return RedisVectorStore(
        embeddings,
        redis_url=REDIS_URL,
        index_name=f"tenant_{tenant_id}_documents",
        vector_dim=1536
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
# TENANT REGISTRY SYSTEM
# ===============================

class TenantRegistry:
    """
    Sistema de registro centralizado para tenants con verificación de existencia
    y manejo de metadata básica
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.registry_key = "tenant_registry"
    
    def register_tenant(self, tenant_id: str, metadata: Optional[Dict] = None) -> bool:
        """Registrar un nuevo tenant con metadata básica"""
        if not tenant_id or not tenant_id.strip():
            raise ValueError("Invalid tenant ID")
        
        metadata = metadata or {}
        metadata.update({
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
            "status": "active"
        })
        
        try:
            # Usar HSET para almacenar metadata del tenant
            self.redis.hset(
                self.registry_key, 
                tenant_id, 
                json.dumps(metadata)
            )
            logger.info(f"✅ Tenant {tenant_id} registered successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register tenant {tenant_id}: {e}")
            return False
    
    def unregister_tenant(self, tenant_id: str) -> bool:
        """Eliminar registro de tenant (no elimina datos asociados)"""
        try:
            removed = self.redis.hdel(self.registry_key, tenant_id)
            if removed > 0:
                logger.info(f"✅ Tenant {tenant_id} unregistered")
                return True
            logger.warning(f"⚠️ Tenant {tenant_id} not found in registry")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to unregister tenant {tenant_id}: {e}")
            return False
    
    def is_tenant_registered(self, tenant_id: str) -> bool:
        """Verificar si un tenant está registrado"""
        try:
            return self.redis.hexists(self.registry_key, tenant_id)
        except Exception as e:
            logger.error(f"❌ Tenant verification failed for {tenant_id}: {e}")
            return False
    
    def get_tenant_metadata(self, tenant_id: str) -> Optional[Dict]:
        """Obtener metadata del tenant"""
        try:
            meta_json = self.redis.hget(self.registry_key, tenant_id)
            return json.loads(meta_json) if meta_json else None
        except Exception as e:
            logger.error(f"❌ Failed to get metadata for tenant {tenant_id}: {e}")
            return None
    
    def update_tenant_activity(self, tenant_id: str) -> bool:
        """Actualizar timestamp de última actividad"""
        if not self.is_tenant_registered(tenant_id):
            logger.warning(f"⚠️ Activity update for unregistered tenant: {tenant_id}")
            return False
        
        try:
            meta = self.get_tenant_metadata(tenant_id) or {}
            meta["last_active"] = datetime.utcnow().isoformat()
            self.redis.hset(self.registry_key, tenant_id, json.dumps(meta))
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update activity for tenant {tenant_id}: {e}")
            return False
    
    def list_registered_tenants(self) -> List[Dict]:
        """Listar todos los tenants registrados con metadata básica"""
        try:
            all_tenants = []
            tenant_map = self.redis.hgetall(self.registry_key)
            
            for tenant_id, meta_json in tenant_map.items():
                try:
                    meta = json.loads(meta_json)
                    all_tenants.append({
                        "tenant_id": tenant_id,
                        "created_at": meta.get("created_at"),
                        "last_active": meta.get("last_active"),
                        "status": meta.get("status", "unknown")
                    })
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Corrupted metadata for tenant {tenant_id}")
            
            return all_tenants
        except Exception as e:
            logger.error(f"❌ Failed to list tenants: {e}")
            return []

# Inicializar el registro de tenants
tenant_registry = TenantRegistry(redis_client)

# ===============================
# MIDDLEWARE DE VERIFICACIÓN DE TENANT
# ===============================

def tenant_required(func):
    """Decorator para verificar tenant registrado antes de procesar requests"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not tenant_id:
            logger.error("❌ Missing X-Tenant-ID header")
            return create_error_response("Tenant ID is required", 400)
        
        if not tenant_registry.is_tenant_registered(tenant_id):
            logger.error(f"❌ Unregistered tenant access attempt: {tenant_id}")
            return create_error_response("Tenant not registered", 403)
        
        # Actualizar actividad del tenant
        tenant_registry.update_tenant_activity(tenant_id)
        
        return func(*args, **kwargs)
    return wrapper

# ===============================
# BOT ACTIVATION LOGIC
# ===============================

BOT_ACTIVE_STATUSES = ["open"]
BOT_INACTIVE_STATUSES = ["pending", "resolved", "snoozed"]

status_lock = threading.Lock()

def update_bot_status(tenant_id: str, conversation_id: str, conversation_status: str):
    """Update bot status for a specific conversation in Redis"""
    with status_lock:
        is_active = conversation_status in BOT_ACTIVE_STATUSES
        
        # Store in Redis with tenant namespace
        status_key = f"tenant_{tenant_id}:bot_status:{conversation_id}"
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

def should_bot_respond(tenant_id: str, conversation_id: str, conversation_status: str):
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

def is_message_already_processed(tenant_id: str, message_id: str, conversation_id: str):
    """Check if message has already been processed using Redis"""
    if not message_id:
        return False
    
    key = f"tenant_{tenant_id}:processed_message:{conversation_id}:{message_id}"
    
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
# REFACTORED Modern Conversation Manager - UNIFIED CHAT HISTORY
# ===============================

class ModernConversationManager:
    """
    REFACTORED: Conversation Manager moderno con métodos unificados de chat history
    y soporte multi-tenant
    """
    
    def __init__(self, redis_client, max_messages: int = 10):
        self.redis_client = redis_client
        self.max_messages = max_messages
        self.redis_prefix = "conversation:"
        self.conversations = {}
        self.message_histories = {}
        # No cargar conversaciones al inicio para multi-tenant
        
    def _get_conversation_key(self, tenant_id: str, user_id: str) -> str:
        """Generate standardized conversation key with tenant namespace"""
        return f"tenant_{tenant_id}:conversation:{user_id}"
    
    def _get_message_history_key(self, tenant_id: str, user_id: str) -> str:
        """Generate standardized message history key for Redis with tenant namespace"""
        return f"tenant_{tenant_id}:chat_history:{user_id}"
    
    def _create_user_id(self, contact_id: str) -> str:
        """Generate standardized user ID"""
        if not contact_id.startswith("chatwoot_contact_"):
            return f"chatwoot_contact_{contact_id}"
        return contact_id
    
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
        REFACTORED: Método interno para crear/obtener RedisChatMessageHistory
        Centraliza la lógica de creación de objetos de historia Redis
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")
        
        # Usar caché en memoria para evitar recrear objetos
        cache_key = f"{tenant_id}:{user_id}"
        if cache_key not in self.message_histories:
            try:
                redis_params = self._get_redis_connection_params()
                
                # Crear RedisChatMessageHistory con parámetros mejorados y namespace
                self.message_histories[cache_key] = RedisChatMessageHistory(
                    session_id=user_id,
                    url=redis_params["url"],
                    key_prefix=f"tenant_{tenant_id}:chat_history:",
                    ttl=redis_params["ttl"]
                )
                
                logger.info(f"✅ Created Redis message history for tenant {tenant_id} user {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Error creating Redis message history for tenant {tenant_id} user {user_id}: {e}")
                # Crear una historia en memoria como fallback
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self.message_histories[cache_key] = InMemoryChatMessageHistory()
                logger.warning(f"⚠️ Using in-memory fallback for tenant {tenant_id} user {user_id}")
            
            # Aplicar límite de mensajes (ventana deslizante)
            self._apply_message_window(tenant_id, user_id)
        
        return self.message_histories[cache_key]
    
    def get_chat_history(self, tenant_id: str, user_id: str, format_type: str = "dict") -> Any:
        """
        REFACTORED: Método unificado para obtener chat history en diferentes formatos
        con soporte multi-tenant
        
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
        if not user_id or not tenant_id:
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
            logger.error(f"Error getting chat history for tenant {tenant_id} user {user_id}: {e}")
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
        MEJORADO: Mejor manejo de errores
        """
        try:
            cache_key = f"{tenant_id}:{user_id}"
            history = self.message_histories[cache_key]
            messages = history.messages
            
            if len(messages) > self.max_messages:
                # Mantener solo los últimos max_messages
                messages_to_keep = messages[-self.max_messages:]
                
                # Limpiar el historial existente
                history.clear()
                
                # Agregar solo los mensajes que queremos mantener
                for message in messages_to_keep:
                    history.add_message(message)
                
                logger.info(f"✅ Tenant {tenant_id} - Applied message window for user {user_id}: kept {len(messages_to_keep)} messages")
        
        except Exception as e:
            logger.error(f"❌ Tenant {tenant_id} - Error applying message window for user {user_id}: {e}")
    
    def add_message(self, tenant_id: str, user_id: str, role: str, content: str) -> bool:
        """
        Add message with automatic window management
        MEJORADO: Mejor validación y manejo de errores
        """
        if not user_id or not content.strip() or not tenant_id:
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
            cache_key = f"{tenant_id}:{user_id}"
            if cache_key in self.message_histories:
                self._apply_message_window(tenant_id, user_id)
            
            # Update metadata
            self._update_conversation_metadata(tenant_id, user_id)
            
            logger.info(f"✅ Tenant {tenant_id} - Message added for user {user_id} (role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tenant {tenant_id} - Error adding message for user {user_id}: {e}")
            return False
    
    def _update_conversation_metadata(self, tenant_id: str, user_id: str):
        """Update conversation metadata in Redis con namespace de tenant"""
        try:
            conversation_key = self._get_conversation_key(tenant_id, user_id)
            metadata = {
                'last_updated': str(time.time()),
                'user_id': user_id,
                'tenant_id': tenant_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)  # 7 días TTL
            
        except Exception as e:
            logger.error(f"Tenant {tenant_id} - Error updating metadata for user {user_id}: {e}")
    
    def load_conversations_from_redis(self, tenant_id: str):
        """
        Load conversations from Redis with modern approach
        MEJORADO: Mejor manejo de errores y migración
        Ahora específico por tenant
        """
        try:
            # Buscar claves de conversación existentes para este tenant
            pattern = f"tenant_{tenant_id}:conversation:*"
            conversation_keys = self.redis_client.keys(pattern)
            pattern = f"tenant_{tenant_id}:chat_history:*"
            chat_history_keys = self.redis_client.keys(pattern)
            
            loaded_count = 0
            
            # Migrar datos existentes si es necesario
            for key in conversation_keys:
                try:
                    # Extraer user_id de la key
                    parts = key.split(':')
                    if len(parts) < 4:
                        continue
                    user_id = parts[3]
                    
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
                            logger.info(f"✅ Tenant {tenant_id} - Migrated conversation for user {user_id}")
                
                except Exception as e:
                    logger.warning(f"Tenant {tenant_id} - Failed to migrate conversation {key}: {e}")
                    continue
            
            # Contar conversaciones ya en nuevo formato
            loaded_count += len(chat_history_keys)
            
            logger.info(f"✅ Tenant {tenant_id} - Loaded {loaded_count} conversation contexts from Redis")
            
        except Exception as e:
            logger.error(f"❌ Tenant {tenant_id} - Error loading contexts from Redis: {e}")
    
    def get_message_count(self, tenant_id: str, user_id: str) -> int:
        """Get total message count for a user"""
        try:
            history = self.get_chat_history(tenant_id, user_id, format_type="langchain")
            return len(history.messages)
        except Exception as e:
            logger.error(f"Tenant {tenant_id} - Error getting message count for user {user_id}: {e}")
            return 0
    
    def clear_conversation(self, tenant_id: str, user_id: str) -> bool:
        """Clear conversation history for a user"""
        try:
            history = self.get_chat_history(tenant_id, user_id, format_type="langchain")
            history.clear()
            
            # Limpiar metadata
            conversation_key = self._get_conversation_key(tenant_id, user_id)
            self.redis_client.delete(conversation_key)
            
            # Limpiar caché
            cache_key = f"{tenant_id}:{user_id}"
            if cache_key in self.message_histories:
                del self.message_histories[cache_key]
            
            logger.info(f"✅ Tenant {tenant_id} - Cleared conversation for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tenant {tenant_id} - Error clearing conversation for user {user_id}: {e}")
            return False


##############################################################
document tracker
####################################################################

class MultiTenantDocumentChangeTracker:
    """
    Sistema multi-tenant para rastrear cambios en documentos y invalidar cache
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    def get_current_version(self, tenant_id: str) -> int:
        """Obtener versión actual del vectorstore para un tenant específico"""
        version_key = f"tenant_{tenant_id}:vectorstore_version"
        try:
            version = self.redis_client.get(version_key)
            return int(version) if version else 0
        except:
            return 0
    
    def increment_version(self, tenant_id: str):
        """Incrementar versión del vectorstore para un tenant específico"""
        version_key = f"tenant_{tenant_id}:vectorstore_version"
        try:
            self.redis_client.incr(version_key)
            logger.info(f"Tenant {tenant_id} - Vectorstore version incremented to {self.get_current_version(tenant_id)}")
        except Exception as e:
            logger.error(f"Tenant {tenant_id} - Error incrementing version: {e}")
    
    def register_document_change(self, tenant_id: str, doc_id: str, change_type: str):
        """
        Registrar cambio en documento para un tenant específico
        change_type: 'added', 'updated', 'deleted'
        """
        try:
            change_data = {
                'doc_id': doc_id,
                'change_type': change_type,
                'timestamp': datetime.utcnow().isoformat(),
                'tenant_id': tenant_id
            }
            
            # Registrar cambio con clave específica del tenant
            change_key = f"tenant_{tenant_id}:doc_change:{doc_id}:{int(time.time())}"
            self.redis_client.setex(change_key, 3600, json.dumps(change_data))  # 1 hour TTL
            
            # Incrementar versión global del tenant
            self.increment_version(tenant_id)
            
            logger.info(f"Tenant {tenant_id} - Document change registered: {doc_id} - {change_type}")
            
        except Exception as e:
            logger.error(f"Tenant {tenant_id} - Error registering document change: {e}")
    
    def should_invalidate_cache(self, tenant_id: str, last_version: int) -> bool:
        """Determinar si se debe invalidar cache para un tenant específico"""
        current_version = self.get_current_version(tenant_id)
        return current_version > last_version

# Instanciar el tracker multi-tenant
document_change_tracker = MultiTenantDocumentChangeTracker(redis_client)

# ===============================
# multiagentSystem - ACTUALIZADO PARA USAR CHAT HISTORY UNIFICADO Y MULTI-TENANT
# ===============================

class MultiTenantMultiAgentSystem:
    """
    Sistema multi-agente integrado con agente de schedule mejorado
    Ahora completamente multi-tenant con aislamiento de datos por empresa
    """
    
    def __init__(self, chat_model, get_vectorstore_func, conversation_manager):
        self.chat_model = chat_model
        self.get_vectorstore_func = get_vectorstore_func  # Función para obtener vectorstore por tenant
        self.conversation_manager = conversation_manager
        
        # URL del microservicio de schedule (configuración para local)
        self.schedule_service_url = os.getenv('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040')
        
        # Configuración para entorno local
        self.is_local_development = os.getenv('ENVIRONMENT', 'production') == 'local'
        
        # Timeout específico para conexiones locales
        self.selenium_timeout = 30 if self.is_local_development else 60
        
        # Cache del estado de Selenium con timestamp
        self.selenium_service_available = False
        self.selenium_status_last_check = 0
        self.selenium_status_cache_duration = 30  # 30 segundos de cache
        
        # Inicializar agentes especializados
        self.router_agent = self._create_router_agent()
        self.emergency_agent = self._create_emergency_agent()
        self.sales_agent = self._create_sales_agent()
        self.support_agent = self._create_support_agent()
        self.schedule_agent = self._create_enhanced_schedule_agent()
        self.availability_agent = self._create_availability_agent()
        
        # Crear orquestador principal
        self.orchestrator = self._create_orchestrator()
        
        # Inicializar conexión con microservicio local
        self._initialize_local_selenium_connection()
    
    def _get_tenant_retriever(self, tenant_id: str):
        """Obtener retriever específico para cada tenant"""
        tenant_vectorstore = self.get_vectorstore_func(tenant_id)
        return tenant_vectorstore.as_retriever(search_kwargs={"k": 3})
    
    def _verify_selenium_service(self, force_check: bool = False) -> bool:
        """
        Verificar disponibilidad del servicio Selenium local con cache inteligente
        Args:
            force_check: Si True, fuerza una nueva verificación ignorando el cache
        """
        import time
        
        current_time = time.time()
        
        # Si no es verificación forzada y el cache es válido, usar el valor cacheado
        if not force_check and (current_time - self.selenium_status_last_check) < self.selenium_status_cache_duration:
            return self.selenium_service_available
        
        # Realizar nueva verificación
        try:
            response = requests.get(
                f"{self.schedule_service_url}/health",
                timeout=3
            )
            
            if response.status_code == 200:
                self.selenium_service_available = True
                self.selenium_status_last_check = current_time
                return True
            else:
                self.selenium_service_available = False
                self.selenium_status_last_check = current_time
                return False
                
        except Exception as e:
            logger.warning(f"Selenium service verification failed: {e}")
            self.selenium_service_available = False
            self.selenium_status_last_check = current_time
            return False
    
    def _initialize_local_selenium_connection(self):
        """Inicializar y verificar conexión con microservicio local"""
        try:
            logger.info(f"Intentando conectar con microservicio de Selenium en: {self.schedule_service_url}")
            
            # Verificar disponibilidad del servicio (forzar verificación inicial)
            is_available = self._verify_selenium_service(force_check=True)
            
            if is_available:
                logger.info("✅ Conexión exitosa con microservicio de Selenium local")
            else:
                logger.warning("⚠️ Servicio de Selenium no disponible")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando conexión con Selenium: {e}")
            self.selenium_service_available = False
    
    def _create_router_agent(self):
        """
        Agente Router: Clasifica la intención del usuario
        """
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un clasificador de intenciones para el centro estético.

ANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:

1. **EMERGENCY** - Urgencias médicas:
   - Palabras clave: "dolor intenso", "sangrado", "emergencia", "reacción alérgica", "inflamación severa"
   - Síntomas post-tratamiento graves
   - Cualquier situación que requiera atención médica inmediata

2. **SALES** - Consultas comerciales:
   - Información sobre tratamientos
   - Precios y promociones
   - Comparación de procedimientos
   - Beneficios y resultados

3. **SCHEDULE** - Gestión de citas:
   - Agendar citas
   - Modificar citas existentes
   - Cancelar citas
   - Consultar disponibilidad
   - Ver citas programadas
   - Reagendar citas

4. **SUPPORT** - Soporte general:
   - Información general del centro
   - Consultas sobre procesos
   - Cualquier otra consulta

RESPONDE SOLO con el formato JSON:
{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación"
}}

Mensaje del usuario: {question}"""),
            ("human", "{question}")
        ])
        
        return router_prompt | self.chat_model | StrOutputParser()
    
    def _create_emergency_agent(self):
        """
        Agente de Emergencias: Maneja urgencias médicas
        """
        emergency_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres María, especialista en emergencias médicas del centro.

SITUACIÓN DETECTADA: Posible emergencia médica.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma
3. Indica que el caso será escalado de emergencia
4. Proporciona información de contacto directo si es necesario

TONO: Profesional, empático, tranquilizador pero urgente.

RESPUESTA MÁXIMA: 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia ahora mismo. 🚨"

Historial de conversación:
{chat_history}

Mensaje del usuario: {question}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        return emergency_prompt | self.chat_model | StrOutputParser()
    
    def _create_sales_agent(self):
        """
        Agente de Ventas: Especializado en información comercial
        """
        sales_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres María, asesora comercial especializada del centro.

OBJETIVO: Proporcionar información comercial precisa y persuasiva.

INFORMACIÓN DISPONIBLE:
{context}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del tratamiento solicitado
3. Beneficios principales (máximo 3)
4. Inversión (si disponible)
5. Llamada a la acción para agendar

TONO: Cálido, profesional, persuasivo.
EMOJIS: Máximo 2 por respuesta.
LONGITUD: Máximo 5 oraciones.

FINALIZA SIEMPRE con: "¿Te gustaría agendar tu cita? 📅"

Historial de conversación:
{chat_history}

Pregunta del usuario: {question}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_sales_context(inputs):
            """Obtener contexto RAG para ventas"""
            try:
                tenant_id = inputs.get("tenant_id")
                question = inputs.get("question", "")
                retriever = self._get_tenant_retriever(tenant_id)
                docs = retriever.invoke(question)
                
                if not docs:
                    return """Información básica del centro:
- Centro estético especializado
- Tratamientos de belleza y bienestar
- Atención personalizada
- Profesionales certificados
Para información específica de tratamientos, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving sales context: {e}")
                return "Información básica disponible. Te conectaré con un especialista para detalles específicos."
        
        return (
            {
                "context": get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "tenant_id": lambda x: x.get("tenant_id")  # Nuevo parámetro
            }
            | sales_prompt
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_support_agent(self):
        """
        Agente de Soporte: Consultas generales y escalación
        """
        support_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres María, especialista en soporte al cliente del centro.

OBJETIVO: Resolver consultas generales y facilitar navegación.

TIPOS DE CONSULTA:
- Información del centro (ubicación, horarios)
- Procesos y políticas
- Escalación a especialistas
- Consultas generales

INFORMACIÓN DISPONIBLE:
{context}

PROTOCOLO:
1. Respuesta directa a la consulta
2. Información adicional relevante
3. Opciones de seguimiento

TONO: Profesional, servicial, eficiente.
LONGITUD: Máximo 4 oraciones.

Si no puedes resolver completamente: "Te conectaré con un especialista para resolver tu consulta específica. 👩‍⚕️"

Historial de conversación:
{chat_history}

Consulta del usuario: {question}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_support_context(inputs):
            """Obtener contexto RAG para soporte"""
            try:
                tenant_id = inputs.get("tenant_id")
                question = inputs.get("question", "")
                retriever = self._get_tenant_retriever(tenant_id)
                docs = retriever.invoke(question)
                
                if not docs:
                    return """Información general del centro:
- Horarios de atención
- Información general del centro
- Consultas sobre procesos
- Información institucional
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving support context: {e}")
                return "Información general disponible. Te conectaré con un especialista para consultas específicas."
        
        return (
            {
                "context": get_support_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "tenant_id": lambda x: x.get("tenant_id")  # Nuevo parámetro
            }
            | support_prompt
            | self.chat_model
            | StrOutputParser()
        )

    def _create_availability_agent(self):
        """Agente que verifica disponibilidad MEJORADO con comunicación robusta"""
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un agente de disponibilidad del centro.
    
    ESTADO DEL SISTEMA:
    {selenium_status}
    
    PROTOCOLO:
    1. Verificar estado del servicio Selenium
    2. Extraer la fecha (DD-MM-YYYY) y el tratamiento del mensaje
    3. Consultar el RAG para obtener la duración del tratamiento (en minutos)
    4. Llamar al endpoint /check-availability con la fecha
    5. Filtrar los slots disponibles que puedan acomodar la duración
    6. Devolver los horarios en formato legible
    
    Ejemplo de respuesta:
    "Horarios disponibles para {fecha} (tratamiento de {duracion} min):
    - 09:00 - 10:00
    - 10:30 - 11:30
    - 14:00 - 15:00"
    
    Si no hay disponibilidad: "No hay horarios disponibles para {fecha} con duración de {duracion} minutos."
    Si hay error del sistema: "Error consultando disponibilidad. Te conectaré con un especialista."
    
    Mensaje del usuario: {question}"""),
            ("human", "{question}")
        ])
        
        def get_availability_selenium_status(inputs):
            """Obtener estado del sistema Selenium para availability (igual que schedule)"""
            # Verificar estado del servicio antes de cada consulta
            is_available = self._verify_selenium_service()
            
            if is_available:
                return f"✅ Sistema de disponibilidad ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de disponibilidad NO DISPONIBLE (Verificar conexión: {self.schedule_service_url})"
        
        def process_availability(inputs):
            """Procesar consulta de disponibilidad MEJORADA"""
            try:
                tenant_id = inputs.get("tenant_id")
                question = inputs.get("question", "")
                chat_history = inputs.get("chat_history", [])
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"=== AVAILABILITY AGENT - PROCESANDO ===")
                logger.info(f"Tenant: {tenant_id}, Pregunta: {question}")
                
                # 1. VERIFICAR SERVICIO DISPONIBLE PRIMERO
                if not self._verify_selenium_service():
                    logger.error("Servicio Selenium no disponible para availability agent")
                    return "Error consultando disponibilidad. Te conectaré con un especialista para verificar horarios. 👩‍⚕️"
                
                # Extract date from question and history
                date = self._extract_date_from_question(question, chat_history)
                treatment = self._extract_treatment_from_question(question)
                
                if not date:
                    return "Por favor especifica la fecha en formato DD-MM-YYYY para consultar disponibilidad."
                
                logger.info(f"Fecha extraída: {date}, Tratamiento: {treatment}")
                
                # Obtener duración del tratamiento desde RAG
                duration = self._get_treatment_duration(tenant_id, treatment)
                logger.info(f"Duración del tratamiento: {duration} minutos")
                
                # 2. LLAMAR ENDPOINT CON MÉTODO MEJORADO
                availability_data = self._call_check_availability(date)
                
                if not availability_data:
                    logger.warning("No se obtuvieron datos de disponibilidad")
                    return "Error consultando disponibilidad. Te conectaré con un especialista."
                
                if not availability_data.get("available_slots"):
                    logger.info("No hay slots disponibles para la fecha solicitada")
                    return f"No hay horarios disponibles para {date}."
                
                # Filtrar slots según duración
                filtered_slots = self._filter_slots_by_duration(
                    availability_data["available_slots"], 
                    duration
                )
                
                logger.info(f"Slots filtrados: {filtered_slots}")
                
                # Formatear respuesta
                response = self._format_slots_response(filtered_slots, date, duration)
                logger.info(f"=== AVAILABILITY AGENT - RESPUESTA GENERADA ===")
                return response
                
            except Exception as e:
                logger.error(f"Error en agente de disponibilidad: {e}")
                logger.exception("Stack trace completo:")
                return "Error consultando disponibilidad. Te conectaré con un especialista."
    
        return (
            {
                "selenium_status": get_availability_selenium_status,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "tenant_id": lambda x: x.get("tenant_id")  # Nuevo parámetro
            }
            | RunnableLambda(process_availability)
        )
    
    def _extract_date_from_question(self, question, chat_history=None):
        """Extract date from question or chat history"""
        import re
        
        # Check current question first
        date_str = self._find_date_in_text(question)
        if date_str:
            return date_str
        
        # Check chat history if provided
        if chat_history:
            history_text = " ".join([
                msg.content if hasattr(msg, 'content') else str(msg) 
                for msg in chat_history
            ])
            date_str = self._find_date_in_text(history_text)
            if date_str:
                return date_str
        
        return None
    
    def _find_date_in_text(self, text):
        """Helper to find date in text"""
        import re
        from datetime import datetime, timedelta
        
        # Check for DD-MM-YYYY format
        match = re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', text)
        if match:
            return match.group(0).replace('/', '-')
        
        # Check for relative dates
        text_lower = text.lower()
        today = datetime.now()
        
        if "hoy" in text_lower:
            return today.strftime("%d-%m-%Y")
        elif "mañana" in text_lower:
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime("%d-%m-%Y")
        elif "pasado mañana" in text_lower:
            day_after = today + timedelta(days=2)
            return day_after.strftime("%d-%m-%Y")
        
        return None
    
    def _extract_treatment_from_question(self, question):
        """Extraer tratamiento del mensaje"""
        question_lower = question.lower()
        
        # Diccionario de tratamientos conocidos
        treatments_keywords = {
            "limpieza facial": ["limpieza", "facial", "limpieza facial"],
            "masaje": ["masaje", "masajes", "relajante"],
            "microagujas": ["microagujas", "micro agujas", "microneedling"],
            "botox": ["botox", "toxina"],
            "rellenos": ["relleno", "rellenos", "ácido hialurónico"],
            "peeling": ["peeling", "exfoliación"],
            "radiofrecuencia": ["radiofrecuencia", "rf"],
            "depilación": ["depilación", "láser"]
        }
        
        for treatment, keywords in treatments_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return treatment
        
        return "tratamiento general"
    
    def _get_treatment_duration(self, tenant_id: str, treatment: str) -> int:
        """Obtener duración del tratamiento desde RAG o configuración por defecto"""
        try:
            # Consultar RAG para obtener duración específica
            retriever = self._get_tenant_retriever(tenant_id)
            docs = retriever.invoke(f"duración tiempo {treatment}")
            
            for doc in docs:
                content = doc.page_content.lower()
                if "duración" in content or "tiempo" in content:
                    # Buscar números seguidos de "minutos" o "min"
                    import re
                    duration_match = re.search(r'(\d+)\s*(?:minutos?|min)', content)
                    if duration_match:
                        return int(duration_match.group(1))
            
            # Duraciones por defecto según tipo de tratamiento
            default_durations = {
                "limpieza facial": 60,
                "masaje": 60,
                "microagujas": 90,
                "botox": 30,
                "rellenos": 45,
                "peeling": 45,
                "radiofrecuencia": 60,
                "depilación": 30,
                "tratamiento general": 60
            }
            
            return default_durations.get(treatment, 60)  # 60 min por defecto
            
        except Exception as e:
            logger.error(f"Error obteniendo duración del tratamiento: {e}")
            return 60  # Duración por defecto
    
    def _call_check_availability(self, date):
        """Llamar al endpoint de disponibilidad con la misma lógica que schedule_agent"""
        try:
            # 1. VERIFICAR ESTADO DEL SERVICIO PRIMERO (como schedule_agent)
            if not self._verify_selenium_service():
                logger.warning("Servicio Selenium no disponible para availability check")
                return None
            
            logger.info(f"Consultando disponibilidad en: {self.schedule_service_url}/check-availability para fecha: {date}")
            
            # 2. USAR LA MISMA CONFIGURACIÓN QUE SCHEDULE_AGENT
            response = requests.post(
                f"{self.schedule_service_url}/check-availability",
                json={"date": date},
                headers={"Content-Type": "application/json"},
                timeout=self.selenium_timeout  # Usar el mismo timeout que schedule_agent
            )
            
            logger.info(f"Respuesta de availability endpoint - Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Datos de disponibilidad obtenidos exitosamente: {result.get('success', False)}")
                return result.get("data", {})
            else:
                logger.warning(f"Endpoint de disponibilidad retornó código {response.status_code}")
                logger.warning(f"Respuesta: {response.text}")
                # Marcar servicio como no disponible si hay error
                self.selenium_service_available = False
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando con endpoint de disponibilidad ({self.selenium_timeout}s)")
            self.selenium_service_available = False
            return None
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"No se pudo conectar con endpoint de disponibilidad: {self.schedule_service_url}")
            logger.error(f"Error de conexión: {e}")
            logger.error("Verifica que el microservicio esté ejecutándose en tu máquina local")
            self.selenium_service_available = False
            return None
            
        except Exception as e:
            logger.error(f"Error llamando endpoint de disponibilidad: {e}")
            self.selenium_service_available = False
            return None
    
    def _filter_slots_by_duration(self, available_slots, required_duration):
        """Filtrar slots que pueden acomodar la duración requerida"""
        try:
            if not available_slots:
                return []
            
            # Convertir duración requerida a número de slots (asumiendo 30 min por slot)
            required_slots = max(1, required_duration // 30)
            
            # Extraer horarios y ordenarlos
            times = []
            for slot in available_slots:
                if isinstance(slot, dict) and "time" in slot:
                    times.append(slot["time"])
                elif isinstance(slot, str):
                    times.append(slot)
            
            times.sort()
            filtered = []
            
            # Para tratamientos de 30 min o menos, todos los slots son válidos
            if required_slots == 1:
                return [f"{time} - {self._add_minutes_to_time(time, required_duration)}" for time in times]
            
            # Para tratamientos más largos, buscar slots consecutivos
            for i in range(len(times) - required_slots + 1):
                consecutive_times = times[i:i + required_slots]
                if self._are_consecutive_times(consecutive_times):
                    start_time = consecutive_times[0]
                    end_time = self._add_minutes_to_time(start_time, required_duration)
                    filtered.append(f"{start_time} - {end_time}")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtrando slots: {e}")
            return []
    
    def _are_consecutive_times(self, times):
        """Verificar si los horarios son consecutivos (diferencia de 30 min)"""
        for i in range(len(times) - 1):
            current_minutes = self._time_to_minutes(times[i])
            next_minutes = self._time_to_minutes(times[i + 1])
            if next_minutes - current_minutes != 30:
                return False
        return True
    
    def _time_to_minutes(self, time_str):
        """Convertir hora a minutos desde medianoche"""
        try:
            # Manejar formato "HH:MM" o "H:MM"
            time_clean = time_str.strip()
            if ':' in time_clean:
                parts = time_clean.split(':')
                hours = int(parts[0])
                minutes = int(parts[1])
                return hours * 60 + minutes
            return 0
        except (ValueError, IndexError):
            return 0
    
    def _add_minutes_to_time(self, time_str, minutes_to_add):
        """Sumar minutos a una hora y retornar en formato HH:MM"""
        try:
            total_minutes = self._time_to_minutes(time_str) + minutes_to_add
            hours = (total_minutes // 60) % 24
            minutes = total_minutes % 60
            return f"{hours:02d}:{minutes:02d}"
        except:
            return time_str
    
    def _format_slots_response(self, slots, date, duration):
        """Formatear respuesta con horarios disponibles"""
        if not slots:
            return f"No hay horarios disponibles para {date} (tratamiento de {duration} min)."
        
        slots_text = "\n".join(f"- {slot}" for slot in slots)
        return f"Horarios disponibles para {date} (tratamiento de {duration} min):\n{slots_text}"

    def _call_local_schedule_microservice(self, question: str, user_id: str, chat_history: list) -> Dict[str, Any]:
        """Llamar al microservicio de schedule LOCAL"""
        try:
            logger.info(f"Llamando a microservicio local en: {self.schedule_service_url}")
            
            response = requests.post(
                f"{self.schedule_service_url}/schedule-request",
                json={
                    "message": question,
                    "user_id": user_id,
                    "chat_history": [
                        {
                            "content": msg.content if hasattr(msg, 'content') else str(msg),
                            "type": getattr(msg, 'type', 'user')
                        } for msg in chat_history
                    ]
                },
                timeout=self.selenium_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Si se agendó exitosamente, notificar al sistema principal
                if result.get('success') and result.get('appointment_data'):
                    self._notify_appointment_success(user_id, result.get('appointment_data'))
                
                logger.info(f"Respuesta exitosa del microservicio local: {result.get('success', False)}")
                return result
            else:
                logger.warning(f"Microservicio local retornó código {response.status_code}")
                # Marcar servicio como no disponible para evitar llamadas adicionales
                self.selenium_service_available = False
                return {"success": False, "message": "Servicio local no disponible"}
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando con microservicio local ({self.selenium_timeout}s)")
            self.selenium_service_available = False
            return {"success": False, "message": "Timeout del servicio local"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"No se pudo conectar con microservicio local: {self.schedule_service_url}")
            logger.error("Verifica que el microservicio esté ejecutándose en tu máquina local")
            self.selenium_service_available = False
            return {"success": False, "message": "Servicio local no disponible"}
        
        except Exception as e:
            logger.error(f"Error llamando microservicio local: {e}")
            self.selenium_service_available = False
            return {"success": False, "message": "Error del servicio local"}
            
    def _create_enhanced_schedule_agent(self):
        """Agente de Schedule mejorado con integración de disponibilidad"""
        schedule_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres María, especialista en gestión de citas del centro.
    
    OBJETIVO: Facilitar la gestión completa de citas y horarios usando herramientas avanzadas.
    
    INFORMACIÓN DISPONIBLE:
    {context}
    
    ESTADO DEL SISTEMA DE AGENDAMIENTO:
    {selenium_status}
    
    DISPONIBILIDAD CONSULTADA:
    {available_slots}
    
    FUNCIONES PRINCIPALES:
    - Agendar nuevas citas (con automatización completa via Selenium LOCAL)
    - Modificar citas existentes
    - Cancelar citas
    - Consultar disponibilidad
    - Verificar citas programadas
    - Reagendar citas
    
    PROCESO DE AGENDAMIENTO AUTOMATIZADO:
    1. SIEMPRE verificar disponibilidad PRIMERO
    2. Mostrar horarios disponibles al usuario
    3. Extraer información del paciente del contexto
    4. Validar datos requeridos
    5. Solo usar herramienta de Selenium LOCAL después de confirmar disponibilidad
    6. Confirmar resultado al cliente
    
    DATOS REQUERIDOS PARA AGENDAR:
    - Nombre completo del paciente
    - Número de cédula
    - Teléfono de contacto
    - Fecha deseada
    - Hora preferida (que esté disponible)
    - Fecha de nacimiento (opcional)
    - Género (opcional)
    
    REGLAS IMPORTANTES:
    - NUNCA agendar sin mostrar disponibilidad primero
    - Si no hay disponibilidad, sugerir fechas alternativas
    - Si el horario solicitado no está disponible, mostrar opciones cercanas
    - Confirmar todos los datos antes de proceder
    
    ESTRUCTURA DE RESPUESTA:
    1. Confirmación de la solicitud
    2. Verificación de disponibilidad (OBLIGATORIO)
    3. Información relevante o solicitud de datos faltantes
    4. Resultado de la acción o siguiente paso
    
    TONO: Profesional, eficiente, servicial.
    EMOJIS: Máximo 2 por respuesta.
    LONGITUD: Máximo 6 oraciones.
    
    Historial de conversación:
    {chat_history}
    
    Solicitud del usuario: {question}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_schedule_context(inputs):
            """Obtener contexto RAG para agenda"""
            try:
                tenant_id = inputs.get("tenant_id")
                question = inputs.get("question", "")
                retriever = self._get_tenant_retriever(tenant_id)
                docs = retriever.invoke(question)
                
                if not docs:
                    return """Información básica de agenda:
    - Horarios de atención: Lunes a Viernes 8:00 AM - 6:00 PM, Sábados 8:00 AM - 4:00 PM
    - Servicios agendables: Consultas médicas, Tratamientos estéticos, Procedimientos de belleza
    - Políticas de cancelación: 24 horas de anticipación
    - Reagendamiento disponible sin costo
    - Sistema de agendamiento automático con Selenium LOCAL disponible
    - Datos requeridos: Nombre, cédula, teléfono, fecha y hora deseada"""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving schedule context: {e}")
                return "Información básica de agenda disponible. Sistema de agendamiento automático disponible."
        
        def get_selenium_status(inputs):
            """Obtener estado del sistema Selenium local usando cache"""
            if self.selenium_service_available:
                return f"✅ Sistema de agendamiento automático ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return "⚠️ Sistema de agendamiento automático NO DISPONIBLE (Verificar conexión local)"
        
        def process_schedule_with_selenium(inputs):
            """Procesar solicitud de agenda con integración de disponibilidad MEJORADA"""
            try:
                tenant_id = inputs.get("tenant_id")
                question = inputs.get("question", "")
                user_id = inputs.get("user_id", "default_user")
                chat_history = inputs.get("chat_history", [])
                context = inputs.get("context", "")
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"Procesando solicitud de agenda: {question}")
                
                # PASO 1: SIEMPRE verificar disponibilidad si se menciona agendamiento
                available_slots = ""
                if self._contains_schedule_intent(question):
                    logger.info("Detectado intent de agendamiento - verificando disponibilidad")
                    try:
                        availability_response = self.availability_agent.invoke({
                            "question": question,
                            "tenant_id": tenant_id
                        })
                        available_slots = availability_response
                        logger.info(f"Disponibilidad obtenida: {available_slots}")
                    except Exception as e:
                        logger.error(f"Error verificando disponibilidad: {e}")
                        available_slots = "Error consultando disponibilidad. Verificaré manualmente."
                
                # Preparar inputs para el prompt
                base_inputs = {
                    "question": question,
                    "chat_history": chat_history,
                    "context": context,
                    "selenium_status": selenium_status,
                    "available_slots": available_slots
                }
                
                # PASO 2: Generar respuesta base con información de disponibilidad
                logger.info("Generando respuesta base con disponibilidad")
                base_response = (schedule_prompt | self.chat_model | StrOutputParser()).invoke(base_inputs)
                
                # PASO 3: Determinar si proceder con Selenium (solo después de verificar disponibilidad)
                should_proceed_selenium = (
                    self._contains_schedule_intent(question) and 
                    self._should_use_selenium(question, chat_history) and
                    self._has_available_slots_confirmation(available_slots) and
                    not self._is_just_availability_check(question)
                )
                
                logger.info(f"¿Proceder con Selenium? {should_proceed_selenium}")
                
                if should_proceed_selenium:
                    logger.info("Procediendo con agendamiento automático via Selenium")
                    selenium_result = self._call_local_schedule_microservice(question, user_id, chat_history)
                    
                    if selenium_result.get('success'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    elif selenium_result.get('requires_more_info'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    else:
                        return f"{available_slots}\n\n{base_response}\n\nNota: Te conectaré con un especialista para completar el agendamiento."
                
                return base_response
                
            except Exception as e:
                logger.error(f"Error en agendamiento: {e}")
                return "Error procesando tu solicitud. Conectando con especialista... 📋"
        
        return (
            {
                "context": get_schedule_context,
                "selenium_status": get_selenium_status,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "user_id": lambda x: x.get("user_id", "default_user"),
                "tenant_id": lambda x: x.get("tenant_id")  # Nuevo parámetro
            }
            | RunnableLambda(process_schedule_with_selenium)
        )
    
    def _contains_schedule_intent(self, question: str) -> bool:
        """Detectar si la pregunta contiene intención de agendamiento"""
        schedule_keywords = [
            "agendar", "reservar", "programar", "cita", "appointment",
            "agenda", "disponibilidad", "horario", "fecha", "hora",
            "procede", "proceder", "confirmar cita"
        ]
        return any(keyword in question.lower() for keyword in schedule_keywords)
    
    def _has_available_slots_confirmation(self, availability_response: str) -> bool:
        """Verificar si la respuesta de disponibilidad contiene slots válidos"""
        if not availability_response:
            return False
        
        availability_lower = availability_response.lower()
        
        # Buscar indicadores de que hay slots disponibles
        text_indicators = [
            "horarios disponibles",
            "disponible para"
        ]
        
        # Verificar indicadores de texto
        has_text_indicators = any(indicator in availability_lower for indicator in text_indicators)
        
        # Verificar indicadores de formato (listas y horarios)
        has_list_format = "- " in availability_response
        has_time_format = ":" in availability_response and "-" in availability_response
        
        # Verificar indicadores negativos
        negative_indicators = [
            "no hay horarios disponibles",
            "no hay disponibilidad", 
            "error consultando disponibilidad"
        ]
        
        has_negative = any(indicator in availability_lower for indicator in negative_indicators)
        
        # Combinar todas las verificaciones
        has_positive = has_text_indicators or has_list_format or has_time_format
        
        return has_positive and not has_negative
    
    def _is_just_availability_check(self, question: str) -> bool:
        """Determinar si solo se está consultando disponibilidad sin agendar"""
        availability_only_keywords = [
            "disponibilidad para", "horarios disponibles", "qué horarios",
            "cuándo hay", "hay disponibilidad", "ver horarios"
        ]
        
        schedule_confirmation_keywords = [
            "agendar", "reservar", "procede", "proceder", "confirmar",
            "quiero la cita", "agenda la cita"
        ]
        
        has_availability_check = any(keyword in question.lower() for keyword in availability_only_keywords)
        has_schedule_confirmation = any(keyword in question.lower() for keyword in schedule_confirmation_keywords)
        
        # Si solo pregunta por disponibilidad y no confirma agendamiento
        return has_availability_check and not has_schedule_confirmation
    
    def _log_schedule_decision_process(self, question: str, availability: str, will_use_selenium: bool):
        """Log detallado del proceso de decisión para agendamiento"""
        logger.info(f"=== PROCESO DE DECISIÓN DE AGENDAMIENTO ===")
        logger.info(f"Pregunta: {question}")
        logger.info(f"Disponibilidad obtenida: {bool(availability)}")
        logger.info(f"Slots disponibles: {'Sí' if self._has_available_slots_confirmation(availability) else 'No'}")
        logger.info(f"Usará Selenium: {will_use_selenium}")
        logger.info(f"Solo consulta disponibilidad: {self._is_just_availability_check(question)}")
        logger.info(f"=============================================")
    
    def _handle_selenium_unavailable(self) -> str:
        """Manejar cuando el servicio Selenium no está disponible"""
        return """Lo siento, el sistema de agendamiento automático no está disponible en este momento. 

Puedes:
1. Intentar nuevamente en unos minutos
2. Contactar directamente a nuestro equipo
3. Te conectaré con un especialista para agendar manualmente

¿Prefieres que te conecte con un especialista? 👩‍⚕️"""
    
    def _should_use_selenium(self, question: str, chat_history: list) -> bool:
        """Determinar si se debe usar el microservicio de Selenium"""
        question_lower = question.lower()
        
        # Palabras clave que indican necesidad de agendamiento
        schedule_keywords = [
            "agendar", "reservar", "programar", "cita", "appointment",
            "agenda", "disponibilidad", "horario", "fecha", "hora"
        ]
        
        # Verificar si la pregunta contiene palabras clave de agendamiento
        has_schedule_intent = any(keyword in question_lower for keyword in schedule_keywords)
        
        # Verificar si hay suficiente información en el historial
        has_patient_info = self._extract_patient_info_from_history(chat_history)
        
        return has_schedule_intent and (has_patient_info or self._has_complete_info_in_message(question))
    
    def _extract_patient_info_from_history(self, chat_history: list) -> bool:
        """Extraer información del paciente del historial"""
        # Buscar información básica en el historial
        history_text = " ".join([msg.content if hasattr(msg, 'content') else str(msg) for msg in chat_history])
        
        # Verificar si hay información básica disponible
        has_name = any(word in history_text.lower() for word in ["nombre", "llamo", "soy"])
        has_phone = any(char.isdigit() for char in history_text) and len([c for c in history_text if c.isdigit()]) >= 7
        has_date = any(word in history_text.lower() for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name and (has_phone or has_date)
    
    def _has_complete_info_in_message(self, message: str) -> bool:
        """Verificar si el mensaje tiene información completa"""
        message_lower = message.lower()
        
        # Verificar elementos básicos
        has_name_indicator = any(word in message_lower for word in ["nombre", "llamo", "soy"])
        has_phone_indicator = any(char.isdigit() for char in message) and len([c for c in message if c.isdigit()]) >= 7
        has_date_indicator = any(word in message_lower for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name_indicator and has_phone_indicator and has_date_indicator
    
    def _notify_appointment_success(self, user_id: str, appointment_data: Dict[str, Any]):
        """Notificar al sistema principal sobre cita exitosa"""
        try:
            # Enviar notificación al sistema principal (si es necesario)
            main_system_url = os.getenv('MAIN_SYSTEM_URL')
            if main_system_url:
                requests.post(
                    f"{main_system_url}/appointment-notification",
                    json={
                        "user_id": user_id,
                        "event": "appointment_scheduled",
                        "data": appointment_data
                    },
                    timeout=5
                )
                logger.info(f"Notificación enviada al sistema principal para usuario {user_id}")
        except Exception as e:
            logger.error(f"Error notificando cita exitosa: {e}")
    
    def _create_orchestrator(self):
        """
        Orquestador principal que coordina los agentes
        """
        def route_to_agent(inputs):
            """Enrutar a agente específico basado en clasificación"""
            try:
                # Obtener clasificación del router
                router_response = self.router_agent.invoke(inputs)
                
                # Parsear respuesta JSON
                try:
                    classification = json.loads(router_response)
                    intent = classification.get("intent", "SUPPORT")
                    confidence = classification.get("confidence", 0.5)
                    
                    logger.info(f"Intent classified: {intent} (confidence: {confidence})")
                    
                except json.JSONDecodeError:
                    # Fallback si no es JSON válido
                    intent = "SUPPORT"
                    confidence = 0.3
                    logger.warning("Router response was not valid JSON, defaulting to SUPPORT")
                
                # Agregar user_id a inputs para el agente de schedule
                inputs["user_id"] = inputs.get("user_id", "default_user")
                
                # Determinar agente basado en intención
                if intent == "EMERGENCY" or confidence > 0.8:
                    if intent == "EMERGENCY":
                        return self.emergency_agent.invoke(inputs)
                    elif intent == "SALES":
                        return self.sales_agent.invoke(inputs)
                    elif intent == "SCHEDULE":
                        return self.schedule_agent.invoke(inputs)
                    else:
                        return self.support_agent.invoke(inputs)
                else:
                    # Baja confianza, usar soporte por defecto
                    return self.support_agent.invoke(inputs)
                    
            except Exception as e:
                logger.error(f"Error in orchestrator: {e}")
                # Fallback a soporte en caso de error
                return self.support_agent.invoke(inputs)
        
        return RunnableLambda(route_to_agent)
    
    def get_response(self, tenant_id: str, question: str, user_id: str) -> Tuple[str, str]:
        """
        Método principal para obtener respuesta del sistema multi-agente
        Retorna: (respuesta, agente_utilizado)
        """
        if not question or not question.strip():
            return "Por favor, envía un mensaje específico para poder ayudarte. 😊", "support"
        
        if not user_id or not user_id.strip():
            return "Error interno: ID de usuario inválido.", "error"
        
        try:
            # Obtener historial de conversación
            chat_history = self.conversation_manager.get_chat_history(tenant_id, user_id, format_type="messages")
            
            # Preparar inputs con tenant_id
            inputs = {
                "tenant_id": tenant_id,  # Nuevo campo crítico
                "question": question.strip(),
                "chat_history": chat_history,
                "user_id": user_id
            }
            
            # Obtener respuesta del orquestador
            response = self.orchestrator.invoke(inputs)
            
            # Agregar mensaje del usuario al historial
            self.conversation_manager.add_message(tenant_id, user_id, "user", question)
            
            # Agregar respuesta del asistente al historial
            self.conversation_manager.add_message(tenant_id, user_id, "assistant", response)
            
            # Determinar qué agente se utilizó (para logging)
            agent_used = self._determine_agent_used(response)
            
            logger.info(f"Tenant {tenant_id} - Multi-agent response generated for user {user_id} using {agent_used}")
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"Error en sistema multi-agente (Tenant: {tenant_id}, User: {user_id})")
            return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", "error"
    
    def _determine_agent_used(self, response: str) -> str:
        """
        Determinar qué agente se utilizó basado en la respuesta
        """
        if "Escalando tu caso de emergencia" in response:
            return "emergency"
        elif "¿Te gustaría agendar tu cita?" in response:
            return "sales"
        elif "Procesando tu solicitud de agenda" in response:
            return "schedule"
        elif "Te conectaré con un especialista" in response:
            return "support"
        else:
            return "support"  # Por defecto
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verificar salud del sistema multi-agente y microservicio LOCAL
        """
        try:
            # Usar el estado cacheado para el health check, solo verificar si está marcado como no disponible
            if not self.selenium_service_available:
                # Intentar una verificación fresca solo si está marcado como no disponible
                service_healthy = self._verify_selenium_service()
            else:
                service_healthy = self.selenium_service_available
            
            return {
                "system_healthy": True,
                "agents_available": ["router", "emergency", "sales", "schedule", "support"],
                "schedule_service_healthy": service_healthy,
                "schedule_service_url": self.schedule_service_url,
                "schedule_service_type": "LOCAL",
                "system_type": "multi-agent_enhanced",
                "orchestrator_active": True,
                "rag_enabled": True,
                "selenium_integration": service_healthy,
                "environment": os.getenv('ENVIRONMENT', 'production')
            }
        except Exception as e:
            return {
                "system_healthy": True,
                "agents_available": ["router", "emergency", "sales", "schedule", "support"],
                "schedule_service_healthy": False,
                "schedule_service_url": self.schedule_service_url,
                "schedule_service_type": "LOCAL",
                "system_type": "multi-agent_enhanced",
                "orchestrator_active": True,
                "rag_enabled": True,
                "selenium_integration": False,
                "environment": os.getenv('ENVIRONMENT', 'production'),
                "error": str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del sistema multi-agente
        """
        return {
            "agents_available": ["router", "emergency", "sales", "schedule", "support"],
            "system_type": "multi-agent_enhanced",
            "orchestrator_active": True,
            "rag_enabled": True,
            "selenium_integration": getattr(self, 'selenium_service_available', False),
            "schedule_service_url": self.schedule_service_url,
            "schedule_service_type": "LOCAL",
            "environment": os.getenv('ENVIRONMENT', 'production')
        }
    
    def reconnect_selenium_service(self) -> bool:
        """
        Método para reconectar con el servicio Selenium local
        """
        logger.info("Intentando reconectar con servicio Selenium local...")
        self._initialize_local_selenium_connection()
        return self.selenium_service_available

# Función de utilidad para inicializar el sistema
def create_enhanced_multiagent_system(chat_model, vectorstore, conversation_manager):
    """
    Crear instancia del sistema multi-agente mejorado con conexión local
    """
    return MultiTenantMultiAgentSystem(chat_model, vectorstore, conversation_manager)

# ===============================
# modern_rag_system_with_multiagent
# ===============================
def create_modern_rag_system_with_multiagent(get_vectorstore_func, chat_model, embeddings, conversation_manager):
    """
    Crear sistema RAG moderno con arquitectura multi-agente
    Reemplaza la clase ModernBenovaRAGSystem manteniendo compatibilidad
    """
    class ModernRAGSystemMultiAgent:
        """
        Wrapper que mantiene compatibilidad con el sistema existente
        pero usa arquitectura multi-agente internamente
        """
        
        def __init__(self, get_vectorstore_func, chat_model, embeddings, conversation_manager):
            self.get_vectorstore_func = get_vectorstore_func
            self.chat_model = chat_model
            self.embeddings = embeddings
            self.conversation_manager = conversation_manager
            
            # Inicializar sistema multi-agente con función de vectorstore
            self.multi_agent_system = MultiTenantMultiAgentSystem(
                chat_model, 
                get_vectorstore_func, 
                conversation_manager
            )
        
        def get_response(self, tenant_id: str, question: str, user_id: str) -> Tuple[str, List]:
            """
            Método compatible con la interfaz existente
            """
            try:
                # Usar sistema multi-agente con tenant_id
                response, agent_used = self.multi_agent_system.get_response(tenant_id, question, user_id)
                
                # Obtener documentos usando vectorstore específico del tenant
                tenant_vectorstore = self.get_vectorstore_func(tenant_id)
                retriever = tenant_vectorstore.as_retriever(search_kwargs={"k": 3})
                docs = retriever.invoke(question)
                
                logger.info(f"Tenant {tenant_id} - Multi-agent response: {response[:100]}... (agent: {agent_used})")
                
                return response, docs
                
            except Exception as e:
                logger.error(f"Tenant {tenant_id} - Error in multi-agent RAG system: {e}")
                return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", []
        
        def add_documents(self, tenant_id: str, documents: List[str], metadatas: List[Dict] = None) -> int:
            """
            ACTUALIZADO: Agregar documentos usando sistema de chunking avanzado
            con soporte multi-tenant
            """
            if not documents:
                return 0
            
            try:
                all_texts = []
                all_metas = []
                
                for i, doc in enumerate(documents):
                    if doc and doc.strip():
                        # Usar sistema de chunking avanzado
                        texts, auto_metadatas = advanced_chunk_processing(doc)
                        
                        # Combinar metadata automática con metadata proporcionada
                        base_metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                        
                        for j, (text, auto_meta) in enumerate(zip(texts, auto_metadatas)):
                            if text.strip():
                                all_texts.append(text)
                                # Combinar metadatas
                                combined_meta = base_metadata.copy()
                                combined_meta.update(auto_meta)
                                combined_meta.update({
                                    "tenant_id": tenant_id,
                                    "chunk_index": j, 
                                    "doc_index": i
                                })
                                all_metas.append(combined_meta)
                
                # Agregar al vectorstore específico del tenant
                if all_texts:
                    tenant_vectorstore = self.get_vectorstore_func(tenant_id)
                    tenant_vectorstore.add_texts(all_texts, metadatas=all_metas)
                    logger.info(f"✅ Tenant {tenant_id} - Added {len(all_texts)} advanced chunks to vectorstore")
                
                return len(all_texts)
                
            except Exception as e:
                logger.error(f"❌ Tenant {tenant_id} - Error adding documents: {e}")
                return 0
        
        def search_documents(self, tenant_id: str, query: str, k: int = 3) -> List:
            """
            Búsqueda de documentos específica por tenant
            """
            try:
                tenant_vectorstore = self.get_vectorstore_func(tenant_id)
                retriever = tenant_vectorstore.as_retriever(search_kwargs={"k": k})
                return retriever.invoke(query)
            except Exception as e:
                logger.error(f"Tenant {tenant_id} - Error searching documents: {e}")
                return []
    
    return ModernRAGSystemMultiAgent(get_vectorstore_func, chat_model, embeddings, conversation_manager)

# ===============================
# Initialize Modern Components
# ===============================

# Crear instancias de los componentes modernos
try:
    modern_conversation_manager = ModernConversationManager(redis_client, MAX_CONTEXT_MESSAGES)
    
    modern_rag_system = create_modern_rag_system_with_multiagent(
        get_vectorstore, 
        chat_model, 
        embeddings, 
        modern_conversation_manager
    )
    logger.info("✅ Modern components initialized successfully")
except Exception as e:
    logger.error(f"❌ Error initializing modern components: {e}")
    sys.exit(1)

# ===============================
# Chat Response Handler
# ===============================

def get_modern_chat_response_multiagent(tenant_id: str, user_id: str, user_message: str) -> str:
    """
    Versión actualizada que usa sistema multi-agente
    Reemplaza la función get_modern_chat_response existente
    """
    if not tenant_id or not user_id or not user_id.strip():
        logger.error("Invalid tenant_id or user_id provided")
        return "Error interno: ID de tenant o usuario inválido."
    
    if not user_message or not user_message.strip():
        logger.error("Empty or invalid message content")
        return "Por favor, envía un mensaje con contenido para poder ayudarte. 😊"
    
    try:
        # Usar sistema multi-agente global
        response, agent_used = modern_rag_system.multi_agent_system.get_response(tenant_id, user_message, user_id)
        
        logger.info(f"Tenant {tenant_id} - Multi-agent response for user {user_id}: {response[:100]}... (agent: {agent_used})")
        
        return response
        
    except Exception as e:
        logger.exception(f"Tenant {tenant_id} - Error in multi-agent chat response for user {user_id}: {e}")
        return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo en unos momentos. 🔧"

# ===============================
# CHATWOOT API FUNCTIONS
# ===============================

def send_message_to_chatwoot(tenant_id: str, conversation_id: str, message_content: str):
    """Send message to Chatwoot using API"""
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{tenant_id}/conversations/{conversation_id}/messages"

    headers = {
        "api_access_token": CHATWOOT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "content": message_content,
        "message_type": "outgoing",
        "private": False
    }

    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            timeout=30,
            verify=True
        )

        logger.info(f"Tenant {tenant_id} - Chatwoot API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info(f"✅ Tenant {tenant_id} - Message sent to conversation {conversation_id}")
            return True
        else:
            logger.error(f"❌ Tenant {tenant_id} - Failed to send message: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Tenant {tenant_id} - Error sending message to Chatwoot: {e}")
        return False

def extract_contact_id(data):
    """
    Extract contact_id with unified priority system and validation
    Returns: (contact_id, method_used, is_valid)
    """
    conversation_data = data.get("conversation", {})
    
    # Priority order for contact extraction
    extraction_methods = [
        ("conversation.contact_inbox.contact_id", 
         lambda: conversation_data.get("contact_inbox", {}).get("contact_id")),
        ("conversation.meta.sender.id", 
         lambda: conversation_data.get("meta", {}).get("sender", {}).get("id")),
        ("root.sender.id", 
         lambda: data.get("sender", {}).get("id") if data.get("sender", {}).get("type") != "agent" else None)
    ]
    
    for method_name, extractor in extraction_methods:
        try:
            contact_id = extractor()
            if contact_id and str(contact_id).strip():
                # Validate contact_id format
                contact_id = str(contact_id).strip()
                if contact_id.isdigit() or contact_id.startswith("contact_"):
                    logger.info(f"✅ Contact ID extracted: {contact_id} (method: {method_name})")
                    return contact_id, method_name, True
        except Exception as e:
            logger.warning(f"Error in extraction method {method_name}: {e}")
            continue
    
    logger.error("❌ No valid contact_id found in webhook data")
    return None, "none", False
    
# ===============================
# WEBHOOK HANDLERS - CORREGIDOS
# ===============================

class WebhookError(Exception):
    """Custom exception for webhook errors"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def validate_webhook_data(data):
    """Validate webhook data structure"""
    if not data:
        raise WebhookError("No JSON data received", 400)
    
    event_type = data.get("event")
    if not event_type:
        raise WebhookError("Missing event type", 400)
    
    # Extract tenant_id from account_id in payload
    tenant_id = data.get("account", {}).get("id")
    if not tenant_id:
        raise WebhookError("Missing account ID (tenant_id)", 400)
    
    return event_type, tenant_id

def handle_conversation_updated(data, tenant_id):
    """Handle conversation_updated events to update bot status"""
    try:
        conversation_id = data.get("id")
        if not conversation_id:
            logger.error(f"❌ Tenant {tenant_id} - Could not extract conversation_id from conversation_updated event")
            return False
        
        conversation_status = data.get("status")
        if not conversation_status:
            logger.warning(f"⚠️ Tenant {tenant_id} - No status found in conversation_updated for {conversation_id}")
            return False
        
        logger.info(f"📋 Tenant {tenant_id} - Conversation {conversation_id} updated to status: {conversation_status}")
        update_bot_status(tenant_id, conversation_id, conversation_status)
        return True
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error handling conversation_updated: {e}")
        return False

def process_incoming_message(data, tenant_id):
    """Process incoming message with comprehensive validation and error handling"""
    try:
        # Validate message type
        message_type = data.get("message_type")
        if message_type != "incoming":
            logger.info(f"🤖 Tenant {tenant_id} - Ignoring message type: {message_type}")
            return {"status": "non_incoming_message", "ignored": True}

        # Extract and validate conversation data
        conversation_data = data.get("conversation", {})
        if not conversation_data:
            raise WebhookError("Missing conversation data", 400)

        conversation_id = conversation_data.get("id")
        conversation_status = conversation_data.get("status")
        
        if not conversation_id:
            raise WebhookError("Missing conversation ID", 400)

        # Validate conversation_id format
        if not str(conversation_id).strip() or not str(conversation_id).isdigit():
            raise WebhookError("Invalid conversation ID format", 400)

        # Check if bot should respond
        if not should_bot_respond(tenant_id, conversation_id, conversation_status):
            return {
                "status": "bot_inactive",
                "message": f"Bot is inactive for status: {conversation_status}",
                "active_only_for": BOT_ACTIVE_STATUSES
            }

        # Extract and validate message content
        content = data.get("content", "").strip()
        message_id = data.get("id")

        if not content:
            raise WebhookError("Missing message content", 400)

        # Validate message content
        if len(content) > 4000:  # Reasonable limit
            logger.warning(f"Tenant {tenant_id} - Message content too long: {len(content)} characters")
            content = content[:4000] + "..."

        # Check for duplicate processing
        if message_id and is_message_already_processed(tenant_id, message_id, conversation_id):
            return {"status": "already_processed", "ignored": True}

        # Extract contact information with improved validation
        contact_id, extraction_method, is_valid = extract_contact_id(data)
        if not is_valid or not contact_id:
            raise WebhookError("Could not extract valid contact_id from webhook data", 400)

        # Generate standardized user_id
        user_id = modern_conversation_manager._create_user_id(contact_id)

        logger.info(f"🔄 Tenant {tenant_id} - Processing message from conversation {conversation_id}")
        logger.info(f"👤 Tenant {tenant_id} - User: {user_id} (contact: {contact_id}, method: {extraction_method})")
        logger.info(f"💬 Tenant {tenant_id} - Message: {content[:100]}...")

        # Generate response with validation - CORREGIDO
        assistant_reply = get_modern_chat_response_multiagent(tenant_id, user_id, content)
        
        if not assistant_reply or not assistant_reply.strip():
            assistant_reply = "Disculpa, no pude procesar tu mensaje. ¿Podrías intentar de nuevo? 😊"
        
        logger.info(f"🤖 Tenant {tenant_id} - Assistant response: {assistant_reply[:100]}...")

        # Send response to Chatwoot
        success = send_message_to_chatwoot(tenant_id, conversation_id, assistant_reply)

        if not success:
            raise WebhookError("Failed to send response to Chatwoot", 500)

        logger.info(f"✅ Tenant {tenant_id} - Successfully processed message for conversation {conversation_id}")
        
        return {
            "status": "success",
            "message": "Response sent successfully",
            "tenant_id": tenant_id,
            "conversation_id": str(conversation_id),
            "user_id": user_id,
            "contact_id": contact_id,
            "contact_extraction_method": extraction_method,
            "conversation_status": conversation_status,
            "message_id": message_id,
            "bot_active": True,
            "model_used": MODEL_NAME,
            "embedding_model": EMBEDDING_MODEL,
            "vectorstore": "RedisVectorStore",
            "message_length": len(content),
            "response_length": len(assistant_reply)
        }

    
    except Exception as e:
        logger.exception(f"💥 Tenant {tenant_id} - Error procesando mensaje (ID: {message_id})")
        raise WebhookError("Internal server error", 500)
    except WebhookError:
        raise


@app.route("/webhook", methods=["POST"])
def chatwoot_webhook():
    try:
        data = request.get_json()
        event_type, tenant_id = validate_webhook_data(data)
        
        logger.info(f"🔔 WEBHOOK RECEIVED - Tenant: {tenant_id}, Event: {event_type}")

        # VERIFICAR TENANT REGISTRADO
        if not tenant_registry.is_tenant_registered(tenant_id):
            logger.error(f"❌ Unregistered tenant webhook: {tenant_id}")
            return jsonify({
                "status": "error",
                "message": "Tenant not registered"
            }), 403

        # Handle conversation updates
        if event_type == "conversation_updated":
            success = handle_conversation_updated(data, tenant_id)
            status_code = 200 if success else 400
            return jsonify({"status": "conversation_updated_processed", "success": success}), status_code

        # Handle only message_created events
        if event_type != "message_created":
            logger.info(f"⏭️ Tenant {tenant_id} - Ignoring event type: {event_type}")
            return jsonify({"status": "ignored_event_type", "event": event_type}), 200

        # Process incoming message
        result = process_incoming_message(data, tenant_id)
        
        if result.get("ignored"):
            return jsonify(result), 200
        
        return jsonify(result), 200

    except WebhookError as e:
        logger.error(f"Webhook error: {e.message} (Status: {e.status_code})")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), e.status_code
    except Exception as e:
        logger.exception("Error no manejado en webhook")
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

# ===============================
# DOCUMENT MANAGEMENT ENDPOINTS - CORREGIDOS
# ===============================

def create_success_response(data, status_code=200):
    """Create standardized success response"""
    return jsonify({"status": "success", **data}), status_code

def create_error_response(message, status_code=400):
    """Create standardized error response"""
    return jsonify({"status": "error", "message": message}), status_code

def validate_document_data(data):
    """Validate document data"""
    if not data or 'content' not in data:
        raise ValueError("Content is required")
    
    content = data['content'].strip()
    if not content:
        raise ValueError("Content cannot be empty")
    
    # Parsear metadata si es string
    metadata = data.get('metadata', {})
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON metadata")
    
    return content, metadata

@app.route("/documents", methods=["POST"])
@tenant_required
def add_document():
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        
        data = request.get_json()
        content, metadata = validate_document_data(data)
        
        # Generar doc_id
        doc_id = hashlib.md5(content.encode()).hexdigest()
        
        # Agregar doc_id a los metadatos
        metadata['doc_id'] = doc_id
        
        # CORRECCIÓN: Pasar tenant_id como primer parámetro
        num_chunks = modern_rag_system.add_documents(tenant_id, [content], [metadata])
        
        # Crear clave del documento con namespace de tenant
        doc_key = f"tenant_{tenant_id}:document:{doc_id}"
        
        # Guardar en Redis
        doc_data = {
            'content': content,
            'metadata': json.dumps(metadata),
            'created_at': str(datetime.utcnow().isoformat()),
            'chunk_count': str(num_chunks),
            'tenant_id': tenant_id
        }
        
        redis_client.hset(doc_key, mapping=doc_data)
        redis_client.expire(doc_key, 604800)  # 7 días TTL
        
        # Registrar cambio en documento
        document_change_tracker.register_document_change(tenant_id, doc_id, 'added')
        
        logger.info(f"✅ Tenant {tenant_id} - Document {doc_id} added with {num_chunks} chunks")
        
        return create_success_response({
            "tenant_id": tenant_id,
            "document_id": doc_id,
            "chunk_count": num_chunks,
            "message": f"Document added with {num_chunks} chunks"
        }, 201)
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        logger.exception("Error adding document")
        return create_error_response("Failed to add document", 500)

@app.route("/documents", methods=["GET"])
@tenant_required
def list_documents():
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        # Obtener claves de documentos con namespace de tenant
        doc_pattern = f"tenant_{tenant_id}:document:*"
        doc_keys = redis_client.keys(doc_pattern)
        
        # Obtener claves de vectores con namespace de tenant
        vector_pattern = f"tenant_{tenant_id}:documents:*"
        vector_keys = redis_client.keys(vector_pattern)
        
        # Organizar vectores por doc_id (solo usando metadata)
        vectors_by_doc = {}
        for vector_key in vector_keys:
            try:
                # Obtener SOLO el campo metadata (evita campos binarios)
                metadata_str = redis_client.hget(vector_key, 'metadata')
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    doc_id = metadata.get('doc_id')
                    if doc_id:
                        if doc_id not in vectors_by_doc:
                            vectors_by_doc[doc_id] = []
                        # Filtrar metadata para excluir campos problemáticos
                        safe_metadata = {k: v for k, v in metadata.items() if k != 'embedding'}
                        vectors_by_doc[doc_id].append({
                            "vector_key": vector_key,
                            "metadata": safe_metadata
                        })
            except Exception as e:
                logger.warning(f"Tenant {tenant_id} - Error parsing vector {vector_key}: {e}")
                continue
        
        # Aplicar paginación a documentos
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_doc_keys = doc_keys[start_idx:end_idx]
        
        # Construir respuesta
        documents = []
        for key in paginated_doc_keys:
            try:
                doc_data = redis_client.hgetall(key)
                if doc_data:
                    doc_id = key.split(':')[2] if len(key.split(':')) > 2 else key
                    content = doc_data.get('content', '')
                    metadata = json.loads(doc_data.get('metadata', '{}'))
                    
                    # Obtener vectores de este documento
                    doc_vectors = vectors_by_doc.get(doc_id, [])
                    
                    documents.append({
                        "tenant_id": tenant_id,
                        "id": doc_id,
                        "content": content[:200] + "..." if len(content) > 200 else content,
                        "metadata": metadata,
                        "created_at": doc_data.get('created_at'),
                        "chunk_count": int(doc_data.get('chunk_count', 0)),
                        "vectors": {
                            "count": len(doc_vectors),
                            "sample_vectors": doc_vectors[:3]  # Limitar a 3
                        }
                    })
            except Exception as e:
                logger.warning(f"Tenant {tenant_id} - Error parsing document {key}: {e}")
                continue
        
        return create_success_response({
            "tenant_id": tenant_id,
            "total_documents": len(doc_keys),
            "total_vectors": len(vector_keys),
            "page": page,
            "page_size": page_size,
            "documents": documents
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error listing documents: {e}")
        return create_error_response("Failed to list documents", 500)

@app.route("/documents/search", methods=["POST"])
@tenant_required
def search_documents():
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        data = request.get_json()
        if not data or 'query' not in data:
            return create_error_response("Query is required", 400)
        
        query = data['query'].strip()
        if not query:
            return create_error_response("Query cannot be empty", 400)
        
        k = min(data.get('k', MAX_RETRIEVED_DOCS), 20)  # Limit max results
        
        # Obtener vectorstore específico del tenant
        tenant_vectorstore = get_vectorstore(tenant_id)
        
        # CORREGIDO: Usar modern_rag_system
        docs = modern_rag_system.search_documents(tenant_id, query, k)
        
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": getattr(doc, 'metadata', {}),
                "score": getattr(doc, 'score', None)
            })
        
        return create_success_response({
            "tenant_id": tenant_id,
            "query": query,
            "results_count": len(results),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error searching documents: {e}")
        return create_error_response("Failed to search documents", 500)

@app.route("/documents/bulk", methods=["POST"])
@tenant_required
def bulk_add_documents():
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        
        data = request.get_json()
        if not data or 'documents' not in data:
            return create_error_response("Documents array is required", 400)

        documents = data['documents']
        if not isinstance(documents, list) or not documents:
            return create_error_response("Documents must be a non-empty array", 400)

        added_docs = 0
        total_chunks = 0
        errors = []
        added_doc_ids = []  # Rastrear IDs agregados

        for i, doc_data in enumerate(documents):
            try:
                content, metadata = validate_document_data(doc_data)

                # Generar doc_id
                doc_id = hashlib.md5(content.encode()).hexdigest()
                metadata['doc_id'] = doc_id

                # CORRECCIÓN: Pasar tenant_id como primer parámetro
                num_chunks = modern_rag_system.add_documents(tenant_id, [content], [metadata])
                total_chunks += num_chunks

                # Save to Redis
                doc_key = f"tenant_{tenant_id}:document:{doc_id}"
                doc_redis_data = {
                    'content': content,
                    'metadata': json.dumps(metadata),
                    'created_at': str(datetime.utcnow().isoformat()),
                    'chunk_count': str(num_chunks),
                    'tenant_id': tenant_id
                }

                redis_client.hset(doc_key, mapping=doc_redis_data)
                redis_client.expire(doc_key, 604800)  # 7 days TTL

                added_docs += 1
                added_doc_ids.append(doc_id)  # Guardar ID

            except Exception as e:
                errors.append(f"Document {i}: {str(e)}")
                continue

        # Registrar cambios en batch
        for doc_id in added_doc_ids:
            document_change_tracker.register_document_change(tenant_id, doc_id, 'added')

        response_data = {
            "tenant_id": tenant_id,
            "documents_added": added_docs,
            "total_chunks": total_chunks,
            "message": f"Added {added_docs} documents with {total_chunks} chunks"
        }

        if errors:
            response_data["errors"] = errors
            response_data["message"] += f". {len(errors)} documents failed."

        logger.info(f"✅ Tenant {tenant_id} - Bulk added {added_docs} documents with {total_chunks} chunks")

        return create_success_response(response_data, 201)

    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error bulk adding documents: {e}")
        return create_error_response("Failed to bulk add documents", 500)

@app.route("/documents/<doc_id>", methods=["DELETE"])
@tenant_required
def delete_document(doc_id):
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        doc_key = f"tenant_{tenant_id}:document:{doc_id}"
        if not redis_client.exists(doc_key):
            return create_error_response("Document not found", 404)
        
        index_name = f"tenant_{tenant_id}:documents"
        pattern = f"{index_name}:*"
        keys = redis_client.keys(pattern)
        
        vectors_to_delete = []
        for key in keys:
            # Verificar el campo 'doc_id' directamente en el hash
            doc_id_in_hash = redis_client.hget(key, 'doc_id')
            if doc_id_in_hash == doc_id:
                vectors_to_delete.append(key)
        
        # Eliminar vectores si se encontraron
        if vectors_to_delete:
            redis_client.delete(*vectors_to_delete)
            logger.info(f"Tenant {tenant_id} - Removed {len(vectors_to_delete)} vectors for doc {doc_id}")
        
        # Eliminar documento y registrar cambio
        redis_client.delete(doc_key)
        document_change_tracker.register_document_change(tenant_id, doc_id, 'deleted')
        
        return create_success_response({
            "tenant_id": tenant_id,
            "message": "Document deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error deleting document: {e}")
        return create_error_response("Failed to delete document", 500)

# ===============================
# CONVERSATION MANAGEMENT ENDPOINTS - CORREGIDOS
# ===============================

@app.route("/conversations", methods=["GET"])
@tenant_required
def list_conversations():
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        # Get conversation keys from Redis using modern pattern
        pattern = f"tenant_{tenant_id}:conversation:*"
        keys = redis_client.keys(pattern)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_keys = keys[start_idx:end_idx]
        
        conversations = []
        for key in paginated_keys:
            try:
                # Extract user_id from key
                parts = key.split(':')
                if len(parts) < 3:
                    continue
                user_id = parts[2]
                
                messages = modern_conversation_manager.get_chat_history(tenant_id, user_id)
                
                conversations.append({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "message_count": len(messages),
                    "last_updated": redis_client.hget(key, 'last_updated')
                })
            except Exception as e:
                logger.warning(f"Tenant {tenant_id} - Error parsing conversation {key}: {e}")
                continue
        
        return create_success_response({
            "tenant_id": tenant_id,
            "total_conversations": len(keys),
            "page": page,
            "page_size": page_size,
            "conversations": conversations
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error listing conversations: {e}")
        return create_error_response("Failed to list conversations", 500)

@app.route("/conversations/<user_id>", methods=["GET"])
@tenant_required
def get_conversation(user_id):
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        messages = modern_conversation_manager.get_chat_history(tenant_id, user_id)
        
        # Get last updated timestamp
        conversation_key = modern_conversation_manager._get_conversation_key(tenant_id, user_id)
        last_updated = redis_client.hget(conversation_key, 'last_updated') if conversation_key else None
        
        return create_success_response({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "message_count": len(messages),
            "messages": messages,
            "last_updated": last_updated
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error getting conversation: {e}")
        return create_error_response("Failed to get conversation", 500)

@app.route("/conversations/<user_id>", methods=["DELETE"])
@tenant_required
def delete_conversation(user_id):
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        modern_conversation_manager.clear_conversation(tenant_id, user_id)
        
        logger.info(f"✅ Tenant {tenant_id} - Conversation {user_id} deleted")
        
        return create_success_response({
            "tenant_id": tenant_id,
            "message": f"Conversation {user_id} deleted"
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error deleting conversation: {e}")
        return create_error_response("Failed to delete conversation", 500)

@app.route("/conversations/<user_id>/test", methods=["POST"])
@tenant_required
def test_conversation(user_id):
    try:
        # Get tenant_id from headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return create_error_response("Missing X-Tenant-ID header", 400)
            
        data = request.get_json()
        if not data or 'message' not in data:
            return create_error_response("Message is required", 400)
        
        message = data['message'].strip()
        if not message:
            return create_error_response("Message cannot be empty", 400)
        
        # Get bot response
        response = get_modern_chat_response_multiagent(tenant_id, user_id, message)
        
        return create_success_response({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_message": message,
            "bot_response": response,
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Tenant {tenant_id} - Error testing conversation: {e}")
        return create_error_response("Failed to test conversation", 500)

# ===============================
# SYSTEM STATUS ENDPOINTS - CORREGIDOS
# ===============================

def check_component_health():
    """Check health of system components"""
    components = {}
    
    # Check Redis
    try:
        redis_client.ping()
        components["redis"] = "connected"
    except Exception as e:
        components["redis"] = f"error: {str(e)}"
    
    # Check OpenAI
    try:
        embeddings.embed_query("test")
        components["openai"] = "connected"
    except Exception as e:
        components["openai"] = f"error: {str(e)}"
    
    # Check vectorstore
    try:
        # We can't check all tenants, so check a sample tenant
        sample_vectorstore = get_vectorstore("sample")
        sample_vectorstore.similarity_search("test", k=1)
        components["vectorstore"] = "connected"
    except Exception as e:
        components["vectorstore"] = f"error: {str(e)}"
    
    return components

@app.route("/health", methods=["GET"])
def health_check():
    try:
        components = check_component_health()
        
        # Get global stats
        conversation_keys = redis_client.keys("tenant_*:conversation:*")
        document_keys = redis_client.keys("tenant_*:document:*")
        bot_status_keys = redis_client.keys("tenant_*:bot_status:*")
        
        # Determine overall health
        healthy = all("error" not in str(status) for status in components.values())
        
        response_data = {
            "timestamp": time.time(),
            "components": {
                **components,
                "conversations": len(conversation_keys),
                "documents": len(document_keys),
                "bot_statuses": len(bot_status_keys)
            },
            "configuration": {
                "model": MODEL_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "max_context_messages": MAX_CONTEXT_MESSAGES,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "max_retrieved_docs": MAX_RETRIEVED_DOCS
            }
        }
        
        if healthy:
            return jsonify({"status": "healthy", **response_data}), 200
        else:
            return jsonify({"status": "unhealthy", **response_data}), 503
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 503

@app.route("/status", methods=["GET"])
def get_status():
    try:
        # Get tenant_id from headers (optional)
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # Get global stats
        conversation_keys = redis_client.keys("tenant_*:conversation:*")
        document_keys = redis_client.keys("tenant_*:document:*")
        bot_status_keys = redis_client.keys("tenant_*:bot_status:*")
        
        # Count active bots
        active_bots = 0
        for key in bot_status_keys:
            try:
                status_data = redis_client.hgetall(key)
                if status_data.get('active') == 'True':
                    active_bots += 1
            except Exception:
                continue
        
        # Get processed message count
        processed_message_count = len(redis_client.keys("tenant_*:processed_message:*"))
        
        # Build response
        response_data = {
            "timestamp": time.time(),
            "statistics": {
                "total_conversations": len(conversation_keys),
                "active_bots": active_bots,
                "total_bot_statuses": len(bot_status_keys),
                "processed_messages": processed_message_count,
                "total_documents": len(document_keys)
            },
            "environment": {
                "chatwoot_url": CHATWOOT_BASE_URL,
                "model": MODEL_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "redis_url": REDIS_URL
            }
        }
        
        # Add tenant-specific stats if tenant_id provided
        if tenant_id:
            # Count tenant-specific resources
            tenant_conversation_keys = redis_client.keys(f"tenant_{tenant_id}:conversation:*")
            tenant_document_keys = redis_client.keys(f"tenant_{tenant_id}:document:*")
            tenant_bot_status_keys = redis_client.keys(f"tenant_{tenant_id}:bot_status:*")
            
            tenant_active_bots = 0
            for key in tenant_bot_status_keys:
                try:
                    status_data = redis_client.hgetall(key)
                    if status_data.get('active') == 'True':
                        tenant_active_bots += 1
                except Exception:
                    continue
            
            tenant_processed_messages = len(redis_client.keys(f"tenant_{tenant_id}:processed_message:*"))
            
            response_data["tenant_statistics"] = {
                "tenant_id": tenant_id,
                "conversations": len(tenant_conversation_keys),
                "active_bots": tenant_active_bots,
                "bot_statuses": len(tenant_bot_status_keys),
                "processed_messages": tenant_processed_messages,
                "documents": len(tenant_document_keys)
            }
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return create_error_response("Failed to get status", 500)

@app.route("/reset", methods=["POST"])
def reset_system():
    try:
        # Get tenant_id from headers (optional)
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if tenant_id:
            # Reset only for specific tenant
            patterns = [
                f"tenant_{tenant_id}:processed_message:*",
                f"tenant_{tenant_id}:bot_status:*",
                f"tenant_{tenant_id}:conversation:*",
                f"tenant_{tenant_id}:document:*",
                f"tenant_{tenant_id}:chat_history:*"
            ]
            
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
            
            logger.info(f"✅ Tenant {tenant_id} - System reset completed")
            return create_success_response({
                "tenant_id": tenant_id,
                "message": "System reset completed for tenant",
                "timestamp": time.time()
            })
        else:
            # Reset entire system (all tenants)
            patterns = [
                "tenant_*:processed_message:*",
                "tenant_*:bot_status:*",
                "tenant_*:conversation:*",
                "tenant_*:document:*",
                "tenant_*:chat_history:*"
            ]
            
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
            
            logger.info("✅ Full system reset completed")
            return create_success_response({
                "message": "Full system reset completed",
                "timestamp": time.time()
            })
        
    except Exception as e:
        tenant_msg = f" for tenant {tenant_id}" if tenant_id else ""
        logger.error(f"System reset failed{tenant_msg}: {e}")
        return create_error_response("Failed to reset system", 500)


# ===============================
# ENDPOINTS DE ADMINISTRACIÓN DE TENANTS
# ===============================

@app.route("/tenants", methods=["POST"])
def register_tenant():
    try:
        data = request.get_json()
        if not data or 'tenant_id' not in data:
            return create_error_response("Tenant ID is required", 400)
        
        tenant_id = data['tenant_id']
        metadata = data.get('metadata', {})
        
        if tenant_registry.register_tenant(tenant_id, metadata):
            return create_success_response({
                "tenant_id": tenant_id,
                "message": "Tenant registered successfully"
            }, 201)
        
        return create_error_response("Failed to register tenant", 500)
    
    except Exception as e:
        logger.error(f"Tenant registration error: {e}")
        return create_error_response("Internal server error", 500)

@app.route("/tenants/<tenant_id>", methods=["DELETE"])
def unregister_tenant(tenant_id):
    if tenant_registry.unregister_tenant(tenant_id):
        return create_success_response({
            "tenant_id": tenant_id,
            "message": "Tenant unregistered"
        })
    
    return create_error_response("Tenant not found or already unregistered", 404)

@app.route("/tenants", methods=["GET"])
def list_tenants():
    try:
        tenants = tenant_registry.list_registered_tenants()
        return create_success_response({
            "count": len(tenants),
            "tenants": tenants
        })
    except Exception as e:
        logger.error(f"Tenant listing error: {e}")
        return create_error_response("Failed to list tenants", 500)
# ===============================
# STATIC FILE SERVING
# ===============================

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/')
def serve_frontend():
    return send_file('index.html')

# ===============================
# ERROR HANDLERS - MEJORADOS
# ===============================

@app.errorhandler(404)
def not_found(error):
    return create_error_response("Endpoint not found", 404)

@app.errorhandler(405)
def method_not_allowed(error):
    return create_error_response("Method not allowed", 405)

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return create_error_response("Internal server error", 500)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    return create_error_response("An unexpected error occurred", 500)

# ===============================
# STARTUP AND CLEANUP - ACTUALIZADOS
# ===============================

def startup_checks():
    """Startup verification checks"""
    try:
        logger.info("🚀 Starting Multi-Tenant ChatBot with Modern Architecture...")
        
        # Check Redis connection
        redis_client.ping()
        logger.info("✅ Redis connection verified")
        
        # Check OpenAI connection
        embeddings.embed_query("test startup")
        logger.info("✅ OpenAI connection verified")
        
        # Check vectorstore for a sample tenant
        sample_vectorstore = get_vectorstore("sample")
        sample_vectorstore.similarity_search("test", k=1)
        logger.info("✅ Vectorstore connection verified")
        
        # Initialize conversation manager
        logger.info("✅ Modern conversation manager initialized")
        
        # Display configuration
        logger.info("📋 Configuration:")
        logger.info(f"   Model: {MODEL_NAME}")
        logger.info(f"   Embedding Model: {EMBEDDING_MODEL}")
        logger.info(f"   Max Tokens: {MAX_TOKENS}")
        logger.info(f"   Temperature: {TEMPERATURE}")
        logger.info(f"   Max Context Messages: {MAX_CONTEXT_MESSAGES}")
        logger.info(f"   Similarity Threshold: {SIMILARITY_THRESHOLD}")
        logger.info(f"   Max Retrieved Docs: {MAX_RETRIEVED_DOCS}")
        logger.info(f"   Redis URL: {REDIS_URL}")
        
        logger.info("🎉 Multi-Tenant ChatBot startup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup check failed: {e}")
        raise

def cleanup():
    """Clean up resources on shutdown"""
    try:
        logger.info("🧹 Cleaning up resources...")
        # Cleanup is handled automatically by Redis TTLs
        logger.info("💾 All resources cleaned up")
        logger.info("👋 ChatBot shutdown completed")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")

# ===============================
# MAIN EXECUTION
# ===============================

if __name__ == "__main__":
    try:
        # Run startup checks
        startup_checks()
        
        # Setup cleanup handler
        import atexit
        atexit.register(cleanup)
        
        # Start server
        logger.info(f"🌐 Starting server on port {PORT}")
        logger.info(f"📡 Webhook endpoint: http://localhost:{PORT}/webhook")
        logger.info(f"🔍 Health check: http://localhost:{PORT}/health")
        logger.info(f"📊 Status: http://localhost:{PORT}/status")
        
        app.run(
            host="0.0.0.0",
            port=PORT,
            debug=os.getenv("ENVIRONMENT") != "production",
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
        cleanup()
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        cleanup()
        sys.exit(1)
