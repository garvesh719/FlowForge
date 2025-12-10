from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.engine.models import (
    EdgeConfig,
    Graph,
    NodeConfig,
    NodeType,
    StepLog,
)
from app.engine.registry import get_node, get_tool, call_maybe_async


def _get_from_state(state: Dict[str, Any], key: str) -> Any:
    """
    Simple dotted-path lookup in state dict, e.g. 'metrics.quality_score'.
    """
    parts = key.split(".")
    value: Any = state
    for p in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(p)
    return value


def _compare(lhs: Any, op: Optional[str], rhs: Any) -> bool:
    if op is None:
        # unconditional
        return True

    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op == "<":
        return lhs < rhs
    if op == ">":
        return lhs > rhs
    if op == "<=":
        return lhs <= rhs
    if op == ">=":
        return lhs >= rhs
    return False


def choose_next_node(
    graph: Graph,
    current_node: str,
    state: Dict[str, Any],
) -> Optional[str]:
    """
    Select the next node based on outgoing edges from current_node.
    First edge whose condition matches wins.
    A special target of '__end__' indicates termination.
    """
    candidates: List[EdgeConfig] = [
        e for e in graph.edges if e.source == current_node
    ]

    for edge in candidates:
        if edge.condition_key:
            lhs = _get_from_state(state, edge.condition_key)
            if not _compare(lhs, edge.operator, edge.value):
                continue
        # unconditional or matched condition
        if edge.target == "__end__":
            return None
        return edge.target

    # No outgoing edge => end execution
    return None


def compute_diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a shallow diff of the state to show what changed in a step.
    """
    diff: Dict[str, Any] = {}
    all_keys = set(before.keys()) | set(after.keys())
    for k in all_keys:
        if before.get(k) != after.get(k):
            diff[k] = {"before": before.get(k), "after": after.get(k)}
    return diff


async def execute_node(node_cfg: NodeConfig, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single node, calling either a node function or a tool.
    """
    if node_cfg.type == NodeType.COMPUTATION:
        fn = get_node(node_cfg.name)
    else:
        if not node_cfg.tool_name:
            raise ValueError(f"Tool node '{node_cfg.name}' missing 'tool_name'")
        fn = get_tool(node_cfg.tool_name)

    new_state = await call_maybe_async(fn, state)
    return new_state


async def run_graph(
    graph: Graph,
    initial_state: Dict[str, Any],
    max_steps: int = 1000,
) -> Tuple[Dict[str, Any], List[StepLog]]:
    """
    Core engine:
    - Starts from graph.entrypoint
    - Executes nodes step-by-step
    - Uses edges for transitions and branching
    - Supports loops naturally (edges pointing backward)
    - Returns final state and execution trace
    """
    state: Dict[str, Any] = copy.deepcopy(initial_state)
    logs: List[StepLog] = []
    current = graph.entrypoint
    steps = 0

    while current is not None and steps < max_steps:
        if current not in graph.nodes:
            raise KeyError(f"Node '{current}' not found in graph")

        node_cfg: NodeConfig = graph.nodes[current]

        before = copy.deepcopy(state)
        started = datetime.utcnow()
        state = await execute_node(node_cfg, state)
        finished = datetime.utcnow()

        diff = compute_diff(before, state)
        logs.append(
            StepLog(
                node=current,
                started_at=started,
                finished_at=finished,
                state_diff=diff,
                info=node_cfg.description,
            )
        )

        current = choose_next_node(graph, current, state)
        steps += 1

    return state, logs
