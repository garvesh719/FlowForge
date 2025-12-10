from __future__ import annotations

import uuid
from typing import Dict, Any

from fastapi import FastAPI, BackgroundTasks, HTTPException

from app.engine.models import (
    EdgeConfig,
    Graph,
    GraphCreateRequest,
    GraphCreateResponse,
    GraphRun,
    GraphRunAsyncResponse,
    GraphRunRequest,
    GraphRunSyncResponse,
    NodeConfig,
    NodeType,
)
from app.engine.registry import register_builtins
from app.engine.runner import run_graph

app = FastAPI(
    title="FlowForge – Minimal Async Workflow Engine",
    description=(
        "A small but expressive workflow/agent engine built for the AI Engineering "
        "assignment. Supports nodes, tools, branching, looping, and async execution."
    ),
    version="0.1.0",
)

# In-memory stores (for assignment purposes).
GRAPHS: Dict[str, Graph] = {}
RUNS: Dict[str, GraphRun] = {}


@app.on_event("startup")
async def startup_event() -> None:
    # Register built-in nodes and tools on startup
    register_builtins()


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": "FlowForge workflow engine is running.",
        "docs": "/docs",
    }


def create_code_review_template_graph(name: str | None = None) -> Graph:
    """
    Built-in sample workflow:
    1. extract_functions (COMPUTATION)
    2. check_complexity (COMPUTATION)
    3. detect_smells (TOOL)
    4. suggest_improvements (COMPUTATION)
    5. evaluate_quality (COMPUTATION)
    Loop: evaluate_quality -> suggest_improvements until metrics.quality_score >= threshold
    """

    graph_id = str(uuid.uuid4())

    nodes = {
        "extract_functions": NodeConfig(
            name="extract_functions",
            type=NodeType.COMPUTATION,
            description="Extract functions from raw code text.",
        ),
        "check_complexity": NodeConfig(
            name="check_complexity",
            type=NodeType.COMPUTATION,
            description="Estimate complexity per function.",
        ),
        "detect_smells": NodeConfig(
            name="detect_smells",
            type=NodeType.TOOL,
            tool_name="detect_smells",
            description="Tool node: detect simple static code smells.",
        ),
        "suggest_improvements": NodeConfig(
            name="suggest_improvements",
            type=NodeType.COMPUTATION,
            description="Suggest improvements and simulate auto-refactor.",
        ),
        "evaluate_quality": NodeConfig(
            name="evaluate_quality",
            type=NodeType.COMPUTATION,
            description="Evaluate whether quality_score meets threshold.",
        ),
    }

    edges = [
        EdgeConfig(source="extract_functions", target="check_complexity"),
        EdgeConfig(source="check_complexity", target="detect_smells"),
        EdgeConfig(source="detect_smells", target="suggest_improvements"),
        EdgeConfig(source="suggest_improvements", target="evaluate_quality"),
        # Loop edge: if meets_quality == False, go back to suggest_improvements
        EdgeConfig(
            source="evaluate_quality",
            target="suggest_improvements",
            condition_key="meets_quality",
            operator="==",
            value=False,
        ),
        # Exit edge: if meets_quality == True, stop
        EdgeConfig(
            source="evaluate_quality",
            target="__end__",
            condition_key="meets_quality",
            operator="==",
            value=True,
        ),
    ]

    graph = Graph(
        id=graph_id,
        name=name or "code_review_agent",
        entrypoint="extract_functions",
        nodes=nodes,
        edges=edges,
    )
    return graph


@app.post("/graph/create", response_model=GraphCreateResponse)
async def create_graph(payload: GraphCreateRequest) -> GraphCreateResponse:
    """
    Create a new graph.

    Two options:
    - Provide 'template': 'code_review_agent' to get the built-in example workflow.
    - OR provide custom nodes + edges (+ entrypoint) to create your own graph.
    """
    if payload.template == "code_review_agent" or (
        payload.nodes is None and payload.edges is None
    ):
        graph = create_code_review_template_graph(name=payload.name)
    else:
        if not payload.nodes or not payload.edges:
            raise HTTPException(
                status_code=400,
                detail="Either provide a template or both nodes and edges.",
            )
        if not payload.entrypoint:
            raise HTTPException(
                status_code=400,
                detail="entrypoint is required when defining a custom graph.",
            )

        graph_id = str(uuid.uuid4())
        node_map: Dict[str, NodeConfig] = {n.name: n for n in payload.nodes}

        graph = Graph(
            id=graph_id,
            name=payload.name,
            entrypoint=payload.entrypoint,
            nodes=node_map,
            edges=payload.edges,
        )

    GRAPHS[graph.id] = graph
    return GraphCreateResponse(graph_id=graph.id)


async def _execute_graph_background(graph_id: str, initial_state: Dict[str, Any], run_id: str) -> None:
    """
    Background task for async graph runs.
    """
    run = RUNS[run_id]
    run.status = "running"

    try:
        graph = GRAPHS[graph_id]
        final_state, logs = await run_graph(graph, initial_state)
        run.state = final_state
        run.logs = logs
        run.status = "completed"
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error = str(exc)


@app.post("/graph/run", response_model=GraphRunSyncResponse, summary="Run a graph synchronously")
async def run_graph_sync(payload: GraphRunRequest) -> GraphRunSyncResponse:
    """
    Synchronous execution:
    Returns final state + execution logs in the response.
    This matches the assignment's required behaviour.
    """
    if payload.graph_id not in GRAPHS:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = GRAPHS[payload.graph_id]
    run_id = str(uuid.uuid4())

    run = GraphRun(
        id=run_id,
        graph_id=graph.id,
        status="running",
        state=payload.initial_state,
        logs=[],
    )
    RUNS[run_id] = run

    final_state, logs = await run_graph(graph, payload.initial_state)

    run.state = final_state
    run.logs = logs
    run.status = "completed"

    return GraphRunSyncResponse(run_id=run_id, final_state=final_state, logs=logs)


@app.post(
    "/graph/run_async",
    response_model=GraphRunAsyncResponse,
    summary="Run a graph asynchronously (background task)",
)
async def run_graph_async(
    payload: GraphRunRequest,
    background_tasks: BackgroundTasks,
) -> GraphRunAsyncResponse:
    """
    Optional novelty: async/background execution.
    Immediately returns run_id + status=running.
    The actual execution happens in a background task.
    """
    if payload.graph_id not in GRAPHS:
        raise HTTPException(status_code=404, detail="Graph not found")

    graph = GRAPHS[payload.graph_id]
    run_id = str(uuid.uuid4())

    run = GraphRun(
        id=run_id,
        graph_id=graph.id,
        status="pending",
        state=payload.initial_state,
        logs=[],
    )
    RUNS[run_id] = run

    background_tasks.add_task(
        _execute_graph_background,
        graph.id,
        payload.initial_state,
        run_id,
    )

    return GraphRunAsyncResponse(run_id=run_id, status="running")


@app.get("/graph/state/{run_id}", response_model=GraphRun)
async def get_graph_state(run_id: str) -> GraphRun:
    """
    Inspect the current state and logs of a run.
    Useful especially for async/background executions.
    """
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    return RUNS[run_id]
