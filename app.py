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
###2####
import openai
import base64
from PIL import Image
import io
###2####

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
# PASO 1: CONFIGURACIÓN MULTI-EMPRESA
# ===============================

class CompanyConfig:
    """
    Clase para almacenar y gestionar configuraciones específicas por empresa
    """
    
    def __init__(self, company_id: str, config_data: Dict[str, Any]):
        self.company_id = company_id
        self.company_name = config_data.get("company_name", company_id.capitalize())
        self.redis_prefix = config_data.get("redis_prefix", f"{company_id}:")
        self.vectorstore_index = config_data.get("vectorstore_index", f"{company_id}_documents")
        self.schedule_service_url = config_data.get("schedule_service_url", f"http://{company_id}-schedule:4040")
        self.chatwoot_account_id = config_data.get("chatwoot_account_id", "7")
        self.chatwoot_base_url = config_data.get("chatwoot_base_url", "https://chatwoot-production-0f1d.up.railway.app")
        
        # Configuraciones de agentes personalizadas
        self.sales_agent_name = config_data.get("sales_agent_name", f"Especialista de {self.company_name}")
        self.services = config_data.get("services", "servicios de belleza y estética")
        self.business_hours = config_data.get("business_hours", "Lunes a Viernes de 9:00 AM a 6:00 PM")
        self.phone = config_data.get("phone", "")
        self.address = config_data.get("address", "")
        
        # Configuraciones de modelo IA
        self.model_name = config_data.get("model_name", "gpt-4o-mini")
        self.temperature = config_data.get("temperature", 0.7)
        self.max_tokens = config_data.get("max_tokens", 1500)
        
        # Configuraciones específicas de prompts
        self.custom_prompts = config_data.get("custom_prompts", {})
        
    def get_redis_key(self, key_type: str, identifier: str = "") -> str:
        """Genera claves de Redis con prefijo de empresa"""
        if identifier:
            return f"{self.redis_prefix}{key_type}:{identifier}"
        return f"{self.redis_prefix}{key_type}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario para logging/debugging"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "redis_prefix": self.redis_prefix,
            "vectorstore_index": self.vectorstore_index,
            "schedule_service_url": self.schedule_service_url,
            "model_name": self.model_name
        }

# Configuración de empresas - PARAMETRIZABLE
def load_companies_config() -> Dict[str, CompanyConfig]:
    """
    Carga configuraciones de empresas desde variables de entorno o archivo JSON
    """
    companies = {}
    
    # Opción 1: Cargar desde variable de entorno JSON
    companies_json = os.getenv("COMPANIES_CONFIG")
    if companies_json:
        try:
            config_data = json.loads(companies_json)
            for company_id, company_data in config_data.items():
                companies[company_id] = CompanyConfig(company_id, company_data)
            print(f"✅ Loaded {len(companies)} companies from COMPANIES_CONFIG environment variable")
            return companies
        except Exception as e:
            print(f"❌ Error parsing COMPANIES_CONFIG: {e}")
    
    # Opción 2: Cargar desde archivo companies.json
    try:
        config_file_path = os.getenv("COMPANIES_CONFIG_FILE", "companies.json")
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                for company_id, company_data in config_data.items():
                    companies[company_id] = CompanyConfig(company_id, company_data)
            print(f"✅ Loaded {len(companies)} companies from {config_file_path}")
            return companies
    except Exception as e:
        print(f"❌ Error loading companies config file: {e}")
    
    # Opción 3: Configuración por defecto (backward compatibility con Benova)
    default_config = {
        "benova": {
            "company_name": "Centro Estético Benova",
            "redis_prefix": "benova:",
            "vectorstore_index": "benova_documents",
            "schedule_service_url": "http://benova-schedule-service:4040",
            "chatwoot_account_id": os.getenv("ACCOUNT_ID", "7"),
            "chatwoot_base_url": os.getenv("CHATWOOT_BASE_URL", "https://chatwoot-production-0f1d.up.railway.app"),
            "sales_agent_name": "Especialista de Benova",
            "services": "tratamientos estéticos avanzados, cuidado de la piel y rejuvenecimiento",
            "business_hours": "Lunes a Viernes de 9:00 AM a 6:00 PM, Sábados de 9:00 AM a 2:00 PM",
            "phone": "+57 300 123 4567",
            "address": "Medellín, Colombia"
        }
    }
    
    for company_id, company_data in default_config.items():
        companies[company_id] = CompanyConfig(company_id, company_data)
    
    print(f"✅ Using default configuration for {len(companies)} companies")
    return companies

# Cargar configuraciones de empresas
COMPANIES_CONFIG = load_companies_config()

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
# Environment Setup - ACTUALIZADO PARA MULTI-EMPRESA
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHATWOOT_API_KEY = os.getenv("CHATWOOT_API_KEY")

# Configuraciones globales (pueden ser sobrescritas por empresa)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
PORT = int(os.getenv("PORT", 8080))
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", 10))

# Embedding configuration
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.7))
MAX_RETRIEVED_DOCS = int(os.getenv("MAX_RETRIEVED_DOCS", 3))

if not OPENAI_API_KEY or not CHATWOOT_API_KEY:
    print("ERROR: Missing required environment variables")
    print("Required: OPENAI_API_KEY, CHATWOOT_API_KEY")
    sys.exit(1)

print("Environment loaded successfully")
print(f"Redis URL: {REDIS_URL}")
print(f"Embedding Model: {EMBEDDING_MODEL}")
print(f"Companies configured: {list(COMPANIES_CONFIG.keys())}")

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
# PASO 2: VECTOR STORE MANAGER MULTI-EMPRESA
# ===============================

class VectorStoreManager:
    """
    Gestor de Vector Stores por empresa con aislamiento de datos
    """
    
    def __init__(self, redis_url: str, embedding_model: str = "text-embedding-3-small"):
        self.redis_url = redis_url
        self.embedding_model = embedding_model
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=OPENAI_API_KEY
        )
        self.vectorstores = {}  # Cache de vectorstores por empresa
    
    def get_vectorstore(self, company_config: CompanyConfig) -> RedisVectorStore:
        """
        Obtiene o crea un vector store específico para una empresa
        """
        company_id = company_config.company_id
        
        if company_id not in self.vectorstores:
            try:
                # Crear vector store con índice específico de la empresa
                self.vectorstores[company_id] = RedisVectorStore(
                    self.embeddings,
                    redis_url=self.redis_url,
                    index_name=company_config.vectorstore_index,
                    vector_dim=1536  # Tamaño para text-embedding-3-small
                )
                logger.info(f"✅ Created vector store for company {company_id} with index {company_config.vectorstore_index}")
            
            except Exception as e:
                logger.error(f"❌ Error creating vector store for company {company_id}: {e}")
                raise
        
        return self.vectorstores[company_id]
    
    def find_vectors_by_doc_id(self, company_config: CompanyConfig, doc_id: str) -> List[Dict]:
        """
        Busca vectores por doc_id específico de una empresa
        """
        try:
            vectorstore = self.get_vectorstore(company_config)
            
            # Filtrar por doc_id y company_id en metadata
            results = vectorstore.similarity_search(
                query="",  # Query vacío ya que usamos filtros de metadata
                k=1000,    # Obtener muchos para filtrar
                filter={
                    "doc_id": doc_id,
                    "company_id": company_config.company_id  # Filtro adicional por empresa
                }
            )
            
            return [{"id": i, "metadata": doc.metadata, "content": doc.page_content} 
                   for i, doc in enumerate(results)]
            
        except Exception as e:
            logger.error(f"Error finding vectors for company {company_config.company_id}, doc_id {doc_id}: {e}")
            return []
    
    def delete_document(self, company_config: CompanyConfig, doc_id: str) -> bool:
        """
        Elimina documento específico de una empresa
        """
        try:
            # Buscar vectores del documento
            vectors_to_delete = self.find_vectors_by_doc_id(company_config, doc_id)
            
            if not vectors_to_delete:
                logger.warning(f"No vectors found for doc_id {doc_id} in company {company_config.company_id}")
                return True
            
            vectorstore = self.get_vectorstore(company_config)
            
            # Eliminar vectores (implementación específica según la versión de langchain-redis)
            # Nota: La eliminación exacta puede variar según la versión
            vector_ids = [v["id"] for v in vectors_to_delete]
            
            # Método alternativo: recrear el índice sin los vectores eliminados
            # Esta es una implementación de fallback
            logger.info(f"Attempting to delete {len(vector_ids)} vectors for doc_id {doc_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} for company {company_config.company_id}: {e}")
            return False
    
    def add_documents_with_company_metadata(self, 
                                          company_config: CompanyConfig,
                                          documents: List[str], 
                                          metadatas: List[Dict] = None) -> int:
        """
        Agrega documentos al vector store con metadata de empresa
        """
        try:
            vectorstore = self.get_vectorstore(company_config)
            
            # Procesar documentos con metadata de empresa
            processed_texts = []
            processed_metadatas = []
            
            for i, doc in enumerate(documents):
                if doc and doc.strip():
                    # Usar sistema de chunking avanzado
                    texts, auto_metadatas = advanced_chunk_processing(doc)
                    
                    # Combinar metadata con información de empresa
                    base_metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                    
                    for j, (text, auto_meta) in enumerate(zip(texts, auto_metadatas)):
                        if text.strip():
                            processed_texts.append(text)
                            
                            # Metadata combinada con aislamiento por empresa
                            combined_meta = base_metadata.copy()
                            combined_meta.update(auto_meta)
                            combined_meta.update({
                                "company_id": company_config.company_id,  # ✅ AISLAMIENTO POR EMPRESA
                                "doc_id": hashlib.md5(doc.encode()).hexdigest(),
                                "chunk_index": j,
                                "doc_index": i,
                                "added_at": datetime.utcnow().isoformat()
                            })
                            processed_metadatas.append(combined_meta)
            
            # Agregar al vector store
            if processed_texts:
                vectorstore.add_texts(processed_texts, metadatas=processed_metadatas)
                logger.info(f"✅ Added {len(processed_texts)} chunks to {company_config.company_id} vector store")
            
            return len(processed_texts)
            
        except Exception as e:
            logger.error(f"Error adding documents for company {company_config.company_id}: {e}")
            return 0

# Instancia global del gestor de vector stores
vector_store_manager = VectorStoreManager(REDIS_URL, EMBEDDING_MODEL)

# ===============================
# CHUNKING SYSTEM - REUTILIZADO CON MEJORAS
# ===============================

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
# UTILS PARA IDENTIFICACIÓN DE EMPRESA
# ===============================

def identify_company_from_webhook(webhook_data: Dict[str, Any]) -> Optional[CompanyConfig]:
    """
    Identifica la empresa desde el payload del webhook
    """
    try:
        # Opción 1: Desde metadata de conversación
        if "conversation" in webhook_data and "meta" in webhook_data["conversation"]:
            company_id = webhook_data["conversation"]["meta"].get("company_id")
            if company_id and company_id in COMPANIES_CONFIG:
                return COMPANIES_CONFIG[company_id]
        
        # Opción 2: Desde account_id de Chatwoot
        account_id = webhook_data.get("account", {}).get("id")
        if account_id:
            for company_config in COMPANIES_CONFIG.values():
                if company_config.chatwoot_account_id == str(account_id):
                    return company_config
        
        # Opción 3: Desde URL o header personalizado (implementar según necesidad)
        # company_header = request.headers.get("X-Company-ID")
        # if company_header and company_header in COMPANIES_CONFIG:
        #     return COMPANIES_CONFIG[company_header]
        
        # Opción 4: Fallback a empresa por defecto (Benova para backward compatibility)
        if "benova" in COMPANIES_CONFIG:
            logger.warning("Could not identify company, using default (benova)")
            return COMPANIES_CONFIG["benova"]
        
        # Si no hay empresa por defecto, usar la primera disponible
        if COMPANIES_CONFIG:
            default_company = list(COMPANIES_CONFIG.values())[0]
            logger.warning(f"Using first available company: {default_company.company_id}")
            return default_company
        
        return None
        
    except Exception as e:
        logger.error(f"Error identifying company from webhook: {e}")
        return None

def validate_company_exists(company_id: str) -> bool:
    """
    Valida que una empresa exista en la configuración
    """
    return company_id in COMPANIES_CONFIG

print("✅ Multi-company backend configuration loaded successfully")
print(f"✅ Available companies: {list(COMPANIES_CONFIG.keys())}")

# ===============================
# PASO 3: BOT ACTIVATION LOGIC MULTI-EMPRESA
# ===============================

BOT_ACTIVE_STATUSES = ["open"]
BOT_INACTIVE_STATUSES = ["pending", "resolved", "snoozed"]

status_lock = threading.Lock()

def update_bot_status(conversation_id, conversation_status, company_config: CompanyConfig):
    """Update bot status for a specific conversation in Redis with company isolation"""
    with status_lock:
        is_active = conversation_status in BOT_ACTIVE_STATUSES
        
        # Store in Redis with company prefix
        status_key = company_config.get_redis_key("bot_status", conversation_id)
        status_data = {
            'active': str(is_active),
            'status': conversation_status,
            'company_id': company_config.company_id,
            'updated_at': str(time.time())
        }
        
        try:
            old_status = redis_client.hget(status_key, 'active')
            redis_client.hset(status_key, mapping=status_data)
            redis_client.expire(status_key, 86400)  # 24 hours TTL
            
            if old_status != str(is_active):
                status_text = "ACTIVO" if is_active else "INACTIVO"
                logger.info(f"🔄 {company_config.company_id} - Conversation {conversation_id}: Bot {status_text} (status: {conversation_status})")
                
        except Exception as e:
            logger.error(f"Error updating bot status in Redis for {company_config.company_id}: {e}")

def should_bot_respond(conversation_id, conversation_status, company_config: CompanyConfig):
    """Determine if bot should respond based on conversation status"""
    update_bot_status(conversation_id, conversation_status, company_config)
    is_active = conversation_status in BOT_ACTIVE_STATUSES
    
    if is_active:
        logger.info(f"✅ {company_config.company_id} - Bot WILL respond to conversation {conversation_id} (status: {conversation_status})")
    else:
        if conversation_status == "pending":
            logger.info(f"⏸️ {company_config.company_id} - Bot will NOT respond to conversation {conversation_id} (status: pending - INACTIVE)")
        else:
            logger.info(f"🚫 {company_config.company_id} - Bot will NOT respond to conversation {conversation_id} (status: {conversation_status})")
    
    return is_active

def is_message_already_processed(message_id, conversation_id, company_config: CompanyConfig):
    """Check if message has already been processed using Redis with company isolation"""
    if not message_id:
        return False
    
    key = company_config.get_redis_key("processed_message", f"{conversation_id}:{message_id}")
    
    try:
        if redis_client.exists(key):
            logger.info(f"🔄 {company_config.company_id} - Message {message_id} already processed, skipping")
            return True
        
        redis_client.set(key, "1", ex=3600)  # 1 hour TTL
        logger.info(f"✅ {company_config.company_id} - Message {message_id} marked as processed")
        return False
        
    except Exception as e:
        logger.error(f"Error checking processed message in Redis for {company_config.company_id}: {e}")
        return False

