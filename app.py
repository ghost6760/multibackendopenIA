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
# COMPANY CONFIGURATION MANAGER
# ===============================

class CompanyConfigManager:
    """
    Gestor de configuraciones multi-empresa
    Permite configuraciones específicas por empresa manteniendo flexibilidad
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.config_prefix = "company_config:"
        self.default_config = self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto del sistema"""
        return {
            "model_name": os.getenv("MODEL_NAME", "gpt-4o-mini"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            "max_tokens": int(os.getenv("MAX_TOKENS", 1500)),
            "temperature": float(os.getenv("TEMPERATURE", 0.7)),
            "max_context_messages": int(os.getenv("MAX_CONTEXT_MESSAGES", 10)),
            "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", 0.7)),
            "max_retrieved_docs": int(os.getenv("MAX_RETRIEVED_DOCS", 3)),
            "vector_dim": 1536,  # Para text-embedding-3-small
            "bot_active_statuses": ["open"],
            "bot_inactive_statuses": ["pending", "resolved", "snoozed"]
        }
    
    def get_company_config(self, company_id: str) -> Dict[str, Any]:
        """
        Obtener configuración específica de una empresa
        Si no existe, retorna configuración por defecto
        """
        try:
            config_key = f"{self.config_prefix}{company_id}"
            stored_config = self.redis_client.hgetall(config_key)
            
            if stored_config:
                # Merge con configuración por defecto
                config = self.default_config.copy()
                
                # Convertir tipos de datos apropiadamente
                for key, value in stored_config.items():
                    if key in ["max_tokens", "max_context_messages", "max_retrieved_docs", "vector_dim"]:
                        config[key] = int(value)
                    elif key in ["temperature", "similarity_threshold"]:
                        config[key] = float(value)
                    elif key in ["bot_active_statuses", "bot_inactive_statuses"]:
                        config[key] = json.loads(value)
                    else:
                        config[key] = value
                
                return config
            else:
                # Guardar configuración por defecto para la empresa
                self.set_company_config(company_id, self.default_config)
                return self.default_config.copy()
                
        except Exception as e:
            logger.error(f"Error getting config for company {company_id}: {e}")
            return self.default_config.copy()
    
    def set_company_config(self, company_id: str, config: Dict[str, Any]) -> bool:
        """Establecer configuración específica para una empresa"""
        try:
            config_key = f"{self.config_prefix}{company_id}"
            
            # Preparar datos para Redis (convertir listas a JSON)
            redis_data = {}
            for key, value in config.items():
                if isinstance(value, (list, dict)):
                    redis_data[key] = json.dumps(value)
                else:
                    redis_data[key] = str(value)
            
            self.redis_client.hset(config_key, mapping=redis_data)
            self.redis_client.expire(config_key, 2592000)  # 30 días TTL
            
            logger.info(f"✅ Config updated for company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting config for company {company_id}: {e}")
            return False

# ===============================
# MULTI-COMPANY ENVIRONMENT SETUP
# ===============================

# Core environment variables (mantienen compatibilidad)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHATWOOT_API_KEY = os.getenv("CHATWOOT_API_KEY")
CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://chatwoot-production-0f1d.up.railway.app")
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "7")
PORT = int(os.getenv("PORT", 8080))

# Validación de variables críticas
if not OPENAI_API_KEY or not CHATWOOT_API_KEY:
    print("ERROR: Missing required environment variables")
    print("Required: OPENAI_API_KEY, CHATWOOT_API_KEY")
    sys.exit(1)

print("Environment loaded successfully")
print(f"Chatwoot URL: {CHATWOOT_BASE_URL}")
print(f"Account ID: {ACCOUNT_ID}")
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

# Initialize Company Config Manager
company_config_manager = CompanyConfigManager(redis_client)

# Logging configuration
log_level = logging.INFO if os.getenv("ENVIRONMENT") == "production" else logging.DEBUG
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ===============================
# MULTI-COMPANY LANGCHAIN COMPONENTS
# ===============================

