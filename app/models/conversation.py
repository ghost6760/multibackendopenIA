from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
import logging
import json
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ConversationManager:
    """Gestión modularizada de conversaciones multi-tenant"""
    
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
        self.message_histories = {}
        
        logger.info(f"ConversationManager initialized for company: {self.company_id}")
    
    def _create_user_id(self, contact_id: str) -> str:
        """Generate standardized user ID with company prefix"""
        # Agregar prefijo de empresa para evitar colisiones
        base_user_id = contact_id
        if not contact_id.startswith("chatwoot_contact_"):
            base_user_id = f"chatwoot_contact_{contact_id}"
        
        # Agregar prefijo de empresa
        return f"{self.company_id}_{base_user_id}"
    
    def get_chat_history(self, user_id: str, format_type: str = "dict"):
        """Get chat history in specified format with company isolation"""
        if not user_id:
            return [] if format_type == "dict" else None
        
        try:
            # Asegurar que user_id tenga prefijo de empresa
            company_user_id = self._ensure_company_prefix(user_id)
            redis_history = self._get_or_create_redis_history(company_user_id)
            
            if format_type == "langchain":
                return redis_history
            elif format_type == "messages":
                return redis_history.messages
            elif format_type == "dict":
                messages = redis_history.messages
                return [
                    {
                        "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                        "content": msg.content
                    }
                    for msg in messages
                ]
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error getting chat history: {e}")
            return [] if format_type == "dict" else None
    
    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Add message to history with company isolation"""
        if not user_id or not content.strip():
            return False
        
        try:
            company_user_id = self._ensure_company_prefix(user_id)
            history = self._get_or_create_redis_history(company_user_id)
            
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            
            self._apply_message_window(company_user_id)
            
            # Log con contexto de empresa
            logger.debug(f"[{self.company_id}] Message added for user {company_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error adding message: {e}")
            return False
    
    def _ensure_company_prefix(self, user_id: str) -> str:
        """Asegurar que user_id tenga prefijo de empresa"""
        if not user_id.startswith(f"{self.company_id}_"):
            return f"{self.company_id}_{user_id}"
        return user_id
    
    def _get_or_create_redis_history(self, user_id: str):
        """Get or create Redis chat history with company-specific key"""
        if user_id not in self.message_histories:
            from flask import current_app
            redis_url = current_app.config['REDIS_URL']
            
            # Clave específica de empresa
            session_key = f"{self.redis_prefix}{user_id}"
            
            self.message_histories[user_id] = RedisChatMessageHistory(
                session_id=session_key,
                url=redis_url,
                key_prefix="",  # Ya incluido en session_id
                ttl=604800  # 7 días
            )
        
        return self.message_histories[user_id]
    
    def _apply_message_window(self, user_id: str):
        """Apply sliding window to messages"""
        try:
            history = self.message_histories.get(user_id)
            if not history:
                return
            
            messages = history.messages
            if len(messages) > self.max_messages:
                messages_to_keep = messages[-self.max_messages:]
                history.clear()
                for message in messages_to_keep:
                    history.add_message(message)
                    
        except Exception as e:
            logger.error(f"[{self.company_id}] Error applying message window: {e}")
    
    def list_conversations(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List conversations specific to company"""
        try:
            # Buscar solo conversaciones de esta empresa
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
            messages = self.get_chat_history(company_user_id, format_type="dict")
            
            if not messages:
                return None
            
            # Calculate stats
            user_messages = [msg for msg in messages if msg["role"] == "user"]
            assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
            
            # Get last activity timestamp
            last_updated = None
            try:
                history_key = f"{self.redis_prefix}{company_user_id}"
                if self.redis_client.exists(history_key):
                    last_updated = time.time()
            except:
                pass
            
            return {
                "company_id": self.company_id,
                "user_id": user_id,  # Sin prefijo para interfaz
                "full_user_id": company_user_id,  # Con prefijo para identificación
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
            
            # Clear from message histories cache
            if company_user_id in self.message_histories:
                history = self.message_histories[company_user_id]
                history.clear()
                del self.message_histories[company_user_id]
            
            # Clear from Redis directly
            history_key = f"{self.redis_prefix}{company_user_id}"
            
            keys_to_delete = []
            if self.redis_client.exists(history_key):
                keys_to_delete.append(history_key)
            
            # Delete all related keys
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
            
            logger.info(f"[{self.company_id}] Cleared conversation for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.company_id}] Error clearing conversation for {user_id}: {e}")
            return False
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics for this company"""
        try:
            # Get conversations specific to this company
            pattern = f"{self.redis_prefix}*"
            all_keys = self.redis_client.keys(pattern)
            
            total_conversations = len(all_keys)
            total_messages = 0
            active_conversations = 0
            
            for key in all_keys[:100]:  # Limit for performance
                try:
                    if key.startswith(self.redis_prefix):
                        user_id = key[len(self.redis_prefix):]
                        messages = self.get_chat_history(user_id, format_type="dict")
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
