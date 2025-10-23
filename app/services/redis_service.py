import redis
from flask import current_app, g
import logging

logger = logging.getLogger(__name__)

def get_redis_client():
    """Get Redis client from Flask g object or create new one"""
    if 'redis_client' not in g:
        g.redis_client = redis.from_url(
            current_app.config['REDIS_URL'], 
            decode_responses=True
        )
    return g.redis_client

def init_redis(app):
    """Initialize Redis connection"""
    try:
        client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)
        client.ping()
        logger.info("✅ Redis connection successful")
        return client
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise

def close_redis(e=None):
    """Close Redis connection"""
    client = g.pop('redis_client', None)
    if client is not None:
        client.close()

def get_company_redis_key(company_id: str, key_type: str, identifier: str = "") -> str:
    """Generate company-specific Redis key"""
    from app.config.company_config import get_company_config
    from app.config.constants import REDIS_KEY_PATTERNS
    
    config = get_company_config(company_id)
    if config:
        prefix = config.redis_prefix
    else:
        prefix = f"{company_id}:"
    
    pattern = REDIS_KEY_PATTERNS.get(key_type, "{company_prefix}{key_type}:")
    base_key = pattern.format(company_prefix=prefix, company_id=company_id, key_type=key_type)
    
    if identifier:
        return f"{base_key}{identifier}"
    return base_key


def serialize_chat_message(message: dict) -> str:
    """
    Serializar mensaje de chat para almacenar en Redis.
    Compatible con get_chat_history_for_graph.
    
    Args:
        message: Dict con 'role' y 'content'
    
    Returns:
        str: JSON serializado
    """
    import json
    
    # Normalizar formato del mensaje
    normalized = {
        "role": message.get("role", "user"),
        "content": message.get("content", ""),
        "timestamp": message.get("timestamp")
    }
    
    # Añadir metadata adicional si existe
    if "metadata" in message:
        normalized["metadata"] = message["metadata"]
    
    return json.dumps(normalized, ensure_ascii=False)


def deserialize_chat_message(message_str: str) -> dict:
    """
    Deserializar mensaje de chat desde Redis.
    Compatible con get_chat_history_for_graph.
    
    Args:
        message_str: String JSON del mensaje
    
    Returns:
        dict: Mensaje deserializado
    """
    import json
    
    try:
        message = json.loads(message_str)
        
        # Normalizar el formato para compatibilidad
        return {
            "role": message.get("role", "user"),
            "content": message.get("content", ""),
            "timestamp": message.get("timestamp"),
            "metadata": message.get("metadata", {})
        }
    except json.JSONDecodeError as e:
        logger.error(f"Error deserializing chat message: {e}")
        # Retornar mensaje por defecto si falla
        return {
            "role": "user",
            "content": message_str,
            "timestamp": None,
            "metadata": {}
        }


def get_chat_history_for_graph(client, session_id: str, company_id: str, max_messages: int = 20) -> list:
    """
    Obtener historial de chat formateado para StateGraph.
    
    Args:
        client: Cliente Redis
        session_id: ID de la sesión
        company_id: ID de la empresa
        max_messages: Máximo número de mensajes a retornar
    
    Returns:
        list: Lista de mensajes en formato compatible con AgentState
    """
    try:
        # Generar clave de Redis para historial
        history_key = get_company_redis_key(company_id, "chat_history", session_id)
        
        # Obtener mensajes de Redis (últimos max_messages)
        raw_messages = client.lrange(history_key, -max_messages, -1)
        
        # Deserializar mensajes
        messages = []
        for raw_msg in raw_messages:
            try:
                msg = deserialize_chat_message(raw_msg)
                messages.append(msg)
            except Exception as e:
                logger.warning(f"Failed to deserialize message: {e}")
                continue
        
        logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")
        return messages
        
    except Exception as e:
        logger.error(f"Error getting chat history for graph: {e}")
        return []


def save_chat_message_to_redis(client, session_id: str, company_id: str, role: str, content: str, metadata: dict = None):
    """
    Guardar mensaje de chat en Redis de forma compatible con get_chat_history_for_graph.
    
    Args:
        client: Cliente Redis
        session_id: ID de la sesión
        company_id: ID de la empresa
        role: Rol del mensaje ('user', 'assistant', 'system')
        content: Contenido del mensaje
        metadata: Metadata adicional opcional
    """
    import json
    from datetime import datetime
    
    try:
        # Construir mensaje
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if metadata:
            message["metadata"] = metadata
        
        # Serializar
        serialized = serialize_chat_message(message)
        
        # Generar clave
        history_key = get_company_redis_key(company_id, "chat_history", session_id)
        
        # Guardar en Redis (añadir al final de la lista)
        client.rpush(history_key, serialized)
        
        # Opcional: Limitar tamaño del historial (mantener últimos 100 mensajes)
        client.ltrim(history_key, -100, -1)
        
        # Establecer TTL de 7 días
        client.expire(history_key, 7 * 24 * 60 * 60)
        
        logger.debug(f"Saved {role} message to session {session_id}")
        
    except Exception as e:
        logger.error(f"Error saving chat message to Redis: {e}")
