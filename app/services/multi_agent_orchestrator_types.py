# app/services/multi_agent_orchestrator_types.py
"""
Tipos y estados para MultiAgentOrchestrator con LangGraph
"""
from typing import TypedDict, Literal, Optional, List, Dict, Any
from datetime import datetime

class OrchestratorState(TypedDict):
    """Estado del grafo de orquestación"""
    # Input
    question: str
    user_id: str
    conversation_id: Optional[str]
    media_type: str
    media_context: Optional[Dict[str, Any]]
    
    # Chat history
    chat_history: List[Any]
    
    # Classification
    intent: Optional[str]
    confidence: float
    keywords: List[str]
    reasoning: str
    
    # Agent execution
    current_agent: Optional[str]
    agent_response: Optional[str]
    agent_metadata: Dict[str, Any]
    
    # Validation
    is_valid: bool
    validation_errors: List[str]
    retry_count: int
    
    # Output
    final_response: str
    execution_time: float
    timestamp: str
    
    # Error handling
    error_message: Optional[str]
    fallback_used: bool

# Tipos de intención
IntentType = Literal["EMERGENCY", "SALES", "SCHEDULE", "SUPPORT", "AVAILABILITY"]

# Decisiones de routing
RoutingDecision = Literal["emergency", "sales", "schedule", "support", "availability"]

# Decisiones de validación
ValidationDecision = Literal["save", "retry", "fallback", "end"]
