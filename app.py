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

# LangChain imports
from langchain.schema import Document as LangChainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_redis import RedisVectorStore

# Otras importaciones
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
# Company Configuration
# ===============================
class CompanyConfig:
    """Configuración específica por empresa"""
    
    def __init__(self, company_id, redis_prefix, vectorstore_index, 
                 schedule_service_url, sales_agent_name, services):
        self.company_id = company_id
        self.redis_prefix = redis_prefix
        self.vectorstore_index = vectorstore_index
        self.schedule_service_url = schedule_service_url
        self.sales_agent_name = sales_agent_name
        self.services = services
    
    @classmethod
    def from_dict(cls, company_id, config_dict):
        return cls(
            company_id=company_id,
            redis_prefix=config_dict.get("redis_prefix", f"{company_id}:"),
            vectorstore_index=config_dict.get("vectorstore_index", f"{company_id}_documents"),
            schedule_service_url=config_dict.get("schedule_service_url"),
            sales_agent_name=config_dict.get("sales_agent_name", "Asistente"),
            services=config_dict.get("services", "servicios")
        )

# Configuración de empresas
COMPANIES_CONFIG = {
    "benova": {
        "redis_prefix": "benova:",
        "vectorstore_index": "benova_documents",
        "schedule_service_url": "http://benova-schedule-service:4040",
        "sales_agent_name": "María",
        "services": "tratamientos estéticos"
    },
    "empresa2": {
        "redis_prefix": "empresa2:",
        "vectorstore_index": "empresa2_documents",
        "schedule_service_url": "http://empresa2-schedule:4040",
        "sales_agent_name": "Asistente",
        "services": "servicios generales"
    }
}

def get_company_config(company_id):
    """Obtener configuración para una empresa específica"""
    if company_id not in COMPANIES_CONFIG:
        logger.warning(f"Company {company_id} not found in config, using default")
        return CompanyConfig.from_dict(company_id, {
            "redis_prefix": f"{company_id}:",
            "vectorstore_index": f"{company_id}_documents",
            "schedule_service_url": f"http://{company_id}-schedule-service:4040",
            "sales_agent_name": "Asistente",
            "services": "servicios"
        })
    
    return CompanyConfig.from_dict(company_id, COMPANIES_CONFIG[company_id])

def validate_openai_setup():
    """Validar que OpenAI está configurado correctamente"""
    try:
        import openai
        from openai import OpenAI
        
        # Verificar versión de OpenAI
        logger.info(f"🔍 OpenAI version: {openai.__version__}")
        
        # Verificar API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            return False
        
        logger.info(f"✅ OpenAI API key found (length: {len(api_key)})")
        
        # Test básico de conexión
        try:
            client = OpenAI(api_key=api_key)
            # Test simple con el modelo más barato
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            logger.info("✅ OpenAI connection test successful")
            return True
        except Exception as connection_error:
            logger.error(f"❌ OpenAI connection test failed: {connection_error}")
            return False
            
    except ImportError as e:
        logger.error(f"❌ OpenAI import error: {e}")
        return False

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

# Initialize Redis
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
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

# Initialize Redis Vector Store (se creará dinámicamente por empresa)
vectorstore = None  # Se inicializará por empresa



###### Chunking#############


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


def enhanced_add_documents_with_tracking(modern_rag_system, documents: List[str], metadatas: List[Dict] = None):
    """
    Versión mejorada de add_documents que garantiza consistencia
    """
    if not documents:
        return 0
    
    try:
        all_texts = []
        all_metas = []
        doc_ids_created = []
        
        for i, doc in enumerate(documents):
            if doc and doc.strip():
                # Generar doc_id consistente
                doc_id = hashlib.md5(doc.encode()).hexdigest()
                doc_ids_created.append(doc_id)
                
                # Usar sistema de chunking avanzado
                texts, auto_metadatas = advanced_chunk_processing(doc)
                
                # Combinar metadata
                base_metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                
                for j, (text, auto_meta) in enumerate(zip(texts, auto_metadatas)):
                    if text.strip():
                        all_texts.append(text)
                        # IMPORTANTE: Asegurar que doc_id esté en metadata
                        combined_meta = base_metadata.copy()
                        combined_meta.update(auto_meta)
                        combined_meta.update({
                            "doc_id": doc_id,  # ✅ GARANTIZAR doc_id en metadata
                            "chunk_index": j, 
                            "doc_index": i
                        })
                        all_metas.append(combined_meta)
        
        # Agregar al vectorstore con metadata mejorada
        if all_texts:
            modern_rag_system.vectorstore.add_texts(all_texts, metadatas=all_metas)
            logger.info(f"✅ Added {len(all_texts)} chunks with consistent doc_id tracking")
        
        return len(all_texts)
        
    except Exception as e:
        logger.error(f"Error in enhanced add_documents: {e}")
        return 0


# ===============================
# BOT ACTIVATION LOGIC
# ===============================

BOT_ACTIVE_STATUSES = ["open"]
BOT_INACTIVE_STATUSES = ["pending", "resolved", "snoozed"]

status_lock = threading.Lock()

def update_bot_status(conversation_id, conversation_status, company_config):
    """Update bot status for a specific conversation in Redis with company prefix"""
    with status_lock:
        is_active = conversation_status in BOT_ACTIVE_STATUSES
        
        # Store in Redis with company prefix
        status_key = f"{company_config.redis_prefix}bot_status:{conversation_id}"
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
                logger.info(f"🔄 Conversation {conversation_id}: Bot {status_text} (status: {conversation_status})")
                
        except Exception as e:
            logger.error(f"Error updating bot status in Redis: {e}")

def should_bot_respond(conversation_id, conversation_status, company_config):
    """Determine if bot should respond based on conversation status"""
    update_bot_status(conversation_id, conversation_status, company_config)
    is_active = conversation_status in BOT_ACTIVE_STATUSES
    
    if is_active:
        logger.info(f"✅ Bot WILL respond to conversation {conversation_id} (status: {conversation_status})")
    else:
        if conversation_status == "pending":
            logger.info(f"⏸️ Bot will NOT respond to conversation {conversation_id} (status: pending - INACTIVE)")
        else:
            logger.info(f"🚫 Bot will NOT respond to conversation {conversation_id} (status: {conversation_status})")
    
    return is_active

def is_message_already_processed(message_id, conversation_id, company_config):
    """Check if message has already been processed using Redis with company prefix"""
    if not message_id:
        return False
    
    key = f"{company_config.redis_prefix}processed_message:{conversation_id}:{message_id}"
    
    try:
        if redis_client.exists(key):
            logger.info(f"🔄 Message {message_id} already processed, skipping")
            return True
        
        redis_client.set(key, "1", ex=3600)  # 1 hour TTL
        logger.info(f"✅ Message {message_id} marked as processed")
        return False
        
    except Exception as e:
        logger.error(f"Error checking processed message in Redis: {e}")
        return False

