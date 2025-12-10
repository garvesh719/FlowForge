# FlowForge – Minimal Async Workflow & Agent Execution Engine

This repository implements a **small but expressive workflow/agent engine** in Python, using FastAPI.

It was built as part of an **AI Engineering Internship assignment** to demonstrate:

- Clean Python structure
- API design with FastAPI
- Async programming & background execution
- Thinking in terms of **state → transitions → loops**

No ML or RL is used – the focus is on **backend systems design**.

---

## Core Idea

The engine is a simplified version of tools like LangGraph:

- A **graph** is made of **nodes** and **edges**.
- A **shared state** (Python dictionary) flows through the graph.
- Each **node** is a Python function that reads and mutates the state.
- **Edges** define which node executes next, with optional conditions for branching.
- Loops are supported naturally by edges that point back to previous nodes.

---

## Novel Design Choices

To go beyond a minimal solution and make this project placement–ready, the engine includes:

### 1. Hybrid Node System (Computation Node + Tool Node)

There are two node types:

- **Computation nodes**: call functions registered as nodes.
- **Tool nodes**: call functions from a separate **tool registry**.

This mirrors real-world "tool-calling" agent frameworks in a tiny form factor.

### 2. Structured Execution Trace with State Diff

For every step, the engine records:

- Node name
- Start & end timestamps
- A **shallow diff of the state** (what changed)
- Optional node description

This makes workflows debuggable and transparent.

### 3. Async Support & Background Runs

- All nodes can be sync or async – the engine handles both.
- There is an optional `/graph/run_async` endpoint that runs workflows in a **FastAPI background task**.
- `/graph/state/{run_id}` lets you inspect long-running or async runs.

---

## Example Workflow: Code Review Mini-Agent

A reference workflow is included as a built-in template: `code_review_agent`.

Nodes:

1. `extract_functions` (computation)  
2. `check_complexity` (computation)  
3. `detect_smells` (tool node)  
4. `suggest_improvements` (computation)  
5. `evaluate_quality` (computation)  

Loop logic:

- `evaluate_quality` sets `meets_quality = True/False` based on `metrics.quality_score` and `threshold`.
- If `meets_quality == False` → go back to `suggest_improvements`.
- If `meets_quality == True` → terminate.

This is a fully rule-based, deterministic mini–agent for code quality review.

---

## Project Structure

```text
app/
  main.py            # FastAPI app + endpoints
  engine/
    models.py        # Pydantic models for nodes, edges, graphs, runs, logs
    registry.py      # Node & tool registries + builtin registration
    runner.py        # Core workflow engine
  nodes/
    code_review.py   # Sample code-review agent workflow nodes
requirements.txt
README.md
