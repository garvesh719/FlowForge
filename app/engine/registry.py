from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

import asyncio

NodeFunc = Callable[[Dict[str, Any]], Any]
ToolFunc = Callable[[Dict[str, Any]], Any]

NODE_REGISTRY: Dict[str, NodeFunc] = {}
TOOL_REGISTRY: Dict[str, ToolFunc] = {}


def register_node(name: str, fn: NodeFunc) -> None:
    NODE_REGISTRY[name] = fn


def register_tool(name: str, fn: ToolFunc) -> None:
    TOOL_REGISTRY[name] = fn


def get_node(name: str) -> NodeFunc:
    if name not in NODE_REGISTRY:
        raise KeyError(f"Node function '{name}' is not registered")
    return NODE_REGISTRY[name]


def get_tool(name: str) -> ToolFunc:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{name}' is not registered")
    return TOOL_REGISTRY[name]


async def call_maybe_async(fn: Callable[[Dict[str, Any]], Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper that works with both sync and async node/tool functions.
    It expects the function to either mutate the state in-place and/or return a new state.
    """
    if asyncio.iscoroutinefunction(fn):
        result = await fn(state)
    else:
        result = fn(state)
        if asyncio.iscoroutine(result):
            result = await result

    if result is None:
        return state
    return result


def register_builtins() -> None:
    """
    Register built-in nodes and tools.
    Currently registers the code review workflow components.
    """
    from app.nodes.code_review import (
        extract_functions,
        check_complexity,
        detect_smells_tool,
        suggest_improvements,
        evaluate_quality,
    )

    register_node("extract_functions", extract_functions)
    register_node("check_complexity", check_complexity)
    register_tool("detect_smells", detect_smells_tool)
    register_node("suggest_improvements", suggest_improvements)
    register_node("evaluate_quality", evaluate_quality)