# ===============================
# Modern Conversation Manager
# ===============================
class ModernConversationManager:
    """
    Conversation Manager moderno con soporte para múltiples empresas
    """
    
    def __init__(self, redis_client, max_messages: int = 10, company_config: CompanyConfig = None):
        self.redis_client = redis_client
        self.max_messages = max_messages
        self.company_config = company_config or get_company_config("default")
        self.redis_prefix = self.company_config.redis_prefix
        self.conversations = {}
        self.message_histories = {}
        self.load_conversations_from_redis()
    
    def _get_conversation_key(self, user_id: str) -> str:
        """Generate standardized conversation key with company prefix"""
        return f"{self.redis_prefix}conversation:{user_id}"
    
    def _get_message_history_key(self, user_id: str) -> str:
        """Generate standardized message history key for Redis with company prefix"""
        return f"{self.redis_prefix}chat_history:{user_id}"
    
    def _create_user_id(self, contact_id: str) -> str:
        """Generate standardized user ID"""
        if not contact_id.startswith("chatwoot_contact_"):
            return f"chatwoot_contact_{contact_id}"
        return contact_id
    
    def _get_redis_connection_params(self) -> Dict[str, Any]:
        """
        Extract Redis connection parameters from client
        """
        try:
            if hasattr(self.redis_client, 'connection_pool'):
                pool = self.redis_client.connection_pool
                connection_kwargs = pool.connection_kwargs
                
                return {
                    "url": REDIS_URL,
                    "ttl": 604800  # 7 días
                }
            
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
    
    def _get_or_create_redis_history(self, user_id: str) -> BaseChatMessageHistory:
        """
        Método interno para crear/obtener RedisChatMessageHistory
        """
        if not user_id:
            raise ValueError("user_id cannot be empty")
        
        if user_id not in self.message_histories:
            try:
                redis_params = self._get_redis_connection_params()
                
                self.message_histories[user_id] = RedisChatMessageHistory(
                    session_id=user_id,
                    url=redis_params["url"],
                    key_prefix=f"{self.redis_prefix}chat_history:",
                    ttl=redis_params["ttl"]
                )
                
                logger.info(f"✅ Created Redis message history for user {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Error creating Redis message history for user {user_id}: {e}")
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self.message_histories[user_id] = InMemoryChatMessageHistory()
                logger.warning(f"⚠️ Using in-memory fallback for user {user_id}")
            
            self._apply_message_window(user_id)
        
        return self.message_histories[user_id]
    
    def get_chat_history(self, user_id: str, format_type: str = "dict") -> Any:
        """
        Método unificado para obtener chat history en diferentes formatos
        """
        if not user_id:
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
            redis_history = self._get_or_create_redis_history(user_id)
            
            if format_type == "langchain":
                return redis_history
            
            elif format_type == "messages":
                return redis_history.messages
            
            elif format_type == "dict":
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
                return self.get_chat_history(user_id, "dict")
                
        except Exception as e:
            logger.error(f"Error getting chat history for user {user_id}: {e}")
            if format_type == "dict":
                return []
            elif format_type == "langchain":
                from langchain_core.chat_history import InMemoryChatMessageHistory
                return InMemoryChatMessageHistory()
            elif format_type == "messages":
                return []
            else:
                return []
    
    def _apply_message_window(self, user_id: str):
        """
        Aplica ventana deslizante de mensajes para mantener solo los últimos N mensajes
        """
        try:
            history = self.message_histories[user_id]
            messages = history.messages
            
            if len(messages) > self.max_messages:
                messages_to_keep = messages[-self.max_messages:]
                
                history.clear()
                
                for message in messages_to_keep:
                    history.add_message(message)
                
                logger.info(f"✅ Applied message window for user {user_id}: kept {len(messages_to_keep)} messages")
        
        except Exception as e:
            logger.error(f"❌ Error applying message window for user {user_id}: {e}")
    
    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """
        Add message with automatic window management
        """
        if not user_id or not content.strip():
            logger.warning("Invalid user_id or content for message")
            return False
        
        try:
            history = self.get_chat_history(user_id, format_type="langchain")
            
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            else:
                logger.warning(f"Unknown role: {role}")
                return False
            
            if user_id in self.message_histories:
                self._apply_message_window(user_id)
            
            self._update_conversation_metadata(user_id)
            
            logger.info(f"✅ Message added for user {user_id} (role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding message for user {user_id}: {e}")
            return False
    
    def _update_conversation_metadata(self, user_id: str):
        """Update conversation metadata in Redis"""
        try:
            conversation_key = self._get_conversation_key(user_id)
            metadata = {
                'last_updated': str(time.time()),
                'user_id': user_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)  # 7 días TTL
            
        except Exception as e:
            logger.error(f"Error updating metadata for user {user_id}: {e}")
    
    def load_conversations_from_redis(self):
        """
        Load conversations from Redis with modern approach
        """
        try:
            conversation_keys = self.redis_client.keys(f"{self.redis_prefix}conversation:*")
            chat_history_keys = self.redis_client.keys(f"{self.redis_prefix}chat_history:*")
            
            loaded_count = 0
            
            for key in conversation_keys:
                try:
                    user_id = key.split(':', 1)[1]
                    context_data = self.redis_client.hgetall(key)
                    
                    if context_data and 'messages' in context_data:
                        old_messages = json.loads(context_data['messages'])
                        history = self.get_chat_history(user_id, format_type="langchain")
                        
                        if len(history.messages) == 0 and old_messages:
                            for msg in old_messages:
                                if msg.get('role') == 'user':
                                    history.add_user_message(msg['content'])
                                elif msg.get('role') == 'assistant':
                                    history.add_ai_message(msg['content'])
                            
                            self._apply_message_window(user_id)
                            loaded_count += 1
                            logger.info(f"✅ Migrated conversation for user {user_id}")
                
                except Exception as e:
                    logger.warning(f"Failed to migrate conversation {key}: {e}")
                    continue
            
            for key in chat_history_keys:
                if key not in [self._get_message_history_key(k.split(':', 1)[1]) for k in conversation_keys]:
                    loaded_count += 1
            
            logger.info(f"✅ Loaded {loaded_count} conversation contexts from Redis")
            
        except Exception as e:
            logger.error(f"❌ Error loading contexts from Redis: {e}")
    
    def get_message_count(self, user_id: str) -> int:
        """Get total message count for a user"""
        try:
            history = self.get_chat_history(user_id, format_type="langchain")
            return len(history.messages)
        except Exception as e:
            logger.error(f"Error getting message count for user {user_id}: {e}")
            return 0
    
    def clear_conversation(self, user_id: str) -> bool:
        """Clear conversation history for a user"""
        try:
            history = self.get_chat_history(user_id, format_type="langchain")
            history.clear()
            
            conversation_key = self._get_conversation_key(user_id)
            self.redis_client.delete(conversation_key)
            
            if user_id in self.message_histories:
                del self.message_histories[user_id]
            
            logger.info(f"✅ Cleared conversation for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing conversation for user {user_id}: {e}")
            return False

#########################4######################

####  GESTION DE VECTORES################

