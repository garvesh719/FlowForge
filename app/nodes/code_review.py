from __future__ import annotations

from typing import Any, Dict, List


def _get_code(state: Dict[str, Any]) -> str:
    return state.get("code", "")


def extract_functions(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Very lightweight function extractor:
    Looks for lines starting with 'def ' and treats them as function definitions.
    Stores a list of function metadata in state['functions'].
    """
    code = _get_code(state)
    functions: List[Dict[str, Any]] = []

    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("def ") and "(" in stripped and ":" in stripped:
            name_part = stripped.split("def ", 1)[1]
            name = name_part.split("(", 1)[0].strip()
            functions.append(
                {
                    "name": name,
                    "line": line,
                }
            )

    state["functions"] = functions
    return state


def check_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple complexity heuristic:
    Counts 'for', 'while', and 'if' occurrences per function as a stand-in
    for cyclomatic complexity.
    """
    code = _get_code(state)
    lines = code.splitlines()
    functions = state.get("functions", [])

    complexity_report: Dict[str, Any] = {}

    for fn in functions:
        name = fn["name"]
        score = 1
        for line in lines:
            if name + "(" in line:
                # we don't try to track exact function bodies; just a simple heuristic
                pass
            # crude signal for complexity
            tokens = line.strip().split()
            score += tokens.count("for") + tokens.count("while") + tokens.count("if")

        complexity_report[name] = {"complexity_score": score}

    state["complexity_report"] = complexity_report

    # baseline quality score (0–1)
    # lower complexity -> higher starting quality
    avg_complexity = 0.0
    if complexity_report:
        avg_complexity = sum(
            v["complexity_score"] for v in complexity_report.values()
        ) / len(complexity_report)

    # clamp complexity to a reasonable range then invert
    normalized = min(avg_complexity / 20.0, 1.0)
    quality_score = float(max(0.0, 1.0 - normalized))

    state.setdefault("metrics", {})
    state["metrics"]["quality_score"] = quality_score
    return state


def detect_smells_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool node:
    Performs simple static "code smell" detection:
    - lines longer than 80 chars
    - presence of 'TODO'
    - deep nesting via multiple indentation levels
    """
    code = _get_code(state)
    issues: List[str] = []

    for idx, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if len(line) > 80:
            issues.append(f"Line {idx}: line longer than 80 characters")
        if "TODO" in line:
            issues.append(f"Line {idx}: TODO comment present")
        if stripped.startswith("if ") and line.startswith("        " * 3):
            issues.append(f"Line {idx}: deeply nested if-statement")

    state["issues"] = issues
    return state


def suggest_improvements(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses complexity + issues to propose rule-based improvements.
    Also simulates an 'auto-refactor' effect by bumping quality_score slightly.
    """
    suggestions: List[str] = []
    complexity_report = state.get("complexity_report", {})
    issues = state.get("issues", [])
    metrics = state.setdefault("metrics", {})
    quality_score = float(metrics.get("quality_score", 0.0))

    # suggestions from complexity
    for fn_name, report in complexity_report.items():
        score = report.get("complexity_score", 0)
        if score > 15:
            suggestions.append(
                f"Function '{fn_name}' has high complexity ({score}). "
                "Consider splitting into smaller helper functions."
            )
        elif score > 8:
            suggestions.append(
                f"Function '{fn_name}' is moderately complex ({score}). "
                "Try reducing nested conditionals."
            )

    # suggestions from issues
    for issue in issues:
        if "80 characters" in issue:
            suggestions.append(
                "Some lines are longer than 80 characters. "
                "Consider wrapping or extracting variables to improve readability."
            )
        if "TODO" in issue:
            suggestions.append(
                "Remove or resolve TODO comments before merging this code."
            )
        if "deeply nested" in issue:
            suggestions.append(
                "Deeply nested conditionals detected. Refactor using guard clauses "
                "or early returns."
            )

    # de-duplicate suggestions
    state["suggestions"] = list(dict.fromkeys(suggestions))

    # simulate “auto-refactor” effect: each pass improves quality a bit
    bump = 0.05 * max(1, len(state["suggestions"]))
    quality_score = min(1.0, quality_score + bump)
    metrics["quality_score"] = quality_score

    return state


def evaluate_quality(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final evaluation node:
    Sets a boolean flag 'meets_quality' = True/False based on threshold.
    This is used by the graph edges to decide whether to loop or stop.
    """
    metrics = state.setdefault("metrics", {})
    quality_score = float(metrics.get("quality_score", 0.0))
    threshold = float(state.get("threshold", 0.8))
    state["meets_quality"] = quality_score >= threshold
    return state
