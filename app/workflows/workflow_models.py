# app/workflows/workflow_models.py

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """Tipos de nodos disponibles en workflows"""
    TRIGGER = "trigger"           # Inicio del workflow
    AGENT = "agent"               # Agente conversacional (sales, support, etc.)
    TOOL = "tool"                 # Herramienta/integración
    CONDITION = "condition"       # If/else branching
    SWITCH = "switch"             # Multi-branch (case/when)
    LOOP = "loop"                 # For/while loops
    PARALLEL = "parallel"         # Ejecutar múltiples en paralelo
    MERGE = "merge"               # Unir branches paralelos
    WAIT = "wait"                 # Delay/timeout
    WEBHOOK = "webhook"           # HTTP request
    VARIABLE = "variable"         # Set/get variables
    END = "end"                   # Fin del workflow

class EdgeType(Enum):
    """Tipos de conexiones entre nodos"""
    DIRECT = "direct"             # Conexión directa
    CONDITIONAL = "conditional"   # Con condición
    ON_SUCCESS = "on_success"     # Solo si success
    ON_ERROR = "on_error"         # Solo si error
    FALLBACK = "fallback"         # Alternativa si falla

@dataclass
class WorkflowNode:
    """
    Nodo individual del workflow.
    Representa una acción o decisión.
    """
    id: str                       # Ej: node_abc123
    type: NodeType
    name: str                     # Nombre legible para UI
    config: Dict[str, Any]        # Configuración específica del tipo
    position: Dict[str, float]    # {"x": 100, "y": 200} para visualización
    
    # Metadata
    description: Optional[str] = None
    enabled: bool = True
    retry_config: Optional[Dict] = None  # {"max_attempts": 3, "delay_ms": 1000}
    timeout_ms: Optional[int] = None
    
    def validate(self) -> List[str]:
        """
        Validar configuración del nodo.
        Retorna lista de errores (vacía si todo OK).
        """
        errors = []
        
        # Validaciones por tipo
        if self.type == NodeType.AGENT:
            if "agent_type" not in self.config:
                errors.append(f"Node {self.id}: agent_type required")
            else:
                valid_agents = ["router", "sales", "support", "schedule", "emergency", "availability"]
                if self.config["agent_type"] not in valid_agents:
                    errors.append(f"Node {self.id}: invalid agent_type '{self.config['agent_type']}'")
        
        elif self.type == NodeType.TOOL:
            if "tool_name" not in self.config:
                errors.append(f"Node {self.id}: tool_name required")
        
        elif self.type == NodeType.CONDITION:
            if "condition" not in self.config:
                errors.append(f"Node {self.id}: condition expression required")
        
        elif self.type == NodeType.VARIABLE:
            if "action" not in self.config:
                errors.append(f"Node {self.id}: action (set/get) required")
            elif self.config["action"] == "set":
                if "variable_name" not in self.config:
                    errors.append(f"Node {self.id}: variable_name required for set action")
        
        elif self.type == NodeType.WAIT:
            if "delay_ms" not in self.config:
                errors.append(f"Node {self.id}: delay_ms required")
        
        elif self.type == NodeType.WEBHOOK:
            if "url" not in self.config:
                errors.append(f"Node {self.id}: url required")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializar a dict"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "config": self.config,
            "position": self.position,
            "description": self.description,
            "enabled": self.enabled,
            "retry_config": self.retry_config,
            "timeout_ms": self.timeout_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowNode":
        """Deserializar desde dict"""
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            name=data["name"],
            config=data["config"],
            position=data["position"],
            description=data.get("description"),
            enabled=data.get("enabled", True),
            retry_config=data.get("retry_config"),
            timeout_ms=data.get("timeout_ms")
        )