# ===============================
# Vector Store Manager
# ===============================
class VectorStoreManager:
    """
    Clase para gestionar vectores de manera consistente con soporte multi-empresa
    """
    
    def __init__(self, redis_client, company_config: CompanyConfig):
        self.redis_client = redis_client
        self.company_config = company_config
        self.index_name = company_config.vectorstore_index
    
    def find_vectors_by_doc_id(self, doc_id: str) -> List[str]:
        """
        Encuentra todos los vectores asociados a un documento
        Busca tanto en campos directos como en metadata JSON
        """
        pattern = f"{self.index_name}:*"
        keys = self.redis_client.keys(pattern)
        vectors_to_delete = []
        
        for key in keys:
            try:
                # Método 1: Buscar en campo directo 'doc_id'
                doc_id_direct = self.redis_client.hget(key, 'doc_id')
                if doc_id_direct == doc_id:
                    vectors_to_delete.append(key)
                    continue
                
                # Método 2: Buscar en metadata JSON con filtro por company_id
                metadata_str = self.redis_client.hget(key, 'metadata')
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                        if metadata.get('doc_id') == doc_id and metadata.get('company_id') == self.company_config.company_id:
                            vectors_to_delete.append(key)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON metadata in vector {key}")
                        continue
                
            except Exception as e:
                logger.warning(f"Error checking vector {key}: {e}")
                continue
        
        return vectors_to_delete
    
    def delete_vectors_by_doc_id(self, doc_id: str) -> int:
        """
        Elimina todos los vectores asociados a un documento
        Retorna el número de vectores eliminados
        """
        vectors_to_delete = self.find_vectors_by_doc_id(doc_id)
        
        if vectors_to_delete:
            self.redis_client.delete(*vectors_to_delete)
            logger.info(f"✅ Deleted {len(vectors_to_delete)} vectors for doc {doc_id}")
        else:
            logger.warning(f"⚠️ No vectors found for doc {doc_id}")
        
        return len(vectors_to_delete)
    
    def verify_cleanup(self, doc_id: str) -> Dict[str, Any]:
        """
        Verifica que se haya limpiado correctamente un documento
        """
        remaining_vectors = self.find_vectors_by_doc_id(doc_id)
        doc_key = f"document:{doc_id}"
        doc_exists = self.redis_client.exists(doc_key)
        
        return {
            "doc_id": doc_id,
            "document_exists": bool(doc_exists),
            "remaining_vectors": len(remaining_vectors),
            "vector_keys": remaining_vectors[:5],
            "cleanup_complete": not doc_exists and len(remaining_vectors) == 0
        }

# ===============================
# multimedia system
# ===============================

def transcribe_audio(audio_path):
    """Transcribir audio a texto usando Whisper con sintaxis v1.x"""
    try:
        # Crear cliente con API key usando la nueva sintaxis
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        with open(audio_path, "rb") as audio_file:
            # Usar la nueva sintaxis v1.x para transcripción
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # En v1.x, transcript es un objeto, no string directo
        return transcript.text if hasattr(transcript, 'text') else str(transcript)
        
    except Exception as e:
        logger.error(f"Error in audio transcription: {e}")
        raise

def transcribe_audio_from_url(audio_url):
    """Transcribir audio desde URL usando Whisper con manejo mejorado de errores"""
    try:
        import requests
        import tempfile
        import os
        
        # Descargar el audio con headers más específicos
        logger.info(f"🔽 Downloading audio from: {audio_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ChatbotAudioTranscriber/1.0)',
            'Accept': 'audio/*,*/*;q=0.9'
        }
        
        response = requests.get(audio_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        # Verificar content-type si está disponible
        content_type = response.headers.get('content-type', '').lower()
        logger.info(f"📄 Audio content-type: {content_type}")
        
        # Determinar extensión basada en content-type o URL
        extension = '.ogg'  # Default para Chatwoot
        if 'mp3' in content_type or audio_url.endswith('.mp3'):
            extension = '.mp3'
        elif 'wav' in content_type or audio_url.endswith('.wav'):
            extension = '.wav'
        elif 'm4a' in content_type or audio_url.endswith('.m4a'):
            extension = '.m4a'
        
        # Crear archivo temporal con extensión correcta
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        logger.info(f"📁 Audio saved to temp file: {temp_path} (size: {os.path.getsize(temp_path)} bytes)")
        
        try:
            # Transcribir usando la función corregida
            result = transcribe_audio(temp_path)
            logger.info(f"🎵 Transcription successful: {len(result)} characters")
            return result
            
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_path)
                logger.info(f"🗑️ Temporary file deleted: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Could not delete temp file {temp_path}: {cleanup_error}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error downloading audio: {e}")
        raise Exception(f"Error downloading audio: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error in audio transcription from URL: {e}")
        raise

def text_to_speech(text):
    """Convertir texto a audio usando TTS de OpenAI con sintaxis v1.x"""
    try:
        # Crear cliente con API key usando la nueva sintaxis
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Usar la nueva sintaxis v1.x para TTS
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        # Guardar audio temporalmente
        temp_path = "/tmp/response.mp3"
        response.stream_to_file(temp_path)
        
        return temp_path
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        raise

def analyze_image(image_file):
    """Analizar imagen usando GPT-4 Vision con manejo mejorado"""
    try:
        # Convertir imagen a base64
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Crear cliente con API key
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Usar la sintaxis v1.x correcta
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Describe esta imagen en detalle, enfocándote en elementos relevantes para una consulta de tratamientos estéticos o servicios médicos. Si es una promoción o anuncio, menciona los detalles principales."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"  # Agregado para mejor análisis
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1  # Más determinista para análisis
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error in image analysis: {e}")
        raise

