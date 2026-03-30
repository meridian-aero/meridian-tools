"""Tests for the provenance tracking system.

Migrated from: OpenAeroStruct/oas_mcp/tests/test_provenance.py

Import mapping applied:
  - oas_mcp.provenance.capture -> hangar.sdk.provenance.middleware
  - oas_mcp.provenance.db -> hangar.sdk.provenance.db
  - oas_mcp.provenance.tools -> hangar.oas.tools.session
"""

from __future__ import annotations

import inspect
import uuid
from pathlib import Path

import numpy as np
import pytest
import pytest_asyncio

from hangar.sdk.provenance.middleware import _prov_session_id, _safe_json, capture_tool
from hangar.sdk.provenance.db import (
    _next_seq,
    get_session_graph,
    init_db,
    list_sessions,
    record_decision,
    record_session,
    record_tool_call,
)
from hangar.oas.tools.session import export_session_graph, log_decision, start_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(prefix="ts") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _make_call_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# DB layer tests
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(tmp_path):
    """init_db creates the 3 required tables."""
    import sqlite3

    db = tmp_path / "prov.db"
    init_db(db)
    conn = sqlite3.connect(str(db))
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"sessions", "tool_calls", "decisions"}.issubset(tables)
    conn.close()


def test_record_and_retrieve_tool_call(tmp_path):
    """Record a tool call and verify it appears in get_session_graph."""
    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid)
    call_id = _make_call_id()
    record_tool_call(
        call_id=call_id,
        session_id=sid,
        seq=0,
        tool_name="run_aero_analysis",
        inputs_json='{"surfaces": ["wing"]}',
        outputs_json='{"CL": 0.5}',
        status="ok",
        error_msg=None,
        started_at="2025-01-01T00:00:00+00:00",
        duration_s=1.23,
    )

    graph = get_session_graph(sid)
    nodes = graph["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["type"] == "tool_call"
    assert nodes[0]["tool_name"] == "run_aero_analysis"
    assert nodes[0]["id"] == call_id


def test_record_decision_with_prior_call(tmp_path):
    """Decision with prior_call_id creates an 'informs' edge."""
    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid)

    call_id = _make_call_id()
    record_tool_call(
        call_id=call_id,
        session_id=sid,
        seq=0,
        tool_name="run_aero_analysis",
        inputs_json="{}",
        outputs_json="{}",
        status="ok",
        error_msg=None,
        started_at="2025-01-01T00:00:00+00:00",
        duration_s=1.0,
    )

    dec_id = str(uuid.uuid4())
    record_decision(
        decision_id=dec_id,
        session_id=sid,
        seq=1,
        decision_type="result_interpretation",
        reasoning="CL looks good",
        prior_call_id=call_id,
        selected_action="proceed",
        confidence="high",
    )

    graph = get_session_graph(sid)
    edges = graph["edges"]
    informs_edges = [e for e in edges if e["label"] == "informs"]
    assert len(informs_edges) == 1
    assert informs_edges[0]["source"] == call_id
    assert informs_edges[0]["target"] == dec_id


def test_get_session_graph_edge_logic(tmp_path):
    """All 3 edge types are correctly generated."""
    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid)

    # Sequence: tool_call0 -> decision1 -> tool_call2 -> tool_call3
    cid0 = _make_call_id()
    cid2 = _make_call_id()
    cid3 = _make_call_id()
    dec1 = str(uuid.uuid4())

    record_tool_call(cid0, sid, 0, "create_surface", "{}", "{}", "ok", None, "2025-01-01T00:00:00+00:00", 0.1)
    record_decision(dec1, sid, 1, "mesh_resolution", "use fine mesh", cid0, "num_y=15", "medium")
    record_tool_call(cid2, sid, 2, "run_aero_analysis", "{}", "{}", "ok", None, "2025-01-01T00:00:01+00:00", 1.0)
    record_tool_call(cid3, sid, 3, "compute_drag_polar", "{}", "{}", "ok", None, "2025-01-01T00:00:02+00:00", 5.0)

    graph = get_session_graph(sid)
    edges = graph["edges"]
    labels = {e["label"] for e in edges}

    assert "informs" in labels   # cid0 -> dec1
    assert "decides" in labels   # dec1 -> cid2
    assert "sequence" in labels  # cid2 -> cid3


def test_list_sessions(tmp_path):
    """list_sessions returns all sessions with counts."""
    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid, notes="test session")
    cid = _make_call_id()
    record_tool_call(cid, sid, 0, "reset", "{}", "{}", "ok", None, "2025-01-01T00:00:00+00:00", 0.01)

    sessions = list_sessions()
    match = [s for s in sessions if s["session_id"] == sid]
    assert len(match) == 1
    assert match[0]["tool_call_count"] == 1
    assert match[0]["decision_count"] == 0