class MultiCompanyLangChainManager:
    """
    Gestor de componentes LangChain por empresa
    Permite tener configuraciones y recursos separados por empresa
    """
    
    def __init__(self, redis_client, config_manager: CompanyConfigManager):
        self.redis_client = redis_client
        self.config_manager = config_manager
        self.company_components = {}  # Cache de componentes por empresa
        
    def _get_company_key(self, company_id: str) -> str:
        """Generar clave estándar para empresa"""
        return f"company:{company_id}"
    
    def get_embeddings(self, company_id: str) -> OpenAIEmbeddings:
        """Obtener embeddings específicos para una empresa"""
        company_key = self._get_company_key(company_id)
        
        if f"{company_key}:embeddings" not in self.company_components:
            config = self.config_manager.get_company_config(company_id)
            
            self.company_components[f"{company_key}:embeddings"] = OpenAIEmbeddings(
                model=config["embedding_model"],
                openai_api_key=OPENAI_API_KEY
            )
        
        return self.company_components[f"{company_key}:embeddings"]
    
    def get_chat_model(self, company_id: str) -> ChatOpenAI:
        """Obtener modelo de chat específico para una empresa"""
        company_key = self._get_company_key(company_id)
        
        if f"{company_key}:chat_model" not in self.company_components:
            config = self.config_manager.get_company_config(company_id)
            
            self.company_components[f"{company_key}:chat_model"] = ChatOpenAI(
                model_name=config["model_name"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                openai_api_key=OPENAI_API_KEY
            )
        
        return self.company_components[f"{company_key}:chat_model"]
    
    def get_vectorstore(self, company_id: str) -> RedisVectorStore:
        """Obtener vector store específico para una empresa"""
        company_key = self._get_company_key(company_id)
        
        if f"{company_key}:vectorstore" not in self.company_components:
            config = self.config_manager.get_company_config(company_id)
            embeddings = self.get_embeddings(company_id)
            
            self.company_components[f"{company_key}:vectorstore"] = RedisVectorStore(
                embeddings,
                redis_url=REDIS_URL,
                index_name=f"{company_id}_documents",  # Índice específico por empresa
                vector_dim=config["vector_dim"]
            )
        
        return self.company_components[f"{company_key}:vectorstore"]
    
    def clear_company_cache(self, company_id: str):
        """Limpiar cache de componentes para una empresa (útil al actualizar config)"""
        company_key = self._get_company_key(company_id)
        
        keys_to_remove = [key for key in self.company_components.keys() if key.startswith(company_key)]
        for key in keys_to_remove:
            del self.company_components[key]
        
        logger.info(f"✅ Cleared component cache for company {company_id}")

# Initialize Multi-Company LangChain Manager
langchain_manager = MultiCompanyLangChainManager(redis_client, company_config_manager)

def create_advanced_chunking_system(company_id: str):
    """
    Crear sistema de chunking avanzado con MarkdownHeaderTextSplitter
    Ahora recibe company_id para futuras personalizaciones
    """
    config = company_config_manager.get_company_config(company_id)
    
    # Headers para dividir el contenido (personalizable por empresa en el futuro)
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

def classify_chunk_metadata(chunk, chunk_text: str, company_id: str) -> Dict[str, Any]:
    """
    Clasificar automáticamente metadata de chunks
    Ahora incluye company_id en metadata
    """
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
    
    # Convertir booleano a string e incluir company_id
    metadata = {
        "company_id": company_id,  # NUEVO: Identificador de empresa
        "treatment": treatment,
        "type": metadata_type,
        "section": section,
        "chunk_length": len(chunk_text),
        "has_headers": str(bool(chunk.metadata)).lower(),  # "true" o "false"
        "processed_at": datetime.utcnow().isoformat()
    }
    
    return metadata

def advanced_chunk_processing(text: str, company_id: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Procesar texto usando sistema de chunking avanzado
    Ahora recibe company_id para procesamiento específico por empresa
    """
    if not text or not text.strip():
        return [], []
    
    try:
        # Crear splitters específicos para la empresa
        markdown_splitter, fallback_splitter = create_advanced_chunking_system(company_id)
        
        # Normalizar texto
        normalized_text = normalize_text(text)
        
        # Intentar chunking con headers primero
        try:
            chunks = markdown_splitter.split_text(normalized_text)
            
            # Si no se encontraron headers, usar fallback
            if not chunks or all(not chunk.metadata for chunk in chunks):
                logger.info(f"No headers found for company {company_id}, using fallback chunking")
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
            logger.warning(f"Error in markdown chunking for company {company_id}, using fallback: {e}")
            text_chunks = fallback_splitter.split_text(normalized_text)
            
            # Crear chunks simples para fallback
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                chunk_obj = type('Chunk', (), {
                    'page_content': chunk_text,
                    'metadata': {'section': f'chunk_{i}', 'treatment': 'general'}
                })()
                chunks.append(chunk_obj)
        
        # Procesar chunks y generar metadatas con company_id
        processed_texts = []
        metadatas = []
        
        for chunk in chunks:
            if chunk.page_content and chunk.page_content.strip():
                processed_texts.append(chunk.page_content)
                metadata = classify_chunk_metadata(chunk, chunk.page_content, company_id)
                metadatas.append(metadata)
        
        logger.info(f"Processed {len(processed_texts)} chunks for company {company_id} using advanced chunking")
        
        return processed_texts, metadatas
        
    except Exception as e:
        logger.error(f"Error in advanced chunk processing for company {company_id}: {e}")
        return [], []

# ===============================
# MULTI-COMPANY BOT ACTIVATION LOGIC
# ===============================

status_lock = threading.Lock()

def update_bot_status(conversation_id: str, conversation_status: str, company_id: str):
    """
    Update bot status for a specific conversation in Redis
    Ahora incluye separación por empresa
    """
    with status_lock:
        config = company_config_manager.get_company_config(company_id)
        is_active = conversation_status in config["bot_active_statuses"]
        
        # Store in Redis con namespace por empresa
        status_key = f"bot_status:{company_id}:{conversation_id}"
        status_data = {
            'active': str(is_active),
            'status': conversation_status,
            'company_id': company_id,
            'updated_at': str(time.time())
        }
        
        try:
            old_status = redis_client.hget(status_key, 'active')
            redis_client.hset(status_key, mapping=status_data)
            redis_client.expire(status_key, 86400)  # 24 hours TTL
            
            if old_status != str(is_active):
                status_text = "ACTIVO" if is_active else "INACTIVO"
                logger.info(f"🔄 Company {company_id} - Conversation {conversation_id}: Bot {status_text} (status: {conversation_status})")
                
        except Exception as e:
            logger.error(f"Error updating bot status in Redis for company {company_id}: {e}")

def should_bot_respond(conversation_id: str, conversation_status: str, company_id: str) -> bool:
    """
    Determine if bot should respond based on conversation status and company config
    Ahora considera configuración específica por empresa
    """
    update_bot_status(conversation_id, conversation_status, company_id)
    
    config = company_config_manager.get_company_config(company_id)
    is_active = conversation_status in config["bot_active_statuses"]
    
    if is_active:
        logger.info(f"✅ Company {company_id} - Bot WILL respond to conversation {conversation_id} (status: {conversation_status})")
    else:
        if conversation_status == "pending":
            logger.info(f"⏸️ Company {company_id} - Bot will NOT respond to conversation {conversation_id} (status: pending - INACTIVE)")
        else:
            logger.info(f"🚫 Company {company_id} - Bot will NOT respond to conversation {conversation_id} (status: {conversation_status})")
    
    return is_active

def is_message_already_processed(message_id: str, conversation_id: str, company_id: str) -> bool:
    """
    Check if message has already been processed using Redis
    Ahora incluye separación por empresa
    """
    if not message_id:
        return False
    
    key = f"processed_message:{company_id}:{conversation_id}:{message_id}"
    
    try:
        if redis_client.exists(key):
            logger.info(f"🔄 Company {company_id} - Message {message_id} already processed, skipping")
            return True
        
        redis_client.set(key, "1", ex=3600)  # 1 hour TTL
        logger.info(f"✅ Company {company_id} - Message {message_id} marked as processed")
        return False
        
    except Exception as e:
        logger.error(f"Error checking processed message in Redis for company {company_id}: {e}")
        return False

# ===============================
# MULTI-COMPANY CONVERSATION MANAGER
# ===============================

class MultiCompanyConversationManager:
    """
    REFACTORED: Conversation Manager moderno con soporte multi-empresa
    
    CAMBIOS PRINCIPALES:
    - Separación completa por empresa usando company_id
    - Configuraciones específicas por empresa
    - Namespacing en Redis por empresa
    - Compatibilidad mantenida con código existente
    """
    
    def __init__(self, redis_client, config_manager: CompanyConfigManager):
        self.redis_client = redis_client
        self.config_manager = config_manager
        self.redis_prefix = "conversation:"
        self.conversations = {}
        self.message_histories = {}
        self.load_conversations_from_redis()
        
    def _get_conversation_key(self, user_id: str, company_id: str) -> str:
        """Generate standardized conversation key with company separation"""
        return f"conversation:{company_id}:{user_id}"
    
    def _get_message_history_key(self, user_id: str, company_id: str) -> str:
        """Generate standardized message history key for Redis with company separation"""
        return f"chat_history:{company_id}:{user_id}"
    
    def _create_user_id(self, contact_id: str, company_id: str) -> str:
        """Generate standardized user ID with company context"""
        base_id = contact_id if contact_id.startswith("chatwoot_contact_") else f"chatwoot_contact_{contact_id}"
        return f"{company_id}:{base_id}"
    
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
    
    def _get_or_create_redis_history(self, user_id: str, company_id: str) -> BaseChatMessageHistory:
        """
        REFACTORED: Método interno para crear/obtener RedisChatMessageHistory con separación por empresa
        Centraliza la lógica de creación de objetos de historia Redis
        """
        if not user_id or not company_id:
            raise ValueError("user_id and company_id cannot be empty")
        
        cache_key = f"{company_id}:{user_id}"
        
        # Usar caché en memoria para evitar recrear objetos
        if cache_key not in self.message_histories:
            try:
                redis_params = self._get_redis_connection_params()
                config = self.config_manager.get_company_config(company_id)
                
                # Crear RedisChatMessageHistory con namespace por empresa
                self.message_histories[cache_key] = RedisChatMessageHistory(
                    session_id=f"{company_id}:{user_id}",  # Incluir company_id en session_id
                    url=redis_params["url"],
                    key_prefix=f"chat_history:{company_id}:",  # Prefix específico por empresa
                    ttl=redis_params["ttl"]
                )
                
                logger.info(f"✅ Created Redis message history for company {company_id}, user {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Error creating Redis message history for company {company_id}, user {user_id}: {e}")
                # Crear una historia en memoria como fallback
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self.message_histories[cache_key] = InMemoryChatMessageHistory()
                logger.warning(f"⚠️ Using in-memory fallback for company {company_id}, user {user_id}")
            
            # Aplicar límite de mensajes (ventana deslizante)
            self._apply_message_window(user_id, company_id)
        
        return self.message_histories[cache_key]
    
    def get_chat_history(self, user_id: str, company_id: str, format_type: str = "dict") -> Any:
        """
        REFACTORED: Método unificado para obtener chat history en diferentes formatos con separación por empresa
        
        Args:
            user_id: ID del usuario
            company_id: ID de la empresa
            format_type: Formato de salida
                - "dict": Lista de diccionarios con role/content (DEFAULT - compatibilidad)
                - "langchain": Objeto BaseChatMessageHistory nativo de LangChain
                - "messages": Lista de objetos BaseMessage de LangChain
        
        Returns:
            Chat history en el formato especificado
        """
        if not user_id or not company_id:
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
            # Obtener el objeto Redis history (centralizado) con separación por empresa
            redis_history = self._get_or_create_redis_history(user_id, company_id)
            
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
                return self.get_chat_history(user_id, company_id, "dict")
                
        except Exception as e:
            logger.error(f"Error getting chat history for company {company_id}, user {user_id}: {e}")
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
    
    def _apply_message_window(self, user_id: str, company_id: str):
        """
        Aplica ventana deslizante de mensajes para mantener solo los últimos N mensajes
        Ahora usa configuración específica por empresa
        """
        try:
            config = self.config_manager.get_company_config(company_id)
            max_messages = config["max_context_messages"]
            
            cache_key = f"{company_id}:{user_id}"
            history = self.message_histories[cache_key]
            messages = history.messages
            
            if len(messages) > max_messages:
                # Mantener solo los últimos max_messages
                messages_to_keep = messages[-max_messages:]
                
                # Limpiar el historial existente
                history.clear()
                
                # Agregar solo los mensajes que queremos mantener
                for message in messages_to_keep:
                    history.add_message(message)
                
                logger.info(f"✅ Applied message window for company {company_id}, user {user_id}: kept {len(messages_to_keep)} messages")
        
        except Exception as e:
            logger.error(f"❌ Error applying message window for company {company_id}, user {user_id}: {e}")
    
    def add_message(self, user_id: str, company_id: str, role: str, content: str) -> bool:
        """
        Add message with automatic window management and company separation
        MEJORADO: Separación por empresa y mejor validación
        """
        if not user_id or not company_id or not content.strip():
            logger.warning(f"Invalid parameters for message - user_id: {user_id}, company_id: {company_id}, content length: {len(content) if content else 0}")
            return False
        
        try:
            # Usar el método unificado para obtener history con separación por empresa
            history = self.get_chat_history(user_id, company_id, format_type="langchain")
            
            # Add message to history
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            else:
                logger.warning(f"Unknown role: {role}")
                return False
            
            # Update cache and apply window management
            cache_key = f"{company_id}:{user_id}"
            if cache_key in self.message_histories:
                self._apply_message_window(user_id, company_id)
            
            # Update metadata
            self._update_conversation_metadata(user_id, company_id)
            
            logger.info(f"✅ Message added for company {company_id}, user {user_id} (role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding message for company {company_id}, user {user_id}: {e}")
            return False
    
    def _update_conversation_metadata(self, user_id: str, company_id: str):
        """Update conversation metadata in Redis with company separation"""
        try:
            conversation_key = self._get_conversation_key(user_id, company_id)
            metadata = {
                'last_updated': str(time.time()),
                'user_id': user_id,
                'company_id': company_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)  # 7 días TTL
            
        except Exception as e:
            logger.error(f"Error updating metadata for company {company_id}, user {user_id}: {e}")
    
    def load_conversations_from_redis(self):
        """
        Load conversations from Redis with modern approach and multi-company support
        MEJORADO: Mejor manejo de errores y migración multi-empresa
        """
        try:
            # Buscar claves de conversación existentes (formato legacy y nuevo)
            legacy_conversation_keys = self.redis_client.keys("conversation:*")
            legacy_chat_history_keys = self.redis_client.keys("chat_history:*")
            
            # Buscar claves con formato multi-empresa
            company_conversation_keys = self.redis_client.keys("conversation:*:*")
            company_chat_history_keys = self.redis_client.keys("chat_history:*:*")
            
            loaded_count = 0
            
            # Migrar datos legacy (sin company_id) - asignar a empresa por defecto
            default_company_id = "benova"  # Empresa por defecto para migración
            
            for key in legacy_conversation_keys:
                try:
                    # Evitar procesar claves que ya tienen formato multi-empresa
                    if key.count(':') > 1:
                        continue
                        
                    user_id = key.split(':', 1)[1]
                    context_data = self.redis_client.hgetall(key)
                    
                    if context_data and 'messages' in context_data:
                        # Migrar mensajes antiguos al nuevo formato multi-empresa
                        old_messages = json.loads(context_data['messages'])
                        history = self.get_chat_history(user_id, default_company_id, format_type="langchain")
                        
                        # Verificar si ya migró
                        if len(history.messages) == 0 and old_messages:
                            for msg in old_messages:
                                if msg.get('role') == 'user':
                                    history.add_user_message(msg['content'])
                                elif msg.get('role') == 'assistant':
                                    history.add_ai_message(msg['content'])
                            
                            self._apply_message_window(user_id, default_company_id)
                            loaded_count += 1
                            logger.info(f"✅ Migrated legacy conversation for user {user_id} to company {default_company_id}")
                
                except Exception as e:
                    logger.warning(f"Failed to migrate legacy conversation {key}: {e}")
                    continue
            
            # Contar conversaciones ya en formato multi-empresa
            for key in company_chat_history_keys:
                try:
                    parts = key.split(':')
                    if len(parts) >= 3:
                        loaded_count += 1
                except Exception:
                    continue
            
            logger.info(f"✅ Loaded {loaded_count} conversation contexts from Redis (including legacy migration)")
            
        except Exception as e:
            logger.error(f"❌ Error loading contexts from Redis: {e}")
    
    def get_message_count(self, user_id: str, company_id: str) -> int:
        """Get total message count for a user in specific company"""
        try:
            history = self.get_chat_history(user_id, company_id, format_type="langchain")
            return len(history.messages)
        except Exception as e:
            logger.error(f"Error getting message count for company {company_id}, user {user_id}: {e}")
            return 0
    
    def clear_conversation(self, user_id: str, company_id: str) -> bool:
        """Clear conversation history for a user in specific company"""
        try:
            history = self.get_chat_history(user_id, company_id, format_type="langchain")
            history.clear()
            
            # Limpiar metadata
            conversation_key = self._get_conversation_key(user_id, company_id)
            self.redis_client.delete(conversation_key)
            
            # Limpiar caché
            cache_key = f"{company_id}:{user_id}"
            if cache_key in self.message_histories:
                del self.message_histories[cache_key]
            
            logger.info(f"✅ Cleared conversation for company {company_id}, user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing conversation for company {company_id}, user {user_id}: {e}")
            return False
    
    def get_company_conversations(self, company_id: str) -> List[Dict[str, Any]]:
        """
        NUEVO: Obtener todas las conversaciones de una empresa específica
        Útil para analytics y gestión por empresa
        """
        try:
            pattern = f"conversation:{company_id}:*"
            conversation_keys = self.redis_client.keys(pattern)
            
            conversations = []
            for key in conversation_keys:
                try:
                    metadata = self.redis_client.hgetall(key)
                    if metadata:
                        user_id = key.split(':', 2)[2]  # Extraer user_id
                        message_count = self.get_message_count(user_id, company_id)
                        
                        conversations.append({
                            'user_id': user_id,
                            'company_id': company_id,
                            'message_count': message_count,
                            'last_updated': metadata.get('last_updated', '0'),
                            'updated_at': metadata.get('updated_at', '')
                        })
                except Exception as e:
                    logger.warning(f"Error processing conversation key {key}: {e}")
                    continue
            
            logger.info(f"✅ Retrieved {len(conversations)} conversations for company {company_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error getting conversations for company {company_id}: {e}")
            return []
    
    def get_all_companies(self) -> List[str]:
        """
        NUEVO: Obtener lista de todas las empresas que tienen conversaciones
        Útil para administración multi-empresa
        """
        try:
            # Buscar todas las claves de conversación
            conversation_keys = self.redis_client.keys("conversation:*:*")
            chat_history_keys = self.redis_client.keys("chat_history:*:*")
            
            companies = set()
            
            # Extraer company_id de conversation keys
            for key in conversation_keys:
                try:
                    parts = key.split(':')
                    if len(parts) >= 3:
                        company_id = parts[1]
                        companies.add(company_id)
                except Exception:
                    continue
            
            # Extraer company_id de chat_history keys
            for key in chat_history_keys:
                try:
                    parts = key.split(':')
                    if len(parts) >= 3:
                        company_id = parts[1]
                        companies.add(company_id)
                except Exception:
                    continue
            
            companies_list = sorted(list(companies))
            logger.info(f"✅ Found {len(companies_list)} companies: {companies_list}")
            return companies_list
            
        except Exception as e:
            logger.error(f"❌ Error getting companies list: {e}")
            return []

# ===============================
# UTILITY FUNCTIONS FOR MULTI-COMPANY SUPPORT
# ===============================

def extract_company_id_from_request(request_data: Dict[str, Any]) -> str:
    """
    NUEVO: Extraer company_id del request
    Prioriza diferentes fuentes: header, query param, body, fallback
    """
    try:
        # Prioridad 1: Header personalizado
        if hasattr(request, 'headers') and 'X-Company-ID' in request.headers:
            return request.headers['X-Company-ID']
        
        # Prioridad 2: Query parameter
        if hasattr(request, 'args') and 'company_id' in request.args:
            return request.args.get('company_id')
        
        # Prioridad 3: En el body del request
        if isinstance(request_data, dict):
            if 'company_id' in request_data:
                return request_data['company_id']
            
            # Buscar en nested objects (ej: conversation.company_id)
            if 'conversation' in request_data and isinstance(request_data['conversation'], dict):
                if 'company_id' in request_data['conversation']:
                    return request_data['conversation']['company_id']
        
        # Prioridad 4: Extraer de account_id o inbox_id (mapeo específico)
        if isinstance(request_data, dict):
            # Mapeo específico account_id -> company_id (personalizable)
            account_id_mapping = {
                "7": "benova",  # Account ID 7 = Benova (compatibilidad legacy)
                # Agregar más mapeos según necesidades
            }
            
            account_id = request_data.get('account', {}).get('id') if 'account' in request_data else None
            if account_id and str(account_id) in account_id_mapping:
                return account_id_mapping[str(account_id)]
        
        # Fallback: empresa por defecto
        default_company = os.getenv("DEFAULT_COMPANY_ID", "benova")
        logger.warning(f"No company_id found in request, using default: {default_company}")
        return default_company
        
    except Exception as e:
        logger.error(f"Error extracting company_id from request: {e}")
        return os.getenv("DEFAULT_COMPANY_ID", "benova")

def validate_company_access(company_id: str, api_key: str = None) -> bool:
    """
    NUEVO: Validar acceso a una empresa específica
    Permite implementar autorización por empresa en el futuro
    """
    try:
        # Por ahora, permitir acceso a todas las empresas
        # En el futuro, implementar lógica de autorización basada en API keys, tokens, etc.
        
        if not company_id or not company_id.strip():
            return False
        
        # Validar formato de company_id (alfanumérico, guiones, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+, company_id):
            logger.warning(f"Invalid company_id format: {company_id}")
            return False
        
        # Longitud razonable
        if len(company_id) > 50:
            logger.warning(f"Company_id too long: {company_id}")
            return False
        
        logger.info(f"✅ Access validated for company: {company_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating company access for {company_id}: {e}")
        return False

# ===============================
# INITIALIZE MULTI-COMPANY COMPONENTS
# ===============================

# Initialize Multi-Company Conversation Manager
conversation_manager = MultiCompanyConversationManager(redis_client, company_config_manager)

# ===============================
# BACKWARDS COMPATIBILITY LAYER
# ===============================

def get_legacy_config_value(key: str, default_value: Any, company_id: str = "benova") -> Any:
    """
    COMPATIBILIDAD: Obtener valores de configuración manteniendo compatibilidad con código legacy
    """
    config = company_config_manager.get_company_config(company_id)
    
    # Mapeo de nombres legacy a nuevos nombres
    legacy_mapping = {
        "MODEL_NAME": "model_name",
        "EMBEDDING_MODEL": "embedding_model", 
        "MAX_TOKENS": "max_tokens",
        "TEMPERATURE": "temperature",
        "MAX_CONTEXT_MESSAGES": "max_context_messages",
        "SIMILARITY_THRESHOLD": "similarity_threshold",
        "MAX_RETRIEVED_DOCS": "max_retrieved_docs",
        "BOT_ACTIVE_STATUSES": "bot_active_statuses",
        "BOT_INACTIVE_STATUSES": "bot_inactive_statuses"
    }
    
    config_key = legacy_mapping.get(key, key.lower())
    return config.get(config_key, default_value)

# Mantener variables globales para compatibilidad (usando empresa por defecto)
DEFAULT_COMPANY_ID = os.getenv("DEFAULT_COMPANY_ID", "benova")

# Variables de compatibilidad que apuntan a configuración de empresa por defecto
MODEL_NAME = get_legacy_config_value("MODEL_NAME", "gpt-4o-mini", DEFAULT_COMPANY_ID)
EMBEDDING_MODEL = get_legacy_config_value("EMBEDDING_MODEL", "text-embedding-3-small", DEFAULT_COMPANY_ID)
MAX_TOKENS = get_legacy_config_value("MAX_TOKENS", 1500, DEFAULT_COMPANY_ID)
TEMPERATURE = get_legacy_config_value("TEMPERATURE", 0.7, DEFAULT_COMPANY_ID)
MAX_CONTEXT_MESSAGES = get_legacy_config_value("MAX_CONTEXT_MESSAGES", 10, DEFAULT_COMPANY_ID)
SIMILARITY_THRESHOLD = get_legacy_config_value("SIMILARITY_THRESHOLD", 0.7, DEFAULT_COMPANY_ID)
MAX_RETRIEVED_DOCS = get_legacy_config_value("MAX_RETRIEVED_DOCS", 3, DEFAULT_COMPANY_ID)

# Componentes legacy que apuntan a empresa por defecto
embeddings = langchain_manager.get_embeddings(DEFAULT_COMPANY_ID)
chat_model = langchain_manager.get_chat_model(DEFAULT_COMPANY_ID)
vectorstore = langchain_manager.get_vectorstore(DEFAULT_COMPANY_ID)

# Mostrar configuración cargada
print(f"Multi-Company System Initialized")
print(f"Default Company: {DEFAULT_COMPANY_ID}")
print(f"Model: {MODEL_NAME}")
print(f"Embedding Model: {EMBEDDING_MODEL}")
print(f"Companies available: {conversation_manager.get_all_companies()}")

logger.info("🏢 Multi-Company Backend System Initialized Successfully")


# ===============================
# NUEVO: Sistema de Invalidación de Cache
# UBICACIÓN: Agregar después de la clase ModernConversationManager
# ===============================

# ===============================
# MULTI-COMPANY: Sistema de Invalidación de Cache
# UBICACIÓN: Agregar después de la clase MultiCompanyConversationManager
# ===============================

class MultiCompanyDocumentChangeTracker:
    """
    Sistema para rastrear cambios en documentos y invalidar cache
    REFACTORIZADO: Soporte multi-empresa con separación por company_id
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.version_key_prefix = "vectorstore_version"  # Prefijo para versiones por empresa
        self.doc_hash_key_prefix = "document_hashes"     # Prefijo para hashes por empresa
        self.global_version_key = "global_vectorstore_version"  # Versión global del sistema
    
    def _get_company_version_key(self, company_id: str) -> str:
        """Generar clave de versión específica para empresa"""
        return f"{self.version_key_prefix}:{company_id}"
    
    def _get_company_doc_hash_key(self, company_id: str) -> str:
        """Generar clave de hashes de documentos específica para empresa"""
        return f"{self.doc_hash_key_prefix}:{company_id}"
    
    def get_current_version(self, company_id: str) -> int:
        """Obtener versión actual del vectorstore para empresa específica"""
        try:
            if not company_id:
                logger.warning("company_id is required for get_current_version")
                return 0
                
            version_key = self._get_company_version_key(company_id)
            version = self.redis_client.get(version_key)
            return int(version) if version else 0
        except Exception as e:
            logger.error(f"Error getting version for company {company_id}: {e}")
            return 0
    
    def increment_version(self, company_id: str):
        """Incrementar versión del vectorstore para empresa específica"""
        try:
            if not company_id:
                logger.warning("company_id is required for increment_version")
                return
                
            version_key = self._get_company_version_key(company_id)
            new_version = self.redis_client.incr(version_key)
            
            # También incrementar versión global del sistema
            global_version = self.redis_client.incr(self.global_version_key)
            
            logger.info(f"Vectorstore version incremented for company {company_id} to {new_version} (global: {global_version})")
        except Exception as e:
            logger.error(f"Error incrementing version for company {company_id}: {e}")
    
    def register_document_change(self, doc_id: str, change_type: str, company_id: str):
        """
        Registrar cambio en documento para empresa específica
        change_type: 'added', 'updated', 'deleted'
        REFACTORIZADO: Incluye company_id para separación por empresa
        """
        try:
            if not company_id:
                logger.warning("company_id is required for register_document_change")
                return
                
            change_data = {
                'doc_id': doc_id,
                'change_type': change_type,
                'company_id': company_id,  # NUEVO: Incluir company_id
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Registrar cambio con namespace por empresa
            change_key = f"doc_change:{company_id}:{doc_id}:{int(time.time())}"
            self.redis_client.setex(change_key, 3600, json.dumps(change_data))  # 1 hour TTL
            
            # Incrementar versión para la empresa específica
            self.increment_version(company_id)
            
            logger.info(f"Document change registered for company {company_id}: {doc_id} - {change_type}")
            
        except Exception as e:
            logger.error(f"Error registering document change for company {company_id}: {e}")
    
    def should_invalidate_cache(self, last_version: int, company_id: str) -> bool:
        """Determinar si se debe invalidar cache para empresa específica"""
        try:
            if not company_id:
                logger.warning("company_id is required for should_invalidate_cache")
                return False
                
            current_version = self.get_current_version(company_id)
            return current_version > last_version
        except Exception as e:
            logger.error(f"Error checking cache invalidation for company {company_id}: {e}")
            return False
    
    def get_all_company_versions(self) -> Dict[str, int]:
        """
        NUEVO: Obtener versiones de todas las empresas
        Útil para administración multi-empresa
        """
        try:
            version_keys = self.redis_client.keys(f"{self.version_key_prefix}:*")
            versions = {}
            
            for key in version_keys:
                try:
                    company_id = key.split(':', 1)[1]  # Extraer company_id
                    version = self.redis_client.get(key)
                    versions[company_id] = int(version) if version else 0
                except Exception as e:
                    logger.warning(f"Error processing version key {key}: {e}")
                    continue
            
            return versions
        except Exception as e:
            logger.error(f"Error getting all company versions: {e}")
            return {}
    
    def get_company_document_changes(self, company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        NUEVO: Obtener cambios recientes de documentos para una empresa específica
        """
        try:
            if not company_id:
                return []
                
            pattern = f"doc_change:{company_id}:*"
            change_keys = self.redis_client.keys(pattern)
            
            changes = []
            for key in sorted(change_keys, reverse=True)[:limit]:  # Más recientes primero
                try:
                    change_data = self.redis_client.get(key)
                    if change_data:
                        changes.append(json.loads(change_data))
                except Exception as e:
                    logger.warning(f"Error processing change key {key}: {e}")
                    continue
            
            return changes
        except Exception as e:
            logger.error(f"Error getting document changes for company {company_id}: {e}")
            return []

# Instanciar el tracker multi-empresa
multi_company_document_change_tracker = MultiCompanyDocumentChangeTracker(redis_client)

# ===============================
# MULTI-COMPANY: Sistema Multi-Agente REFACTORIZADO
# ===============================

class MultiCompanyBenovaMultiAgentSystem:
    """
    Sistema multi-agente integrado con soporte multi-empresa
    REFACTORIZADO: Arquitectura escalable para múltiples empresas
    
    CAMBIOS PRINCIPALES:
    - Separación completa por company_id
    - Configuraciones específicas por empresa  
    - Componentes LangChain por empresa
    - Microservicios con contexto de empresa
    - Compatibilidad mantenida con API existente
    """
    
    def __init__(self, langchain_manager: MultiCompanyLangChainManager, 
                 conversation_manager: MultiCompanyConversationManager,
                 config_manager: CompanyConfigManager):
        self.langchain_manager = langchain_manager
        self.conversation_manager = conversation_manager
        self.config_manager = config_manager
        
        # Cache de agentes por empresa para optimización
        self.company_agents = {}
        
        # Configuración de microservicio de schedule (mantenida para compatibilidad)
        self.schedule_service_url = os.getenv('SCHEDULE_SERVICE_URL', 'http://127.0.0.1:4040')
        self.is_local_development = os.getenv('ENVIRONMENT', 'production') == 'local'
        self.selenium_timeout = 30 if self.is_local_development else 60
        
        # Cache del estado de Selenium con timestamp (por empresa)
        self.selenium_service_status = {}  # {company_id: {available: bool, last_check: timestamp}}
        self.selenium_status_cache_duration = 30  # 30 segundos de cache
        
        logger.info("🏢 Multi-Company Multi-Agent System initialized")
    
    def _get_company_key(self, company_id: str) -> str:
        """Generar clave estándar para empresa"""
        return f"company_agents:{company_id}"
    
    def _verify_selenium_service(self, company_id: str, force_check: bool = False) -> bool:
        """
        Verificar disponibilidad del servicio Selenium con cache por empresa
        REFACTORIZADO: Separación por empresa para futuras personalizaciones
        """
        current_time = time.time()
        
        # Inicializar status si no existe
        if company_id not in self.selenium_service_status:
            self.selenium_service_status[company_id] = {
                'available': False,
                'last_check': 0
            }
        
        company_status = self.selenium_service_status[company_id]
        
        # Si no es verificación forzada y el cache es válido, usar el valor cacheado
        if not force_check and (current_time - company_status['last_check']) < self.selenium_status_cache_duration:
            return company_status['available']
        
        # Realizar nueva verificación
        try:
            # En el futuro, aquí se podría personalizar por empresa
            # Por ahora, usar el mismo endpoint para todas las empresas
            response = requests.get(
                f"{self.schedule_service_url}/health",
                headers={"X-Company-ID": company_id},  # NUEVO: Header de empresa
                timeout=3
            )
            
            if response.status_code == 200:
                company_status['available'] = True
                company_status['last_check'] = current_time
                return True
            else:
                company_status['available'] = False
                company_status['last_check'] = current_time
                return False
                
        except Exception as e:
            logger.warning(f"Selenium service verification failed for company {company_id}: {e}")
            company_status['available'] = False
            company_status['last_check'] = current_time
            return False
    
    def _get_or_create_agents(self, company_id: str) -> Dict[str, Any]:
        """
        Obtener o crear agentes específicos para una empresa
        NUEVO: Sistema de cache de agentes por empresa
        """
        company_key = self._get_company_key(company_id)
        
        if company_key not in self.company_agents:
            logger.info(f"Creating new agent set for company {company_id}")
            
            # Obtener componentes LangChain específicos para la empresa
            chat_model = self.langchain_manager.get_chat_model(company_id)
            vectorstore = self.langchain_manager.get_vectorstore(company_id)
            retriever = vectorstore.as_retriever(
                search_kwargs={"k": self.config_manager.get_company_config(company_id)["max_retrieved_docs"]}
            )
            
            # Crear agentes específicos para la empresa
            self.company_agents[company_key] = {
                'router_agent': self._create_router_agent(company_id),
                'emergency_agent': self._create_emergency_agent(company_id),
                'sales_agent': self._create_sales_agent(company_id, retriever),
                'support_agent': self._create_support_agent(company_id, retriever),
                'schedule_agent': self._create_enhanced_schedule_agent(company_id, retriever),
                'availability_agent': self._create_availability_agent(company_id),
                'orchestrator': None  # Se creará cuando se necesite
            }
            
            # Crear orquestador para la empresa
            self.company_agents[company_key]['orchestrator'] = self._create_orchestrator(company_id)
            
            logger.info(f"✅ Agent set created for company {company_id}")
        
        return self.company_agents[company_key]
    
    def _create_router_agent(self, company_id: str):
        """
        Agente Router: Clasifica la intención del usuario
        REFACTORIZADO: Usa modelo específico de la empresa
        """
        chat_model = self.langchain_manager.get_chat_model(company_id)
        
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un clasificador de intenciones para un centro estético.

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
        
        return router_prompt | chat_model | StrOutputParser()
    
    def _create_emergency_agent(self, company_id: str):
        """
        Agente de Emergencias: Maneja urgencias médicas
        REFACTORIZADO: Usa modelo específico de la empresa
        """
        chat_model = self.langchain_manager.get_chat_model(company_id)
        
        emergency_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un especialista en emergencias médicas del centro estético.

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
        
        return emergency_prompt | chat_model | StrOutputParser()
    
    def _create_sales_agent(self, company_id: str, retriever):
        """
        Agente de Ventas: Especializado en información comercial
        REFACTORIZADO: Usa componentes específicos de la empresa
        """
        chat_model = self.langchain_manager.get_chat_model(company_id)
        
        sales_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asesor comercial especializado del centro estético.

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
            """Obtener contexto RAG para ventas usando retriever específico de la empresa"""
            try:
                question = inputs.get("question", "")
                docs = retriever.invoke(question)
                
                if not docs:
                    return f"""Información básica del centro estético:
- Centro estético especializado
- Tratamientos de belleza y bienestar
- Atención personalizada
- Profesionales certificados
Para información específica de tratamientos, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving sales context for company {company_id}: {e}")
                return "Información básica disponible. Te conectaré con un especialista para detalles específicos."
        
        return (
            {
                "context": get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | sales_prompt
            | chat_model
            | StrOutputParser()
        )
    
    def _create_support_agent(self, company_id: str, retriever):
        """
        Agente de Soporte: Consultas generales y escalación
        REFACTORIZADO: Usa componentes específicos de la empresa
        """
        chat_model = self.langchain_manager.get_chat_model(company_id)
        
        support_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un especialista en soporte al cliente del centro estético.

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
            """Obtener contexto RAG para soporte usando retriever específico de la empresa"""
            try:
                question = inputs.get("question", "")
                docs = retriever.invoke(question)
                
                if not docs:
                    return f"""Información general del centro estético:
- Horarios de atención
- Información general del centro
- Consultas sobre procesos
- Información institucional
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving support context for company {company_id}: {e}")
                return "Información general disponible. Te conectaré con un especialista para consultas específicas."
        
        return (
            {
                "context": get_support_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | support_prompt
            | chat_model
            | StrOutputParser()
        )
    
    def _create_availability_agent(self, company_id: str):
        """
        Agente que verifica disponibilidad MEJORADO con soporte multi-empresa
        REFACTORIZADO: Usa componentes específicos de la empresa
        """
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un agente de disponibilidad del centro estético.
    
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
            """Obtener estado del sistema Selenium para availability por empresa"""
            is_available = self._verify_selenium_service(company_id)
            
            if is_available:
                return f"✅ Sistema de disponibilidad ACTIVO para empresa {company_id} (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de disponibilidad NO DISPONIBLE para empresa {company_id} (Verificar conexión: {self.schedule_service_url})"
        
        def process_availability(inputs):
            """Procesar consulta de disponibilidad para empresa específica"""
            try:
                question = inputs.get("question", "")
                chat_history = inputs.get("chat_history", [])
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"Procesando solicitud de agenda para empresa {company_id}: {question}")
                
                # PASO 1: SIEMPRE verificar disponibilidad si se menciona agendamiento
                available_slots = ""
                if self._contains_schedule_intent(question):
                    logger.info(f"Detectado intent de agendamiento para empresa {company_id} - verificando disponibilidad")
                    try:
                        # Obtener agente de disponibilidad específico de la empresa
                        company_agents = self._get_or_create_agents(company_id)
                        availability_response = company_agents['availability_agent'].invoke({"question": question})
                        available_slots = availability_response
                        logger.info(f"Disponibilidad obtenida para empresa {company_id}: {available_slots}")
                    except Exception as e:
                        logger.error(f"Error verificando disponibilidad para empresa {company_id}: {e}")
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
                logger.info(f"Generando respuesta base con disponibilidad para empresa {company_id}")
                base_response = (schedule_prompt | chat_model | StrOutputParser()).invoke(base_inputs)
                
                # PASO 3: Determinar si proceder con Selenium (solo después de verificar disponibilidad)
                should_proceed_selenium = (
                    self._contains_schedule_intent(question) and 
                    self._should_use_selenium(question, chat_history) and
                    self._has_available_slots_confirmation(available_slots) and
                    not self._is_just_availability_check(question)
                )
                
                logger.info(f"¿Proceder con Selenium para empresa {company_id}? {should_proceed_selenium}")
                
                if should_proceed_selenium:
                    logger.info(f"Procediendo con agendamiento automático via Selenium para empresa {company_id}")
                    selenium_result = self._call_local_schedule_microservice(question, user_id, chat_history, company_id)
                    
                    if selenium_result.get('success'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    elif selenium_result.get('requires_more_info'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    else:
                        return f"{available_slots}\n\n{base_response}\n\nNota: Te conectaré con un especialista para completar el agendamiento."
                
                return base_response
                
            except Exception as e:
                logger.error(f"Error en agendamiento para empresa {company_id}: {e}")
                return "Error procesando tu solicitud. Conectando con especialista... 📋"
        
        return (
            {
                "context": get_schedule_context,
                "selenium_status": get_selenium_status,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", []),
                "user_id": lambda x: x.get("user_id", "default_user")
            }
            | RunnableLambda(process_schedule_with_selenium)
        )
    
    def _create_orchestrator(self, company_id: str):
        """
        Orquestador principal que coordina los agentes para empresa específica
        REFACTORIZADO: Usa agentes específicos de la empresa
        """
        def route_to_agent(inputs):
            """Enrutar a agente específico basado en clasificación para empresa específica"""
            try:
                # Obtener agentes específicos de la empresa
                company_agents = self._get_or_create_agents(company_id)
                
                # Obtener clasificación del router específico de la empresa
                router_response = company_agents['router_agent'].invoke(inputs)
                
                # Parsear respuesta JSON
                try:
                    classification = json.loads(router_response)
                    intent = classification.get("intent", "SUPPORT")
                    confidence = classification.get("confidence", 0.5)
                    
                    logger.info(f"Intent classified for company {company_id}: {intent} (confidence: {confidence})")
                    
                except json.JSONDecodeError:
                    # Fallback si no es JSON válido
                    intent = "SUPPORT"
                    confidence = 0.3
                    logger.warning(f"Router response was not valid JSON for company {company_id}, defaulting to SUPPORT")
                
                # Agregar user_id a inputs para el agente de schedule
                inputs["user_id"] = inputs.get("user_id", "default_user")
                inputs["company_id"] = company_id  # NUEVO: Agregar company_id a inputs
                
                # Determinar agente basado en intención usando agentes específicos de la empresa
                if intent == "EMERGENCY" or confidence > 0.8:
                    if intent == "EMERGENCY":
                        return company_agents['emergency_agent'].invoke(inputs)
                    elif intent == "SALES":
                        return company_agents['sales_agent'].invoke(inputs)
                    elif intent == "SCHEDULE":
                        return company_agents['schedule_agent'].invoke(inputs)
                    else:
                        return company_agents['support_agent'].invoke(inputs)
                else:
                    # Baja confianza, usar soporte por defecto
                    return company_agents['support_agent'].invoke(inputs)
                    
            except Exception as e:
                logger.error(f"Error in orchestrator for company {company_id}: {e}")
                # Fallback a soporte en caso de error
                company_agents = self._get_or_create_agents(company_id)
                return company_agents['support_agent'].invoke(inputs)
        
        return RunnableLambda(route_to_agent)
    
    # ===============================
    # MÉTODOS DE UTILIDAD MULTI-EMPRESA
    # ===============================
    
    def _extract_date_from_question(self, question, chat_history=None):
        """Extract date from question or chat history (sin cambios - es agnóstico a empresa)"""
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
        """Helper to find date in text (sin cambios - es agnóstico a empresa)"""
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
        """Extraer tratamiento del mensaje (sin cambios - es agnóstico a empresa)"""
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
    
    def _get_treatment_duration(self, treatment, company_id: str):
        """
        Obtener duración del tratamiento desde RAG específico de la empresa
        REFACTORIZADO: Usa retriever específico de la empresa
        """
        try:
            # Usar retriever específico de la empresa
            vectorstore = self.langchain_manager.get_vectorstore(company_id)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            
            # Consultar RAG para obtener duración específica
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
            logger.error(f"Error obteniendo duración del tratamiento para empresa {company_id}: {e}")
            return 60  # Duración por defecto
    
    def _call_check_availability(self, date, company_id: str):
        """
        Llamar al endpoint de disponibilidad con contexto de empresa
        REFACTORIZADO: Incluye company_id en headers
        """
        try:
            # 1. VERIFICAR ESTADO DEL SERVICIO PRIMERO
            if not self._verify_selenium_service(company_id):
                logger.warning(f"Servicio Selenium no disponible para availability check empresa {company_id}")
                return None
            
            logger.info(f"Consultando disponibilidad en: {self.schedule_service_url}/check-availability para fecha: {date} empresa: {company_id}")
            
            # 2. INCLUIR COMPANY_ID EN HEADERS
            response = requests.post(
                f"{self.schedule_service_url}/check-availability",
                json={"date": date, "company_id": company_id},  # NUEVO: Incluir company_id
                headers={
                    "Content-Type": "application/json",
                    "X-Company-ID": company_id  # NUEVO: Header de empresa
                },
                timeout=self.selenium_timeout
            )
            
            logger.info(f"Respuesta de availability endpoint empresa {company_id} - Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Datos de disponibilidad obtenidos exitosamente para empresa {company_id}: {result.get('success', False)}")
                return result.get("data", {})
            else:
                logger.warning(f"Endpoint de disponibilidad retornó código {response.status_code} para empresa {company_id}")
                logger.warning(f"Respuesta: {response.text}")
                # Marcar servicio como no disponible para esta empresa
                if company_id in self.selenium_service_status:
                    self.selenium_service_status[company_id]['available'] = False
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando con endpoint de disponibilidad ({self.selenium_timeout}s) empresa {company_id}")
            if company_id in self.selenium_service_status:
                self.selenium_service_status[company_id]['available'] = False
            return None
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"No se pudo conectar con endpoint de disponibilidad para empresa {company_id}: {self.schedule_service_url}")
            logger.error(f"Error de conexión: {e}")
            if company_id in self.selenium_service_status:
                self.selenium_service_status[company_id]['available'] = False
            return None
            
        except Exception as e:
            logger.error(f"Error llamando endpoint de disponibilidad para empresa {company_id}: {e}")
            if company_id in self.selenium_service_status:
                self.selenium_service_status[company_id]['available'] = False
            return None
    
    def _call_local_schedule_microservice(self, question: str, user_id: str, chat_history: list, company_id: str) -> Dict[str, Any]:
        """
        Llamar al microservicio de schedule LOCAL con contexto de empresa
        REFACTORIZADO: Incluye company_id en la llamada
        """
        try:
            logger.info(f"Llamando a microservicio local en: {self.schedule_service_url} para empresa {company_id}")
            
            response = requests.post(
                f"{self.schedule_service_url}/schedule-request",
                json={
                    "message": question,
                    "user_id": user_id,
                    "company_id": company_id,  # NUEVO: Incluir company_id
                    "chat_history": [
                        {
                            "content": msg.content if hasattr(msg, 'content') else str(msg),
                            "type": getattr(msg, 'type', 'user')
                        } for msg in chat_history
                    ]
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Company-ID": company_id  # NUEVO: Header de empresa
                },
                timeout=self.selenium_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Si se agendó exitosamente, notificar al sistema principal
                if result.get('success') and result.get('appointment_data'):
                    self._notify_appointment_success(user_id, result.get('appointment_data'), company_id)
                
                logger.info(f"Respuesta exitosa del microservicio local para empresa {company_id}: {result.get('success', False)}")
                return result
            else:
                logger.warning(f"Microservicio local retornó código {response.status_code} para empresa {company_id}")
                # Marcar servicio como no disponible para esta empresa
                if company_id in self.selenium_service_status:
                    self.selenium_service_status[company_id]['available'] = False
                return {"success": False, "message": "Servicio local no disponible"}
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout conectando con microservicio local ({self.selenium_timeout}s) empresa {company_id}")
            if company_id in self.selenium_service_status:
                self.selenium_service_status[company_id]['available'] = False
            return {"success": False, "message": "Timeout del servicio local"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"No se pudo conectar con microservicio local para empresa {company_id}: {self.schedule_service_url}")
            if company_id in self.selenium_service_status:
                self.selenium_service_status[company_id]['available'] = False
            return {"success": False, "message": "Servicio local no disponible"}
        
        except Exception as e:
            logger.error(f"Error llamando microservicio local para empresa {company_id}: {e}")
            if company_id in self.selenium_service_status:
                self.selenium_service_status[company_id]['available'] = False
            return {"success": False, "message": "Error del servicio local"}
    
    # Métodos de utilidad sin cambios (agnósticos a empresa)
    def _filter_slots_by_duration(self, available_slots, required_duration):
        """Filtrar slots que pueden acomodar la duración requerida (sin cambios)"""
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
        """Verificar si los horarios son consecutivos (sin cambios)"""
        for i in range(len(times) - 1):
            current_minutes = self._time_to_minutes(times[i])
            next_minutes = self._time_to_minutes(times[i + 1])
            if next_minutes - current_minutes != 30:
                return False
        return True
    
    def _time_to_minutes(self, time_str):
        """Convertir hora a minutos desde medianoche (sin cambios)"""
        try:
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
        """Sumar minutos a una hora (sin cambios)"""
        try:
            total_minutes = self._time_to_minutes(time_str) + minutes_to_add
            hours = (total_minutes // 60) % 24
            minutes = total_minutes % 60
            return f"{hours:02d}:{minutes:02d}"
        except:
            return time_str
    
    def _format_slots_response(self, slots, date, duration):
        """Formatear respuesta con horarios disponibles (sin cambios)"""
        if not slots:
            return f"No hay horarios disponibles para {date} (tratamiento de {duration} min)."
        
        slots_text = "\n".join(f"- {slot}" for slot in slots)
        return f"Horarios disponibles para {date} (tratamiento de {duration} min):\n{slots_text}"
    
    def _contains_schedule_intent(self, question: str) -> bool:
        """Detectar si la pregunta contiene intención de agendamiento (sin cambios)"""
        schedule_keywords = [
            "agendar", "reservar", "programar", "cita", "appointment",
            "agenda", "disponibilidad", "horario", "fecha", "hora",
            "procede", "proceder", "confirmar cita"
        ]
        return any(keyword in question.lower() for keyword in schedule_keywords)
    
    def _has_available_slots_confirmation(self, availability_response: str) -> bool:
        """Verificar si hay slots disponibles (sin cambios)"""
        if not availability_response:
            return False
        
        availability_lower = availability_response.lower()
        
        text_indicators = [
            "horarios disponibles",
            "disponible para"
        ]
        
        has_text_indicators = any(indicator in availability_lower for indicator in text_indicators)
        has_list_format = "- " in availability_response
        has_time_format = ":" in availability_response and "-" in availability_response
        
        negative_indicators = [
            "no hay horarios disponibles",
            "no hay disponibilidad", 
            "error consultando disponibilidad"
        ]
        
        has_negative = any(indicator in availability_lower for indicator in negative_indicators)
        has_positive = has_text_indicators or has_list_format or has_time_format
        
        return has_positive and not has_negative
    
    def _is_just_availability_check(self, question: str) -> bool:
        """Determinar si solo se está consultando disponibilidad (sin cambios)"""
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
        
        return has_availability_check and not has_schedule_confirmation
    
    def _should_use_selenium(self, question: str, chat_history: list) -> bool:
        """Determinar si se debe usar el microservicio de Selenium (sin cambios)"""
        question_lower = question.lower()
        
        schedule_keywords = [
            "agendar", "reservar", "programar", "cita", "appointment",
            "agenda", "disponibilidad", "horario", "fecha", "hora"
        ]
        
        has_schedule_intent = any(keyword in question_lower for keyword in schedule_keywords)
        has_patient_info = self._extract_patient_info_from_history(chat_history)
        
        return has_schedule_intent and (has_patient_info or self._has_complete_info_in_message(question))
    
    def _extract_patient_info_from_history(self, chat_history: list) -> bool:
        """Extraer información del paciente del historial (sin cambios)"""
        history_text = " ".join([msg.content if hasattr(msg, 'content') else str(msg) for msg in chat_history])
        
        has_name = any(word in history_text.lower() for word in ["nombre", "llamo", "soy"])
        has_phone = any(char.isdigit() for char in history_text) and len([c for c in history_text if c.isdigit()]) >= 7
        has_date = any(word in history_text.lower() for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name and (has_phone or has_date)
    
    def _has_complete_info_in_message(self, message: str) -> bool:
        """Verificar si el mensaje tiene información completa (sin cambios)"""
        message_lower = message.lower()
        
        has_name_indicator = any(word in message_lower for word in ["nombre", "llamo", "soy"])
        has_phone_indicator = any(char.isdigit() for char in message) and len([c for c in message if c.isdigit()]) >= 7
        has_date_indicator = any(word in message_lower for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name_indicator and has_phone_indicator and has_date_indicator
    
    def _notify_appointment_success(self, user_id: str, appointment_data: Dict[str, Any], company_id: str):
        """
        Notificar al sistema principal sobre cita exitosa
        REFACTORIZADO: Incluye company_id en la notificación
        """
        try:
            main_system_url = os.getenv('MAIN_SYSTEM_URL')
            if main_system_url:
                requests.post(
                    f"{main_system_url}/appointment-notification",
                    json={
                        "user_id": user_id,
                        "company_id": company_id,  # NUEVO: Incluir company_id
                        "event": "appointment_scheduled",
                        "data": appointment_data
                    },
                    headers={
                        "X-Company-ID": company_id  # NUEVO: Header de empresa
                    },
                    timeout=5
                )
                logger.info(f"Notificación enviada al sistema principal para usuario {user_id} empresa {company_id}")
        except Exception as e:
            logger.error(f"Error notificando cita exitosa para empresa {company_id}: {e}")
    
    # ===============================
    # API PÚBLICA MULTI-EMPRESA
    # ===============================
    
    def get_response(self, question: str, user_id: str, company_id: str) -> Tuple[str, str]:
        """
        Método principal para obtener respuesta del sistema multi-agente
        REFACTORIZADO: Requiere company_id y usa componentes específicos de la empresa
        
        Args:
            question: Pregunta del usuario
            user_id: ID del usuario 
            company_id: ID de la empresa
            
        Returns:
            Tuple[respuesta, agente_utilizado]
        """
        if not question or not question.strip():
            return "Por favor, envía un mensaje específico para poder ayudarte. 😊", "support"
        
        if not user_id or not user_id.strip():
            return "Error interno: ID de usuario inválido.", "error"
        
        if not company_id or not company_id.strip():
            return "Error interno: ID de empresa inválido.", "error"
        
        try:
            # Validar acceso a la empresa
            if not validate_company_access(company_id):
                return "Error: Acceso no autorizado a esta empresa.", "error"
            
            # Obtener historial de conversación específico de la empresa
            chat_history = self.conversation_manager.get_chat_history(user_id, company_id, format_type="messages")
            
            # Obtener orquestador específico de la empresa
            company_agents = self._get_or_create_agents(company_id)
            orchestrator = company_agents['orchestrator']
            
            # Preparar inputs
            inputs = {
                "question": question.strip(),
                "chat_history": chat_history,
                "user_id": user_id,
                "company_id": company_id
            }
            
            # Obtener respuesta del orquestador específico de la empresa
            response = orchestrator.invoke(inputs)
            
            # Agregar mensajes al historial específico de la empresa
            self.conversation_manager.add_message(user_id, company_id, "user", question)
            self.conversation_manager.add_message(user_id, company_id, "assistant", response)
            
            # Determinar qué agente se utilizó
            agent_used = self._determine_agent_used(response)
            
            logger.info(f"Multi-agent response generated for user {user_id} company {company_id} using {agent_used}")
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"Error en sistema multi-agente (User: {user_id}, Company: {company_id})")
            return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", "error"
    
    def _determine_agent_used(self, response: str) -> str:
        """Determinar qué agente se utilizó basado en la respuesta (sin cambios)"""
        if "Escalando tu caso de emergencia" in response:
            return "emergency"
        elif "¿Te gustaría agendar tu cita?" in response:
            return "sales"
        elif "Procesando tu solicitud de agenda" in response:
            return "schedule"
        elif "Te conectaré con un especialista" in response:
            return "support"
        else:
            return "support"
    
    def health_check(self, company_id: str = None) -> Dict[str, Any]:
        """
        Verificar salud del sistema multi-agente
        REFACTORIZADO: Puede verificar empresa específica o sistema general
        """
        try:
            # Si no se especifica empresa, verificar sistema general
            if not company_id:
                # Verificar todas las empresas registradas
                all_companies = self.conversation_manager.get_all_companies()
                company_health = {}
                
                for comp_id in all_companies:
                    try:
                        service_healthy = self._verify_selenium_service(comp_id)
                        company_health[comp_id] = {
                            "selenium_service_healthy": service_healthy,
                            "agents_created": self._get_company_key(comp_id) in self.company_agents
                        }
                    except Exception as e:
                        company_health[comp_id] = {
                            "selenium_service_healthy": False,
                            "agents_created": False,
                            "error": str(e)
                        }
                
                return {
                    "system_healthy": True,
                    "system_type": "multi-company_multi-agent_enhanced",
                    "companies_health": company_health,
                    "total_companies": len(all_companies),
                    "schedule_service_url": self.schedule_service_url,
                    "environment": os.getenv('ENVIRONMENT', 'production')
                }
            
            # Verificar empresa específica
                
                logger.info(f"=== AVAILABILITY AGENT - EMPRESA {company_id} ===")
                logger.info(f"Pregunta: {question}")
                logger.info(f"Estado Selenium: {selenium_status}")
                
                # 1. VERIFICAR SERVICIO DISPONIBLE PRIMERO
                if not self._verify_selenium_service(company_id):
                    logger.error(f"Servicio Selenium no disponible para empresa {company_id}")
                    return "Error consultando disponibilidad. Te conectaré con un especialista para verificar horarios. 👩‍⚕️"
                
                # Extract date from question and history
                date = self._extract_date_from_question(question, chat_history)
                treatment = self._extract_treatment_from_question(question)
                
                if not date:
                    return "Por favor especifica la fecha en formato DD-MM-YYYY para consultar disponibilidad."
                
                logger.info(f"Empresa {company_id} - Fecha extraída: {date}, Tratamiento: {treatment}")
                
                # Obtener duración del tratamiento desde RAG específico de la empresa
                duration = self._get_treatment_duration(treatment, company_id)
                logger.info(f"Empresa {company_id} - Duración del tratamiento: {duration} minutos")
                
                # 2. LLAMAR ENDPOINT CON MÉTODO MEJORADO
                availability_data = self._call_check_availability(date, company_id)
                
                if not availability_data:
                    logger.warning(f"No se obtuvieron datos de disponibilidad para empresa {company_id}")
                    return "Error consultando disponibilidad. Te conectaré con un especialista."
                
                if not availability_data.get("available_slots"):
                    logger.info(f"No hay slots disponibles para empresa {company_id} en fecha {date}")
                    return f"No hay horarios disponibles para {date}."
                
                # Filtrar slots según duración
                filtered_slots = self._filter_slots_by_duration(
                    availability_data["available_slots"], 
                    duration
                )
                
                logger.info(f"Empresa {company_id} - Slots filtrados: {filtered_slots}")
                
                # Formatear respuesta
                response = self._format_slots_response(filtered_slots, date, duration)
                logger.info(f"=== AVAILABILITY AGENT - EMPRESA {company_id} - RESPUESTA GENERADA ===")
                return response
                
            except Exception as e:
                logger.error(f"Error en agente de disponibilidad para empresa {company_id}: {e}")
                logger.exception("Stack trace completo:")
                return "Error consultando disponibilidad. Te conectaré con un especialista."
    
        return (
            {
                "selenium_status": get_availability_selenium_status,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | RunnableLambda(process_availability)
        )
    
    def _create_enhanced_schedule_agent(self, company_id: str, retriever):
        """
        Agente de Schedule mejorado con integración de disponibilidad
        REFACTORIZADO: Usa componentes específicos de la empresa
        """
        chat_model = self.langchain_manager.get_chat_model(company_id)
        
        schedule_prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un especialista en gestión de citas del centro estético.
    
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
            """Obtener contexto RAG para agenda usando retriever específico de la empresa"""
            try:
                question = inputs.get("question", "")
                docs = retriever.invoke(question)
                
                if not docs:
                    return f"""Información básica de agenda del centro estético:
    - Horarios de atención: Lunes a Viernes 8:00 AM - 6:00 PM, Sábados 8:00 AM - 4:00 PM
    - Servicios agendables: Consultas médicas, Tratamientos estéticos, Procedimientos de belleza
    - Políticas de cancelación: 24 horas de anticipación
    - Reagendamiento disponible sin costo
    - Sistema de agendamiento automático con Selenium LOCAL disponible
    - Datos requeridos: Nombre, cédula, teléfono, fecha y hora deseada"""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving schedule context for company {company_id}: {e}")
                return "Información básica de agenda disponible. Sistema de agendamiento automático disponible."
        
        def get_selenium_status(inputs):
            """Obtener estado del sistema Selenium específico para la empresa"""
            if self._verify_selenium_service(company_id):
                return f"✅ Sistema de agendamiento automático ACTIVO para empresa {company_id} (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de agendamiento automático NO DISPONIBLE para empresa {company_id} (Verificar conexión local)"

#####################################################################################################################################
        def process_schedule_with_selenium(inputs):
                    """Procesar solicitud de agenda con integración de disponibilidad MEJORADA para empresa específica"""
                    try:
                        question = inputs.get("question", "")
                        user_id = inputs.get("user_id", "default_user")
                        chat_history = inputs.get("chat_history", [])
                        context = inputs.get("context", "")
                        selenium_status = inputs.get("selenium_status", "")
                        
                        logger.info(f"Procesando solicitud de agenda para empresa {company_id}: {question}")
                        
                        # PASO 1: SIEMPRE verificar disponibilidad si se menciona agendamiento
                        available_slots = ""
                        if self._contains_schedule_intent(question):
                            logger.info(f"Detectado intent de agendamiento para empresa {company_id} - verificando disponibilidad")
                            try:
                                # Obtener agente de disponibilidad específico de la empresa
                                company_agents = self._get_or_create_agents(company_id)
                                availability_response = company_agents['availability_agent'].invoke({"question": question})
                                available_slots = availability_response
                                logger.info(f"Disponibilidad obtenida para empresa {company_id}: {available_slots}")
                            except Exception as e:
                                logger.error(f"Error verificando disponibilidad para empresa {company_id}: {e}")
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
                        logger.info(f"Generando respuesta base con disponibilidad para empresa {company_id}")
                        base_response = (schedule_prompt | chat_model | StrOutputParser()).invoke(base_inputs)
                        
                        # PASO 3: Determinar si proceder con Selenium (solo después de verificar disponibilidad)
                        should_proceed_selenium = (
                            self._contains_schedule_intent(question) and 
                            self._should_use_selenium(question, chat_history) and
                            self._has_available_slots_confirmation(available_slots) and
                            not self._is_just_availability_check(question)
                        )
                        
                        logger.info(f"¿Proceder con Selenium para empresa {company_id}? {should_proceed_selenium}")
                        
                        if should_proceed_selenium:
                            logger.info(f"Procediendo con agendamiento automático via Selenium para empresa {company_id}")
                            selenium_result = self._call_local_schedule_microservice(question, user_id, chat_history, company_id)
                            
                            if selenium_result.get('success'):
                                return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                            elif selenium_result.get('requires_more_info'):
                                return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                            else:
                                return f"{available_slots}\n\n{base_response}\n\nNota: Te conectaré con un especialista para completar el agendamiento."
                        
                        return base_response
                        
                    except Exception as e:
                        logger.error(f"Error en agendamiento para empresa {company_id}: {e}")
                        return "Error procesando tu solicitud. Conectando con especialista... 📋"
                
                return (
                    {
                        "context": get_schedule_context,
                        "selenium_status": get_selenium_status,
                        "question": lambda x: x.get("question", ""),
                        "chat_history": lambda x: x.get("chat_history", []),
                        "user_id": lambda x: x.get("user_id", "default_user")
                    }
                    | RunnableLambda(process_schedule_with_selenium)
                )
            
            def health_check(self, company_id: str = None) -> Dict[str, Any]:
                """
                Verificar salud del sistema multi-agente
                REFACTORIZADO: Puede verificar empresa específica o sistema general
                """
                try:
                    # Si no se especifica empresa, verificar sistema general
                    if not company_id:
                        # Verificar todas las empresas registradas
                        all_companies = self.conversation_manager.get_all_companies()
                        company_health = {}
                        
                        for comp_id in all_companies:
                            try:
                                service_healthy = self._verify_selenium_service(comp_id)
                                company_health[comp_id] = {
                                    "selenium_service_healthy": service_healthy,
                                    "agents_created": self._get_company_key(comp_id) in self.company_agents
                                }
                            except Exception as e:
                                company_health[comp_id] = {
                                    "selenium_service_healthy": False,
                                    "agents_created": False,
                                    "error": str(e)
                                }
                        
                        return {
                            "system_healthy": True,
                            "system_type": "multi-company_multi-agent_enhanced",
                            "companies_health": company_health,
                            "total_companies": len(all_companies),
                            "schedule_service_url": self.schedule_service_url,
                            "environment": os.getenv('ENVIRONMENT', 'production')
                        }
                    
                    # Verificar empresa específica
                    else:
                        service_healthy = self._verify_selenium_service(company_id)
                        agents_created = self._get_company_key(company_id) in self.company_agents
                        
                        return {
                            "system_healthy": True,
                            "company_id": company_id,
                            "agents_available": ["router", "emergency", "sales", "schedule", "support", "availability"],
                            "agents_created": agents_created,
                            "schedule_service_healthy": service_healthy,
                            "schedule_service_url": self.schedule_service_url,
                            "schedule_service_type": "LOCAL",
                            "system_type": "multi-company_multi-agent_enhanced",
                            "orchestrator_active": agents_created,
                            "rag_enabled": True,
                            "selenium_integration": service_healthy,
                            "environment": os.getenv('ENVIRONMENT', 'production')
                        }
                        
                except Exception as e:
                    logger.error(f"Error en health check para empresa {company_id}: {e}")
                    return {
                        "system_healthy": False,
                        "company_id": company_id,
                        "error": str(e),
                        "system_type": "multi-company_multi-agent_enhanced"
                    }
            
            def get_system_stats(self, company_id: str = None) -> Dict[str, Any]:
                """
                Obtener estadísticas del sistema multi-agente
                REFACTORIZADO: Puede obtener stats de empresa específica o sistema general
                """
                try:
                    if not company_id:
                        # Estadísticas generales del sistema
                        all_companies = self.conversation_manager.get_all_companies()
                        total_agents_created = len(self.company_agents)
                        
                        return {
                            "system_type": "multi-company_multi-agent_enhanced",
                            "total_companies": len(all_companies),
                            "companies_with_agents": total_agents_created,
                            "agents_per_company": ["router", "emergency", "sales", "schedule", "support", "availability"],
                            "orchestrator_active": True,
                            "rag_enabled": True,
                            "schedule_service_url": self.schedule_service_url,
                            "schedule_service_type": "LOCAL",
                            "environment": os.getenv('ENVIRONMENT', 'production'),
                            "companies": list(all_companies)
                        }
                    else:
                        # Estadísticas específicas de la empresa
                        agents_created = self._get_company_key(company_id) in self.company_agents
                        selenium_available = self._verify_selenium_service(company_id, force_check=False)
                        
                        return {
                            "company_id": company_id,
                            "agents_available": ["router", "emergency", "sales", "schedule", "support", "availability"],
                            "agents_created": agents_created,
                            "system_type": "multi-company_multi-agent_enhanced",
                            "orchestrator_active": agents_created,
                            "rag_enabled": True,
                            "selenium_integration": selenium_available,
                            "schedule_service_url": self.schedule_service_url,
                            "schedule_service_type": "LOCAL",
                            "environment": os.getenv('ENVIRONMENT', 'production')
                        }
                        
                except Exception as e:
                    logger.error(f"Error obteniendo estadísticas para empresa {company_id}: {e}")
                    return {
                        "system_type": "multi-company_multi-agent_enhanced",
                        "error": str(e),
                        "company_id": company_id
                    }
            
            def reconnect_selenium_service(self, company_id: str) -> bool:
                """
                Método para reconectar con el servicio Selenium para empresa específica
                REFACTORIZADO: Reconexión específica por empresa
                """
                try:
                    logger.info(f"Intentando reconectar con servicio Selenium para empresa {company_id}...")
                    
                    # Forzar verificación del servicio para la empresa
                    service_available = self._verify_selenium_service(company_id, force_check=True)
                    
                    if service_available:
                        logger.info(f"✅ Reconexión exitosa con servicio Selenium para empresa {company_id}")
                    else:
                        logger.warning(f"⚠️ No se pudo reconectar con servicio Selenium para empresa {company_id}")
                    
                    return service_available
                    
                except Exception as e:
                    logger.error(f"Error en reconexión Selenium para empresa {company_id}: {e}")
                    return False
            
            def clear_company_cache(self, company_id: str) -> bool:
                """
                Limpiar cache de agentes para una empresa específica
                NUEVO: Método para limpiar cache específico de empresa
                """
                try:
                    company_key = self._get_company_key(company_id)
                    
                    if company_key in self.company_agents:
                        del self.company_agents[company_key]
                        logger.info(f"Cache de agentes limpiado para empresa {company_id}")
                        return True
                    else:
                        logger.info(f"No había cache de agentes para empresa {company_id}")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error limpiando cache para empresa {company_id}: {e}")
                    return False
            
            def validate_company_access(self, company_id: str) -> bool:
                """
                Validar acceso a empresa específica
                NUEVO: Método de validación de acceso por empresa
                """
                try:
                    # Verificar que la empresa existe en el sistema
                    all_companies = self.conversation_manager.get_all_companies()
                    
                    if company_id not in all_companies:
                        logger.warning(f"Acceso denegado: empresa {company_id} no registrada")
                        return False
                    
                    # Verificar configuración de la empresa
                    if not self.config_manager.get_company_config(company_id):
                        logger.warning(f"Acceso denegado: configuración no encontrada para empresa {company_id}")
                        return False
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Error validando acceso para empresa {company_id}: {e}")
                    return False

# Función de utilidad para inicializar el sistema multi-empresa
def create_multicompany_multiagent_system(
    langchain_manager: MultiCompanyLangChainManager,
    conversation_manager: MultiCompanyConversationManager,
    config_manager: CompanyConfigManager
):
    """
    Crear instancia del sistema multi-agente multi-empresa
    REFACTORIZADO: Función de inicialización para sistema multi-empresa
    """
    return MultiCompanyBenovaMultiAgentSystem(
        langchain_manager=langchain_manager,
        conversation_manager=conversation_manager,
        config_manager=config_manager
    )

# Función de validación global
def validate_company_access(company_id: str) -> bool:
    """
    Función global para validar acceso a empresa
    NUEVO: Validación global de acceso por empresa
    """
    try:
        # Aquí se puede implementar lógica adicional de validación
        # Por ejemplo, verificar permisos, licencias, etc.
        
        if not company_id or not company_id.strip():
            return False
        
        # Verificaciones básicas de formato
        if len(company_id) < 3 or len(company_id) > 50:
            return False
        
        # Caracteres permitidos (letras, números, guiones, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', company_id):
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error en validación global de empresa {company_id}: {e}")
        return False

# ===============================
# modern_rag_system_with_multiagent
# ===============================
def create_modern_rag_system_with_multiagent(vectorstore, chat_model, embeddings, conversation_manager):
    """
    Crear sistema RAG moderno con arquitectura multi-agente
    Reemplaza la clase ModernBenovaRAGSystem manteniendo compatibilidad
    """
    class ModernBenovaRAGSystemMultiAgent:
        """
        Wrapper que mantiene compatibilidad con el sistema existente
        pero usa arquitectura multi-agente internamente
        """
        
        def __init__(self, vectorstore, chat_model, embeddings, conversation_manager):
            self.vectorstore = vectorstore
            self.chat_model = chat_model
            self.embeddings = embeddings
            self.conversation_manager = conversation_manager
            self.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            
            # Inicializar sistema multi-agente
            self.multi_agent_system = BenovaMultiAgentSystem(
                chat_model, vectorstore, conversation_manager
            )
        
        def get_response(self, question: str, user_id: str) -> Tuple[str, List]:
            """
            Método compatible con la interfaz existente - FIXED: Usar invoke
            """
            try:
                # Usar sistema multi-agente
                response, agent_used = self.multi_agent_system.get_response(question, user_id)
                
                # Obtener documentos para compatibilidad
                docs = self.retriever.invoke(question)
                
                logger.info(f"Multi-agent response: {response[:100]}... (agent: {agent_used})")
                
                return response, docs
                
            except Exception as e:
                logger.error(f"Error in multi-agent RAG system: {e}")
                return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", []
        
        def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
            """
            ACTUALIZADO: Agregar documentos usando sistema de chunking avanzado
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
                                combined_meta.update({"chunk_index": j, "doc_index": i})
                                all_metas.append(combined_meta)
                
                # Agregar al vectorstore
                if all_texts:
                    self.vectorstore.add_texts(all_texts, metadatas=all_metas)
                    logger.info(f"Added {len(all_texts)} advanced chunks to vectorstore")
                
                return len(all_texts)
                
            except Exception as e:
                logger.error(f"Error adding documents with advanced chunking: {e}")
                return 0
    
    return ModernBenovaRAGSystemMultiAgent(vectorstore, chat_model, embeddings, conversation_manager)

# ===============================
# Initialize Modern Components
# ===============================

# Crear instancias de los componentes modernos
try:
    modern_conversation_manager = ModernConversationManager(redis_client, MAX_CONTEXT_MESSAGES)
    
    modern_rag_system = create_modern_rag_system_with_multiagent(
        vectorstore, 
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

def get_modern_chat_response_multiagent(user_id: str, user_message: str) -> str:
    """
    Versión actualizada que usa sistema multi-agente
    Reemplaza la función get_modern_chat_response existente
    """
    if not user_id or not user_id.strip():
        logger.error("Invalid user_id provided")
        return "Error interno: ID de usuario inválido."
    
    if not user_message or not user_message.strip():
        logger.error("Empty or invalid message content")
        return "Por favor, envía un mensaje con contenido para poder ayudarte. 😊"
    
    try:
        # Usar sistema multi-agente global
        response, agent_used = modern_rag_system.multi_agent_system.get_response(user_message, user_id)
        
        logger.info(f"Multi-agent response for user {user_id}: {response[:100]}... (agent: {agent_used})")
        
        return response
        
    except Exception as e:
        logger.exception(f"Error in multi-agent chat response for user {user_id}: {e}")
        return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo en unos momentos. 🔧"

# ===============================
# CHATWOOT API FUNCTIONS
# ===============================

def send_message_to_chatwoot(conversation_id, message_content):
    """Send message to Chatwoot using API"""
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conversation_id}/messages"

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

        logger.info(f"Chatwoot API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info(f"✅ Message sent to conversation {conversation_id}")
            return True
        else:
            logger.error(f"❌ Failed to send message: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Error sending message to Chatwoot: {e}")
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
    
    return event_type

def handle_conversation_updated(data):
    """Handle conversation_updated events to update bot status"""
    try:
        conversation_id = data.get("id")
        if not conversation_id:
            logger.error("❌ Could not extract conversation_id from conversation_updated event")
            return False
        
        conversation_status = data.get("status")
        if not conversation_status:
            logger.warning(f"⚠️ No status found in conversation_updated for {conversation_id}")
            return False
        
        logger.info(f"📋 Conversation {conversation_id} updated to status: {conversation_status}")
        update_bot_status(conversation_id, conversation_status)
        return True
        
    except Exception as e:
        logger.error(f"Error handling conversation_updated: {e}")
        return False

def process_incoming_message(data):
    """Process incoming message with comprehensive validation and error handling"""
    try:
        # Validate message type
        message_type = data.get("message_type")
        if message_type != "incoming":
            logger.info(f"🤖 Ignoring message type: {message_type}")
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
        if not should_bot_respond(conversation_id, conversation_status):
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
            logger.warning(f"Message content too long: {len(content)} characters")
            content = content[:4000] + "..."

        # Check for duplicate processing
        if message_id and is_message_already_processed(message_id, conversation_id):
            return {"status": "already_processed", "ignored": True}

        # Extract contact information with improved validation
        contact_id, extraction_method, is_valid = extract_contact_id(data)
        if not is_valid or not contact_id:
            raise WebhookError("Could not extract valid contact_id from webhook data", 400)

        # Generate standardized user_id
        user_id = modern_conversation_manager._create_user_id(contact_id)

        logger.info(f"🔄 Processing message from conversation {conversation_id}")
        logger.info(f"👤 User: {user_id} (contact: {contact_id}, method: {extraction_method})")
        logger.info(f"💬 Message: {content[:100]}...")

        # Generate response with validation - CORREGIDO
        assistant_reply = get_modern_chat_response_multiagent(user_id, content)
        
        if not assistant_reply or not assistant_reply.strip():
            assistant_reply = "Disculpa, no pude procesar tu mensaje. ¿Podrías intentar de nuevo? 😊"
        
        logger.info(f"🤖 Assistant response: {assistant_reply[:100]}...")

        # Send response to Chatwoot
        success = send_message_to_chatwoot(conversation_id, assistant_reply)

        if not success:
            raise WebhookError("Failed to send response to Chatwoot", 500)

        logger.info(f"✅ Successfully processed message for conversation {conversation_id}")
        
        return {
            "status": "success",
            "message": "Response sent successfully",
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
        logger.exception(f"💥 Error procesando mensaje (ID: {message_id})")
        raise WebhookError("Internal server error", 500)
    except WebhookError:
        raise


@app.route("/webhook", methods=["POST"])
def chatwoot_webhook():
    try:
        data = request.get_json()
        event_type = validate_webhook_data(data)
        
        logger.info(f"🔔 WEBHOOK RECEIVED - Event: {event_type}")

        # Handle conversation updates
        if event_type == "conversation_updated":
            success = handle_conversation_updated(data)
            status_code = 200 if success else 400
            return jsonify({"status": "conversation_updated_processed", "success": success}), status_code

        # Handle only message_created events
        if event_type != "message_created":
            logger.info(f"⏭️ Ignoring event type: {event_type}")
            return jsonify({"status": "ignored_event_type", "event": event_type}), 200

        # Process incoming message
        result = process_incoming_message(data)
        
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
def add_document():
    try:
        data = request.get_json()
        content, metadata = validate_document_data(data)
        
        # Generar doc_id
        doc_id = hashlib.md5(content.encode()).hexdigest()
        
        # Agregar doc_id a los metadatos
        metadata['doc_id'] = doc_id
        
        # Usar modern_rag_system
        num_chunks = modern_rag_system.add_documents([content], [metadata])
        
        # Crear clave del documento
        doc_key = f"document:{doc_id}"
        
        # Guardar en Redis
        doc_data = {
            'content': content,
            'metadata': json.dumps(metadata),
            'created_at': str(datetime.utcnow().isoformat()),
            'chunk_count': str(num_chunks)
        }
        
        redis_client.hset(doc_key, mapping=doc_data)
        redis_client.expire(doc_key, 604800)  # 7 días TTL
        
        # NUEVO: Registrar cambio en documento
        document_change_tracker.register_document_change(doc_id, 'added')
        
        logger.info(f"✅ Document {doc_id} added with {num_chunks} chunks")
        
        return create_success_response({
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
def list_documents():
    try:
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        # Obtener claves de documentos
        doc_pattern = "document:*"
        doc_keys = redis_client.keys(doc_pattern)
        
        # Obtener claves de vectores
        vector_pattern = "benova_documents:*"
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
                logger.warning(f"Error parsing vector {vector_key}: {e}")
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
                    doc_id = key.split(':')[1] if ':' in key else key
                    content = doc_data.get('content', '')
                    metadata = json.loads(doc_data.get('metadata', '{}'))
                    
                    # Obtener vectores de este documento
                    doc_vectors = vectors_by_doc.get(doc_id, [])
                    
                    documents.append({
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
                logger.warning(f"Error parsing document {key}: {e}")
                continue
        
        return create_success_response({
            "total_documents": len(doc_keys),
            "total_vectors": len(vector_keys),
            "page": page,
            "page_size": page_size,
            "documents": documents
        })
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return create_error_response("Failed to list documents", 500)

@app.route("/documents/search", methods=["POST"])
def search_documents():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return create_error_response("Query is required", 400)
        
        query = data['query'].strip()
        if not query:
            return create_error_response("Query cannot be empty", 400)
        
        k = min(data.get('k', MAX_RETRIEVED_DOCS), 20)  # Limit max results
        
        # CORREGIDO: Usar modern_rag_system
        docs = modern_rag_system.search_documents(query, k)
        
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": getattr(doc, 'metadata', {}),
                "score": getattr(doc, 'score', None)
            })
        
        return create_success_response({
            "query": query,
            "results_count": len(results),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return create_error_response("Failed to search documents", 500)

@app.route("/documents/bulk", methods=["POST"])
def bulk_add_documents():
    try:
        data = request.get_json()
        if not data or 'documents' not in data:
            return create_error_response("Documents array is required", 400)

        documents = data['documents']
        if not isinstance(documents, list) or not documents:
            return create_error_response("Documents must be a non-empty array", 400)

        added_docs = 0
        total_chunks = 0
        errors = []
        added_doc_ids = []  # NUEVO: Rastrear IDs agregados

        for i, doc_data in enumerate(documents):
            try:
                content, metadata = validate_document_data(doc_data)

                # Generar doc_id
                doc_id = hashlib.md5(content.encode()).hexdigest()
                metadata['doc_id'] = doc_id

                # Usar modern_rag_system
                num_chunks = modern_rag_system.add_documents([content], [metadata])
                total_chunks += num_chunks

                # Save to Redis
                doc_key = f"document:{doc_id}"
                doc_redis_data = {
                    'content': content,
                    'metadata': json.dumps(metadata),
                    'created_at': str(datetime.utcnow().isoformat()),
                    'chunk_count': str(num_chunks)
                }

                redis_client.hset(doc_key, mapping=doc_redis_data)
                redis_client.expire(doc_key, 604800)  # 7 days TTL

                added_docs += 1
                added_doc_ids.append(doc_id)  # NUEVO: Guardar ID

            except Exception as e:
                errors.append(f"Document {i}: {str(e)}")
                continue

        # NUEVO: Registrar cambios en batch
        for doc_id in added_doc_ids:
            document_change_tracker.register_document_change(doc_id, 'added')

        response_data = {
            "documents_added": added_docs,
            "total_chunks": total_chunks,
            "message": f"Added {added_docs} documents with {total_chunks} chunks"
        }

        if errors:
            response_data["errors"] = errors
            response_data["message"] += f". {len(errors)} documents failed."

        logger.info(f"✅ Bulk added {added_docs} documents with {total_chunks} chunks")

        return create_success_response(response_data, 201)

    except Exception as e:
        logger.error(f"Error bulk adding documents: {e}")
        return create_error_response("Failed to bulk add documents", 500)


@app.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    try:
        doc_key = f"document:{doc_id}"
        if not redis_client.exists(doc_key):
            return create_error_response("Document not found", 404)
        
        index_name = "benova_documents"
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
            logger.info(f"Removed {len(vectors_to_delete)} vectors for doc {doc_id}")
        
        # Eliminar documento y registrar cambio
        redis_client.delete(doc_key)
        document_change_tracker.register_document_change(doc_id, 'deleted')
        
        return create_success_response({"message": "Document deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return create_error_response("Failed to delete document", 500)

# ===============================
# CONVERSATION MANAGEMENT ENDPOINTS - CORREGIDOS
# ===============================

@app.route("/conversations", methods=["GET"])
def list_conversations():
    try:
        # CORREGIDO: Usar modern_conversation_manager
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        # Get conversation keys from Redis using modern pattern
        pattern = f"{modern_conversation_manager.redis_prefix}*"
        keys = redis_client.keys(pattern)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_keys = keys[start_idx:end_idx]
        
        conversations = []
        for key in paginated_keys:
            try:
                user_id = key.replace(modern_conversation_manager.redis_prefix, '')
                messages = modern_conversation_manager.get_chat_history(user_id)
                
                conversations.append({
                    "user_id": user_id,
                    "message_count": len(messages),
                    "last_updated": modern_conversation_manager.get_last_updated(user_id)
                })
            except Exception as e:
                logger.warning(f"Error parsing conversation {key}: {e}")
                continue
        
        return create_success_response({
            "total_conversations": len(keys),
            "page": page,
            "page_size": page_size,
            "conversations": conversations
        })
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return create_error_response("Failed to list conversations", 500)

@app.route("/conversations/<user_id>", methods=["GET"])
def get_conversation(user_id):
    try:
        # CORREGIDO: Usar modern_conversation_manager
        messages = modern_conversation_manager.get_chat_history(user_id)
        
        return create_success_response({
            "user_id": user_id,
            "message_count": len(messages),
            "messages": messages,
            "last_updated": modern_conversation_manager.get_last_updated(user_id)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return create_error_response("Failed to get conversation", 500)

@app.route("/conversations/<user_id>", methods=["DELETE"])
def delete_conversation(user_id):
    try:
        # CORREGIDO: Usar modern_conversation_manager
        modern_conversation_manager.clear_conversation(user_id)
        
        logger.info(f"✅ Conversation {user_id} deleted")
        
        return create_success_response({
            "message": f"Conversation {user_id} deleted"
        })
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return create_error_response("Failed to delete conversation", 500)

@app.route("/conversations/<user_id>/test", methods=["POST"])
def test_conversation(user_id):
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return create_error_response("Message is required", 400)
        
        message = data['message'].strip()
        if not message:
            return create_error_response("Message cannot be empty", 400)
        
        # Get bot response
        response = get_modern_chat_response_multiagent(user_id, message)
        
        return create_success_response({
            "user_id": user_id,
            "user_message": message,
            "bot_response": response,
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"Error testing conversation: {e}")
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
        # CORREGIDO: Usar modern_rag_system
        modern_rag_system.embeddings.embed_query("test")
        components["openai"] = "connected"
    except Exception as e:
        components["openai"] = f"error: {str(e)}"
    
    # Check vectorstore
    try:
        # CORREGIDO: Usar modern_rag_system
        modern_rag_system.vectorstore.similarity_search("test", k=1)
        components["vectorstore"] = "connected"
    except Exception as e:
        components["vectorstore"] = f"error: {str(e)}"
    
    return components

@app.route("/health", methods=["GET"])
def health_check():
    try:
        components = check_component_health()
        
        # CORREGIDO: Usar modern patterns
        conversation_count = len(redis_client.keys(f"{modern_conversation_manager.redis_prefix}*"))
        document_count = len(redis_client.keys("document:*"))
        bot_status_count = len(redis_client.keys("bot_status:*"))
        
        # Determine overall health
        healthy = all("error" not in str(status) for status in components.values())
        
        response_data = {
            "timestamp": time.time(),
            "components": {
                **components,
                "conversations": conversation_count,
                "documents": document_count,
                "bot_statuses": bot_status_count
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
        # CORREGIDO: Usar modern patterns
        conversation_count = len(redis_client.keys(f"{modern_conversation_manager.redis_prefix}*"))
        document_count = len(redis_client.keys("document:*"))
        bot_status_keys = redis_client.keys("bot_status:*")
        
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
        processed_message_count = len(redis_client.keys("processed_message:*"))
        
        return create_success_response({
            "timestamp": time.time(),
            "statistics": {
                "total_conversations": conversation_count,
                "active_bots": active_bots,
                "total_bot_statuses": len(bot_status_keys),
                "processed_messages": processed_message_count,
                "total_documents": document_count
            },
            "environment": {
                "chatwoot_url": CHATWOOT_BASE_URL,
                "account_id": ACCOUNT_ID,
                "model": MODEL_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "redis_url": REDIS_URL
            }
        })
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return create_error_response("Failed to get status", 500)

@app.route("/reset", methods=["POST"])
def reset_system():
    try:
        # CORREGIDO: Usar modern_conversation_manager
        # Clear Redis caches
        patterns = ["processed_message:*", "bot_status:*"]
        for pattern in patterns:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        
        # Clear all conversations using modern manager
        conversation_keys = redis_client.keys(f"{modern_conversation_manager.redis_prefix}*")
        for key in conversation_keys:
            user_id = key.replace(modern_conversation_manager.redis_prefix, '')
            modern_conversation_manager.clear_conversation(user_id)
        
        logger.info("✅ System reset completed")
        
        return create_success_response({
            "message": "System reset completed",
            "timestamp": time.time()
        })
        
    except Exception as e:
        logger.error(f"System reset failed: {e}")
        return create_error_response("Failed to reset system", 500)

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
        logger.info("🚀 Starting Benova Bot with Modern Architecture...")
        
        # Check Redis connection
        redis_client.ping()
        logger.info("✅ Redis connection verified")
        
        # Check OpenAI connection
        modern_rag_system.embeddings.embed_query("test startup")
        logger.info("✅ OpenAI connection verified")
        
        # Check vectorstore
        modern_rag_system.vectorstore.similarity_search("test", k=1)
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
        
        logger.info("🎉 Benova Bot startup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup check failed: {e}")
        raise

def cleanup():
    """Clean up resources on shutdown"""
    try:
        logger.info("🧹 Cleaning up resources...")
        
        # Clear in-memory data using modern manager
        # modern_conversation_manager handles its own cleanup
        
        logger.info("💾 All resources cleaned up")
        logger.info("👋 Benova Bot shutdown completed")
        
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