# Función mejorada para manejo de attachments de Chatwoot
def process_chatwoot_attachment(attachment):
    """Procesar attachment de Chatwoot con validación mejorada"""
    try:
        logger.info(f"🔍 Processing Chatwoot attachment: {attachment}")
        
        # Extraer tipo de archivo con múltiples métodos
        attachment_type = None
        
        # Método 1: file_type (más común en Chatwoot)
        if attachment.get("file_type"):
            attachment_type = attachment["file_type"].lower()
            logger.info(f"📝 Type from 'file_type': {attachment_type}")
        
        # Método 2: extension
        elif attachment.get("extension"):
            ext = attachment["extension"].lower().lstrip('.')
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                attachment_type = "image"
            elif ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                attachment_type = "audio"
            logger.info(f"📝 Type inferred from extension '{ext}': {attachment_type}")
        
        # Extraer URL con prioridad correcta
        url = attachment.get("data_url") or attachment.get("url") or attachment.get("thumb_url")
        
        if not url:
            logger.warning(f"⚠️ No URL found in attachment")
            return None
        
        # Validar que la URL es accesible
        if not url.startswith("http"):
            logger.warning(f"⚠️ Invalid URL format: {url}")
            return None
        
        return {
            "type": attachment_type,
            "url": url,
            "file_size": attachment.get("file_size", 0),
            "width": attachment.get("width"),
            "height": attachment.get("height"),
            "original_data": attachment
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing Chatwoot attachment: {e}")
        return None

#######3#######
# ===============================
# NUEVO: Sistema de Invalidación de Cache
# UBICACIÓN: Agregar después de la clase ModernConversationManager
# ===============================

class DocumentChangeTracker:
    """
    Sistema para rastrear cambios en documentos y invalidar cache
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.version_key = "vectorstore_version"
        self.doc_hash_key = "document_hashes"
    
    def get_current_version(self) -> int:
        """Obtener versión actual del vectorstore"""
        try:
            version = self.redis_client.get(self.version_key)
            return int(version) if version else 0
        except:
            return 0
    
    def increment_version(self):
        """Incrementar versión del vectorstore"""
        try:
            self.redis_client.incr(self.version_key)
            logger.info(f"Vectorstore version incremented to {self.get_current_version()}")
        except Exception as e:
            logger.error(f"Error incrementing version: {e}")
    
    def register_document_change(self, doc_id: str, change_type: str):
        """
        Registrar cambio en documento
        change_type: 'added', 'updated', 'deleted'
        """
        try:
            change_data = {
                'doc_id': doc_id,
                'change_type': change_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Registrar cambio
            change_key = f"doc_change:{doc_id}:{int(time.time())}"
            self.redis_client.setex(change_key, 3600, json.dumps(change_data))  # 1 hour TTL
            
            # Incrementar versión global
            self.increment_version()
            
            logger.info(f"Document change registered: {doc_id} - {change_type}")
            
        except Exception as e:
            logger.error(f"Error registering document change: {e}")
    
    def should_invalidate_cache(self, last_version: int) -> bool:
        """Determinar si se debe invalidar cache"""
        current_version = self.get_current_version()
        return current_version > last_version

# Instanciar el tracker
document_change_tracker = DocumentChangeTracker(redis_client)

# ===============================
# Multi-Agent System
# ===============================
class MultiAgentSystem:
    """
    Sistema multi-agente para múltiples empresas
    """
    
    def __init__(self, chat_model, vectorstore, conversation_manager, company_config):
        self.chat_model = chat_model
        self.vectorstore = vectorstore
        self.conversation_manager = conversation_manager
        self.company_config = company_config
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        self.voice_enabled = os.getenv("VOICE_ENABLED", "false").lower() == "true"
        self.image_enabled = os.getenv("IMAGE_ENABLED", "false").lower() == "true"
        
        # URL del microservicio de schedule
        self.schedule_service_url = company_config.schedule_service_url
        
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
        
        # Inicializar conexión con microservicio
        self._initialize_service_connection()
    
    def _verify_selenium_service(self, force_check: bool = False) -> bool:
        """
        Verificar disponibilidad del servicio Selenium local con cache inteligente
        """
        import time
        
        current_time = time.time()
        
        if not force_check and (current_time - self.selenium_status_last_check) < self.selenium_status_cache_duration:
            return self.selenium_service_available
        
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
    
    def _initialize_service_connection(self):
        """Inicializar y verificar conexión con microservicio"""
        try:
            logger.info(f"Intentando conectar con microservicio en: {self.schedule_service_url}")
            
            is_available = self._verify_selenium_service(force_check=True)
            
            if is_available:
                logger.info("✅ Conexión exitosa con microservicio")
            else:
                logger.warning("⚠️ Servicio no disponible")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando conexión: {e}")
            self.selenium_service_available = False
    
    def _create_router_agent(self):
        """
        Agente Router: Clasifica la intención del usuario
        """
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un clasificador de intenciones para {self.company_config.company_id}.

ANALIZA el mensaje del usuario y clasifica la intención en UNA de estas categorías:

1. **EMERGENCY** - Urgencias médicas:
   - Palabras clave: "dolor intenso", "sangrado", "emergencia", "reacción alérgica", "inflamación severa"
   - Síntomas post-tratamiento graves
   - Cualquier situación que requiera atención médica inmediata

2. **SALES** - Consultas comerciales:
   - Información sobre {self.company_config.services}
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

Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
        
        return router_prompt | self.chat_model | StrOutputParser()
    
    def _create_emergency_agent(self):
        """
        Agente de Emergencias: Maneja urgencias médicas
        """
        emergency_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, especialista en emergencias médicas de {self.company_config.company_id}.

SITUACIÓN DETECTADA: Posible emergencia médica.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma
3. Indica que el caso será escalado de emergencia
4. Proporciona información de contacto directo si es necesario

TONO: Profesional, empático, tranquilizador pero urgente.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        return emergency_prompt | self.chat_model | StrOutputParser()
    
    def _create_sales_agent(self):
        """
        Agente de Ventas: Especializado en información comercial
        """
        sales_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, asesora comercial especializada de {self.company_config.company_id}.

OBJETIVO: Proporcionar información comercial precisa y persuasiva.

INFORMACIÓN DISPONIBLE:
{{context}}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del {self.company_config.services} solicitado
3. Beneficios principales (máximo 3)
4. Inversión (si disponible)
5. Llamada a la acción para agendar

TONO: Cálido, profesional, persuasivo.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 5 oraciones.

FINALIZA SIEMPRE con: "¿Te gustaría agendar tu cita? 📅"

Historial de conversación:
{{chat_history}}

Pregunta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_sales_context(inputs):
            """Obtener contexto RAG para ventas"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de {self.company_config.company_id}:
- Centro especializado en {self.company_config.services}
- Atención personalizada
- Profesionales certificados
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"Error retrieving sales context: {e}")
                return "Información básica disponible. Te conectaré con un especialista para detalles específicos."
        
        return (
            {
                "context": get_sales_context,
                "question": lambda x: x.get("question", ""),
                "chat_history": lambda x: x.get("chat_history", [])
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
            ("system", f"""Eres {self.company_config.sales_agent_name}, especialista en soporte al cliente de {self.company_config.company_id}.

OBJETIVO: Resolver consultas generales y facilitar navegación.

TIPOS DE CONSULTA:
- Información del centro (ubicación, horarios)
- Procesos y políticas
- Escalación a especialistas
- Consultas generales

INFORMACIÓN DISPONIBLE:
{{context}}

PROTOCOLO:
1. Respuesta directa a la consulta
2. Información adicional relevante
3. Opciones de seguimiento

TONO: Profesional, servicial, eficiente.
LONGITUD: Máximo 4 oraciones.
EMOJIS: Máximo 3 por respuesta.

Si no puedes resolver completamente: "Te conectaré con un especialista para resolver tu consulta específica. 👩‍⚕️"

Historial de conversación:
{{chat_history}}

Consulta del usuario: {{question}}"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_support_context(inputs):
            """Obtener contexto RAG para soporte"""
            try:
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información general de {self.company_config.company_id}:
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
                "chat_history": lambda x: x.get("chat_history", [])
            }
            | support_prompt
            | self.chat_model
            | StrOutputParser()
        )
    
    def _create_availability_agent(self):
        """Agente que verifica disponibilidad"""
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un agente de disponibilidad de {self.company_config.company_id}.
    
    ESTADO DEL SISTEMA:
    {{selenium_status}}
    
    PROTOCOLO:
    1. Verificar estado del servicio Selenium
    2. Extraer la fecha (DD-MM-YYYY) y el tratamiento del mensaje
    3. Consultar el RAG para obtener la duración del tratamiento (en minutos)
    4. Llamar al endpoint /check-availability con la fecha
    5. Filtrar los slots disponibles que puedan acomodar la duración
    6. Devolver los horarios en formato legible
    
    Ejemplo de respuesta:
    "Horarios disponibles para {{fecha}} (tratamiento de {{duracion}} min):
    - 09:00 - 10:00
    - 10:30 - 11:30
    - 14:00 - 15:00"
    
    Si no hay disponibilidad: "No hay horarios disponibles para {{fecha}} con duración de {{duracion}} minutos."
    Si hay error del sistema: "Error consultando disponibilidad. Te conectaré con un especialista."
    
    Mensaje del usuario: {{question}}"""),
            ("human", "{question}")
        ])
        
        def get_availability_selenium_status(inputs):
            """Obtener estado del sistema Selenium para availability"""
            is_available = self._verify_selenium_service()
            
            if is_available:
                return f"✅ Sistema de disponibilidad ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ Sistema de disponibilidad NO DISPONIBLE (Verificar conexión: {self.schedule_service_url})"
        
        def process_availability(inputs):
            """Procesar consulta de disponibilidad"""
            try:
                question = inputs.get("question", "")
                chat_history = inputs.get("chat_history", [])
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"=== AVAILABILITY AGENT - PROCESANDO ===")
                logger.info(f"Pregunta: {question}")
                logger.info(f"Estado Selenium: {selenium_status}")
                
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
                duration = self._get_treatment_duration(treatment)
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
                "chat_history": lambda x: x.get("chat_history", [])
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
    
    def _get_treatment_duration(self, treatment):
        """Obtener duración del tratamiento desde RAG o configuración por defecto"""
        try:
            # Consultar RAG para obtener duración específica
            docs = self.retriever.invoke(f"duración tiempo {treatment}")
            
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
        """Llamar al endpoint de disponibilidad"""
        try:
            # 1. VERIFICAR ESTADO DEL SERVICIO PRIMERO
            if not self._verify_selenium_service():
                logger.warning("Servicio Selenium no disponible para availability check")
                return None
            
            logger.info(f"Consultando disponibilidad en: {self.schedule_service_url}/check-availability para fecha: {date}")
            
            # 2. USAR LA MISMA CONFIGURACIÓN QUE SCHEDULE_AGENT
            response = requests.post(
                f"{self.schedule_service_url}/check-availability",
                json={"date": date},
                headers={"Content-Type": "application/json"},
                timeout=self.selenium_timeout
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

    def _create_enhanced_schedule_agent(self):
        """Agente de Schedule mejorado con integración de disponibilidad"""
        schedule_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres {self.company_config.sales_agent_name}, especialista en gestión de citas de {self.company_config.company_id}.
    
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
    EMOJIS: Máximo 3 por respuesta.
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
                question = inputs.get("question", "")
                self._log_retriever_usage(question, [])
                
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de agenda {self.company_config.company_id}:
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
                        availability_response = self.availability_agent.invoke({"question": question,})
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
                "user_id": lambda x: x.get("user_id", "default_user")
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
    
    def get_response(self, question: str, user_id: str, media_type: str = "text", media_context: str = None) -> Tuple[str, str]:
        """
        Método principal para obtener respuesta del sistema multi-agente
        """
        # Procesar según el tipo de multimedia
        if media_type == "image" and media_context:
            processed_question = f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            processed_question = f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        else:
            processed_question = question
    
        # Validaciones
        if not processed_question or not processed_question.strip():
            return "Por favor, envía un mensaje específico para poder ayudarte. 😊", "support"
        
        if not user_id or not user_id.strip():
            return "Error interno: ID de usuario inválido.", "error"
        
        try:
            # Obtener historial de conversación
            chat_history = self.conversation_manager.get_chat_history(user_id, format_type="messages")
            
            # Preparar inputs usando la pregunta procesada
            inputs = {
                "question": processed_question.strip(), 
                "chat_history": chat_history,
                "user_id": user_id
            }
            
            # Determinar si la consulta podría necesitar RAG (pre-check)
            might_need_rag = self._might_need_rag(processed_question)
            
            # Log inicial de la consulta
            logger.info(f"🔍 CONSULTA INICIADA - Company: {self.company_config.company_id}, User: {user_id}, Pregunta: {processed_question[:100]}...")
            if might_need_rag:
                logger.info("   → Posible consulta RAG detectada")
            
            # Obtener respuesta del orquestador
            response = self.orchestrator.invoke(inputs)
            
            # Log de la respuesta
            logger.info(f"🤖 RESPUESTA GENERADA - Agente: {self._determine_agent_used(response)}")
            logger.info(f"   → Longitud respuesta: {len(response)} caracteres")
            
            # Agregar mensaje del usuario al historial (usando processed_question)
            self.conversation_manager.add_message(user_id, "user", processed_question)
            
            # Agregar respuesta del asistente al historial
            self.conversation_manager.add_message(user_id, "assistant", response)
            
            # Determinar qué agente se utilizó (para logging)
            agent_used = self._determine_agent_used(response)
            
            logger.info(f"Multi-agent response generated for user {user_id} using {agent_used}")
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"Error en sistema multi-agente (Company: {self.company_config.company_id}, User: {user_id})")
            return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", "error"
    
    def _might_need_rag(self, question: str) -> bool:
        """Determina si una consulta podría necesitar RAG basado en keywords"""
        rag_keywords = [
            "precio", "costo", "inversión", "duración", "tiempo", 
            "tratamiento", "procedimiento", "servicio", "beneficio",
            "horario", "disponibilidad", "agendar", "cita", "información"
        ]
        return any(keyword in question.lower() for keyword in rag_keywords)
    
    def _log_retriever_usage(self, question: str, docs: List) -> None:
        """Log detallado del uso del retriever"""
        if not docs:
            logger.info("   → RAG: No se recuperaron documentos")
            return
        
        logger.info(f"   → RAG: Recuperados {len(docs)} documentos")
        logger.info(f"   → Pregunta: {question[:50]}...")
        
        for i, doc in enumerate(docs[:3]):  # Limitar a 3 para no saturar logs
            content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
            metadata = getattr(doc, 'metadata', {})
            score = getattr(doc, 'score', None)
            
            logger.info(f"   → Doc {i+1}:")
            logger.info(f"      - Contenido: {content_preview}")
            if metadata:
                logger.info(f"      - Metadata: {dict(list(metadata.items())[:3])}...")  # Limitar metadata
            if score is not None:
                logger.info(f"      - Score: {score:.4f}")
    
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
        Verificar salud del sistema multi-agente y microservicio
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
        self._initialize_service_connection()
        return self.selenium_service_available