# ---------------------------------------------------------------------------
# capture_tool decorator tests
# ---------------------------------------------------------------------------


def test_capture_decorator_preserves_signature(tmp_path):
    """@capture_tool must not alter the function's __signature__."""
    init_db(tmp_path / "prov.db")

    async def my_tool(x: int, y: str = "hello") -> dict:
        return {}

    wrapped = capture_tool(my_tool)
    # eval_str=True resolves PEP 563 string annotations to actual types
    assert inspect.signature(wrapped) == inspect.signature(my_tool, eval_str=True)


@pytest.mark.asyncio
async def test_capture_decorator_records_on_success(tmp_path):
    """A successful call is recorded with status='ok'."""
    import sqlite3

    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid)
    token = _prov_session_id.set(sid)

    try:

        @capture_tool
        async def my_tool(x: int) -> dict:
            return {"result": x * 2}

        await my_tool(x=3)

        db_conn = sqlite3.connect(str(tmp_path / "prov.db"))
        rows = db_conn.execute(
            "SELECT * FROM tool_calls WHERE session_id=? AND tool_name='my_tool'", (sid,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][6] == "ok"  # status column
        db_conn.close()
    finally:
        _prov_session_id.reset(token)


@pytest.mark.asyncio
async def test_capture_decorator_records_on_error(tmp_path):
    """A failing call is recorded with status='error'."""
    import sqlite3

    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid)
    token = _prov_session_id.set(sid)

    try:

        @capture_tool
        async def failing_tool() -> dict:
            raise ValueError("intentional failure")

        with pytest.raises(ValueError):
            await failing_tool()

        db_conn = sqlite3.connect(str(tmp_path / "prov.db"))
        rows = db_conn.execute(
            "SELECT * FROM tool_calls WHERE session_id=?", (sid,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][6] == "error"  # status
        assert "intentional failure" in (rows[0][7] or "")
        db_conn.close()
    finally:
        _prov_session_id.reset(token)


@pytest.mark.asyncio
async def test_capture_decorator_injects_provenance(tmp_path):
    """_provenance dict is injected into returned dict on success."""
    init_db(tmp_path / "prov.db")
    sid = _make_session()
    record_session(sid)
    token = _prov_session_id.set(sid)

    try:

        @capture_tool
        async def my_tool() -> dict:
            return {"CL": 0.5}

        result = await my_tool()
        assert "_provenance" in result
        assert "call_id" in result["_provenance"]
        assert result["_provenance"]["session_id"] == sid
    finally:
        _prov_session_id.reset(token)


def test_safe_json_handles_numpy():
    """_safe_json serialises numpy arrays and scalars without error."""
    obj = {
        "arr": np.array([1.0, 2.0, 3.0]),
        "scalar": np.float32(3.14),
        "int": np.int64(42),
    }
    result = _safe_json(obj)
    import json

    parsed = json.loads(result)
    assert parsed["arr"] == [1.0, 2.0, 3.0]
    assert abs(parsed["scalar"] - 3.14) < 0.01
    assert parsed["int"] == 42


# ---------------------------------------------------------------------------
# tools.py tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_session_creates_record(tmp_path):
    """start_session creates a DB record and sets the context var."""
    init_db(tmp_path / "prov.db")
    result = await start_session(notes="unit test")
    sid = result["session_id"]
    assert sid.startswith("sess-")
    assert _prov_session_id.get() == sid


@pytest.mark.asyncio
async def test_log_decision_records_decision(tmp_path):
    """log_decision returns a decision_id and writes to DB."""
    import sqlite3

    init_db(tmp_path / "prov.db")
    sess = await start_session()
    sid = sess["session_id"]

    result = await log_decision(
        decision_type="dv_selection",
        reasoning="chose twist for minimum drag",
        selected_action="twist_cp",
        confidence="high",
    )
    assert "decision_id" in result

    db_conn = sqlite3.connect(str(tmp_path / "prov.db"))
    rows = db_conn.execute(
        "SELECT * FROM decisions WHERE session_id=?", (sid,)
    ).fetchall()
    assert len(rows) == 1
    db_conn.close()


@pytest.mark.asyncio
async def test_export_session_graph_writes_file(tmp_path):
    """export_session_graph writes JSON to disk and returns path."""
    init_db(tmp_path / "prov.db")
    sess = await start_session(notes="export test")
    sid = sess["session_id"]

    # Add a tool call manually
    cid = _make_call_id()
    record_tool_call(cid, sid, 0, "create_surface", "{}", "{}", "ok", None, "2025-01-01T00:00:00+00:00", 0.1)

    out = tmp_path / "graph.json"
    result = await export_session_graph(session_id=sid, output_path=str(out))

    assert out.exists()
    assert result["path"] == str(out)
    assert "nodes" in result
    assert len(result["nodes"]) == 1
