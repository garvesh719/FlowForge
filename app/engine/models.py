from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    COMPUTATION = "computation"
    TOOL = "tool"


class NodeConfig(BaseModel):
    """
    Definition of a node in the workflow graph.
    - COMPUTATION nodes call a Python function registered as a node.
    - TOOL nodes call a function registered in the tool registry.
    """

    name: str
    type: NodeType = NodeType.COMPUTATION
    tool_name: Optional[str] = None
    description: Optional[str] = None


class EdgeConfig(BaseModel):
    """
    Directed edge with an optional condition.
    If condition_key is set, then this edge is taken only if:
        compare(state[condition_key], operator, value) is True.
    If operator/condition_key/value are None, it's unconditional.
    """

    source: str
    target: str
    condition_key: Optional[str] = None
    operator: Optional[
        Literal["==", "!=", "<", ">", "<=", ">="]
    ] = None
    value: Optional[Any] = None


class Graph(BaseModel):
    id: str
    name: Optional[str] = None
    entrypoint: str
    nodes: Dict[str, NodeConfig]
    edges: List[EdgeConfig]


class StepLog(BaseModel):
    node: str
    started_at: datetime
    finished_at: datetime
    state_diff: Dict[str, Any] = Field(default_factory=dict)
    info: Optional[str] = None


class GraphRun(BaseModel):
    id: str
    graph_id: str
    status: Literal["pending", "running", "completed", "failed"]
    state: Dict[str, Any] = Field(default_factory=dict)
    logs: List[StepLog] = Field(default_factory=list)
    error: Optional[str] = None


class GraphCreateRequest(BaseModel):
    """
    If template is provided, nodes/edges can be omitted and a built-in
    example graph will be created (e.g., 'code_review_agent').
    """

    template: Optional[str] = None
    name: Optional[str] = None
    nodes: Optional[List[NodeConfig]] = None
    edges: Optional[List[EdgeConfig]] = None
    entrypoint: Optional[str] = None


class GraphCreateResponse(BaseModel):
    graph_id: str


class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any] = Field(default_factory=dict)


class GraphRunSyncResponse(BaseModel):
    run_id: str
    final_state: Dict[str, Any]
    logs: List[StepLog]


class GraphRunAsyncResponse(BaseModel):
    run_id: str
    status: str