# Función de utilidad para inicializar el sistema
def create_enhanced_multiagent_system(chat_model, vectorstore, conversation_manager):
    """
    Crear instancia del sistema multi-agente mejorado con conexión local
    """
    return BenovaMultiAgentSystem(chat_model, vectorstore, conversation_manager)


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

def get_modern_chat_response_multiagent(user_id: str, user_message: str, media_type: str = "text", media_context: str = None) -> str:
    """
    Versión actualizada que usa sistema multi-agente con soporte para multimedia
    
    Args:
        user_id: Identificador único del usuario
        user_message: Mensaje de texto del usuario
        media_type: Tipo de medio ('text', 'voice', 'image')
        media_context: Contexto adicional del medio (transcripción o descripción)
    
    Returns:
        str: Respuesta del asistente
    """
    if not user_id or not user_id.strip():
        logger.error("Invalid user_id provided")
        return "Error interno: ID de usuario inválido."
    
    # Validar que al menos haya user_message o media_context
    if (not user_message or not user_message.strip()) and not media_context:
        logger.error("Empty or invalid message content and no media context")
        return "Por favor, envía un mensaje con contenido para poder ayudarte. 😊"
    
    try:
        # Usar sistema multi-agente global con soporte multimedia
        response, agent_used = modern_rag_system.multi_agent_system.get_response(
            question=user_message, 
            user_id=user_id, 
            media_type=media_type, 
            media_context=media_context
        )
        
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
# Webhook Handlers
# ===============================
def extract_company_id(data):
    """
    Extraer company_id del payload del webhook
    """
    # Intentar obtener desde custom_attributes
    conversation_data = data.get("conversation", {})
    custom_attributes = conversation_data.get("custom_attributes", {})
    company_id = custom_attributes.get("company_id")
    
    if company_id:
        return company_id
    
    # Intentar obtener desde inbox_id (mapeo preconfigurado)
    inbox_id = conversation_data.get("inbox_id")
    if inbox_id:
        # Mapeo de inbox_id a company_id (configurable)
        inbox_to_company = {
            "1": "benova",
            "2": "empresa2"
        }
        return inbox_to_company.get(str(inbox_id), "benova")  # Default a benova
    
    # Default a benova si no se encuentra
    return "benova"

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