@dataclass
class WorkflowEdge:
    """
    Conexión entre nodos.
    Define el flujo del workflow.
    """
    id: str                       # Ej: edge_xyz789
    source_node_id: str           # De dónde viene
    target_node_id: str           # A dónde va
    edge_type: EdgeType
    
    # Condición (para edges condicionales)
    condition: Optional[str] = None  # "{{interest}} == true"
    
    # Label para visualización
    label: Optional[str] = None
    
    # Metadata
    description: Optional[str] = None
    enabled: bool = True
    
    def evaluate_condition(self, state: Dict[str, Any]) -> bool:
        """
        Evaluar si esta edge debe ejecutarse dado el estado actual.
        """
        if not self.condition:
            return True  # Sin condición = siempre ejecutar
        
        try:
            from app.workflows.condition_evaluator import ConditionEvaluator
            evaluator = ConditionEvaluator()
            result = evaluator.evaluate(self.condition, state)
            logger.debug(f"Edge {self.id} condition '{self.condition}' evaluated to {result}")
            return result
        except Exception as e:
            logger.error(f"Error evaluating condition for edge {self.id}: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializar a dict"""
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
            "label": self.label,
            "description": self.description,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowEdge":
        """Deserializar desde dict"""
        return cls(
            id=data["id"],
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            edge_type=EdgeType(data["edge_type"]),
            condition=data.get("condition"),
            label=data.get("label"),
            description=data.get("description"),
            enabled=data.get("enabled", True)
        )

@dataclass
class WorkflowGraph:
    """
    Definición completa de un workflow como grafo dirigido.
    Compatible con visualización y ejecución.
    """
    # Identificación
    id: str
    name: str
    description: str
    company_id: str
    
    # Estructura del grafo
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    edges: Dict[str, WorkflowEdge] = field(default_factory=dict)
    
    # Entry point
    start_node_id: Optional[str] = None
    
    # Variables globales del workflow
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Triggers (cuándo ejecutar)
    triggers: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    version: int = 1
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    created_by: str = "system"
    updated_at: Optional[str] = None
    
    # === GRAPH OPERATIONS === #
    
    def add_node(self, node: WorkflowNode):
        """Agregar nodo al grafo"""
        self.nodes[node.id] = node
        
        # Si es el primer nodo o es TRIGGER, marcarlo como start
        if not self.start_node_id or node.type == NodeType.TRIGGER:
            self.start_node_id = node.id
    
    def add_edge(self, edge: WorkflowEdge):
        """Agregar edge al grafo"""
        # Validar que los nodos existen
        if edge.source_node_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_node_id} not found")
        if edge.target_node_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_node_id} not found")
        
        self.edges[edge.id] = edge
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Obtener nodo por ID"""
        return self.nodes.get(node_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Obtener edges que salen de un nodo"""
        return [
            edge for edge in self.edges.values()
            if edge.source_node_id == node_id and edge.enabled
        ]
    
    def get_incoming_edges(self, node_id: str) -> List[WorkflowEdge]:
        """Obtener edges que llegan a un nodo"""
        return [
            edge for edge in self.edges.values()
            if edge.target_node_id == node_id and edge.enabled
        ]
    
    def get_next_nodes(self, node_id: str, state: Dict[str, Any]) -> List[str]:
        """
        Determinar siguientes nodos a ejecutar basado en estado actual.
        Evalúa condiciones de edges.
        """
        outgoing = self.get_outgoing_edges(node_id)
        next_nodes = []
        
        for edge in outgoing:
            if edge.evaluate_condition(state):
                next_nodes.append(edge.target_node_id)
        
        return next_nodes
    
    # === VALIDATION === #
    
    def validate(self) -> Dict[str, List[str]]:
        """
        Validar grafo completo.
        Retorna diccionario con errores y warnings.
        """
        errors = []
        warnings = []
        
        # 1. Debe tener nodos
        if not self.nodes:
            errors.append("Workflow must have at least one node")
            return {"errors": errors, "warnings": warnings}
        
        # 2. Debe tener start node válido
        if not self.start_node_id or self.start_node_id not in self.nodes:
            errors.append("Workflow must have a valid start node")
        
        # 3. Validar cada nodo
        for node in self.nodes.values():
            node_errors = node.validate()
            errors.extend(node_errors)
        
        # 4. Detectar nodos huérfanos (sin incoming edges, excepto start)
        for node_id in self.nodes.keys():
            if node_id != self.start_node_id:
                incoming = self.get_incoming_edges(node_id)
                if not incoming:
                    warnings.append(f"Node {node_id} ({self.nodes[node_id].name}) is orphaned (no incoming edges)")
        
        # 5. Detectar nodos sin salida (dead ends, excepto END)
        for node_id, node in self.nodes.items():
            if node.type != NodeType.END:
                outgoing = self.get_outgoing_edges(node_id)
                if not outgoing:
                    warnings.append(f"Node {node_id} ({node.name}) has no outgoing edges (dead end)")
        
        # 6. Detectar ciclos (loops sin condición de salida pueden ser infinitos)
        cycles = self._detect_cycles()
        if cycles:
            for cycle in cycles:
                cycle_names = [self.nodes[nid].name for nid in cycle]
                warnings.append(f"Potential infinite loop detected: {' → '.join(cycle_names)}")
        
        # 7. Validar que edges referencian nodos existentes
        for edge in self.edges.values():
            if edge.source_node_id not in self.nodes:
                errors.append(f"Edge {edge.id} references non-existent source node: {edge.source_node_id}")
            if edge.target_node_id not in self.nodes:
                errors.append(f"Edge {edge.id} references non-existent target node: {edge.target_node_id}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _detect_cycles(self) -> List[List[str]]:
        """
        Detectar ciclos en el grafo usando DFS.
        Retorna lista de ciclos encontrados.
        """
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node_id: str, path: List[str]):
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for edge in self.get_outgoing_edges(node_id):
                next_node = edge.target_node_id
                
                if next_node not in visited:
                    dfs(next_node, path.copy())
                elif next_node in rec_stack:
                    # Ciclo detectado
                    cycle_start = path.index(next_node)
                    cycle = path[cycle_start:] + [next_node]
                    cycles.append(cycle)
            
            rec_stack.remove(node_id)
        
        # Ejecutar DFS desde cada nodo no visitado
        for node_id in self.nodes.keys():
            if node_id not in visited:
                dfs(node_id, [])
        
        return cycles
    
    # === SERIALIZATION === #
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializar a dict (para JSON/PostgreSQL)"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "company_id": self.company_id,
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            },
            "edges": {
                edge_id: edge.to_dict()
                for edge_id, edge in self.edges.items()
            },
            "start_node_id": self.start_node_id,
            "variables": self.variables,
            "triggers": self.triggers,
            "version": self.version,
            "enabled": self.enabled,
            "tags": self.tags,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "created_by": self.created_by,
            "updated_at": self.updated_at or datetime.utcnow().isoformat()
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serializar a JSON string"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGraph":
        """Deserializar desde dict"""
        
        # CAMBIAR ESTA LÍNEA: Hacer id opcional con auto-generación
        import time
        workflow_id = data.get("id") or f"wf_{data.get('company_id', 'unknown')}_{int(time.time())}"
        
        workflow = cls(
            id=workflow_id,  # Usar el id generado o proporcionado
            name=data["name"],
            description=data.get("description", ""),  # También hacer opcional
            company_id=data["company_id"],
            start_node_id=data.get("start_node_id"),
            variables=data.get("variables", {}),
            triggers=data.get("triggers", []),
            version=data.get("version", 1),
            enabled=data.get("enabled", True),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            created_by=data.get("created_by", "system"),
            updated_at=data.get("updated_at")
        )
        
        # Reconstruir nodos
        for node_data in data.get("nodes", {}).values():
            node = WorkflowNode.from_dict(node_data)
            workflow.add_node(node)
        
        # Reconstruir edges
        for edge_data in data.get("edges", {}).values():
            edge = WorkflowEdge.from_dict(edge_data)
            workflow.add_edge(edge)
        
        return workflow
    
    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowGraph":
        """Deserializar desde JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    # === UTILITY METHODS === #
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Obtener resumen ejecutable del workflow"""
        validation = self.validate()
        
        return {
            "workflow_id": self.id,
            "workflow_name": self.name,
            "company_id": self.company_id,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "start_node": self.start_node_id,
            "node_types": self._count_node_types(),
            "is_valid": len(validation["errors"]) == 0,
            "validation_errors": validation["errors"],
            "validation_warnings": validation["warnings"],
            "enabled": self.enabled
        }
    
    def _count_node_types(self) -> Dict[str, int]:
        """Contar nodos por tipo"""
        counts = {}
        for node in self.nodes.values():
            node_type = node.type.value
            counts[node_type] = counts.get(node_type, 0) + 1
        return counts
    
    def clone(self, new_id: str = None, new_name: str = None) -> "WorkflowGraph":
        """Clonar workflow con nuevo ID"""
        import copy
        cloned = copy.deepcopy(self)
        
        if new_id:
            cloned.id = new_id
        if new_name:
            cloned.name = new_name
        
        cloned.created_at = datetime.utcnow().isoformat()
        cloned.version = 1
        
        return cloned
