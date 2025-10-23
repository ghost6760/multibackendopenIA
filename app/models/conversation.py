# app/models/conversation.py
# MIGRADO A LANGGRAPH - SIN DEPENDENCIAS DE LANGCHAIN

from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config
import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ConversationManager:
    """Gestión modularizada de conversaciones multi-tenant - Compatible con LangGraph"""
    
    def __init__(self, company_id: str = None, max_messages: int = 10):
        self.company_id = company_id or "default"
        self.company_config = get_company_config(self.company_id)
        
        # Configurar prefijo específico de empresa
        if self.company_config:
            self.redis_prefix = self.company_config.redis_prefix + "conversation:"
        else:
            self.redis_prefix = f"{self.company_id}:conversation:"
        
        self.redis_client = get_redis_client()
        self.max_messages = max_messages
        
        logger.info(f"ConversationManager initialized for company: {self.company_id}")
    
    def _create_user_id(self, contact_id: str) -> str:
        """Generate standardized user ID with company prefix"""
        base_user_id = contact_id
        if not contact_id.startswith("chatwoot_contact_"):
            base_user_id = f"chatwoot_contact_{contact_id}"
        
        return f"{self.company_id}_{base_user_id}"
    
    def _ensure_company_prefix(self, user_id: str) -> str:
        """Asegurar que user_id tenga prefijo de empresa"""
        if not user_id.startswith(f"{self.company_id}_"):
            return f"{self.company_id}_{user_id}"
        return user_id
    
    def _get_redis_key(self, user_id: str) -> str:
        """Generar la clave Redis completa para un usuario"""
        company_user_id = self._ensure_company_prefix(user_id)
        return f"{self.redis_prefix}{company_user_id}"
    
    def get_chat_history_for_graph(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        🆕 FUNCIÓN PARA LANGGRAPH
        Lee el historial de Redis y lo retorna en formato normalizado
        para usar con LangGraph StateGraph.
        
        Args:
            conversation_id: ID de la conversación (user_id)
            
        Returns:
            List[{"role": "user"|"assistant", "content": str}]
        """
        if not conversation_id:
            return []
        
        try:
            company_user_id = self._ensure_company_prefix(conversation_id)
            history_key = self._get_redis_key(conversation_id)
            
            logger.debug(f"📚 [{self.company_id}] Reading chat history for LangGraph:")
            logger.debug(f"   → Conversation ID: {conversation_id}")
            logger.debug(f"   → Redis key: {history_key}")
            
            # Leer directamente de Redis sin usar RedisChatMessageHistory
            if not self.redis_client.exists(history_key):
                logger.debug(f"   → No history found in Redis")
                return []
            
            # Redis almacena mensajes como lista en formato JSON
            messages_raw = self.redis_client.lrange(history_key, 0, -1)
            
            normalized_messages = []
            for msg_bytes in messages_raw:
                try:
                    msg_data = json.loads(msg_bytes)
                    
                    # Normalizar formato independientemente de cómo se almacenó
                    if isinstance(msg_data, dict):
                        # Detectar tipo de mensaje
                        msg_type = msg_data.get('type', '')
                        content = msg_data.get('data', {}).get('content', '')
                        
                        # Normalizar role
                        if msg_type == 'human' or msg_data.get('role') == 'user':
                            role = 'user'
                        elif msg_type == 'ai' or msg_data.get('role') == 'assistant':
                            role = 'assistant'
                        else:
                            # Fallback: si no hay tipo claro, intentar inferir
                            role = msg_data.get('role', 'user')
                        
                        if content:
                            normalized_messages.append({
                                "role": role,
                                "content": content
                            })
                
                except json.JSONDecodeError as e:
                    logger.warning(f"   → Failed to parse message: {e}")
                    continue
            
            logger.debug(f"   → Normalized messages: {len(normalized_messages)}")
            if normalized_messages:
                logger.debug(f"   → Last message: {normalized_messages[-1]['content'][:50]}...")
            
            return normalized_messages
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting chat history for graph: {e}")
            return []
    
    def get_chat_history(self, user_id: str, format_type: str = "dict") -> Any:
        """
        LEGACY - Mantener compatibilidad con código existente
        Get chat history in specified format with company isolation
        """
        if not user_id:
            return [] if format_type in ["dict", "messages"] else None
        
        try:
            company_user_id = self._ensure_company_prefix(user_id)
            history_key = self._get_redis_key(user_id)
            
            logger.debug(f"📚 [{self.company_id}] Retrieving chat history (legacy):")
            logger.debug(f"   → User: {user_id}")
            logger.debug(f"   → Redis key: {history_key}")
            
            exists_in_redis = self.redis_client.exists(history_key)
            logger.debug(f"   → Exists in Redis: {exists_in_redis}")
            
            if not exists_in_redis:
                return [] if format_type in ["dict", "messages"] else None
            
            # Usar la nueva función normalizada
            messages = self.get_chat_history_for_graph(user_id)
            
            logger.debug(f"   → Messages found: {len(messages)}")
            if messages:
                logger.debug(f"   → Last message: {messages[-1]['content'][:50]}...")
            
            if format_type == "dict":
                return messages
            elif format_type == "messages":
                # Convertir a formato de objetos si es necesario
                # (para compatibilidad con código legacy que espera objetos)
                return messages
            elif format_type == "langchain":
                # Para compatibilidad legacy - retornar None ya que no usamos LangChain
                logger.warning(f"   → 'langchain' format requested but not supported in LangGraph mode")
                return None
            
            return messages
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting chat history: {e}")
            return [] if format_type in ["dict", "messages"] else None
    
    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """
        Add message to history with company isolation
        MANTIENE EL FORMATO DE ALMACENAMIENTO ORIGINAL EN REDIS
        """
        # Defensive normalization: ensure content is a string to avoid AttributeError on .strip()
        try:
            original_content = content  # Mantener referencia para debug
    
            # If content is None, normalize to empty string
            if content is None:
                content = ""
            # If content is not a string, try to extract common keys (dict from agents) or coerce to str
            elif not isinstance(content, str):
                try:
                    if isinstance(content, dict):
                        # Prefer explicit textual keys in this order
                        content = (
                            content.get("text")
                            or content.get("response")
                            or content.get("result")
                            or content.get("output")
                            or content.get("raw")
                        )
                        # If we found a nested dict in 'raw' or similar, try to extract text there too
                        if isinstance(content, dict):
                            content = (
                                content.get("text")
                                or content.get("response")
                                or str(content)
                            )
                        # If still not a string, coerce to string representation
                        if content is None:
                            content = ""
                        elif not isinstance(content, str):
                            content = str(content)
                    else:
                        # Non-dict non-string object: coerce to string
                        content = str(content)
                except Exception:
                    # On any unexpected issue, coerce to string as last resort
                    content = str(content)
        except Exception:
            # Safety net: ensure content is a string
            content = str(content)
    
        # 🔍 DEBUG: Log type and keys of original content (before normalization)
        try:
            logger.debug(
                f"[{self.company_id}] add_message normalized content from type {type(original_content)}; "
                f"keys={list(original_content.keys()) if isinstance(original_content, dict) else None}"
            )
        except Exception:
            logger.debug(f"[{self.company_id}] add_message could not inspect original_content safely")
    
        # If user_id missing or content empty after normalization, bail out
        if not user_id or not content.strip():
            return False
    
        try:
            company_user_id = self._ensure_company_prefix(user_id)
            history_key = self._get_redis_key(user_id)
            
            # Crear mensaje en formato compatible con RedisChatMessageHistory
            # para no romper historiales existentes
            if role == "user":
                message_data = {
                    "type": "human",
                    "data": {
                        "content": content,
                        "additional_kwargs": {},
                        "type": "human"
                    }
                }
            elif role == "assistant":
                message_data = {
                    "type": "ai",
                    "data": {
                        "content": content,
                        "additional_kwargs": {},
                        "type": "ai"
                    }
                }
            else:
                logger.warning(f"Unknown role: {role}, defaulting to user")
                message_data = {
                    "type": "human",
                    "data": {
                        "content": content,
                        "additional_kwargs": {},
                        "type": "human"
                    }
                }
            
            # Agregar mensaje a Redis
            self.redis_client.rpush(history_key, json.dumps(message_data))
            
            # Aplicar ventana de mensajes
            self._apply_message_window_direct(history_key)
            
            # Establecer TTL (7 días)
            self.redis_client.expire(history_key, 604800)
            
            logger.debug(f"[{self.company_id}] Message added for user {company_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error adding message: {e}")
            return False

    
    def _apply_message_window_direct(self, history_key: str):
        """Aplicar ventana deslizante directamente en Redis"""
        try:
            total_messages = self.redis_client.llen(history_key)
            if total_messages > self.max_messages:
                # Eliminar mensajes antiguos
                messages_to_remove = total_messages - self.max_messages
                for _ in range(messages_to_remove):
                    self.redis_client.lpop(history_key)
                    
        except Exception as e:
            logger.error(f"[{self.company_id}] Error applying message window: {e}")
    
    def _apply_message_window(self, user_id: str):
        """LEGACY - mantener compatibilidad"""
        history_key = self._get_redis_key(user_id)
        self._apply_message_window_direct(history_key)
    
    def list_conversations(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List conversations specific to company"""
        try:
            pattern = f"{self.redis_prefix}*"
            all_keys = self.redis_client.keys(pattern)
            
            # Extract user IDs (removing company prefix)
            user_ids = []
            for key in all_keys:
                if key.startswith(self.redis_prefix):
                    user_id = key[len(self.redis_prefix):]
                    user_ids.append(user_id)
            
            # Pagination
            total_conversations = len(user_ids)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_user_ids = user_ids[start_idx:end_idx]
            
            conversations = []
            for user_id in paginated_user_ids:
                try:
                    details = self.get_conversation_details(user_id)
                    if details:
                        conversations.append(details)
                except Exception as e:
                    logger.warning(f"[{self.company_id}] Error getting details for {user_id}: {e}")
                    continue
            
            return {
                "company_id": self.company_id,
                "total_conversations": total_conversations,
                "page": page,
                "page_size": page_size,
                "conversations": conversations
            }
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error listing conversations: {e}")
            return {
                "company_id": self.company_id,
                "total_conversations": 0,
                "page": page,
                "page_size": page_size,
                "conversations": []
            }
    
    def get_conversation_details(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a conversation"""
        try:
            if not user_id:
                return None
            
            company_user_id = self._ensure_company_prefix(user_id)
            messages = self.get_chat_history_for_graph(user_id)
            
            if not messages:
                return None
            
            # Calculate stats
            user_messages = [msg for msg in messages if msg["role"] == "user"]
            assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
            
            # Get last activity timestamp
            last_updated = None
            try:
                history_key = self._get_redis_key(user_id)
                if self.redis_client.exists(history_key):
                    last_updated = time.time()
            except:
                pass
            
            return {
                "company_id": self.company_id,
                "user_id": user_id,
                "full_user_id": company_user_id,
                "message_count": len(messages),
                "user_message_count": len(user_messages),
                "assistant_message_count": len(assistant_messages),
                "messages": messages[-10:],  # Last 10 messages for preview
                "last_updated": last_updated,
                "created_at": None
            }
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting conversation details for {user_id}: {e}")
            return None
    
    def clear_conversation(self, user_id: str) -> bool:
        """Clear/delete a conversation specific to company"""
        try:
            if not user_id:
                return False
            
            company_user_id = self._ensure_company_prefix(user_id)
            history_key = self._get_redis_key(user_id)
            
            # Clear from Redis
            if self.redis_client.exists(history_key):
                self.redis_client.delete(history_key)
            
            logger.info(f"[{self.company_id}] Cleared conversation for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error clearing conversation for {user_id}: {e}")
            return False
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics for this company"""
        try:
            pattern = f"{self.redis_prefix}*"
            all_keys = self.redis_client.keys(pattern)
            
            total_conversations = len(all_keys)
            total_messages = 0
            active_conversations = 0
            
            for key in all_keys[:100]:  # Limit for performance
                try:
                    if key.startswith(self.redis_prefix):
                        user_id = key[len(self.redis_prefix):]
                        messages = self.get_chat_history_for_graph(user_id)
                        if messages:
                            total_messages += len(messages)
                            active_conversations += 1
                except:
                    continue
            
            return {
                "company_id": self.company_id,
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "total_messages": total_messages,
                "average_messages_per_conversation": round(total_messages / max(active_conversations, 1), 2)
            }
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting conversation stats: {e}")
            return {
                "company_id": self.company_id,
                "total_conversations": 0,
                "active_conversations": 0,
                "total_messages": 0,
                "average_messages_per_conversation": 0
            }