def process_incoming_message(data):
    """Process incoming message with company-specific configuration"""
    try:
        # Extraer company_id
        company_id = extract_company_id(data)
        company_config = get_company_config(company_id)
        
        # Validar que la empresa existe
        if company_id not in COMPANIES_CONFIG and company_id != "default":
            logger.error(f"Company {company_id} not found in configuration")
            return {"status": "error", "message": "Company configuration not found"}
        
        # Validar message type
        message_type = data.get("message_type")
        if message_type != "incoming":
            logger.info(f"🤖 Ignoring message type: {message_type}")
            return {"status": "non_incoming_message", "ignored": True}

        # Extract and validate conversation data
        conversation_data = data.get("conversation", {})
        if not conversation_data:
            raise Exception("Missing conversation data")

        conversation_id = conversation_data.get("id")
        conversation_status = conversation_data.get("status")
        
        if not conversation_id:
            raise Exception("Missing conversation ID")

        # Validate conversation_id format
        if not str(conversation_id).strip() or not str(conversation_id).isdigit():
            raise Exception("Invalid conversation ID format")

        # Check if bot should respond
        if not should_bot_respond(conversation_id, conversation_status, company_config):
            return {
                "status": "bot_inactive",
                "message": f"Bot is inactive for status: {conversation_status}",
                "active_only_for": BOT_ACTIVE_STATUSES
            }

        # Extract and validate message content
        content = data.get("content", "").strip()
        message_id = data.get("id")

        # Check for duplicate processing
        if message_id and is_message_already_processed(message_id, conversation_id, company_config):
            return {"status": "already_processed", "ignored": True}

        # Extract contact information
        contact_id, extraction_method, is_valid = extract_contact_id(data)
        if not is_valid or not contact_id:
            raise Exception("Could not extract valid contact_id from webhook data")

        # Generate standardized user_id
        conversation_manager = ModernConversationManager(redis_client, company_config=company_config)
        user_id = conversation_manager._create_user_id(contact_id)

        logger.info(f"🔄 Processing message from company {company_id}, conversation {conversation_id}")
        logger.info(f"👤 User: {user_id} (contact: {contact_id}, method: {extraction_method})")
        logger.info(f"💬 Message: {content[:100]}...")

        # Crear vectorstore específico para la empresa
        vectorstore = RedisVectorStore(
            embeddings,
            redis_url=REDIS_URL,
            index_name=company_config.vectorstore_index,
            vector_dim=1536
        )
        
        # Crear sistema multi-agente para la empresa
        multi_agent_system = MultiAgentSystem(
            chat_model, 
            vectorstore, 
            conversation_manager,
            company_config
        )
        
        # Generar respuesta
        assistant_reply, agent_used = multi_agent_system.get_response(
            content, user_id, "text", None
        )
        
        if not assistant_reply or not assistant_reply.strip():
            assistant_reply = "Disculpa, no pude procesar tu mensaje. ¿Podrías intentar de nuevo? 😊"
        
        logger.info(f"🤖 Assistant response: {assistant_reply[:100]}...")

        # Send response to Chatwoot
        success = send_message_to_chatwoot(conversation_id, assistant_reply)

        if not success:
            raise Exception("Failed to send response to Chatwoot")

        logger.info(f"✅ Successfully processed message for conversation {conversation_id}")
        
        return {
            "status": "success",
            "message": "Response sent successfully",
            "company_id": company_id,
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
            "response_length": len(assistant_reply),
            "agent_used": agent_used
        }

    except Exception as e:
        logger.exception(f"💥 Error procesando mensaje (Company: {company_id})")
        return {"status": "error", "message": str(e)}

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
        
        # Extraer company_id para obtener la configuración correcta
        company_id = extract_company_id(data)
        company_config = get_company_config(company_id)
        
        logger.info(f"📋 Conversation {conversation_id} updated to status: {conversation_status}")
        update_bot_status(conversation_id, conversation_status, company_config)
        return True
        
    except Exception as e:
        logger.error(f"Error handling conversation_updated: {e}")
        return False

# ===============================
# FUNCIONES AUXILIARES MULTIMEDIA - NUEVAS
# ===============================

