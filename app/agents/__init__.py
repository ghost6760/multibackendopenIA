# app/agents/__init__.py

# Base cognitiva (núcleo LangGraph)
from ._cognitive_base import CognitiveAgentBase, AgentState

# Nodos o subgrafos LangGraph
from .router_node import build_router_graph  # 🚀 reemplaza RouterAgent
from .emergency_agent import EmergencyAgent
from .sales_agent import SalesAgent
from .support_agent import SupportAgent
from .schedule_agent import ScheduleAgent
from .availability_agent import AvailabilityAgent
from .planning_agent import PlanningAgent  # opcional si ya está migrado

__all__ = [
    "CognitiveAgentBase",
    "AgentState",
    "build_router_graph",        # 🔹 router node moderno
    "EmergencyAgent",
    "SalesAgent",
    "SupportAgent",
    "ScheduleAgent",
    "AvailabilityAgent",
    "PlanningAgent",
]

