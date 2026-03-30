"""User-defined pass/fail assertions against analysis results.

Migrated from: OpenAeroStruct/oas_mcp/core/requirements.py
"""

from __future__ import annotations

import operator
from typing import Any

_OPERATORS: dict[str, Any] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _resolve_path(data: dict, path: str) -> tuple[bool, Any]:
    """Resolve a dot-separated path into *data*.

    Returns
    -------
    (found, value) — found is False if any key is missing.
    """
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict):
            return False, None
        if part not in current:
            return False, None
        current = current[part]
    return True, current


def check_requirements(
    requirements: list[dict],
    results: dict,
) -> dict:
    """Check a list of requirements against *results*.

    Parameters
    ----------
    requirements:
        List of requirement dicts, each with:
          - ``path`` (str): dot-separated path into results
          - ``operator`` (str): one of ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``
          - ``value`` (float | int | bool | str): right-hand side
          - ``label`` (str, optional): human-readable name for this requirement

    results:
        The results dict from an analysis tool.

    Returns
    -------
    dict with keys:
      - ``passed`` (bool): all requirements satisfied
      - ``results`` (list[dict]): per-requirement outcome
    """
    outcomes: list[dict] = []
    all_passed = True

    for req in requirements:
        path = req.get("path", "")
        op_str = req.get("operator", "==")
        target = req.get("value")
        label = req.get("label") or f"{path} {op_str} {target}"

        if op_str not in _OPERATORS:
            outcomes.append({
                "label": label,
                "path": path,
                "operator": op_str,
                "target": target,
                "actual": None,
                "passed": False,
                "error": f"Unknown operator '{op_str}'. Supported: {list(_OPERATORS)}",
            })
            all_passed = False
            continue

        found, actual = _resolve_path(results, path)
        if not found:
            outcomes.append({
                "label": label,
                "path": path,
                "operator": op_str,
                "target": target,
                "actual": None,
                "passed": False,
                "error": f"Path '{path}' not found in results",
            })
            all_passed = False
            continue

        try:
            passed = bool(_OPERATORS[op_str](actual, target))
        except TypeError as exc:
            outcomes.append({
                "label": label,
                "path": path,
                "operator": op_str,
                "target": target,
                "actual": actual,
                "passed": False,
                "error": f"Type error comparing {type(actual).__name__} {op_str} {type(target).__name__}: {exc}",
            })
            all_passed = False
            continue

        if not passed:
            all_passed = False

        outcomes.append({
            "label": label,
            "path": path,
            "operator": op_str,
            "target": target,
            "actual": actual,
            "passed": passed,
        })

    return {
        "passed": all_passed,
        "total": len(requirements),
        "passed_count": sum(1 for o in outcomes if o["passed"]),
        "results": outcomes,
    }