def analyze_image_from_url(image_url):
    """Analizar imagen desde URL usando GPT-4 Vision"""
    try:
        import requests
        from io import BytesIO
        
        # Descargar la imagen
        logger.info(f"🔽 Downloading image from: {image_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ChatbotImageAnalyzer/1.0)'
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Verificar que es una imagen
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
            logger.warning(f"⚠️ Content type might not be image: {content_type}")
        
        # Crear archivo en memoria
        image_file = BytesIO(response.content)
        
        # Analizar usando la función existente
        return analyze_image(image_file)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error downloading image: {e}")
        raise Exception(f"Error downloading image: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error in image analysis from URL: {e}")
        raise

def transcribe_audio_from_url(audio_url):
    """Transcribir audio desde URL usando Whisper"""
    try:
        import requests
        import tempfile
        import os
        
        # Descargar el audio
        logger.info(f"🔽 Downloading audio from: {audio_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ChatbotAudioTranscriber/1.0)'
        }
        response = requests.get(audio_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name
        
        try:
            # Transcribir usando la función existente
            result = transcribe_audio(temp_path)
            return result
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(temp_path)
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Could not delete temp file {temp_path}: {cleanup_error}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error downloading audio: {e}")
        raise Exception(f"Error downloading audio: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error in audio transcription from URL: {e}")
        raise

def debug_webhook_data(data):
    """Función para debugging completo del webhook de Chatwoot"""
    logger.info("🔍 === WEBHOOK DEBUG INFO ===")
    logger.info(f"Event: {data.get('event')}")
    logger.info(f"Message ID: {data.get('id')}")
    logger.info(f"Message Type: {data.get('message_type')}")
    logger.info(f"Content: '{data.get('content')}'")
    logger.info(f"Content Length: {len(data.get('content', ''))}")
    
    attachments = data.get('attachments', [])
    logger.info(f"Attachments Count: {len(attachments)}")
    
    for i, att in enumerate(attachments):
        logger.info(f"  Attachment {i}:")
        logger.info(f"    Keys: {list(att.keys())}")
        logger.info(f"    Type: {att.get('type')}")
        logger.info(f"    File Type: {att.get('file_type')}")
        logger.info(f"    URL: {att.get('url')}")
        logger.info(f"    Data URL: {att.get('data_url')}")
        logger.info(f"    Thumb URL: {att.get('thumb_url')}")
    
    logger.info("🔍 === END DEBUG INFO ===")



# ===============================
# Flask Endpoints
# ===============================
@app.route("/webhook", methods=["POST"])
def chatwoot_webhook():
    try:
        data = request.get_json()
        event_type = data.get("event")
        
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
        ##redis_client.expire(doc_key, 604800)  # 7 días TTL
        
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

################################################################################################
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
######################################################################################

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
                ####redis_client.expire(doc_key, 604800)  # 7 days TTL

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
    """
    Endpoint mejorado para eliminar documentos garantizando eliminación completa de vectores
    Mantiene compatibilidad con el código existente
    """
    try:
        doc_key = f"document:{doc_id}"
        if not redis_client.exists(doc_key):
            return create_error_response("Document not found", 404)
        
        index_name = "benova_documents"
        pattern = f"{index_name}:*"
        keys = redis_client.keys(pattern)
        
        vectors_to_delete = []
        vectors_found_direct = 0
        vectors_found_metadata = 0
        
        for key in keys:
            try:
                vector_found = False
                
                # MÉTODO 1: Verificar el campo 'doc_id' directamente en el hash (lógica original)
                doc_id_in_hash = redis_client.hget(key, 'doc_id')
                if doc_id_in_hash == doc_id:
                    vectors_to_delete.append(key)
                    vectors_found_direct += 1
                    vector_found = True
                    logger.debug(f"Found vector {key} via direct doc_id field")
                
                # MÉTODO 2: Si no se encontró, buscar en metadata JSON (mejora)
                if not vector_found:
                    metadata_str = redis_client.hget(key, 'metadata')
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                            if metadata.get('doc_id') == doc_id:
                                vectors_to_delete.append(key)
                                vectors_found_metadata += 1
                                vector_found = True
                                logger.debug(f"Found vector {key} via metadata doc_id")
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON metadata in vector {key}")
                            continue
                
            except Exception as e:
                logger.warning(f"Error checking vector {key}: {e}")
                continue
        
        # Eliminar vectores si se encontraron
        total_vectors_deleted = 0
        if vectors_to_delete:
            # Eliminar duplicados (por si acaso)
            unique_vectors = list(set(vectors_to_delete))
            redis_client.delete(*unique_vectors)
            total_vectors_deleted = len(unique_vectors)
            
            logger.info(f"✅ Removed {total_vectors_deleted} vectors for doc {doc_id}")
            logger.info(f"   - Found via direct field: {vectors_found_direct}")
            logger.info(f"   - Found via metadata: {vectors_found_metadata}")
        else:
            logger.warning(f"⚠️ No vectors found for doc {doc_id} - this might indicate an issue")
        
        # Eliminar documento y registrar cambio (lógica original intacta)
        redis_client.delete(doc_key)
        document_change_tracker.register_document_change(doc_id, 'deleted')
        
        # MEJORA: Verificación post-eliminación opcional
        verification_enabled = True  # Puedes hacer esto configurable
        cleanup_verification = None
        
        if verification_enabled:
            # Verificar que no quedaron vectores huérfanos
            remaining_vectors = []
            for key in redis_client.keys(pattern):
                try:
                    # Verificar método 1
                    doc_id_direct = redis_client.hget(key, 'doc_id')
                    if doc_id_direct == doc_id:
                        remaining_vectors.append(key)
                        continue
                    
                    # Verificar método 2
                    metadata_str = redis_client.hget(key, 'metadata')
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                            if metadata.get('doc_id') == doc_id:
                                remaining_vectors.append(key)
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    pass
            
            cleanup_verification = {
                "cleanup_complete": len(remaining_vectors) == 0,
                "remaining_vectors": len(remaining_vectors),
                "remaining_vector_keys": remaining_vectors[:3] if remaining_vectors else []
            }
            
            if remaining_vectors:
                logger.error(f"❌ CLEANUP INCOMPLETE: {len(remaining_vectors)} vectors still exist for deleted doc {doc_id}")
                # Intentar eliminar los vectores restantes
                try:
                    redis_client.delete(*remaining_vectors)
                    logger.info(f"🔧 Force-deleted {len(remaining_vectors)} remaining vectors")
                    cleanup_verification["force_cleanup_applied"] = True
                except Exception as cleanup_error:
                    logger.error(f"Failed to force-delete remaining vectors: {cleanup_error}")
                    cleanup_verification["force_cleanup_failed"] = True
        
        # Construir respuesta manteniendo compatibilidad
        response_data = {
            "message": "Document deleted successfully",
            "vectors_deleted": total_vectors_deleted,
            "vectors_breakdown": {
                "found_via_direct_field": vectors_found_direct,
                "found_via_metadata": vectors_found_metadata,
                "total": total_vectors_deleted
            }
        }
        
        # Agregar verificación solo si está habilitada y hay información relevante
        if cleanup_verification and (not cleanup_verification["cleanup_complete"] or total_vectors_deleted == 0):
            response_data["cleanup_verification"] = cleanup_verification
        
        logger.info(f"✅ Document {doc_id} deleted successfully with {total_vectors_deleted} vectors removed")
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"❌ Error deleting document {doc_id}: {e}")
        return create_error_response("Failed to delete document", 500)


@app.route("/documents/cleanup", methods=["POST"])
def cleanup_orphaned_vectors():
    """
    Nuevo endpoint para limpiar vectores huérfanos
    """
    try:
        data = request.get_json()
        dry_run = data.get('dry_run', True) if data else True
        
        # Obtener todos los documentos existentes
        doc_pattern = "document:*"
        doc_keys = redis_client.keys(doc_pattern)
        existing_doc_ids = set()
        
        for key in doc_keys:
            doc_id = key.split(':', 1)[1] if ':' in key else key
            existing_doc_ids.add(doc_id)
        
        # Obtener todos los vectores
        vector_pattern = f"{vector_manager.index_name}:*"
        vector_keys = redis_client.keys(vector_pattern)
        
        orphaned_vectors = []
        total_vectors = len(vector_keys)
        
        for vector_key in vector_keys:
            try:
                # Buscar doc_id en el vector
                doc_id = None
                
                # Método 1: Campo directo
                doc_id_direct = redis_client.hget(vector_key, 'doc_id')
                if doc_id_direct:
                    doc_id = doc_id_direct
                else:
                    # Método 2: Metadata JSON
                    metadata_str = redis_client.hget(vector_key, 'metadata')
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                            doc_id = metadata.get('doc_id')
                        except json.JSONDecodeError:
                            pass
                
                # Si el vector tiene doc_id pero el documento no existe
                if doc_id and doc_id not in existing_doc_ids:
                    orphaned_vectors.append({
                        "vector_key": vector_key,
                        "doc_id": doc_id
                    })
                    
            except Exception as e:
                logger.warning(f"Error checking vector {vector_key}: {e}")
                continue
        
        # Eliminar vectores huérfanos si no es dry_run
        deleted_count = 0
        if not dry_run and orphaned_vectors:
            keys_to_delete = [v["vector_key"] for v in orphaned_vectors]
            redis_client.delete(*keys_to_delete)
            deleted_count = len(keys_to_delete)
            logger.info(f"✅ Deleted {deleted_count} orphaned vectors")
        
        return create_success_response({
            "total_vectors": total_vectors,
            "total_documents": len(existing_doc_ids),
            "orphaned_vectors_found": len(orphaned_vectors),
            "orphaned_vectors_deleted": deleted_count,
            "dry_run": dry_run,
            "orphaned_samples": orphaned_vectors[:10]  # Muestra solo 10 ejemplos
        })
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return create_error_response("Failed to cleanup orphaned vectors", 500)

@app.route("/documents/<doc_id>/vectors", methods=["GET"])
def get_document_vectors(doc_id):
    """
    Nuevo endpoint para inspeccionar vectores de un documento específico
    """
    try:
        vectors = vector_manager.find_vectors_by_doc_id(doc_id)
        
        vector_details = []
        for vector_key in vectors:
            try:
                # Obtener metadata sin el embedding (para evitar datos binarios)
                metadata_str = redis_client.hget(vector_key, 'metadata')
                doc_id_direct = redis_client.hget(vector_key, 'doc_id')
                
                vector_info = {
                    "vector_key": vector_key,
                    "doc_id_direct": doc_id_direct,
                    "has_metadata": bool(metadata_str)
                }
                
                if metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                        # Filtrar campos problemáticos
                        safe_metadata = {k: v for k, v in metadata.items() 
                                       if k not in ['embedding', 'vector']}
                        vector_info["metadata"] = safe_metadata
                    except json.JSONDecodeError:
                        vector_info["metadata_error"] = "Invalid JSON"
                
                vector_details.append(vector_info)
                
            except Exception as e:
                logger.warning(f"Error getting details for vector {vector_key}: {e}")
                continue
        
        return create_success_response({
            "doc_id": doc_id,
            "vectors_found": len(vectors),
            "vectors": vector_details
        })
        
    except Exception as e:
        logger.error(f"Error getting vectors for doc {doc_id}: {e}")
        return create_error_response("Failed to get document vectors", 500)

@app.route("/documents/diagnostics", methods=["GET"])
def document_diagnostics():
    """
    Endpoint para diagnosticar el estado del vectorstore
    """
    try:
        # Contar documentos
        doc_pattern = "document:*"
        doc_keys = redis_client.keys(doc_pattern)
        total_docs = len(doc_keys)
        
        # Contar vectores
        vector_pattern = f"benova_documents:*"
        vector_keys = redis_client.keys(vector_pattern)
        total_vectors = len(vector_keys)
        
        # Analizar vectores por doc_id
        doc_id_counts = {}
        vectors_without_doc_id = 0
        
        for vector_key in vector_keys:
            try:
                doc_id = None
                
                # Buscar doc_id
                doc_id_direct = redis_client.hget(vector_key, 'doc_id')
                if doc_id_direct:
                    doc_id = doc_id_direct
                else:
                    metadata_str = redis_client.hget(vector_key, 'metadata')
                    if metadata_str:
                        try:
                            metadata = json.loads(metadata_str)
                            doc_id = metadata.get('doc_id')
                        except json.JSONDecodeError:
                            pass
                
                if doc_id:
                    doc_id_counts[doc_id] = doc_id_counts.get(doc_id, 0) + 1
                else:
                    vectors_without_doc_id += 1
                    
            except Exception as e:
                logger.warning(f"Error analyzing vector {vector_key}: {e}")
                continue
        
        # Identificar inconsistencias
        orphaned_docs = []
        for doc_key in doc_keys:
            doc_id = doc_key.split(':', 1)[1] if ':' in doc_key else doc_key
            if doc_id not in doc_id_counts:
                orphaned_docs.append(doc_id)
        
        return create_success_response({
            "total_documents": total_docs,
            "total_vectors": total_vectors,
            "vectors_without_doc_id": vectors_without_doc_id,
            "documents_with_vectors": len(doc_id_counts),
            "orphaned_documents": len(orphaned_docs),
            "avg_vectors_per_doc": round(sum(doc_id_counts.values()) / len(doc_id_counts), 2) if doc_id_counts else 0,
            "sample_doc_vector_counts": dict(list(doc_id_counts.items())[:10]),
            "orphaned_doc_samples": orphaned_docs[:5]
        })
        
    except Exception as e:
        logger.error(f"Error in diagnostics: {e}")
        return create_error_response("Failed to run diagnostics", 500)

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

#######1############
@app.route("/process-voice", methods=["POST"])
def process_voice_message():
    try:
        if 'audio' not in request.files:
            return create_error_response("No audio file provided", 400)
        
        audio_file = request.files['audio']
        user_id = request.form.get('user_id')
        conversation_id = request.form.get('conversation_id')
        
        # Guardar archivo temporalmente
        temp_path = f"/tmp/{audio_file.filename}"
        audio_file.save(temp_path)
        
        # Transcribir audio a texto usando Whisper
        transcript = transcribe_audio(temp_path)
        
        # Procesar con sistema multi-agente usando parámetros multimedia
        response = get_modern_chat_response_multiagent(
            user_id=user_id,
            user_message="",  # Mensaje textual vacío ya que todo viene del audio
            media_type="voice",
            media_context=transcript
        )
        
        # Convertir respuesta a audio si es necesario
        if request.form.get('return_audio', False):
            audio_response = text_to_speech(response)
            return send_file(audio_response, mimetype="audio/mpeg")
        
        return create_success_response({
            "transcript": transcript,
            "response": response
        })
        
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        return create_error_response("Failed to process voice message", 500)

@app.route("/process-image", methods=["POST"])
def process_image_message():
    try:
        if 'image' not in request.files:
            return create_error_response("No image file provided", 400)
        
        image_file = request.files['image']
        user_id = request.form.get('user_id')
        question = request.form.get('question', "").strip()
        
        # Analizar imagen con GPT-4V
        image_description = analyze_image(image_file)
        
        # Procesar con sistema multi-agente usando parámetros multimedia
        response = get_modern_chat_response_multiagent(
            user_id=user_id,
            user_message=question,  # Pregunta textual (puede estar vacía)
            media_type="image",
            media_context=image_description
        )
        
        return create_success_response({
            "image_description": image_description,
            "response": response
        })
        
    except Exception as e:
        logger.error(f"Error processing image message: {e}")
        return create_error_response("Failed to process image message", 500)

###########1###############################################

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

# ===============================
# Health Check Endpoint
# ===============================
@app.route("/health", methods=["GET"])
def health_check():
    try:
        # Check Redis
        redis_client.ping()
        
        # Check OpenAI
        embeddings.embed_query("test")
        
        # Información de empresas configuradas
        companies_info = {}
        for company_id, config in COMPANIES_CONFIG.items():
            companies_info[company_id] = {
                "vectorstore_index": config["vectorstore_index"],
                "redis_prefix": config["redis_prefix"],
                "configured": True
            }
        
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "companies": companies_info,
            "environment": os.getenv('ENVIRONMENT', 'production')
        }), 200
        
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

# ===============================
# Main Execution
# ===============================
if __name__ == "__main__":
    try:
        # Run startup checks
        logger.info("🚀 Starting Multi-Company Bot Server...")
        
        # Check Redis connection
        redis_client.ping()
        logger.info("✅ Redis connection verified")
        
        # Check OpenAI connection
        embeddings.embed_query("test startup")
        logger.info("✅ OpenAI connection verified")
        
        # Display configuration
        logger.info("📋 Configuration:")
        logger.info(f"   Model: {MODEL_NAME}")
        logger.info(f"   Embedding Model: {EMBEDDING_MODEL}")
        logger.info(f"   Companies: {list(COMPANIES_CONFIG.keys())}")
        
        # Start server
        logger.info(f"🌐 Starting server on port {PORT}")
        app.run(
            host="0.0.0.0",
            port=PORT,
            debug=os.getenv("ENVIRONMENT") != "production",
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)
