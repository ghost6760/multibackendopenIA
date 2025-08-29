from app.services.redis_service import get_redis_client
from app.config.company_config import get_company_config, CompanyConfig
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
import logging
import json
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ConversationManager:
    """Gestión modularizada de conversaciones multi-empresa"""
    
    def __init__(self, company_id: str = "default", max_messages: int = 10):
        self.redis_client = get_redis_client()
        self.company_config = get_company_config(company_id)
        self.company_id = company_id
        self.max_messages = max_messages
        self.redis_prefix = self.company_config.redis_prefix
        self.message_histories = {}
    
    def _create_user_id(self, contact_id: str) -> str:
        """Generate standardized user ID with company prefix"""
        if not contact_id.startswith(f"{self.company_id}_contact_"):
            return f"{self.company_id}_contact_{contact_id}"
        return contact_id
    
    def _get_conversation_key(self, user_id: str) -> str:
        """Get Redis key for conversation with company prefix"""
        return f"{self.redis_prefix}conversation:{user_id}"
    
    def _get_chat_history_key(self, user_id: str) -> str:
        """Get Redis key for chat history with company prefix"""
        return f"{self.redis_prefix}chat_history:{user_id}"
    
    def get_chat_history(self, user_id: str, format_type: str = "dict"):
        """Get chat history in specified format"""
        if not user_id:
            return [] if format_type == "dict" else None
        
        try:
            redis_history = self._get_or_create_redis_history(user_id)
            
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
            logger.error(f"Error getting chat history for {self.company_id}/{user_id}: {e}")
            return [] if format_type == "dict" else None
    
    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Add message to history"""
        if not user_id or not content.strip():
            return False
        
        try:
            history = self._get_or_create_redis_history(user_id)
            
            if role == "user":
                history.add_user_message(content)
            elif role == "assistant":
                history.add_ai_message(content)
            
            self._apply_message_window(user_id)
            
            # Update conversation metadata
            self._update_conversation_metadata(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding message for {self.company_id}/{user_id}: {e}")
            return False
    
    def _get_or_create_redis_history(self, user_id: str):
        """Get or create Redis chat history with company prefix"""
        history_key = self._get_chat_history_key(user_id)
        
        if history_key not in self.message_histories:
            from flask import current_app
            redis_url = current_app.config['REDIS_URL']
            
            self.message_histories[history_key] = RedisChatMessageHistory(
                session_id=user_id,
                url=redis_url,
                key_prefix=f"{self.redis_prefix}chat_history:",
                ttl=604800  # 7 días
            )
        
        return self.message_histories[history_key]
    
    def _apply_message_window(self, user_id: str):
        """Apply sliding window to messages"""
        try:
            history_key = self._get_chat_history_key(user_id)
            history = self.message_histories.get(history_key)
            if not history:
                return
            
            messages = history.messages
            if len(messages) > self.max_messages:
                messages_to_keep = messages[-self.max_messages:]
                history.clear()
                for message in messages_to_keep:
                    history.add_message(message)
                    
        except Exception as e:
            logger.error(f"Error applying message window for {self.company_id}/{user_id}: {e}")
    
    def _update_conversation_metadata(self, user_id: str):
        """Update conversation metadata"""
        try:
            conversation_key = self._get_conversation_key(user_id)
            metadata = {
                'company_id': self.company_id,
                'last_updated': str(time.time()),
                'updated_at': str(time.time())
            }
            
            self.redis_client.hset(conversation_key, mapping=metadata)
            self.redis_client.expire(conversation_key, 604800)  # 7 days TTL
            
        except Exception as e:
            logger.error(f"Error updating conversation metadata: {e}")
    
    def list_conversations(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """List all conversations for this company with pagination"""
        try:
            # Get all conversation keys for this company
            pattern = f"{self.redis_prefix}conversation:*"
            all_keys = self.redis_client.keys(pattern)
            
            # Extract user IDs
            user_ids = []
            for key in all_keys:
                if key.startswith(f"{self.redis_prefix}conversation:"):
                    user_id = key[len(f"{self.redis_prefix}conversation:"):]
                    user_ids.append(user_id)
            
            # Pagination
            total_conversations = len(user_ids)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_user_ids = user_ids[start_idx:end_idx]
            
            conversations = []
            for user_id in paginated_user_ids:
                try:
                    # Get conversation details
                    details = self.get_conversation_details(user_id)
                    if details:
                        conversations.append(details)
                except Exception as e:
                    logger.warning(f"Error getting details for conversation {self.company_id}/{user_id}: {e}")
                    continue
            
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "total_conversations": total_conversations,
                "page": page,
                "page_size": page_size,
                "conversations": conversations
            }
            
        except Exception as e:
            logger.error(f"Error listing conversations for {self.company_id}: {e}")
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
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
            
            # Get chat history
            messages = self.get_chat_history(user_id, format_type="dict")
            
            if not messages:
                return None
            
            # Calculate stats
            user_messages = [msg for msg in messages if msg["role"] == "user"]
            assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
            
            # Get last activity timestamp
            last_updated = None
            try:
                conversation_key = self._get_conversation_key(user_id)
                if self.redis_client.exists(conversation_key):
                    metadata = self.redis_client.hgetall(conversation_key)
                    last_updated = metadata.get('last_updated')
                    if not last_updated:
                        last_updated = time.time()
            except:
                pass
            
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "user_id": user_id,
                "message_count": len(messages),
                "user_message_count": len(user_messages),
                "assistant_message_count": len(assistant_messages),
                "messages": messages[-10:],  # Last 10 messages for preview
                "last_updated": last_updated,
                "created_at": None  # Would need to be tracked separately if needed
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation details for {self.company_id}/{user_id}: {e}")
            return None
    
    def clear_conversation(self, user_id: str) -> bool:
        """Clear/delete a conversation for this company"""
        try:
            if not user_id:
                return False
            
            # Clear from message histories cache
            history_key = self._get_chat_history_key(user_id)
            if history_key in self.message_histories:
                history = self.message_histories[history_key]
                history.clear()
                del self.message_histories[history_key]
            
            # Clear from Redis directly
            conversation_key = self._get_conversation_key(user_id)
            
            keys_to_delete = []
            
            # Check if keys exist and add to deletion list
            if self.redis_client.exists(history_key):
                keys_to_delete.append(history_key)
            
            if self.redis_client.exists(conversation_key):
                keys_to_delete.append(conversation_key)
            
            # Delete all related keys
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
            
            logger.info(f"Cleared conversation for {self.company_id}/{user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing conversation for {self.company_id}/{user_id}: {e}")
            return False

    def get_last_updated(self, user_id: str) -> Optional[str]:
        """Get last updated timestamp for a conversation"""
        try:
            conversation_key = self._get_conversation_key(user_id)
            metadata = self.redis_client.hgetall(conversation_key)
            return metadata.get('last_updated')
        except Exception as e:
            logger.error(f"Error getting last updated for {self.company_id}/{user_id}: {e}")
            return None
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get overall conversation statistics for this company"""
        try:
            # Get all conversation keys for this company
            pattern = f"{self.redis_prefix}conversation:*"
            all_keys = self.redis_client.keys(pattern)
            
            total_conversations = len(all_keys)
            
            # Count messages across all conversations
            total_messages = 0
            active_conversations = 0
            
            for key in all_keys[:100]:  # Limit to first 100 to avoid performance issues
                try:
                    if key.startswith(f"{self.redis_prefix}conversation:"):
                        user_id = key[len(f"{self.redis_prefix}conversation:"):]
                        messages = self.get_chat_history(user_id, format_type="dict")
                        if messages:
                            total_messages += len(messages)
                            active_conversations += 1
                except:
                    continue
            
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "total_messages": total_messages,
                "average_messages_per_conversation": round(total_messages / max(active_conversations, 1), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation stats for {self.company_id}: {e}")
            return {
                "company_id": self.company_id,
                "company_name": self.company_config.company_name,
                "total_conversations": 0,
                "active_conversations": 0,
                "total_messages": 0,
                "average_messages_per_conversation": 0
            }

class MultiCompanyConversationManager:
    """Gestor de conversaciones para múltiples empresas"""
    
    def __init__(self):
        self.company_managers = {}
    
    def get_manager_for_company(self, company_id: str) -> ConversationManager:
        """Obtener gestor de conversaciones para una empresa específica"""
        if company_id not in self.company_managers:
            self.company_managers[company_id] = ConversationManager(company_id)
        
        return self.company_managers[company_id]
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas globales de todas las empresas"""
        global_stats = {
            "total_companies": len(self.company_managers),
            "companies": {},
            "global_totals": {
                "conversations": 0,
                "messages": 0,
                "active_conversations": 0
            }
        }
        
        for company_id, manager in self.company_managers.items():
            try:
                company_stats = manager.get_conversation_stats()
                global_stats["companies"][company_id] = company_stats
                
                # Agregar a totales globales
                global_stats["global_totals"]["conversations"] += company_stats.get("total_conversations", 0)
                global_stats["global_totals"]["messages"] += company_stats.get("total_messages", 0)
                global_stats["global_totals"]["active_conversations"] += company_stats.get("active_conversations", 0)
                
            except Exception as e:
                logger.error(f"Error getting stats for company {company_id}: {e}")
                continue
        
        return global_stats
