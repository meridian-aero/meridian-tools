"""Write provenance graph JSON to the artifact directory.

The graph file is co-located with run artifacts at a deterministic path:
    {data_dir}/{user}/{project}/{session_id}/_provenance_graph.json

This module is the single point of graph-to-file persistence.  It is called:
  - Explicitly via export_session_graph()
  - Automatically on reset() and session teardown
  - Periodically by the @capture_tool middleware (every N tool calls)
  - As a side-effect of the viewer /graph endpoint
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

GRAPH_FILENAME = "_provenance_graph.json"


def flush_session_graph(
    session_id: str,
    *,
    user: str | None = None,
    project: str | None = None,
    data_dir: Path | None = None,
) -> dict:
    """Write the provenance graph for *session_id* to the artifact directory.

    Returns ``{path, node_count, edge_count}`` on success,
    or ``{path: None, node_count: 0, edge_count: 0, error: "..."}`` on failure.

    If *user* or *project* are not provided, they are looked up from
    the session record in the provenance DB.

    Idempotent -- safe to call multiple times; overwrites the previous file.
    """
    from hangar.sdk.artifacts.store import _default_data_dir
    from hangar.sdk.provenance.db import _dumps, get_session_graph, get_session_meta

    # Resolve user/project from DB if not provided
    if user is None or project is None:
        try:
            meta = get_session_meta(session_id)
        except Exception:
            meta = None
        if meta:
            user = user or meta.get("user") or "default"
            project = project or meta.get("project") or "default"
        else:
            user = user or "default"
            project = project or "default"

    try:
        graph = get_session_graph(session_id)
    except Exception as exc:
        logger.warning("Failed to build provenance graph for %s: %s", session_id, exc)
        return {"path": None, "node_count": 0, "edge_count": 0, "error": str(exc)}

    node_count = len(graph.get("nodes", []))
    edge_count = len(graph.get("edges", []))

    base = data_dir or _default_data_dir()
    out_dir = base / user / project / session_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / GRAPH_FILENAME

    try:
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(_dumps(graph), encoding="utf-8")
        tmp.replace(out_path)
    except OSError as exc:
        logger.warning("Failed to flush provenance graph to %s: %s", out_path, exc)
        return {"path": None, "node_count": node_count, "edge_count": edge_count, "error": str(exc)}

    return {
        "path": str(out_path),
        "node_count": node_count,
        "edge_count": edge_count,
    }
