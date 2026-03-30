"""Unit tests for the response envelope and error taxonomy.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/test_envelope.py
Import mapping:
    oas_mcp.core.envelope → hangar.sdk.envelope.response
    oas_mcp.core.errors   → hangar.sdk.errors
    OASMCPError           → HangarError
"""

from __future__ import annotations

import pytest
from hangar.sdk.envelope.response import SCHEMA_VERSION, make_envelope, make_error_envelope
from hangar.sdk.errors import (
    CacheEvictedError,
    HangarError,
    InternalError,
    SolverConvergenceError,
    UserInputError,
)


class TestEnvelope:
    def test_make_envelope_has_required_keys(self):
        env = make_envelope("run_aero_analysis", "run123", {"alpha": 5.0}, {"CL": 0.5})
        assert env["schema_version"] == SCHEMA_VERSION
        assert env["tool_name"] == "run_aero_analysis"
        assert env["run_id"] == "run123"
        assert "timestamp" in env
        assert "inputs_hash" in env
        assert env["results"] == {"CL": 0.5}

    def test_make_envelope_inputs_hash_is_stable(self):
        inputs = {"alpha": 5.0, "velocity": 248.0}
        env1 = make_envelope("t", "r1", inputs, {})
        env2 = make_envelope("t", "r2", inputs, {})
        assert env1["inputs_hash"] == env2["inputs_hash"]

    def test_make_envelope_hash_changes_with_inputs(self):
        env1 = make_envelope("t", "r", {"alpha": 5.0}, {})
        env2 = make_envelope("t", "r", {"alpha": 6.0}, {})
        assert env1["inputs_hash"] != env2["inputs_hash"]

    def test_make_envelope_optional_validation(self):
        env = make_envelope("t", "r", {}, {}, validation={"passed": True})
        assert env["validation"] == {"passed": True}

    def test_make_envelope_optional_telemetry(self):
        env = make_envelope("t", "r", {}, {}, telemetry={"elapsed_s": 0.5})
        assert env["telemetry"]["elapsed_s"] == 0.5

    def test_make_envelope_no_validation_key_when_none(self):
        env = make_envelope("t", "r", {}, {})
        assert "validation" not in env
        assert "telemetry" not in env

    def test_make_error_envelope_has_error_key(self):
        env = make_error_envelope("run_aero_analysis", "USER_INPUT_ERROR", "bad alpha")
        assert env["schema_version"] == SCHEMA_VERSION
        assert env["run_id"] is None
        assert env["results"] is None
        assert env["error"]["code"] == "USER_INPUT_ERROR"
        assert "bad alpha" in env["error"]["message"]

    def test_make_error_envelope_details(self):
        env = make_error_envelope("t", "INTERNAL_ERROR", "msg", details={"field": "alpha"})
        assert env["error"]["details"] == {"field": "alpha"}

    def test_make_error_envelope_handles_empty_inputs(self):
        env = make_error_envelope("t", "INTERNAL_ERROR", "msg")
        assert "inputs_hash" in env


class TestErrorClasses:
    def test_user_input_error_code(self):
        e = UserInputError("bad value")
        assert e.error_code == "USER_INPUT_ERROR"

    def test_solver_convergence_error_code(self):
        e = SolverConvergenceError("did not converge")
        assert e.error_code == "SOLVER_CONVERGENCE_ERROR"

    def test_cache_evicted_error_code(self):
        e = CacheEvictedError("evicted")
        assert e.error_code == "CACHE_EVICTED_ERROR"

    def test_internal_error_code(self):
        e = InternalError("bug")
        assert e.error_code == "INTERNAL_ERROR"

    def test_to_dict(self):
        e = UserInputError("bad", details={"field": "alpha", "allowed": [-90, 90]})
        d = e.to_dict()
        assert d["code"] == "USER_INPUT_ERROR"
        assert d["message"] == "bad"
        assert d["details"]["field"] == "alpha"

    def test_all_errors_are_subclass_of_hangar_error(self):
        for cls in [UserInputError, SolverConvergenceError, CacheEvictedError, InternalError]:
            assert issubclass(cls, HangarError)

    def test_error_is_exception(self):
        with pytest.raises(UserInputError):
            raise UserInputError("test")