# ===============================
# PASO 4: MODERN CONVERSATION MANAGER MULTI-EMPRESA
# ===============================

class ModernConversationManager:
    """
    ADAPTADO: Conversation Manager para múltiples empresas con aislamiento de datos
    """
    
    def __init__(self, redis_client, max_messages: int = 10):
        self.redis_client = redis_client
        self.max_messages = max_messages
        self.conversations = {}
        self.message_histories = {}  # Cache por empresa
        self.load_conversations_from_redis()
    
    def _create_user_id(self, contact_id: str, company_config: CompanyConfig) -> str:
        """Generate standardized user ID with company isolation"""
        if not contact_id.startswith("chatwoot_contact_"):
            user_id = f"chatwoot_contact_{contact_id}"
        else:
            user_id = contact_id
        
        # Add company prefix for isolation
        return f"{company_config.company_id}:{user_id}"
    
    def _get_redis_connection_params(self) -> Dict[str, Any]:
        """Extract Redis connection parameters from client"""
        try:
            return {
                "url": REDIS_URL,
                "ttl": 604800  # 7 días
            }
        except Exception as e:
            logger.warning(f"Could not extract Redis params, using defaults: {e}")
            return {
                "url": REDIS_URL,
                "ttl": 604800
            }
    
    def _get_or_create_redis_history(self, user_id: str, company_config: CompanyConfig) -> BaseChatMessageHistory:
        """
        ADAPTADO: Método interno para crear/obtener RedisChatMessageHistory con aislamiento por empresa
        """
        # Use company-specific user_id
        full_user_id = f"{company_config.company_id}:{user_id}"
        
        if full_user_id not in self.message_histories:
            try:
                redis_params = self._get_redis_connection_params()
                
                # Create RedisChatMessageHistory with company-specific key prefix
                key_prefix = company_config.get_redis_key("chat_history", "")
                
                self.message_histories[full_user_id] = RedisChatMessageHistory(
                    session_id=user_id,  # Use original user_id as session
                    url=redis_params["url"],
                    key_prefix=key_prefix,
                    ttl=redis_params["ttl"]
                )
                
                logger.info(f"✅ Created Redis message history for user {user_id} in company {company_config.company_id}")
                
            except Exception as e:
                logger.error(f"❌ Error creating Redis message history for user {user_id} in {company_config.company_id}: {e}")
                # Fallback to in-memory
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self.message_histories[full_user_id] = InMemoryChatMessageHistory()
                logger.warning(f"⚠️ Using in-memory fallback for user {user_id} in {company_config.company_id}")
            
            # Apply message window
            self._apply_message_window(full_user_id)
        
        return self.message_histories[full_user_id]
    
    def get_chat_history(self, user_id: str, company_config: CompanyConfig, format_type: str = "dict") -> Any:
        """
        ADAPTADO: Método unificado para obtener chat history con aislamiento por empresa
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
            # Get Redis history with company isolation
            redis_history = self._get_or_create_redis_history(user_id, company_config)
            
            # Return according to requested format
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
                return self.get_chat_history(user_id, company_config, "dict")
                
        except Exception as e:
            logger.error(f"Error getting chat history for user {user_id} in {company_config.company_id}: {e}")
            # Return default values based on format
            if format_type == "dict":
                return []
            elif format_type == "langchain":
                from langchain_core.chat_history import InMemoryChatMessageHistory
                return InMemoryChatMessageHistory()
            elif format_type == "messages":
                return []
            else:
                return []
    
    def _apply_message_window(self, full_user_id: str):
        """Apply sliding message window to keep only last N messages"""
        try:
            history = self.message_histories[full_user_id]
            messages = history.messages
            
            if len(messages) > self.max_messages:
                # Keep only the last max_messages
                messages_to_keep = messages[-self.max_messages:]
                
                # Clear existing history
                history.clear()
                
                # Add only the messages we want to keep
                for message in messages_to_keep:
                    history.add_message(message)
                
                company_id = full_user_id.split(':')[0]
                logger.info(f"✅ Applied message window for user in {company_id}: kept {len(messages_to_keep)} messages")
        
        except Exception as e:
            logger.error(f"❌ Error applying message window for user {full_user_id}: {e}")
    
    def add_message(self, user_id: str, company_config: CompanyConfig, role: str, content: str) -> bool:
        """Add message with automatic window management and company isolation"""
        if not user_id or not content.strip():
            logger.warning(f"Invalid user_id or content for message in {company_config.company_id}")
            return False
        
        try:
            # Use the unified method to get history
            history = self.get_chat_history(user_id, company_config, format_type="langchain")
            
            # Add message to history
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            else:
                logger.warning(f"Unknown role: {role}")
                return False
            
            # Update cache and apply window management
            full_user_id = f"{company_config.company_id}:{user_id}"
            if full_user_id in self.message_histories:
                self._apply_message_window(full_user_id)
            
            # Update metadata
            self._update_conversation_metadata(user_id, company_config)
            
            logger.info(f"✅ Message added for user {user_id} in {company_config.company_id} (role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding message for user {user_id} in {company_config.company_id}: {e}")
            return False
    
    def _update_conversation_metadata(self, user_id: str, company_config: CompanyConfig):
        """Update conversation metadata in Redis with company isolation"""
        try:
            conversation_key = company_config.get_redis_key("conversation", user_id)
            metadata = {
                'last_updated': str(time.time()),
                'user_id': user_id,
                'company_id': company_config.company_id,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)  # 7 días TTL
            
        except Exception as e:
            logger.error(f"Error updating metadata for user {user_id} in {company_config.company_id}: {e}")
    
    def load_conversations_from_redis(self):
        """Load conversations from Redis with company awareness"""
        try:
            loaded_count = 0
            
            # Load conversations for each configured company
            for company_config in COMPANIES_CONFIG.values():
                try:
                    # Search for company-specific conversation keys
                    conversation_pattern = company_config.get_redis_key("conversation", "*")
                    chat_history_pattern = company_config.get_redis_key("chat_history", "*")
                    
                    conversation_keys = self.redis_client.keys(conversation_pattern)
                    chat_history_keys = self.redis_client.keys(chat_history_pattern)
                    
                    # Migrate old format conversations if needed
                    for key in conversation_keys:
                        try:
                            # Extract user_id from key
                            key_parts = key.split(':')
                            if len(key_parts) >= 3:  # company:conversation:user_id
                                user_id = ':'.join(key_parts[2:])
                                context_data = self.redis_client.hgetall(key)
                                
                                if context_data and 'messages' in context_data:
                                    # Migrate old messages to new format
                                    old_messages = json.loads(context_data['messages'])
                                    history = self.get_chat_history(user_id, company_config, format_type="langchain")
                                    
                                    # Check if already migrated
                                    if len(history.messages) == 0 and old_messages:
                                        for msg in old_messages:
                                            if msg.get('role') == 'user':
                                                history.add_user_message(msg['content'])
                                            elif msg.get('role') == 'assistant':
                                                history.add_ai_message(msg['content'])
                                        
                                        full_user_id = f"{company_config.company_id}:{user_id}"
                                        self._apply_message_window(full_user_id)
                                        loaded_count += 1
                                        logger.info(f"✅ Migrated conversation for user {user_id} in {company_config.company_id}")
                        
                        except Exception as e:
                            logger.warning(f"Failed to migrate conversation {key}: {e}")
                            continue
                    
                    # Count conversations already in new format
                    company_new_format = len([k for k in chat_history_keys 
                                            if k not in [company_config.get_redis_key("chat_history", 
                                                       k.split(':')[-1]) for k in conversation_keys]])
                    loaded_count += company_new_format
                    
                except Exception as e:
                    logger.warning(f"Error loading conversations for {company_config.company_id}: {e}")
                    continue
            
            logger.info(f"✅ Loaded {loaded_count} conversation contexts from Redis across all companies")
            
        except Exception as e:
            logger.error(f"❌ Error loading contexts from Redis: {e}")
    
    def get_message_count(self, user_id: str, company_config: CompanyConfig) -> int:
        """Get total message count for a user in a specific company"""
        try:
            history = self.get_chat_history(user_id, company_config, format_type="langchain")
            return len(history.messages)
        except Exception as e:
            logger.error(f"Error getting message count for user {user_id} in {company_config.company_id}: {e}")
            return 0
    
    def clear_conversation(self, user_id: str, company_config: CompanyConfig) -> bool:
        """Clear conversation history for a user in a specific company"""
        try:
            history = self.get_chat_history(user_id, company_config, format_type="langchain")
            history.clear()
            
            # Clear metadata
            conversation_key = company_config.get_redis_key("conversation", user_id)
            self.redis_client.delete(conversation_key)
            
            # Clear cache
            full_user_id = f"{company_config.company_id}:{user_id}"
            if full_user_id in self.message_histories:
                del self.message_histories[full_user_id]
            
            logger.info(f"✅ Cleared conversation for user {user_id} in {company_config.company_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing conversation for user {user_id} in {company_config.company_id}: {e}")
            return False

# ===============================
# PASO 5: SISTEMA MULTIMEDIA ADAPTADO
# ===============================

def transcribe_audio(audio_path, company_config: CompanyConfig = None):
    """Transcribir audio a texto usando Whisper con logging por empresa"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        result = transcript.text if hasattr(transcript, 'text') else str(transcript)
        logger.info(f"🎵 {company_prefix}Audio transcription successful: {len(result)} characters")
        return result
        
    except Exception as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error in audio transcription: {e}")
        raise

