"""MCP resources: reference guide, workflow guide, dashboard widget.

Migrated from: OpenAeroStruct/oas_mcp/tools/resources.py
"""

from __future__ import annotations

import json
from pathlib import Path

from hangar.sdk.viz.widget import DASHBOARD_HTML
from hangar.sdk.state import artifacts as _artifacts

_REFERENCE = (Path(__file__).parent.parent / "reference.md").read_text()
_WORKFLOWS = (Path(__file__).parent.parent / "workflows.md").read_text()

WIDGET_URI = "ui://oas/dashboard.html"


def oas_dashboard_view() -> str:
    """Return the embedded dashboard HTML for MCP Apps hosts."""
    return DASHBOARD_HTML


def reference_guide() -> str:
    return _REFERENCE


def workflow_guide() -> str:
    return _WORKFLOWS


def artifact_by_run_id(run_id: str) -> str:
    """Return the full artifact JSON for the given run_id."""
    artifact = _artifacts.get(run_id)
    if artifact is None:
        return json.dumps({"error": f"Artifact '{run_id}' not found"})
    return json.dumps(artifact, indent=2)
