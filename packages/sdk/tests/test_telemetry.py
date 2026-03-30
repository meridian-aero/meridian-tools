"""Unit tests for telemetry and logging utilities.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/test_telemetry.py
Import mapping:
    oas_mcp.core.telemetry → hangar.sdk.telemetry.logging
"""

from __future__ import annotations

import pytest
import numpy as np
from hangar.sdk.telemetry.logging import get_run_logs, make_telemetry, redact


class TestRedact:
    def test_numpy_array_becomes_summary(self):
        arr = np.array([1.0, 2.0, 3.0])
        result = redact(arr)
        assert isinstance(result, dict)
        assert result["shape"] == [3]
        assert "hash" in result
        assert result["min"] == pytest.approx(1.0)
        assert result["max"] == pytest.approx(3.0)

    def test_dict_is_recursively_redacted(self):
        obj = {"mesh": np.ones((3, 3, 3)), "CL": 0.5}
        result = redact(obj)
        assert isinstance(result["mesh"], dict)
        assert result["CL"] == 0.5

    def test_long_list_is_summarized(self):
        obj = list(range(25))
        result = redact(obj)
        assert isinstance(result, dict)
        assert result["type"] == "list"
        assert result["length"] == 25
        assert result["first"] == 0
        assert result["last"] == 24

    def test_short_list_passes_through(self):
        obj = [1, 2, 3]
        result = redact(obj)
        assert result == [1, 2, 3]

    def test_scalar_passes_through(self):
        assert redact(42) == 42
        assert redact("hello") == "hello"


class TestMakeTelemetry:
    def test_basic_telemetry(self):
        telem = make_telemetry(elapsed_s=0.123, cache_hit=True, surface_count=2)
        assert telem["elapsed_s"] == pytest.approx(0.123)
        assert telem["oas.cache.hit"] is True
        assert telem["oas.surface.count"] == 2

    def test_mesh_shape_included(self):
        telem = make_telemetry(0.1, False, 1, mesh_shape=(2, 7, 3))
        assert telem["oas.mesh.nx"] == 2
        assert telem["oas.mesh.ny"] == 7

    def test_extra_keys_included(self):
        telem = make_telemetry(0.1, False, extra={"custom": "value"})
        assert telem["custom"] == "value"

    def test_elapsed_rounded_to_4dp(self):
        telem = make_telemetry(0.123456789, False)
        assert telem["elapsed_s"] == pytest.approx(0.1235, abs=1e-4)


class TestRunLogs:
    def test_unknown_run_id_returns_empty(self):
        logs = get_run_logs("nonexistent_run_id_xyz")
        assert logs is None or logs == []