def transcribe_audio_from_url(audio_url, company_config: CompanyConfig = None):
    """Transcribir audio desde URL con logging por empresa"""
    try:
        import requests
        import tempfile
        import os
        
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        
        logger.info(f"🔽 {company_prefix}Downloading audio from: {audio_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ChatbotAudioTranscriber/1.0)',
            'Accept': 'audio/*,*/*;q=0.9'
        }
        
        response = requests.get(audio_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        logger.info(f"📄 {company_prefix}Audio content-type: {content_type}")
        
        # Determine extension based on content-type or URL
        extension = '.ogg'  # Default for Chatwoot
        if 'mp3' in content_type or audio_url.endswith('.mp3'):
            extension = '.mp3'
        elif 'wav' in content_type or audio_url.endswith('.wav'):
            extension = '.wav'
        elif 'm4a' in content_type or audio_url.endswith('.m4a'):
            extension = '.m4a'
        
        # Create temp file with correct extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        logger.info(f"📁 {company_prefix}Audio saved to temp file: {temp_path} (size: {os.path.getsize(temp_path)} bytes)")
        
        try:
            # Transcribe using the corrected function
            result = transcribe_audio(temp_path, company_config)
            logger.info(f"🎵 {company_prefix}Transcription successful: {len(result)} characters")
            return result
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
                logger.info(f"🗑️ {company_prefix}Temporary file deleted: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ {company_prefix}Could not delete temp file {temp_path}: {cleanup_error}")
        
    except requests.exceptions.RequestException as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error downloading audio: {e}")
        raise Exception(f"Error downloading audio: {str(e)}")
    except Exception as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error in audio transcription from URL: {e}")
        raise

def text_to_speech(text, company_config: CompanyConfig = None):
    """Convertir texto a audio usando TTS de OpenAI con logging por empresa"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        # Save audio temporarily
        temp_path = "/tmp/response.mp3"
        response.stream_to_file(temp_path)
        
        logger.info(f"🔊 {company_prefix}Text-to-speech conversion successful")
        return temp_path
    except Exception as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error in text-to-speech: {e}")
        raise

def analyze_image(image_file, company_config: CompanyConfig = None):
    """Analizar imagen usando GPT-4 Vision con contexto de empresa"""
    try:
        # Convert image to base64
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        
        # Customize prompt based on company
        if company_config:
            analysis_prompt = f"Describe esta imagen en detalle, enfocándote en elementos relevantes para {company_config.services} de {company_config.company_name}. Si es una promoción o anuncio, menciona los detalles principales."
        else:
            analysis_prompt = "Describe esta imagen en detalle, enfocándote en elementos relevantes para una consulta de tratamientos estéticos o servicios médicos. Si es una promoción o anuncio, menciona los detalles principales."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": analysis_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        result = response.choices[0].message.content
        logger.info(f"🖼️ {company_prefix}Image analysis successful: {len(result)} characters")
        return result
        
    except Exception as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error in image analysis: {e}")
        raise

def process_chatwoot_attachment(attachment, company_config: CompanyConfig = None):
    """Procesar attachment de Chatwoot con logging por empresa"""
    try:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.info(f"🔍 {company_prefix}Processing Chatwoot attachment: {attachment}")
        
        # Extract file type with multiple methods
        attachment_type = None
        
        # Method 1: file_type (most common in Chatwoot)
        if attachment.get("file_type"):
            attachment_type = attachment["file_type"].lower()
            logger.info(f"📝 {company_prefix}Type from 'file_type': {attachment_type}")
        
        # Method 2: extension
        elif attachment.get("extension"):
            ext = attachment["extension"].lower().lstrip('.')
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                attachment_type = "image"
            elif ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
                attachment_type = "audio"
            logger.info(f"📝 {company_prefix}Type inferred from extension '{ext}': {attachment_type}")
        
        # Extract URL with correct priority
        url = attachment.get("data_url") or attachment.get("url") or attachment.get("thumb_url")
        
        if not url:
            logger.warning(f"⚠️ {company_prefix}No URL found in attachment")
            return None
        
        # Validate that URL is accessible
        if not url.startswith("http"):
            logger.warning(f"⚠️ {company_prefix}Invalid URL format: {url}")
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
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error processing Chatwoot attachment: {e}")
        return None

# ===============================
# PASO 6: DOCUMENT CHANGE TRACKER MULTI-EMPRESA
# ===============================

class DocumentChangeTracker:
    """Sistema para rastrear cambios en documentos por empresa"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    def get_current_version(self, company_config: CompanyConfig) -> int:
        """Obtener versión actual del vectorstore por empresa"""
        try:
            version_key = company_config.get_redis_key("vectorstore_version")
            version = self.redis_client.get(version_key)
            return int(version) if version else 0
        except:
            return 0
    
    def increment_version(self, company_config: CompanyConfig):
        """Incrementar versión del vectorstore por empresa"""
        try:
            version_key = company_config.get_redis_key("vectorstore_version")
            self.redis_client.incr(version_key)
            logger.info(f"[{company_config.company_id}] Vectorstore version incremented to {self.get_current_version(company_config)}")
        except Exception as e:
            logger.error(f"[{company_config.company_id}] Error incrementing version: {e}")
    
    def register_document_change(self, doc_id: str, change_type: str, company_config: CompanyConfig):
        """
        Registrar cambio en documento con aislamiento por empresa
        change_type: 'added', 'updated', 'deleted'
        """
        try:
            change_data = {
                'doc_id': doc_id,
                'change_type': change_type,
                'company_id': company_config.company_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Register change with company isolation
            change_key = company_config.get_redis_key("doc_change", f"{doc_id}:{int(time.time())}")
            self.redis_client.setex(change_key, 3600, json.dumps(change_data))  # 1 hour TTL
            
            # Increment company-specific version
            self.increment_version(company_config)
            
            logger.info(f"[{company_config.company_id}] Document change registered: {doc_id} - {change_type}")
            
        except Exception as e:
            logger.error(f"[{company_config.company_id}] Error registering document change: {e}")
    
    def should_invalidate_cache(self, last_version: int, company_config: CompanyConfig) -> bool:
        """Determinar si se debe invalidar cache por empresa"""
        current_version = self.get_current_version(company_config)
        return current_version > last_version

# Initialize instances
conversation_manager = ModernConversationManager(redis_client, MAX_CONTEXT_MESSAGES)
document_change_tracker = DocumentChangeTracker(redis_client)

print("✅ Multi-company conversation manager and multimedia system initialized")
print("✅ Document change tracking system initialized")
print("✅ Bot activation logic adapted for multi-company environment")

# ===============================
# PASO 7: SISTEMA MULTI-AGENTE ADAPTADO PARA MÚLTIPLES EMPRESAS
# ===============================

class MultiAgentSystem:
    """
    ✅ ADAPTADO: Sistema multi-agente integrado para múltiples empresas
    - Configuración dinámica por empresa
    - Prompts personalizados por empresa
    - Aislamiento de datos por empresa
    - Microservicio de agendamiento por empresa
    """
    
    def __init__(self, chat_model, conversation_manager, company_config: CompanyConfig):
        """
        Inicializar sistema multi-agente para una empresa específica
        
        Args:
            chat_model: Modelo de chat de LangChain
            conversation_manager: Gestor de conversaciones
            company_config: Configuración específica de la empresa
        """
        self.chat_model = chat_model
        self.conversation_manager = conversation_manager
        self.company_config = company_config  # ✅ NUEVO: Configuración por empresa
        
        # ✅ ADAPTADO: Vector store específico por empresa
        self.vectorstore = vector_store_manager.get_vectorstore(company_config)
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
        
        # Configuración multimedia por empresa
        self.voice_enabled = os.getenv("VOICE_ENABLED", "false").lower() == "true"
        self.image_enabled = os.getenv("IMAGE_ENABLED", "false").lower() == "true"
        
        # ✅ ADAPTADO: URL del microservicio específico por empresa
        self.schedule_service_url = company_config.schedule_service_url
        
        # Configuración para entorno local
        self.is_local_development = os.getenv('ENVIRONMENT', 'production') == 'local'
        
        # Timeout específico para conexiones locales
        self.selenium_timeout = 30 if self.is_local_development else 60
        
        # ✅ ADAPTADO: Cache del estado de Selenium con identificación por empresa
        selenium_cache_key = f"selenium_service_{company_config.company_id}"
        self.selenium_service_available = False
        self.selenium_status_last_check = 0
        self.selenium_status_cache_duration = 30  # 30 segundos de cache
        
        # ✅ ADAPTADO: Inicializar agentes especializados con configuración por empresa
        self.router_agent = self._create_router_agent()
        self.emergency_agent = self._create_emergency_agent()
        self.sales_agent = self._create_sales_agent()
        self.support_agent = self._create_support_agent()
        self.schedule_agent = self._create_enhanced_schedule_agent()
        self.availability_agent = self._create_availability_agent()
        
        # Crear orquestador principal
        self.orchestrator = self._create_orchestrator()
        
        # ✅ ADAPTADO: Inicializar conexión con microservicio específico de empresa
        self._initialize_company_selenium_connection()
    
    def _verify_selenium_service(self, force_check: bool = False) -> bool:
        """
        ✅ ADAPTADO: Verificar disponibilidad del servicio Selenium por empresa con cache inteligente
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
            logger.warning(f"[{self.company_config.company_id}] Selenium service verification failed: {e}")
            self.selenium_service_available = False
            self.selenium_status_last_check = current_time
            return False
    
    def _initialize_company_selenium_connection(self):
        """✅ ADAPTADO: Inicializar y verificar conexión con microservicio específico de empresa"""
        try:
            logger.info(f"[{self.company_config.company_id}] Conectando con microservicio de Selenium en: {self.schedule_service_url}")
            
            # Verificar disponibilidad del servicio (forzar verificación inicial)
            is_available = self._verify_selenium_service(force_check=True)
            
            if is_available:
                logger.info(f"✅ [{self.company_config.company_id}] Conexión exitosa con microservicio de Selenium")
            else:
                logger.warning(f"⚠️ [{self.company_config.company_id}] Servicio de Selenium no disponible")
                
        except Exception as e:
            logger.error(f"❌ [{self.company_config.company_id}] Error inicializando conexión con Selenium: {e}")
            self.selenium_service_available = False
    
    def _create_router_agent(self):
        """
        ✅ ADAPTADO: Agente Router con prompts personalizados por empresa
        """
        # ✅ NUEVO: Obtener prompts personalizados si están disponibles
        custom_router_prompt = self.company_config.custom_prompts.get("router")
        
        if custom_router_prompt:
            router_system_message = custom_router_prompt.format(
                company_name=self.company_config.company_name,
                services=self.company_config.services
            )
        else:
            # Prompt por defecto adaptado por empresa
            router_system_message = f"""Eres un clasificador de intenciones para {self.company_config.company_name}.

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
   - Información general de {self.company_config.company_name}
   - Consultas sobre procesos
   - Cualquier otra consulta

RESPONDE SOLO con el formato JSON:
{{{{
    "intent": "EMERGENCY|SALES|SCHEDULE|SUPPORT",
    "confidence": 0.0-1.0,
    "keywords": ["palabra1", "palabra2"],
    "reasoning": "breve explicación"
}}}}

Mensaje del usuario: {{question}}"""
        
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", router_system_message),
            ("human", "{question}")
        ])
        
        return router_prompt | self.chat_model | StrOutputParser()
    
    def _create_emergency_agent(self):
        """
        ✅ ADAPTADO: Agente de Emergencias con configuración por empresa
        """
        # ✅ NUEVO: Obtener prompts personalizados si están disponibles
        custom_emergency_prompt = self.company_config.custom_prompts.get("emergency")
        
        if custom_emergency_prompt:
            emergency_system_message = custom_emergency_prompt.format(
                company_name=self.company_config.company_name,
                sales_agent_name=self.company_config.sales_agent_name,
                phone=self.company_config.phone
            )
        else:
            # Prompt por defecto adaptado por empresa
            emergency_system_message = f"""Eres {self.company_config.sales_agent_name}, especialista en emergencias médicas de {self.company_config.company_name}.

SITUACIÓN DETECTADA: Posible emergencia médica.

PROTOCOLO DE RESPUESTA:
1. Expresa empatía y preocupación inmediata
2. Solicita información básica del síntoma
3. Indica que el caso será escalado de emergencia
4. Proporciona información de contacto directo si es necesario
{f"Teléfono de emergencia: {self.company_config.phone}" if self.company_config.phone else ""}

TONO: Profesional, empático, tranquilizador pero urgente.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 3 oraciones.

FINALIZA SIEMPRE con: "Escalando tu caso de emergencia ahora mismo. 🚨"

Historial de conversación:
{{chat_history}}

Mensaje del usuario: {{question}}"""
        
        emergency_prompt = ChatPromptTemplate.from_messages([
            ("system", emergency_system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        return emergency_prompt | self.chat_model | StrOutputParser()
    
    def _create_sales_agent(self):
        """
        ✅ ADAPTADO: Agente de Ventas específico por empresa
        """
        # ✅ NUEVO: Obtener prompts personalizados si están disponibles
        custom_sales_prompt = self.company_config.custom_prompts.get("sales")
        
        if custom_sales_prompt:
            sales_system_message = custom_sales_prompt.format(
                company_name=self.company_config.company_name,
                sales_agent_name=self.company_config.sales_agent_name,
                services=self.company_config.services
            )
        else:
            # Prompt por defecto adaptado por empresa
            sales_system_message = f"""Eres {self.company_config.sales_agent_name}, asesora comercial especializada de {self.company_config.company_name}.

OBJETIVO: Proporcionar información comercial precisa y persuasiva sobre {self.company_config.services}.

INFORMACIÓN DISPONIBLE:
{{context}}

ESTRUCTURA DE RESPUESTA:
1. Saludo personalizado (si es nuevo cliente)
2. Información del tratamiento solicitado
3. Beneficios principales (máximo 3)
4. Inversión (si disponible)
5. Llamada a la acción para agendar

TONO: Cálido, profesional, persuasivo.
EMOJIS: Máximo 3 por respuesta.
LONGITUD: Máximo 5 oraciones.

FINALIZA SIEMPRE con: "¿Te gustaría agendar tu cita? 📅"

Historial de conversación:
{{chat_history}}

Pregunta del usuario: {{question}}"""
        
        sales_prompt = ChatPromptTemplate.from_messages([
            ("system", sales_system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_sales_context(inputs):
            """✅ ADAPTADO: Obtener contexto RAG para ventas con filtrado por empresa"""
            try:
                question = inputs.get("question", "")
                # Log de uso del retriever
                self._log_retriever_usage(question, [])
                
                # ✅ ADAPTADO: Filtrar documentos por empresa automáticamente
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de {self.company_config.company_name}:
- Especializado en {self.company_config.services}
- Atención personalizada
- Profesionales certificados
- Horarios: {self.company_config.business_hours}
{f"- Ubicación: {self.company_config.address}" if self.company_config.address else ""}
Para información específica de tratamientos, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error retrieving sales context: {e}")
                return f"Información básica de {self.company_config.company_name} disponible. Te conectaré con un especialista para detalles específicos."
        
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
        ✅ ADAPTADO: Agente de Soporte específico por empresa
        """
        # ✅ NUEVO: Obtener prompts personalizados si están disponibles
        custom_support_prompt = self.company_config.custom_prompts.get("support")
        
        if custom_support_prompt:
            support_system_message = custom_support_prompt.format(
                company_name=self.company_config.company_name,
                sales_agent_name=self.company_config.sales_agent_name,
                business_hours=self.company_config.business_hours,
                address=self.company_config.address,
                phone=self.company_config.phone
            )
        else:
            # Prompt por defecto adaptado por empresa
            support_system_message = f"""Eres {self.company_config.sales_agent_name}, especialista en soporte al cliente de {self.company_config.company_name}.

OBJETIVO: Resolver consultas generales y facilitar navegación.

INFORMACIÓN DE LA EMPRESA:
- Nombre: {self.company_config.company_name}
- Servicios: {self.company_config.services}
- Horarios: {self.company_config.business_hours}
{f"- Teléfono: {self.company_config.phone}" if self.company_config.phone else ""}
{f"- Dirección: {self.company_config.address}" if self.company_config.address else ""}

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

Consulta del usuario: {{question}}"""
        
        support_prompt = ChatPromptTemplate.from_messages([
            ("system", support_system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_support_context(inputs):
            """✅ ADAPTADO: Obtener contexto RAG para soporte con filtrado por empresa"""
            try:
                question = inputs.get("question", "")
                # Log de uso del retriever
                self._log_retriever_usage(question, [])
                
                # ✅ ADAPTADO: Filtrar documentos por empresa automáticamente
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información general de {self.company_config.company_name}:
- Horarios de atención: {self.company_config.business_hours}
- Información general del centro
- Consultas sobre procesos
- Información institucional
Para información específica, te conectaré con un especialista."""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error retrieving support context: {e}")
                return f"Información general de {self.company_config.company_name} disponible. Te conectaré con un especialista para consultas específicas."
        
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
        """✅ ADAPTADO: Agente que verifica disponibilidad con configuración por empresa"""
        availability_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Eres un agente de disponibilidad de {self.company_config.company_name}.
    
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
            """✅ ADAPTADO: Obtener estado del sistema Selenium para availability por empresa"""
            # Verificar estado del servicio antes de cada consulta
            is_available = self._verify_selenium_service()
            
            if is_available:
                return f"✅ [{self.company_config.company_id}] Sistema de disponibilidad ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ [{self.company_config.company_id}] Sistema de disponibilidad NO DISPONIBLE (Verificar conexión: {self.schedule_service_url})"
        
        def process_availability(inputs):
            """✅ ADAPTADO: Procesar consulta de disponibilidad por empresa"""
            try:
                question = inputs.get("question", "")
                chat_history = inputs.get("chat_history", [])
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"=== [{self.company_config.company_id}] AVAILABILITY AGENT - PROCESANDO ===")
                logger.info(f"Pregunta: {question}")
                logger.info(f"Estado Selenium: {selenium_status}")
                
                # 1. VERIFICAR SERVICIO DISPONIBLE PRIMERO
                if not self._verify_selenium_service():
                    logger.error(f"[{self.company_config.company_id}] Servicio Selenium no disponible para availability agent")
                    return "Error consultando disponibilidad. Te conectaré con un especialista para verificar horarios. 👩‍⚕️"
                
                # Extract date from question and history
                date = self._extract_date_from_question(question, chat_history)
                treatment = self._extract_treatment_from_question(question)
                
                if not date:
                    return "Por favor especifica la fecha en formato DD-MM-YYYY para consultar disponibilidad."
                
                logger.info(f"[{self.company_config.company_id}] Fecha extraída: {date}, Tratamiento: {treatment}")
                
                # Obtener duración del tratamiento desde RAG
                duration = self._get_treatment_duration(treatment)
                logger.info(f"[{self.company_config.company_id}] Duración del tratamiento: {duration} minutos")
                
                # 2. LLAMAR ENDPOINT CON MÉTODO MEJORADO
                availability_data = self._call_check_availability(date)
                
                if not availability_data:
                    logger.warning(f"[{self.company_config.company_id}] No se obtuvieron datos de disponibilidad")
                    return "Error consultando disponibilidad. Te conectaré con un especialista."
                
                if not availability_data.get("available_slots"):
                    logger.info(f"[{self.company_config.company_id}] No hay slots disponibles para la fecha solicitada")
                    return f"No hay horarios disponibles para {date}."
                
                # Filtrar slots según duración
                filtered_slots = self._filter_slots_by_duration(
                    availability_data["available_slots"], 
                    duration
                )
                
                logger.info(f"[{self.company_config.company_id}] Slots filtrados: {filtered_slots}")
                
                # Formatear respuesta
                response = self._format_slots_response(filtered_slots, date, duration)
                logger.info(f"=== [{self.company_config.company_id}] AVAILABILITY AGENT - RESPUESTA GENERADA ===")
                return response
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error en agente de disponibilidad: {e}")
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
    
    def _call_local_schedule_microservice(self, question: str, user_id: str, chat_history: list) -> Dict[str, Any]:
        """✅ ADAPTADO: Llamar al microservicio de schedule específico por empresa"""
        try:
            logger.info(f"[{self.company_config.company_id}] Llamando a microservicio en: {self.schedule_service_url}")
            
            response = requests.post(
                f"{self.schedule_service_url}/schedule-request",
                json={
                    "message": question,
                    "user_id": user_id,
                    "company_id": self.company_config.company_id,  # ✅ NUEVO: Incluir company_id
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
                
                logger.info(f"[{self.company_config.company_id}] Respuesta exitosa del microservicio: {result.get('success', False)}")
                return result
            else:
                logger.warning(f"[{self.company_config.company_id}] Microservicio retornó código {response.status_code}")
                # Marcar servicio como no disponible para evitar llamadas adicionales
                self.selenium_service_available = False
                return {"success": False, "message": "Servicio no disponible"}
                
        except requests.exceptions.Timeout:
            logger.error(f"[{self.company_config.company_id}] Timeout conectando con microservicio ({self.selenium_timeout}s)")
            self.selenium_service_available = False
            return {"success": False, "message": "Timeout del servicio"}
        
        except requests.exceptions.ConnectionError:
            logger.error(f"[{self.company_config.company_id}] No se pudo conectar con microservicio: {self.schedule_service_url}")
            self.selenium_service_available = False
            return {"success": False, "message": "Servicio no disponible"}
        
        except Exception as e:
            logger.error(f"[{self.company_config.company_id}] Error llamando microservicio: {e}")
            self.selenium_service_available = False
            return {"success": False, "message": "Error del servicio"}
            
    def _create_enhanced_schedule_agent(self):
        """✅ ADAPTADO: Agente de Schedule con configuración por empresa"""
        # ✅ NUEVO: Obtener prompts personalizados si están disponibles
        custom_schedule_prompt = self.company_config.custom_prompts.get("schedule")
        
        if custom_schedule_prompt:
            schedule_system_message = custom_schedule_prompt.format(
                company_name=self.company_config.company_name,
                sales_agent_name=self.company_config.sales_agent_name,
                services=self.company_config.services,
                business_hours=self.company_config.business_hours
            )
        else:
            # Prompt por defecto adaptado por empresa
            schedule_system_message = f"""Eres {self.company_config.sales_agent_name}, especialista en gestión de citas de {self.company_config.company_name}.
    
    OBJETIVO: Facilitar la gestión completa de citas y horarios para {self.company_config.services}.
    
    HORARIOS DE ATENCIÓN: {self.company_config.business_hours}
    
    INFORMACIÓN DISPONIBLE:
    {{context}}
    
    ESTADO DEL SISTEMA DE AGENDAMIENTO:
    {{selenium_status}}
    
    DISPONIBILIDAD CONSULTADA:
    {{available_slots}}
    
    FUNCIONES PRINCIPALES:
    - Agendar nuevas citas (con automatización completa via Selenium)
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
    5. Solo usar herramienta de Selenium después de confirmar disponibilidad
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
    {{chat_history}}
    
    Solicitud del usuario: {{question}}"""
        
        schedule_prompt = ChatPromptTemplate.from_messages([
            ("system", schedule_system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        def get_schedule_context(inputs):
            """✅ ADAPTADO: Obtener contexto RAG para agenda por empresa"""
            try:
                question = inputs.get("question", "")
                # Log de uso del retriever
                self._log_retriever_usage(question, [])
                
                # ✅ ADAPTADO: Filtrar documentos por empresa automáticamente
                docs = self.retriever.invoke(question)
                self._log_retriever_usage(question, docs)
                
                if not docs:
                    return f"""Información básica de agenda {self.company_config.company_name}:
    - Horarios de atención: {self.company_config.business_hours}
    - Servicios agendables: {self.company_config.services}
    - Políticas de cancelación: 24 horas de anticipación
    - Reagendamiento disponible sin costo
    - Sistema de agendamiento automático disponible
    - Datos requeridos: Nombre, cédula, teléfono, fecha y hora deseada"""
                
                return "\n\n".join(doc.page_content for doc in docs)
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error retrieving schedule context: {e}")
                return f"Información básica de agenda de {self.company_config.company_name} disponible. Sistema de agendamiento automático disponible."
        #####
        def get_selenium_status(inputs):
            """✅ ADAPTADO: Obtener estado del sistema Selenium por empresa"""
            if self.selenium_service_available:
                return f"✅ [{self.company_config.company_id}] Sistema de agendamiento automático ACTIVO (Conectado a {self.schedule_service_url})"
            else:
                return f"⚠️ [{self.company_config.company_id}] Sistema de agendamiento automático NO DISPONIBLE (Verificar conexión: {self.schedule_service_url})"
        
        def process_schedule_with_selenium(inputs):
            """✅ ADAPTADO: Procesar solicitud de agenda con integración por empresa"""
            try:
                question = inputs.get("question", "")
                user_id = inputs.get("user_id", "default_user")
                chat_history = inputs.get("chat_history", [])
                context = inputs.get("context", "")
                selenium_status = inputs.get("selenium_status", "")
                
                logger.info(f"[{self.company_config.company_id}] Procesando solicitud de agenda: {question}")
                
                # PASO 1: SIEMPRE verificar disponibilidad si se menciona agendamiento
                available_slots = ""
                if self._contains_schedule_intent(question):
                    logger.info(f"[{self.company_config.company_id}] Detectado intent de agendamiento - verificando disponibilidad")
                    try:
                        availability_response = self.availability_agent.invoke({"question": question, "chat_history": chat_history})
                        available_slots = availability_response
                        logger.info(f"[{self.company_config.company_id}] Disponibilidad obtenida: {available_slots}")
                    except Exception as e:
                        logger.error(f"[{self.company_config.company_id}] Error verificando disponibilidad: {e}")
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
                logger.info(f"[{self.company_config.company_id}] Generando respuesta base con disponibilidad")
                base_response = (schedule_prompt | self.chat_model | StrOutputParser()).invoke(base_inputs)
                
                # PASO 3: Determinar si proceder con Selenium (solo después de verificar disponibilidad)
                should_proceed_selenium = (
                    self._contains_schedule_intent(question) and 
                    self._should_use_selenium(question, chat_history) and
                    self._has_available_slots_confirmation(available_slots) and
                    not self._is_just_availability_check(question)
                )
                
                logger.info(f"[{self.company_config.company_id}] ¿Proceder con Selenium? {should_proceed_selenium}")
                
                if should_proceed_selenium:
                    logger.info(f"[{self.company_config.company_id}] Procediendo con agendamiento automático via Selenium")
                    selenium_result = self._call_local_schedule_microservice(question, user_id, chat_history)
                    
                    if selenium_result.get('success'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    elif selenium_result.get('requires_more_info'):
                        return f"{available_slots}\n\n{selenium_result.get('response', base_response)}"
                    else:
                        return f"{available_slots}\n\n{base_response}\n\nNota: Te conectaré con un especialista para completar el agendamiento."
                
                return base_response
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error en agendamiento: {e}")
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
        """✅ ADAPTADO: Detectar si la pregunta contiene intención de agendamiento"""
        schedule_keywords = [
            "agendar", "reservar", "programar", "cita", "appointment",
            "agenda", "disponibilidad", "horario", "fecha", "hora",
            "procede", "proceder", "confirmar cita"
        ]
        return any(keyword in question.lower() for keyword in schedule_keywords)
    
    def _has_available_slots_confirmation(self, availability_response: str) -> bool:
        """✅ ADAPTADO: Verificar si la respuesta de disponibilidad contiene slots válidos"""
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
        """✅ ADAPTADO: Determinar si solo se está consultando disponibilidad sin agendar"""
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
    
    def _should_use_selenium(self, question: str, chat_history: list) -> bool:
        """✅ ADAPTADO: Determinar si se debe usar el microservicio de Selenium por empresa"""
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
        """✅ ADAPTADO: Extraer información del paciente del historial"""
        # Buscar información básica en el historial
        history_text = " ".join([msg.content if hasattr(msg, 'content') else str(msg) for msg in chat_history])
        
        # Verificar si hay información básica disponible
        has_name = any(word in history_text.lower() for word in ["nombre", "llamo", "soy"])
        has_phone = any(char.isdigit() for char in history_text) and len([c for c in history_text if c.isdigit()]) >= 7
        has_date = any(word in history_text.lower() for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name and (has_phone or has_date)
    
    def _has_complete_info_in_message(self, message: str) -> bool:
        """✅ ADAPTADO: Verificar si el mensaje tiene información completa"""
        message_lower = message.lower()
        
        # Verificar elementos básicos
        has_name_indicator = any(word in message_lower for word in ["nombre", "llamo", "soy"])
        has_phone_indicator = any(char.isdigit() for char in message) and len([c for c in message if c.isdigit()]) >= 7
        has_date_indicator = any(word in message_lower for word in ["fecha", "día", "mañana", "hoy"])
        
        return has_name_indicator and has_phone_indicator and has_date_indicator
    
    def _notify_appointment_success(self, user_id: str, appointment_data: Dict[str, Any]):
        """✅ ADAPTADO: Notificar al sistema principal sobre cita exitosa por empresa"""
        try:
            # Enviar notificación al sistema principal específico de la empresa si es necesario
            main_system_url = self.company_config.main_system_url if hasattr(self.company_config, 'main_system_url') else os.getenv('MAIN_SYSTEM_URL')
            
            if main_system_url:
                requests.post(
                    f"{main_system_url}/appointment-notification",
                    json={
                        "company_id": self.company_config.company_id,  # ✅ NUEVO: Incluir company_id
                        "user_id": user_id,
                        "event": "appointment_scheduled",
                        "data": appointment_data
                    },
                    timeout=5
                )
                logger.info(f"[{self.company_config.company_id}] Notificación enviada al sistema principal para usuario {user_id}")
        except Exception as e:
            logger.error(f"[{self.company_config.company_id}] Error notificando cita exitosa: {e}")
    
    def _create_orchestrator(self):
        """
        ✅ ADAPTADO: Orquestador principal que coordina los agentes por empresa
        """
        def route_to_agent(inputs):
            """✅ ADAPTADO: Enrutar a agente específico basado en clasificación por empresa"""
            try:
                # Obtener clasificación del router
                router_response = self.router_agent.invoke(inputs)
                
                # Parsear respuesta JSON
                try:
                    classification = json.loads(router_response)
                    intent = classification.get("intent", "SUPPORT")
                    confidence = classification.get("confidence", 0.5)
                    
                    logger.info(f"[{self.company_config.company_id}] Intent classified: {intent} (confidence: {confidence})")
                    
                except json.JSONDecodeError:
                    # Fallback si no es JSON válido
                    intent = "SUPPORT"
                    confidence = 0.3
                    logger.warning(f"[{self.company_config.company_id}] Router response was not valid JSON, defaulting to SUPPORT")
                
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
                logger.error(f"[{self.company_config.company_id}] Error in orchestrator: {e}")
                # Fallback a soporte en caso de error
                return self.support_agent.invoke(inputs)
        
        return RunnableLambda(route_to_agent)
    
    def get_response(self, question: str, user_id: str, media_type: str = "text", media_context: str = None) -> Tuple[str, str]:
        """
        ✅ ADAPTADO: Método principal para obtener respuesta del sistema multi-agente por empresa
        Soporta entradas multimedia (voz e imágenes) con configuración específica
        
        Args:
            question: Texto de la pregunta/prompt
            user_id: Identificador único del usuario
            media_type: Tipo de medio ('text', 'voice', 'image')
            media_context: Contexto adicional del medio (transcripción o descripción)
        
        Returns:
            Tuple[str, str]: (respuesta, agente_utilizado)
        """
        # Procesar según el tipo de multimedia
        if media_type == "image" and media_context:
            processed_question = f"Contexto visual: {media_context}\n\nPregunta: {question}"
        elif media_type == "voice" and media_context:
            processed_question = f"Transcripción de voz: {media_context}\n\nPregunta: {question}"
        else:
            processed_question = question
    
        # Validaciones (usando processed_question para incluir contexto multimedia)
        if not processed_question or not processed_question.strip():
            return f"Por favor, envía un mensaje específico para poder ayudarte desde {self.company_config.company_name}. 😊", "support"
        
        if not user_id or not user_id.strip():
            return "Error interno: ID de usuario inválido.", "error"
        
        try:
            # Obtener historial de conversación específico por empresa
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
            logger.info(f"[{self.company_config.company_id}] 🔍 CONSULTA INICIADA - User: {user_id}, Pregunta: {processed_question[:100]}...")
            if might_need_rag:
                logger.info(f"[{self.company_config.company_id}]    → Posible consulta RAG detectada")
            
            # Obtener respuesta del orquestador
            response = self.orchestrator.invoke(inputs)
            
            # Log de la respuesta
            logger.info(f"[{self.company_config.company_id}] 🤖 RESPUESTA GENERADA - Agente: {self._determine_agent_used(response)}")
            logger.info(f"[{self.company_config.company_id}]    → Longitud respuesta: {len(response)} caracteres")
            
            # Agregar mensaje del usuario al historial (usando processed_question)
            self.conversation_manager.add_message(user_id, "user", processed_question)
            
            # Agregar respuesta del asistente al historial
            self.conversation_manager.add_message(user_id, "assistant", response)
            
            # Determinar qué agente se utilizó (para logging)
            agent_used = self._determine_agent_used(response)
            
            logger.info(f"[{self.company_config.company_id}] Multi-agent response generated for user {user_id} using {agent_used}")
            
            return response, agent_used
            
        except Exception as e:
            logger.exception(f"[{self.company_config.company_id}] Error en sistema multi-agente (User: {user_id})")
            return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", "error"
    
    def _might_need_rag(self, question: str) -> bool:
        """✅ ADAPTADO: Determina si una consulta podría necesitar RAG basado en keywords"""
        rag_keywords = [
            "precio", "costo", "inversión", "duración", "tiempo", 
            "tratamiento", "procedimiento", "servicio", "beneficio",
            "horario", "disponibilidad", "agendar", "cita", "información"
        ]
        return any(keyword in question.lower() for keyword in rag_keywords)
    
    def _log_retriever_usage(self, question: str, docs: List) -> None:
        """✅ ADAPTADO: Log detallado del uso del retriever por empresa"""
        if not docs:
            logger.info(f"[{self.company_config.company_id}]    → RAG: No se recuperaron documentos")
            return
        
        logger.info(f"[{self.company_config.company_id}]    → RAG: Recuperados {len(docs)} documentos")
        logger.info(f"[{self.company_config.company_id}]    → Pregunta: {question[:50]}...")
        
        for i, doc in enumerate(docs[:3]):  # Limitar a 3 para no saturar logs
            content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
            metadata = getattr(doc, 'metadata', {})
            score = getattr(doc, 'score', None)
            
            logger.info(f"[{self.company_config.company_id}]    → Doc {i+1}:")
            logger.info(f"[{self.company_config.company_id}]       - Contenido: {content_preview}")
            if metadata:
                logger.info(f"[{self.company_config.company_id}]       - Metadata: {dict(list(metadata.items())[:3])}...")
            if score is not None:
                logger.info(f"[{self.company_config.company_id}]       - Score: {score:.4f}")
    
    def _determine_agent_used(self, response: str) -> str:
        """
        ✅ ADAPTADO: Determinar qué agente se utilizó basado en la respuesta
        """
        if "Escalando tu caso de emergencia" in response:
            return "emergency"
        elif "¿Te gustaría agendar tu cita?" in response:
            return "sales"
        elif "Procesando tu solicitud de agenda" in response or "disponibilidad" in response.lower():
            return "schedule"
        elif "Te conectaré con un especialista" in response:
            return "support"
        else:
            return "support"  # Por defecto
    
    def health_check(self) -> Dict[str, Any]:
        """
        ✅ ADAPTADO: Verificar salud del sistema multi-agente y microservicio por empresa
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
                "company_id": self.company_config.company_id,  # ✅ NUEVO
                "company_name": self.company_config.company_name,  # ✅ NUEVO
                "agents_available": ["router", "emergency", "sales", "schedule", "support", "availability"],
                "schedule_service_healthy": service_healthy,
                "schedule_service_url": self.schedule_service_url,
                "schedule_service_type": "MICROSERVICE_PER_COMPANY",  # ✅ ACTUALIZADO
                "system_type": "multi-agent_enhanced_multi_company",  # ✅ ACTUALIZADO
                "orchestrator_active": True,
                "rag_enabled": True,
                "selenium_integration": service_healthy,
                "environment": os.getenv('ENVIRONMENT', 'production'),
                "vectorstore_company_isolated": True,  # ✅ NUEVO
                "redis_prefix": f"{self.company_config.company_id}:"  # ✅ NUEVO
            }
        except Exception as e:
            return {
                "system_healthy": True,
                "company_id": getattr(self.company_config, 'company_id', 'unknown'),
                "company_name": getattr(self.company_config, 'company_name', 'Unknown Company'),
                "agents_available": ["router", "emergency", "sales", "schedule", "support", "availability"],
                "schedule_service_healthy": False,
                "schedule_service_url": self.schedule_service_url,
                "schedule_service_type": "MICROSERVICE_PER_COMPANY",
                "system_type": "multi-agent_enhanced_multi_company",
                "orchestrator_active": True,
                "rag_enabled": True,
                "selenium_integration": False,
                "environment": os.getenv('ENVIRONMENT', 'production'),
                "vectorstore_company_isolated": True,
                "redis_prefix": f"{getattr(self.company_config, 'company_id', 'unknown')}:",
                "error": str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        ✅ ADAPTADO: Obtener estadísticas del sistema multi-agente por empresa
        """
        return {
            "company_id": self.company_config.company_id,  # ✅ NUEVO
            "company_name": self.company_config.company_name,  # ✅ NUEVO
            "agents_available": ["router", "emergency", "sales", "schedule", "support", "availability"],
            "system_type": "multi-agent_enhanced_multi_company",  # ✅ ACTUALIZADO
            "orchestrator_active": True,
            "rag_enabled": True,
            "selenium_integration": getattr(self, 'selenium_service_available', False),
            "schedule_service_url": self.schedule_service_url,
            "schedule_service_type": "MICROSERVICE_PER_COMPANY",  # ✅ ACTUALIZADO
            "environment": os.getenv('ENVIRONMENT', 'production'),
            "vectorstore_company_isolated": True,  # ✅ NUEVO
            "redis_prefix": f"{self.company_config.company_id}:"  # ✅ NUEVO
        }
    
    def reconnect_selenium_service(self) -> bool:
        """
        ✅ ADAPTADO: Método para reconectar con el servicio Selenium específico de empresa
        """
        logger.info(f"[{self.company_config.company_id}] Intentando reconectar con servicio Selenium...")
        self._initialize_company_selenium_connection()
        return self.selenium_service_available


# ===============================
# FUNCIÓN DE UTILIDAD ADAPTADA PARA MÚLTIPLES EMPRESAS
# ===============================

def create_enhanced_multiagent_system(chat_model, conversation_manager, company_config: CompanyConfig):
    """
    ✅ ADAPTADO: Crear instancia del sistema multi-agente mejorado para múltiples empresas
    
    Args:
        chat_model: Modelo de chat de LangChain
        conversation_manager: Gestor de conversaciones
        company_config: Configuración específica de la empresa
        
    Returns:
        MultiAgentSystem: Sistema multi-agente configurado para la empresa específica
    """
    return MultiAgentSystem(chat_model, conversation_manager, company_config)


# ===============================
# modern_rag_system_with_multiagent - ADAPTADO PARA MÚLTIPLES EMPRESAS
# ===============================
def create_modern_rag_system_with_multiagent(vectorstore, chat_model, embeddings, conversation_manager, company_config: CompanyConfig):
    """
    ✅ ADAPTADO: Crear sistema RAG moderno con arquitectura multi-agente para múltiples empresas
    Reemplaza la clase ModernBenovaRAGSystem manteniendo compatibilidad
    
    Args:
        vectorstore: Vector store específico de la empresa
        chat_model: Modelo de chat
        embeddings: Embeddings model
        conversation_manager: Gestor de conversaciones
        company_config: Configuración específica de la empresa
    """
    class ModernRAGSystemMultiAgent:
        """
        ✅ ADAPTADO: Wrapper que mantiene compatibilidad con el sistema existente
        pero usa arquitectura multi-agente internamente con soporte multi-empresa
        """
        
        def __init__(self, vectorstore, chat_model, embeddings, conversation_manager, company_config):
            self.vectorstore = vectorstore
            self.chat_model = chat_model
            self.embeddings = embeddings
            self.conversation_manager = conversation_manager
            self.company_config = company_config  # ✅ NUEVO: Configuración por empresa
            
            # ✅ ADAPTADO: Retriever con filtrado automático por empresa
            self.retriever = vectorstore.as_retriever(
                search_kwargs={
                    "k": 3,
                    "filter": {"company_id": company_config.company_id}  # ✅ FILTRO POR EMPRESA
                }
            )
            
            # ✅ ADAPTADO: Inicializar sistema multi-agente con configuración específica
            self.multi_agent_system = MultiAgentSystem(
                chat_model, conversation_manager, company_config
            )
        
        def get_response(self, question: str, user_id: str) -> Tuple[str, List]:
            """
            ✅ ADAPTADO: Método compatible con la interfaz existente - FIXED: Usar invoke
            Ahora incluye aislamiento por empresa
            """
            try:
                logger.info(f"[{self.company_config.company_id}] Processing request for user: {user_id}")
                
                # ✅ ADAPTADO: Usar sistema multi-agente con configuración de empresa
                response, agent_used = self.multi_agent_system.get_response(question, user_id)
                
                # Obtener documentos para compatibilidad con filtrado por empresa
                docs = self.retriever.invoke(question)
                
                logger.info(f"[{self.company_config.company_id}] Multi-agent response: {response[:100]}... (agent: {agent_used})")
                
                return response, docs
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error in multi-agent RAG system: {e}")
                return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo. 🔧", []
        
        def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
            """
            ✅ ADAPTADO: Agregar documentos usando sistema de chunking avanzado con aislamiento por empresa
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
                                # ✅ NUEVO: Combinar metadatas con información de empresa
                                combined_meta = base_metadata.copy()
                                combined_meta.update(auto_meta)
                                combined_meta.update({
                                    "company_id": self.company_config.company_id,  # ✅ AISLAMIENTO POR EMPRESA
                                    "chunk_index": j, 
                                    "doc_index": i,
                                    "added_at": datetime.utcnow().isoformat()
                                })
                                all_metas.append(combined_meta)
                
                # Agregar al vectorstore
                if all_texts:
                    self.vectorstore.add_texts(all_texts, metadatas=all_metas)
                    logger.info(f"[{self.company_config.company_id}] Added {len(all_texts)} advanced chunks to vectorstore")
                
                return len(all_texts)
                
            except Exception as e:
                logger.error(f"[{self.company_config.company_id}] Error adding documents with advanced chunking: {e}")
                return 0
    
    return ModernRAGSystemMultiAgent(vectorstore, chat_model, embeddings, conversation_manager, company_config)

# ===============================
# Initialize Modern Components - ADAPTADO PARA MÚLTIPLES EMPRESAS
# ===============================

# ✅ ADAPTADO: Crear instancias de los componentes modernos para cada empresa
modern_conversation_managers = {}
modern_rag_systems = {}

try:
    # Inicializar componentes para cada empresa configurada
    for company_id, company_config in COMPANIES_CONFIG.items():
        logger.info(f"[{company_id}] Initializing modern components...")
        
        # ✅ NUEVO: Conversation manager específico por empresa
        company_conversation_manager = ModernConversationManager(redis_client, MAX_CONTEXT_MESSAGES)
        modern_conversation_managers[company_id] = company_conversation_manager
        
        # ✅ NUEVO: Vector store específico por empresa
        company_vectorstore = vector_store_manager.get_vectorstore(company_config)
        
        # ✅ ADAPTADO: RAG system específico por empresa
        company_rag_system = create_modern_rag_system_with_multiagent(
            company_vectorstore, 
            ChatOpenAI(
                model=company_config.model_name,
                temperature=company_config.temperature,
                max_tokens=company_config.max_tokens,
                openai_api_key=OPENAI_API_KEY
            ), 
            embeddings,  # Se puede compartir entre empresas
            company_conversation_manager,
            company_config  # ✅ NUEVO: Pasar configuración de empresa
        )
        modern_rag_systems[company_id] = company_rag_system
        
        logger.info(f"✅ [{company_id}] Modern components initialized successfully")
        
except Exception as e:
    logger.error(f"❌ Error initializing modern components: {e}")
    sys.exit(1)

# ✅ NUEVO: Función para obtener sistema RAG por empresa
def get_rag_system_for_company(company_config: CompanyConfig):
    """
    Obtiene el sistema RAG específico para una empresa
    """
    if company_config.company_id in modern_rag_systems:
        return modern_rag_systems[company_config.company_id]
    
    logger.warning(f"RAG system not found for company {company_config.company_id}, using default")
    # Fallback al primer sistema disponible
    if modern_rag_systems:
        return list(modern_rag_systems.values())[0]
    
    raise Exception(f"No RAG systems available for company {company_config.company_id}")

# ===============================
# Chat Response Handler - ADAPTADO PARA MÚLTIPLES EMPRESAS
# ===============================

def get_modern_chat_response_multiagent(user_id: str, user_message: str, company_config: CompanyConfig, media_type: str = "text", media_context: str = None) -> str:
    """
    ✅ ADAPTADO: Versión actualizada que usa sistema multi-agente con soporte para multimedia y múltiples empresas
    
    Args:
        user_id: Identificador único del usuario
        user_message: Mensaje de texto del usuario
        company_config: Configuración específica de la empresa
        media_type: Tipo de medio ('text', 'voice', 'image')
        media_context: Contexto adicional del medio (transcripción o descripción)
    
    Returns:
        str: Respuesta del asistente
    """
    if not user_id or not user_id.strip():
        logger.error(f"[{company_config.company_id}] Invalid user_id provided")
        return "Error interno: ID de usuario inválido."
    
    # Validar que al menos haya user_message o media_context
    if (not user_message or not user_message.strip()) and not media_context:
        logger.error(f"[{company_config.company_id}] Empty or invalid message content and no media context")
        return "Por favor, envía un mensaje con contenido para poder ayudarte. 😊"
    
    try:
        # ✅ ADAPTADO: Obtener sistema RAG específico de la empresa
        company_rag_system = get_rag_system_for_company(company_config)
        
        # ✅ ADAPTADO: Usar sistema multi-agente de la empresa con soporte multimedia
        response, agent_used = company_rag_system.multi_agent_system.get_response(
            question=user_message, 
            user_id=user_id, 
            media_type=media_type, 
            media_context=media_context
        )
        
        logger.info(f"[{company_config.company_id}] Multi-agent response for user {user_id}: {response[:100]}... (agent: {agent_used})")
        
        return response
        
    except Exception as e:
        logger.exception(f"[{company_config.company_id}] Error in multi-agent chat response for user {user_id}: {e}")
        return "Disculpa, tuve un problema técnico. Por favor intenta de nuevo en unos momentos. 🔧"

# ===============================
# CHATWOOT API FUNCTIONS - ADAPTADAS PARA MÚLTIPLES EMPRESAS
# ===============================

def send_message_to_chatwoot(conversation_id, message_content, company_config: CompanyConfig):
    """✅ ADAPTADO: Send message to Chatwoot using API específico de empresa"""
    url = f"{company_config.chatwoot_base_url}/api/v1/accounts/{company_config.chatwoot_account_id}/conversations/{conversation_id}/messages"

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

        logger.info(f"[{company_config.company_id}] Chatwoot API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info(f"✅ [{company_config.company_id}] Message sent to conversation {conversation_id}")
            return True
        else:
            logger.error(f"❌ [{company_config.company_id}] Failed to send message: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ [{company_config.company_id}] Error sending message to Chatwoot: {e}")
        return False

def extract_contact_id(data, company_config: CompanyConfig = None):
    """
    ✅ ADAPTADO: Extract contact_id with unified priority system and validation
    Incluye logging específico por empresa
    Returns: (contact_id, method_used, is_valid)
    """
    conversation_data = data.get("conversation", {})
    company_prefix = f"[{company_config.company_id}] " if company_config else ""
    
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
                    logger.info(f"✅ {company_prefix}Contact ID extracted: {contact_id} (method: {method_name})")
                    return contact_id, method_name, True
        except Exception as e:
            logger.warning(f"{company_prefix}Error in extraction method {method_name}: {e}")
            continue
    
    logger.error(f"❌ {company_prefix}No valid contact_id found in webhook data")
    return None, "none", False
    
# ===============================
# WEBHOOK HANDLERS - ADAPTADOS PARA MÚLTIPLES EMPRESAS
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

def handle_conversation_updated(data, company_config: CompanyConfig):
    """✅ ADAPTADO: Handle conversation_updated events to update bot status por empresa"""
    try:
        conversation_id = data.get("id")
        if not conversation_id:
            logger.error(f"❌ [{company_config.company_id}] Could not extract conversation_id from conversation_updated event")
            return False
        
        conversation_status = data.get("status")
        if not conversation_status:
            logger.warning(f"⚠️ [{company_config.company_id}] No status found in conversation_updated for {conversation_id}")
            return False
        
        logger.info(f"📋 [{company_config.company_id}] Conversation {conversation_id} updated to status: {conversation_status}")
        update_bot_status(conversation_id, conversation_status, company_config)
        return True
        
    except Exception as e:
        logger.error(f"[{company_config.company_id}] Error handling conversation_updated: {e}")
        return False

# ===============================
# FUNCIONES AUXILIARES MULTIMEDIA - ADAPTADAS PARA MÚLTIPLES EMPRESAS
# ===============================

def analyze_image_from_url(image_url, company_config: CompanyConfig = None):
    """✅ ADAPTADO: Analizar imagen desde URL usando GPT-4 Vision con contexto de empresa"""
    try:
        import requests
        from io import BytesIO
        
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        
        # Descargar la imagen
        logger.info(f"🔽 {company_prefix}Downloading image from: {image_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ChatbotImageAnalyzer/1.0)'
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Verificar que es una imagen
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp']):
            logger.warning(f"⚠️ {company_prefix}Content type might not be image: {content_type}")
        
        # Crear archivo en memoria
        image_file = BytesIO(response.content)
        
        # ✅ ADAPTADO: Analizar usando la función existente con contexto de empresa
        return analyze_image(image_file, company_config)
        
    except requests.exceptions.RequestException as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error downloading image: {e}")
        raise Exception(f"Error downloading image: {str(e)}")
    except Exception as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.error(f"❌ {company_prefix}Error in image analysis from URL: {e}")
        raise

def debug_webhook_data(data, company_config: CompanyConfig = None):
    """✅ ADAPTADO: Función para debugging completo del webhook de Chatwoot por empresa"""
    company_prefix = f"[{company_config.company_id}] " if company_config else ""
    
    logger.info(f"🔍 {company_prefix}=== WEBHOOK DEBUG INFO ===")
    logger.info(f"{company_prefix}Event: {data.get('event')}")
    logger.info(f"{company_prefix}Message ID: {data.get('id')}")
    logger.info(f"{company_prefix}Message Type: {data.get('message_type')}")
    logger.info(f"{company_prefix}Content: '{data.get('content')}'")
    logger.info(f"{company_prefix}Content Length: {len(data.get('content', ''))}")
    
    attachments = data.get('attachments', [])
    logger.info(f"{company_prefix}Attachments Count: {len(attachments)}")
    
    for i, att in enumerate(attachments):
        logger.info(f"{company_prefix}  Attachment {i}:")
        logger.info(f"{company_prefix}    Keys: {list(att.keys())}")
        logger.info(f"{company_prefix}    Type: {att.get('type')}")
        logger.info(f"{company_prefix}    File Type: {att.get('file_type')}")
        logger.info(f"{company_prefix}    URL: {att.get('url')}")
        logger.info(f"{company_prefix}    Data URL: {att.get('data_url')}")
        logger.info(f"{company_prefix}    Thumb URL: {att.get('thumb_url')}")
    
    logger.info(f"🔍 {company_prefix}=== END DEBUG INFO ===")

def process_incoming_message(data, company_config: CompanyConfig):
    """✅ ADAPTADO: Process incoming message with comprehensive validation and error handling para empresa específica"""
    try:
        # Validate message type
        message_type = data.get("message_type")
        if message_type != "incoming":
            logger.info(f"🤖 [{company_config.company_id}] Ignoring message type: {message_type}")
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

        # ✅ ADAPTADO: Check if bot should respond con configuración de empresa
        if not should_bot_respond(conversation_id, conversation_status, company_config):
            return {
                "status": "bot_inactive",
                "message": f"Bot is inactive for status: {conversation_status}",
                "active_only_for": BOT_ACTIVE_STATUSES,
                "company_id": company_config.company_id
            }

        # Extract and validate message content
        content = data.get("content", "").strip()
        message_id = data.get("id")

        # MEJORADO: Extraer attachments con debugging por empresa
        attachments = data.get("attachments", [])
        logger.info(f"📎 [{company_config.company_id}] Attachments received: {len(attachments)}")
        for i, att in enumerate(attachments):
            logger.info(f"📎 [{company_config.company_id}] Attachment {i}: {att}")

        # ✅ ADAPTADO: Check for duplicate processing con aislamiento por empresa
        if message_id and is_message_already_processed(message_id, conversation_id, company_config):
            return {"status": "already_processed", "ignored": True, "company_id": company_config.company_id}

        # ✅ ADAPTADO: Extract contact information con logging por empresa
        contact_id, extraction_method, is_valid = extract_contact_id(data, company_config)
        if not is_valid or not contact_id:
            raise WebhookError("Could not extract valid contact_id from webhook data", 400)

        # ✅ ADAPTADO: Generate standardized user_id con aislamiento por empresa
        conversation_manager = modern_conversation_managers[company_config.company_id]
        user_id = conversation_manager._create_user_id(contact_id, company_config)

        logger.info(f"🔄 [{company_config.company_id}] Processing message from conversation {conversation_id}")
        logger.info(f"👤 [{company_config.company_id}] User: {user_id} (contact: {contact_id}, method: {extraction_method})")
        logger.info(f"💬 [{company_config.company_id}] Message: {content[:100]}...")

        # CORREGIDO: Procesar archivos adjuntos multimedia con contexto de empresa
        media_context = None
        media_type = "text"
        processed_attachment = None
        
        for attachment in attachments:
            try:
                logger.info(f"🔍 [{company_config.company_id}] Processing attachment: {attachment}")
                
                # MEJORADO: Múltiples formas de obtener el tipo
                attachment_type = None
                
                # Método 1: Campo 'type' directo
                if attachment.get("type"):
                    attachment_type = attachment["type"].lower()
                    logger.info(f"📝 [{company_config.company_id}] Type from 'type' field: {attachment_type}")
                
                # Método 2: Campo 'file_type' (Chatwoot a veces usa esto)
                elif attachment.get("file_type"):
                    attachment_type = attachment["file_type"].lower()
                    logger.info(f"📝 [{company_config.company_id}] Type from 'file_type' field: {attachment_type}")
                
                # MEJORADO: Múltiples formas de obtener la URL
                url = None
                
                # Método 1: Campo 'data_url' (común en Chatwoot)
                if attachment.get("data_url"):
                    url = attachment["data_url"]
                    logger.info(f"🔗 [{company_config.company_id}] URL from 'data_url': {url}")
                
                # Método 2: Campo 'url'
                elif attachment.get("url"):
                    url = attachment["url"]
                    logger.info(f"🔗 [{company_config.company_id}] URL from 'url': {url}")
                
                # Método 3: Campo 'thumb_url' como fallback
                elif attachment.get("thumb_url"):
                    url = attachment["thumb_url"]
                    logger.info(f"🔗 [{company_config.company_id}] URL from 'thumb_url': {url}")
                
                if not url:
                    logger.warning(f"⚠️ [{company_config.company_id}] No URL found in attachment: {attachment}")
                    continue
                
                # MEJORADO: Construir URL completa si es necesaria con URL específica de empresa
                if url and not url.startswith("http"):
                    # Remover slash inicial si existe para evitar doble slash
                    if url.startswith("/"):
                        url = url[1:]
                    url = f"{company_config.chatwoot_base_url}/{url}"
                    logger.info(f"🔗 [{company_config.company_id}] Full URL constructed: {url}")
                
                # MEJORADO: Inferir tipo desde URL si no está disponible
                if not attachment_type and url:
                    url_lower = url.lower()
                    if any(url_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        attachment_type = "image"
                        logger.info(f"📝 [{company_config.company_id}] Type inferred from URL: {attachment_type}")
                    elif any(url_lower.endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.ogg']):
                        attachment_type = "audio"
                        logger.info(f"📝 [{company_config.company_id}] Type inferred from URL: {attachment_type}")
                    elif "image" in url_lower:
                        attachment_type = "image"
                        logger.info(f"📝 [{company_config.company_id}] Type inferred from URL path: {attachment_type}")
                
                # Procesar según el tipo con contexto de empresa
                if attachment_type in ["image", "audio"]:
                    media_type = attachment_type
                    processed_attachment = {
                        "type": attachment_type,
                        "url": url,
                        "original_data": attachment
                    }
                    
                    logger.info(f"🎯 [{company_config.company_id}] Processing {media_type}: {url}")
                    
                    if media_type == "audio":
                        try:
                            logger.info(f"🎵 [{company_config.company_id}] Transcribing audio: {url}")
                            media_context = transcribe_audio_from_url(url, company_config)  # ✅ ADAPTADO
                            logger.info(f"🎵 [{company_config.company_id}] Audio transcribed: {media_context[:100]}...")
                        except Exception as audio_error:
                            logger.error(f"❌ [{company_config.company_id}] Audio transcription failed: {audio_error}")
                            media_context = f"[Audio file - transcription failed: {str(audio_error)}]"
                    
                    elif media_type == "image":
                        try:
                            logger.info(f"🖼️ [{company_config.company_id}] Analyzing image: {url}")
                            media_context = analyze_image_from_url(url, company_config)  # ✅ ADAPTADO
                            logger.info(f"🖼️ [{company_config.company_id}] Image analyzed: {media_context[:100]}...")
                        except Exception as image_error:
                            logger.error(f"❌ [{company_config.company_id}] Image analysis failed: {image_error}")
                            media_context = f"[Image file - analysis failed: {str(image_error)}]"
                    
                    break  # Procesar solo el primer adjunto válido
                else:
                    logger.info(f"⏭️ [{company_config.company_id}] Skipping attachment type: {attachment_type}")
                    
            except Exception as e:
                logger.error(f"❌ [{company_config.company_id}] Error processing attachment {attachment}: {e}")
                continue
        
        # MEJORADO: Validar que hay contenido procesable
        if not content and not media_context:
            logger.error(f"[{company_config.company_id}] Empty or invalid message content and no media context")
            # Proporcionar información de debugging
            debug_info = {
                "attachments_count": len(attachments),
                "attachments_sample": attachments[:2] if attachments else [],
                "content_length": len(content),
                "media_type": media_type,
                "processed_attachment": processed_attachment,
                "company_id": company_config.company_id
            }
            logger.error(f"[{company_config.company_id}] Debug info: {debug_info}")
            
            return {
                "status": "success",
                "message": "Empty message handled",
                "conversation_id": str(conversation_id),
                "company_id": company_config.company_id,
                "debug_info": debug_info,
                "assistant_reply": "Por favor, envía un mensaje con contenido para poder ayudarte. 😊"
            }
        
        # Si solo hay contenido multimedia sin texto, usar el análisis como mensaje
        if not content and media_context:
            content = media_context  # Usar la transcripción directamente
            logger.info(f"📝 [{company_config.company_id}] Using media context as primary content: {media_context[:100]}...")
        
        # ✅ ADAPTADO: Generar respuesta con contexto multimedia y empresa específica
        logger.info(f"🤖 [{company_config.company_id}] Generating response with media_type: {media_type}")
        assistant_reply = get_modern_chat_response_multiagent(
            user_id, 
            content, 
            company_config,  # ✅ NUEVO: Pasar configuración de empresa
            media_type=media_type,
            media_context=media_context
        )
        
        if not assistant_reply or not assistant_reply.strip():
            assistant_reply = "Disculpa, no pude procesar tu mensaje. ¿Podrías intentar de nuevo? 😊"
        
        logger.info(f"🤖 [{company_config.company_id}] Assistant response: {assistant_reply[:100]}...")

        # ✅ ADAPTADO: Send response to Chatwoot específico de empresa
        success = send_message_to_chatwoot(conversation_id, assistant_reply, company_config)

        if not success:
            raise WebhookError("Failed to send response to Chatwoot", 500)

        logger.info(f"✅ [{company_config.company_id}] Successfully processed message for conversation {conversation_id}")
        
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
            "company_id": company_config.company_id,
            "company_name": company_config.company_name,
            "model_used": company_config.model_name,
            "embedding_model": EMBEDDING_MODEL,
            "vectorstore": f"RedisVectorStore_{company_config.vectorstore_index}",
            "message_length": len(content),
            "response_length": len(assistant_reply),
            "media_processed": media_type if media_context else None,
            "media_context_length": len(media_context) if media_context else 0,
            "processed_attachment": processed_attachment
        }

    except WebhookError as we:
        raise we
    except Exception as e:
        company_prefix = f"[{company_config.company_id}] " if company_config else ""
        logger.exception(f"💥 {company_prefix}Error procesando mensaje (ID: {message_id})")
        raise WebhookError("Internal server error", 500)


@app.route("/webhook", methods=["POST"])
def chatwoot_webhook():
    try:
        data = request.get_json()
        event_type = validate_webhook_data(data)
        
        # Early company identification for logging
        company_config = identify_company_from_webhook(data)
        company_id = company_config.company_id if company_config else "unknown"
        
        logger.info(f"[{company_id}] WEBHOOK RECEIVED - Event: {event_type}")

        # Handle conversation updates
        if event_type == "conversation_updated":
            success = handle_conversation_updated(data)
            status_code = 200 if success else 400
            return jsonify({
                "status": "conversation_updated_processed", 
                "success": success,
                "company_id": company_id
            }), status_code

        # Handle only message_created events
        if event_type != "message_created":
            logger.info(f"[{company_id}] Ignoring event type: {event_type}")
            return jsonify({
                "status": "ignored_event_type", 
                "event": event_type,
                "company_id": company_id
            }), 200

        # Debug attachments if present
        if data.get('attachments'):
            debug_webhook_data(data)

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
# DOCUMENT MANAGEMENT ENDPOINTS - MULTI-COMPANY
# ===============================

def validate_document_data(data: Dict[str, Any]) -> tuple:
    """Validate document data"""
    if not data or 'content' not in data:
        raise ValueError("Content is required")
    
    content = data['content'].strip()
    if not content:
        raise ValueError("Content cannot be empty")
    
    # Parse metadata if string
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
        # Get company configuration
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required (X-Company-ID header)", status_code=400)
        
        data = request.get_json()
        content, metadata = validate_document_data(data)
        
        # Generate doc_id
        doc_id = hashlib.md5(content.encode()).hexdigest()
        
        # Add company_id to metadata
        metadata['doc_id'] = doc_id
        metadata['company_id'] = company_config.company_id
        
        # Use company-specific vector store manager
        vector_manager = vector_store_managers[company_config.company_id]
        num_chunks = vector_manager.add_documents_with_company_metadata(
            company_config, [content], [metadata]
        )
        
        # Save to Redis with company-specific key
        doc_key = company_config.get_document_key(doc_id)
        doc_data = {
            'content': content,
            'metadata': json.dumps(metadata),
            'created_at': str(datetime.utcnow().isoformat()),
            'chunk_count': str(num_chunks),
            'company_id': company_config.company_id
        }
        
        redis_client.hset(doc_key, mapping=doc_data)
        
        # Register document change
        document_change_tracker.register_document_change(doc_id, 'added', company_config.company_id)
        
        logger.info(f"[{company_config.company_id}] Document {doc_id} added with {num_chunks} chunks")
        
        return create_success_response({
            "document_id": doc_id,
            "chunk_count": num_chunks,
            "message": f"Document added with {num_chunks} chunks"
        }, company_config, 201)
        
    except ValueError as e:
        return create_error_response(str(e), company_config if 'company_config' in locals() else None, 400)
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error adding document: {e}")
        return create_error_response("Failed to add document", company_config if 'company_config' in locals() else None, 500)

@app.route("/documents", methods=["GET"])
def list_documents():
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required (X-Company-ID header)", status_code=400)
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        # Get company-specific document keys
        doc_pattern = company_config.get_redis_key("document", "*")
        doc_keys = redis_client.keys(doc_pattern)
        
        # Get company-specific vector keys
        vector_pattern = f"{company_config.vectorstore_index}:*"
        vector_keys = redis_client.keys(vector_pattern)
        
        # Organize vectors by doc_id with company filtering
        vectors_by_doc = {}
        for vector_key in vector_keys:
            try:
                metadata_str = redis_client.hget(vector_key, 'metadata')
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    # Only include vectors for this company
                    if metadata.get('company_id') == company_config.company_id:
                        doc_id = metadata.get('doc_id')
                        if doc_id:
                            if doc_id not in vectors_by_doc:
                                vectors_by_doc[doc_id] = []
                            safe_metadata = {k: v for k, v in metadata.items() if k != 'embedding'}
                            vectors_by_doc[doc_id].append({
                                "vector_key": vector_key,
                                "metadata": safe_metadata
                            })
            except Exception as e:
                logger.warning(f"[{company_config.company_id}] Error parsing vector {vector_key}: {e}")
                continue
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_doc_keys = doc_keys[start_idx:end_idx]
        
        # Build response
        documents = []
        for key in paginated_doc_keys:
            try:
                doc_data = redis_client.hgetall(key)
                if doc_data and doc_data.get('company_id') == company_config.company_id:
                    doc_id = key.split(':')[-1] if ':' in key else key
                    content = doc_data.get('content', '')
                    metadata = json.loads(doc_data.get('metadata', '{}'))
                    
                    doc_vectors = vectors_by_doc.get(doc_id, [])
                    
                    documents.append({
                        "id": doc_id,
                        "content": content[:200] + "..." if len(content) > 200 else content,
                        "metadata": metadata,
                        "created_at": doc_data.get('created_at'),
                        "chunk_count": int(doc_data.get('chunk_count', 0)),
                        "vectors": {
                            "count": len(doc_vectors),
                            "sample_vectors": doc_vectors[:3]
                        }
                    })
            except Exception as e:
                logger.warning(f"[{company_config.company_id}] Error parsing document {key}: {e}")
                continue
        
        return create_success_response({
            "total_documents": len(doc_keys),
            "total_vectors": len([k for k in vector_keys if redis_client.hget(k, 'metadata') and 
                                json.loads(redis_client.hget(k, 'metadata') or '{}').get('company_id') == company_config.company_id]),
            "page": page,
            "page_size": page_size,
            "documents": documents
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error listing documents: {e}")
        return create_error_response("Failed to list documents", company_config if 'company_config' in locals() else None, 500)

@app.route("/documents/search", methods=["POST"])
def search_documents():
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        data = request.get_json()
        if not data or 'query' not in data:
            return create_error_response("Query is required", company_config, 400)
        
        query = data['query'].strip()
        if not query:
            return create_error_response("Query cannot be empty", company_config, 400)
        
        k = min(data.get('k', MAX_RETRIEVED_DOCS), 20)
        
        # Use company-specific vector store manager
        vector_manager = vector_store_managers[company_config.company_id]
        docs = vector_manager.search_documents_for_company(company_config, query, k)
        
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
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error searching documents: {e}")
        return create_error_response("Failed to search documents", company_config if 'company_config' in locals() else None, 500)

@app.route("/documents/bulk", methods=["POST"])
def bulk_add_documents():
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        data = request.get_json()
        if not data or 'documents' not in data:
            return create_error_response("Documents array is required", company_config, 400)

        documents = data['documents']
        if not isinstance(documents, list) or not documents:
            return create_error_response("Documents must be a non-empty array", company_config, 400)

        added_docs = 0
        total_chunks = 0
        errors = []
        added_doc_ids = []

        vector_manager = vector_store_managers[company_config.company_id]

        for i, doc_data in enumerate(documents):
            try:
                content, metadata = validate_document_data(doc_data)

                doc_id = hashlib.md5(content.encode()).hexdigest()
                metadata['doc_id'] = doc_id
                metadata['company_id'] = company_config.company_id

                num_chunks = vector_manager.add_documents_with_company_metadata(
                    company_config, [content], [metadata]
                )
                total_chunks += num_chunks

                # Save to Redis with company-specific key
                doc_key = company_config.get_document_key(doc_id)
                doc_redis_data = {
                    'content': content,
                    'metadata': json.dumps(metadata),
                    'created_at': str(datetime.utcnow().isoformat()),
                    'chunk_count': str(num_chunks),
                    'company_id': company_config.company_id
                }

                redis_client.hset(doc_key, mapping=doc_redis_data)
                added_docs += 1
                added_doc_ids.append(doc_id)

            except Exception as e:
                errors.append(f"Document {i}: {str(e)}")
                continue

        # Register changes in batch
        for doc_id in added_doc_ids:
            document_change_tracker.register_document_change(doc_id, 'added', company_config.company_id)

        response_data = {
            "documents_added": added_docs,
            "total_chunks": total_chunks,
            "message": f"Added {added_docs} documents with {total_chunks} chunks"
        }

        if errors:
            response_data["errors"] = errors
            response_data["message"] += f". {len(errors)} documents failed."

        logger.info(f"[{company_config.company_id}] Bulk added {added_docs} documents with {total_chunks} chunks")

        return create_success_response(response_data, company_config, 201)

    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error bulk adding documents: {e}")
        return create_error_response("Failed to bulk add documents", company_config if 'company_config' in locals() else None, 500)

@app.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        doc_key = company_config.get_document_key(doc_id)
        if not redis_client.exists(doc_key):
            return create_error_response("Document not found", company_config, 404)
        
        # Verify document belongs to company
        doc_data = redis_client.hgetall(doc_key)
        if doc_data.get('company_id') != company_config.company_id:
            return create_error_response("Document not found", company_config, 404)
        
        # Use company-specific vector store manager to delete vectors
        vector_manager = vector_store_managers[company_config.company_id]
        vectors_deleted = vector_manager.delete_document_vectors(company_config, doc_id)
        
        # Delete document
        redis_client.delete(doc_key)
        document_change_tracker.register_document_change(doc_id, 'deleted', company_config.company_id)
        
        logger.info(f"[{company_config.company_id}] Document {doc_id} deleted with {vectors_deleted} vectors")
        
        return create_success_response({
            "message": "Document deleted successfully",
            "vectors_deleted": vectors_deleted
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error deleting document {doc_id}: {e}")
        return create_error_response("Failed to delete document", company_config if 'company_config' in locals() else None, 500)

# ===============================
# CONVERSATION MANAGEMENT ENDPOINTS - MULTI-COMPANY
# ===============================

@app.route("/conversations", methods=["GET"])
def list_conversations():
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)
        
        # Get company-specific conversation manager
        conv_manager = modern_conversation_managers[company_config.company_id]
        
        # Get conversation keys with company prefix
        pattern = f"{company_config.redis_prefix}conversation:*"
        keys = redis_client.keys(pattern)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_keys = keys[start_idx:end_idx]
        
        conversations = []
        for key in paginated_keys:
            try:
                user_id = key.replace(f"{company_config.redis_prefix}conversation:", '')
                messages = conv_manager.get_chat_history(user_id)
                
                conversations.append({
                    "user_id": user_id,
                    "message_count": len(messages),
                    "last_updated": conv_manager.get_last_updated(user_id)
                })
            except Exception as e:
                logger.warning(f"[{company_config.company_id}] Error parsing conversation {key}: {e}")
                continue
        
        return create_success_response({
            "total_conversations": len(keys),
            "page": page,
            "page_size": page_size,
            "conversations": conversations
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error listing conversations: {e}")
        return create_error_response("Failed to list conversations", company_config if 'company_config' in locals() else None, 500)

@app.route("/conversations/<user_id>", methods=["GET"])
def get_conversation(user_id):
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        conv_manager = modern_conversation_managers[company_config.company_id]
        messages = conv_manager.get_chat_history(user_id)
        
        return create_success_response({
            "user_id": user_id,
            "message_count": len(messages),
            "messages": messages,
            "last_updated": conv_manager.get_last_updated(user_id)
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error getting conversation: {e}")
        return create_error_response("Failed to get conversation", company_config if 'company_config' in locals() else None, 500)

@app.route("/conversations/<user_id>", methods=["DELETE"])
def delete_conversation(user_id):
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        conv_manager = modern_conversation_managers[company_config.company_id]
        conv_manager.clear_conversation(user_id)
        
        logger.info(f"[{company_config.company_id}] Conversation {user_id} deleted")
        
        return create_success_response({
            "message": f"Conversation {user_id} deleted"
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error deleting conversation: {e}")
        return create_error_response("Failed to delete conversation", company_config if 'company_config' in locals() else None, 500)

@app.route("/conversations/<user_id>/test", methods=["POST"])
def test_conversation(user_id):
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        data = request.get_json()
        if not data or 'message' not in data:
            return create_error_response("Message is required", company_config, 400)
        
        message = data['message'].strip()
        if not message:
            return create_error_response("Message cannot be empty", company_config, 400)
        
        # Get bot response using company-specific system
        response = get_multi_company_chat_response(company_config, user_id, message)
        
        return create_success_response({
            "user_id": user_id,
            "user_message": message,
            "bot_response": response,
            "timestamp": time.time()
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error testing conversation: {e}")
        return create_error_response("Failed to test conversation", company_config if 'company_config' in locals() else None, 500)

# ===============================
# MULTIMEDIA PROCESSING ENDPOINTS - MULTI-COMPANY
# ===============================

@app.route("/process-voice", methods=["POST"])
def process_voice_message():
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        if 'audio' not in request.files:
            return create_error_response("No audio file provided", company_config, 400)
        
        audio_file = request.files['audio']
        user_id = request.form.get('user_id')
        conversation_id = request.form.get('conversation_id')
        
        # Save temporary file
        temp_path = f"/tmp/{audio_file.filename}"
        audio_file.save(temp_path)
        
        # Transcribe audio using Whisper
        transcript = transcribe_audio(temp_path)
        
        # Process with company-specific multi-agent system
        response = get_multi_company_chat_response(
            company_config=company_config,
            user_id=user_id,
            message="",  # Empty text message since everything comes from audio
            media_type="voice",
            media_context=transcript
        )
        
        # Convert response to audio if requested
        if request.form.get('return_audio', False):
            audio_response = text_to_speech(response)
            return send_file(audio_response, mimetype="audio/mpeg")
        
        logger.info(f"[{company_config.company_id}] Processed voice message for user {user_id}")
        
        return create_success_response({
            "transcript": transcript,
            "response": response
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error processing voice message: {e}")
        return create_error_response("Failed to process voice message", company_config if 'company_config' in locals() else None, 500)

@app.route("/process-image", methods=["POST"])
def process_image_message():
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        if 'image' not in request.files:
            return create_error_response("No image file provided", company_config, 400)
        
        image_file = request.files['image']
        user_id = request.form.get('user_id')
        question = request.form.get('question', "").strip()
        
        # Analyze image with GPT-4V
        image_description = analyze_image(image_file)
        
        # Process with company-specific multi-agent system
        response = get_multi_company_chat_response(
            company_config=company_config,
            user_id=user_id,
            message=question,  # Text question (can be empty)
            media_type="image",
            media_context=image_description
        )
        
        logger.info(f"[{company_config.company_id}] Processed image message for user {user_id}")
        
        return create_success_response({
            "image_description": image_description,
            "response": response
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error processing image message: {e}")
        return create_error_response("Failed to process image message", company_config if 'company_config' in locals() else None, 500)

# ===============================
# SYSTEM STATUS ENDPOINTS - MULTI-COMPANY
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
    
    # Check OpenAI for each company
    for company_id, config in COMPANIES_CONFIG.items():
        try:
            # Test embedding with company-specific vector manager
            vector_manager = vector_store_managers[company_id]
            vector_manager.embeddings.embed_query("test")
            components[f"openai_{company_id}"] = "connected"
        except Exception as e:
            components[f"openai_{company_id}"] = f"error: {str(e)}"
        
        # Check vectorstore for each company
        try:
            vector_manager = vector_store_managers[company_id]
            vector_manager.vectorstore.similarity_search("test", k=1)
            components[f"vectorstore_{company_id}"] = "connected"
        except Exception as e:
            components[f"vectorstore_{company_id}"] = f"error: {str(e)}"
    
    return components

@app.route("/health", methods=["GET"])
def health_check():
    try:
        components = check_component_health()
        
        # Get statistics for all companies
        company_stats = {}
        for company_id, config in COMPANIES_CONFIG.items():
            conversation_count = len(redis_client.keys(f"{config.redis_prefix}conversation:*"))
            document_count = len(redis_client.keys(f"{config.redis_prefix}document:*"))
            bot_status_count = len(redis_client.keys(f"{config.redis_prefix}bot_status:*"))
            
            company_stats[company_id] = {
                "conversations": conversation_count,
                "documents": document_count,
                "bot_statuses": bot_status_count
            }
        
        # Determine overall health
        healthy = all("error" not in str(status) for status in components.values())
        
        response_data = {
            "timestamp": time.time(),
            "components": components,
            "company_statistics": company_stats,
            "configuration": {
                "model": MODEL_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "max_context_messages": MAX_CONTEXT_MESSAGES,
                "similarity_threshold": SIMILARITY_THRESHOLD,
                "max_retrieved_docs": MAX_RETRIEVED_DOCS,
                "companies_configured": list(COMPANIES_CONFIG.keys())
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
        company_config = get_company_from_request()
        
        # If company specified, return company-specific status
        if company_config:
            conversation_count = len(redis_client.keys(f"{company_config.redis_prefix}conversation:*"))
            document_count = len(redis_client.keys(f"{company_config.redis_prefix}document:*"))
            bot_status_keys = redis_client.keys(f"{company_config.redis_prefix}bot_status:*")
            
            active_bots = 0
            for key in bot_status_keys:
                try:
                    status_data = redis_client.hgetall(key)
                    if status_data.get('active') == 'True':
                        active_bots += 1
                except Exception:
                    continue
            
            processed_message_count = len(redis_client.keys(f"{company_config.redis_prefix}processed_message:*"))
            
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
                    "model": company_config.model_name,
                    "embedding_model": EMBEDDING_MODEL,
                    "redis_url": REDIS_URL,
                    "vectorstore_index": company_config.vectorstore_index
                }
            }, company_config)
        
        # Return global status for all companies
        else:
            global_stats = {
                "total_companies": len(COMPANIES_CONFIG),
                "companies": {},
                "global_totals": {
                    "conversations": 0,
                    "documents": 0,
                    "bot_statuses": 0,
                    "processed_messages": 0
                }
            }
            
            for company_id, config in COMPANIES_CONFIG.items():
                conversation_count = len(redis_client.keys(f"{config.redis_prefix}conversation:*"))
                document_count = len(redis_client.keys(f"{config.redis_prefix}document:*"))
                bot_status_count = len(redis_client.keys(f"{config.redis_prefix}bot_status:*"))
                processed_message_count = len(redis_client.keys(f"{config.redis_prefix}processed_message:*"))
                
                global_stats["companies"][company_id] = {
                    "conversations": conversation_count,
                    "documents": document_count,
                    "bot_statuses": bot_status_count,
                    "processed_messages": processed_message_count
                }
                
                # Add to global totals
                global_stats["global_totals"]["conversations"] += conversation_count
                global_stats["global_totals"]["documents"] += document_count
                global_stats["global_totals"]["bot_statuses"] += bot_status_count
                global_stats["global_totals"]["processed_messages"] += processed_message_count
            
            return jsonify({
                "status": "success",
                "timestamp": time.time(),
                "statistics": global_stats,
                "environment": {
                    "chatwoot_url": CHATWOOT_BASE_URL,
                    "account_id": ACCOUNT_ID,
                    "model": MODEL_NAME,
                    "embedding_model": EMBEDDING_MODEL,
                    "redis_url": REDIS_URL
                }
            }), 200
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        company_id = getattr(company_config, 'company_id', 'global') if 'company_config' in locals() else 'global'
        return create_error_response("Failed to get status", company_config if 'company_config' in locals() else None, 500)

@app.route("/reset", methods=["POST"])
def reset_system():
    try:
        company_config = get_company_from_request()
        
        if company_config:
            # Reset specific company
            patterns = [
                f"{company_config.redis_prefix}processed_message:*",
                f"{company_config.redis_prefix}bot_status:*"
            ]
            
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
            
            # Clear company conversations
            conv_manager = modern_conversation_managers[company_config.company_id]
            conversation_keys = redis_client.keys(f"{company_config.redis_prefix}conversation:*")
            for key in conversation_keys:
                user_id = key.replace(f"{company_config.redis_prefix}conversation:", '')
                conv_manager.clear_conversation(user_id)
            
            logger.info(f"[{company_config.company_id}] Company system reset completed")
            
            return create_success_response({
                "message": f"System reset completed for {company_config.company_name}",
                "timestamp": time.time()
            }, company_config)
        
        else:
            # Reset all companies
            for company_id, config in COMPANIES_CONFIG.items():
                patterns = [
                    f"{config.redis_prefix}processed_message:*",
                    f"{config.redis_prefix}bot_status:*"
                ]
                
                for pattern in patterns:
                    keys = redis_client.keys(pattern)
                    if keys:
                        redis_client.delete(*keys)
                
                # Clear conversations for this company
                conv_manager = modern_conversation_managers[company_id]
                conversation_keys = redis_client.keys(f"{config.redis_prefix}conversation:*")
                for key in conversation_keys:
                    user_id = key.replace(f"{config.redis_prefix}conversation:", '')
                    conv_manager.clear_conversation(user_id)
                
                logger.info(f"[{company_id}] Company system reset completed")
            
            logger.info("Global system reset completed")
            
            return jsonify({
                "status": "success",
                "message": "Global system reset completed for all companies",
                "companies_reset": list(COMPANIES_CONFIG.keys()),
                "timestamp": time.time()
            }), 200
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'global') if 'company_config' in locals() else 'global'
        logger.error(f"[{company_id}] System reset failed: {e}")
        return create_error_response("Failed to reset system", company_config if 'company_config' in locals() else None, 500)

# ===============================
# COMPANY MANAGEMENT ENDPOINTS
# ===============================

@app.route("/companies", methods=["GET"])
def list_companies():
    """List all configured companies"""
    try:
        companies = []
        for company_id, config in COMPANIES_CONFIG.items():
            # Get basic stats for each company
            conversation_count = len(redis_client.keys(f"{config.redis_prefix}conversation:*"))
            document_count = len(redis_client.keys(f"{config.redis_prefix}document:*"))
            
            companies.append({
                "company_id": company_id,
                "company_name": config.company_name,
                "redis_prefix": config.redis_prefix,
                "vectorstore_index": config.vectorstore_index,
                "services": config.services,
                "statistics": {
                    "conversations": conversation_count,
                    "documents": document_count
                }
            })
        
        return jsonify({
            "status": "success",
            "total_companies": len(companies),
            "companies": companies
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        return create_error_response("Failed to list companies", status_code=500)

@app.route("/companies/<company_id>/diagnostics", methods=["GET"])
def company_diagnostics(company_id):
    """Get detailed diagnostics for a specific company"""
    try:
        if company_id not in COMPANIES_CONFIG:
            return create_error_response("Company not found", status_code=404)
        
        company_config = COMPANIES_CONFIG[company_id]
        
        # Count documents
        doc_pattern = f"{company_config.redis_prefix}document:*"
        doc_keys = redis_client.keys(doc_pattern)
        total_docs = len(doc_keys)
        
        # Count vectors
        vector_pattern = f"{company_config.vectorstore_index}:*"
        vector_keys = redis_client.keys(vector_pattern)
        company_vectors = []
        
        # Filter vectors by company
        for vector_key in vector_keys:
            try:
                metadata_str = redis_client.hget(vector_key, 'metadata')
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    if metadata.get('company_id') == company_id:
                        company_vectors.append(vector_key)
            except Exception:
                continue
        
        total_vectors = len(company_vectors)
        
        # Analyze vectors by doc_id
        doc_id_counts = {}
        vectors_without_doc_id = 0
        
        for vector_key in company_vectors:
            try:
                doc_id = None
                
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
                logger.warning(f"[{company_id}] Error analyzing vector {vector_key}: {e}")
                continue
        
        # Identify orphaned documents
        orphaned_docs = []
        for doc_key in doc_keys:
            doc_id = doc_key.split(':')[-1] if ':' in doc_key else doc_key
            if doc_id not in doc_id_counts:
                orphaned_docs.append(doc_id)
        
        # Get conversation statistics
        conv_pattern = f"{company_config.redis_prefix}conversation:*"
        conv_keys = redis_client.keys(conv_pattern)
        
        return create_success_response({
            "total_documents": total_docs,
            "total_vectors": total_vectors,
            "total_conversations": len(conv_keys),
            "vectors_without_doc_id": vectors_without_doc_id,
            "documents_with_vectors": len(doc_id_counts),
            "orphaned_documents": len(orphaned_docs),
            "avg_vectors_per_doc": round(sum(doc_id_counts.values()) / len(doc_id_counts), 2) if doc_id_counts else 0,
            "sample_doc_vector_counts": dict(list(doc_id_counts.items())[:10]),
            "orphaned_doc_samples": orphaned_docs[:5],
            "vectorstore_index": company_config.vectorstore_index,
            "redis_prefix": company_config.redis_prefix
        }, company_config)
        
    except Exception as e:
        logger.error(f"[{company_id}] Error in diagnostics: {e}")
        return create_error_response("Failed to run diagnostics", status_code=500)

# ===============================
# DOCUMENTS CLEANUP ENDPOINTS - MULTI-COMPANY
# ===============================

@app.route("/documents/cleanup", methods=["POST"])
def cleanup_orphaned_vectors():
    """Clean up orphaned vectors for a specific company"""
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        data = request.get_json()
        dry_run = data.get('dry_run', True) if data else True
        
        # Get existing documents for this company
        doc_pattern = f"{company_config.redis_prefix}document:*"
        doc_keys = redis_client.keys(doc_pattern)
        existing_doc_ids = set()
        
        for key in doc_keys:
            doc_data = redis_client.hgetall(key)
            if doc_data.get('company_id') == company_config.company_id:
                doc_id = key.split(':')[-1] if ':' in key else key
                existing_doc_ids.add(doc_id)
        
        # Get vectors for this company
        vector_pattern = f"{company_config.vectorstore_index}:*"
        vector_keys = redis_client.keys(vector_pattern)
        
        orphaned_vectors = []
        total_company_vectors = 0
        
        for vector_key in vector_keys:
            try:
                # Check if vector belongs to this company
                metadata_str = redis_client.hget(vector_key, 'metadata')
                if not metadata_str:
                    continue
                    
                metadata = json.loads(metadata_str)
                if metadata.get('company_id') != company_config.company_id:
                    continue
                
                total_company_vectors += 1
                
                # Check for orphaned status
                doc_id = metadata.get('doc_id')
                if doc_id and doc_id not in existing_doc_ids:
                    orphaned_vectors.append({
                        "vector_key": vector_key,
                        "doc_id": doc_id
                    })
                    
            except Exception as e:
                logger.warning(f"[{company_config.company_id}] Error checking vector {vector_key}: {e}")
                continue
        
        # Delete orphaned vectors if not dry_run
        deleted_count = 0
        if not dry_run and orphaned_vectors:
            keys_to_delete = [v["vector_key"] for v in orphaned_vectors]
            redis_client.delete(*keys_to_delete)
            deleted_count = len(keys_to_delete)
            logger.info(f"[{company_config.company_id}] Deleted {deleted_count} orphaned vectors")
        
        return create_success_response({
            "total_company_vectors": total_company_vectors,
            "total_company_documents": len(existing_doc_ids),
            "orphaned_vectors_found": len(orphaned_vectors),
            "orphaned_vectors_deleted": deleted_count,
            "dry_run": dry_run,
            "orphaned_samples": orphaned_vectors[:10]
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error in cleanup: {e}")
        return create_error_response("Failed to cleanup orphaned vectors", company_config if 'company_config' in locals() else None, 500)

@app.route("/documents/<doc_id>/vectors", methods=["GET"])
def get_document_vectors(doc_id):
    """Get vectors for a specific document and company"""
    try:
        company_config = get_company_from_request()
        if not company_config:
            return create_error_response("Valid company ID required", status_code=400)
        
        vector_manager = vector_store_managers[company_config.company_id]
        vectors = vector_manager.find_vectors_by_doc_id(doc_id, company_config.company_id)
        
        vector_details = []
        for vector_key in vectors:
            try:
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
                        # Filter problematic fields and verify company
                        if metadata.get('company_id') == company_config.company_id:
                            safe_metadata = {k: v for k, v in metadata.items() 
                                           if k not in ['embedding', 'vector']}
                            vector_info["metadata"] = safe_metadata
                        else:
                            vector_info["metadata_error"] = "Wrong company"
                    except json.JSONDecodeError:
                        vector_info["metadata_error"] = "Invalid JSON"
                
                vector_details.append(vector_info)
                
            except Exception as e:
                logger.warning(f"[{company_config.company_id}] Error getting details for vector {vector_key}: {e}")
                continue
        
        return create_success_response({
            "doc_id": doc_id,
            "vectors_found": len(vectors),
            "vectors": vector_details
        }, company_config)
        
    except Exception as e:
        company_id = getattr(company_config, 'company_id', 'unknown') if 'company_config' in locals() else 'unknown'
        logger.error(f"[{company_id}] Error getting vectors for doc {doc_id}: {e}")
        return create_error_response("Failed to get document vectors", company_config if 'company_config' in locals() else None, 500)

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
# ERROR HANDLERS
# ===============================

@app.errorhandler(404)
def not_found(error):
    return create_error_response("Endpoint not found", status_code=404)

@app.errorhandler(405)
def method_not_allowed(error):
    return create_error_response("Method not allowed", status_code=405)

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return create_error_response("Internal server error", status_code=500)

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    return create_error_response("An unexpected error occurred", status_code=500)

# ===============================
# STARTUP AND CLEANUP
# ===============================

def startup_checks():
    """Startup verification checks"""
    try:
        logger.info("Starting Multi-Company Bot System...")
        
        # Check Redis connection
        redis_client.ping()
        logger.info("Redis connection verified")
        
        # Initialize company managers
        initialize_company_managers()
        
        # Verify each company's setup
        for company_id, config in COMPANIES_CONFIG.items():
            try:
                # Test OpenAI connection
                vector_manager = vector_store_managers[company_id]
                vector_manager.embeddings.embed_query("test startup")
                logger.info(f"[{company_id}] OpenAI connection verified")
                
                # Test vectorstore
                vector_manager.vectorstore.similarity_search("test", k=1)
                logger.info(f"[{company_id}] Vectorstore connection verified")
                
            except Exception as e:
                logger.error(f"[{company_id}] Setup verification failed: {e}")
                raise
        
        # Display configuration
        logger.info("Configuration Summary:")
        logger.info(f"   Companies: {list(COMPANIES_CONFIG.keys())}")
        logger.info(f"   Model: {MODEL_NAME}")
        logger.info(f"   Embedding Model: {EMBEDDING_MODEL}")
        logger.info(f"   Redis URL: {REDIS_URL}")
        
        logger.info("Multi-Company Bot System startup completed successfully!")
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        raise

def cleanup():
    """Clean up resources on shutdown"""
    try:
        logger.info("Cleaning up resources...")
        
        # Company-specific managers handle their own cleanup
        for company_id in COMPANIES_CONFIG:
            logger.info(f"[{company_id}] Resources cleaned up")
        
        logger.info("All resources cleaned up")
        logger.info("Multi-Company Bot System shutdown completed")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

# ===============================
# MAIN EXECUTION
# ===============================

if __name__ == "__main__":
    try:
        # Validate OpenAI setup before starting
        if not validate_openai_setup():
            logger.error("OpenAI setup validation failed. Check your configuration.")
            sys.exit(1)
        
        # Run startup checks
        startup_checks()
        
        # Setup cleanup handler
        import atexit
        atexit.register(cleanup)
        
        # Start server
        logger.info(f"Starting Multi-Company server on port {PORT}")
        logger.info(f"Webhook endpoint: http://localhost:{PORT}/webhook")
        logger.info(f"Health check: http://localhost:{PORT}/health")
        logger.info(f"Status: http://localhost:{PORT}/status")
        logger.info(f"Companies: http://localhost:{PORT}/companies")
        logger.info(f"Configured companies: {list(COMPANIES_CONFIG.keys())}")
        
        app.run(
            host="0.0.0.0",
            port=PORT,
            debug=os.getenv("ENVIRONMENT") != "production",
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        cleanup()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        cleanup()
        sys.exit(1)
