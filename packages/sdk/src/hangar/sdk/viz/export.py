"""DAG export logic for provenance session graphs.

Migrated from: OpenAeroStruct/oas_mcp/provenance/tools.py
(export_session_graph — DAG export logic only, not MCP tool registration)
"""

from __future__ import annotations

from pathlib import Path

from hangar.sdk.provenance.db import _dumps, get_session_graph


def export_session_graph(
    session_id: str,
    output_path: str | None = None,
) -> dict:
    """Export the provenance graph for a session as a JSON dict.

    Returns ``{session, nodes, edges, path}`` where *path* is the output file
    path (or ``None`` if not written).

    Parameters
    ----------
    session_id:
        The session ID to export.
    output_path:
        File path to write the JSON graph.  ``None`` means return only,
        do not write to disk.
    """
    graph = get_session_graph(session_id)

    written_path: str | None = None
    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_dumps(graph), encoding="utf-8")
        written_path = str(p)

    return {**graph, "path": written_path}
