"""Versioned response envelope for tool results.

Migrated from: OpenAeroStruct/oas_mcp/core/envelope.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"


def _hash_inputs(inputs: dict) -> str:
    """Return a short sha256 fingerprint of the inputs dict."""
    try:
        raw = json.dumps(inputs, sort_keys=True, default=str)
        return "sha256-" + hashlib.sha256(raw.encode()).hexdigest()[:16]
    except Exception:
        return "sha256-unknown"


def make_envelope(
    tool_name: str,
    run_id: str | None,
    inputs: dict,
    results: dict | None,
    validation: dict | None = None,
    telemetry: dict | None = None,
) -> dict:
    """Construct a successful versioned response envelope.

    Parameters
    ----------
    tool_name:
        The MCP tool that produced this response (e.g. ``'run_aero_analysis'``).
    run_id:
        Artifact run ID returned by the ArtifactStore.
    inputs:
        The inputs passed to the tool — used only for fingerprinting.
    results:
        Tool-specific results payload.
    validation:
        Validation check results (from ``hangar.sdk.validation``).
    telemetry:
        Performance / observability data (from ``hangar.sdk.telemetry``).
    """
    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool_name": tool_name,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs_hash": _hash_inputs(inputs),
        "results": results,
    }
    if validation is not None:
        envelope["validation"] = validation
    if telemetry is not None:
        envelope["telemetry"] = telemetry
    return envelope


def make_error_envelope(
    tool_name: str,
    error_code: str,
    message: str,
    details: dict | None = None,
    inputs: dict | None = None,
) -> dict:
    """Construct an error envelope for a failed tool call.

    Parameters
    ----------
    tool_name:
        The MCP tool that failed.
    error_code:
        One of the codes defined in ``hangar.sdk.errors``.
    message:
        Human-readable error description.
    details:
        Optional structured details (field name, allowed values, etc.).
    inputs:
        The inputs that caused the failure — used for fingerprinting.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_name": tool_name,
        "run_id": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs_hash": _hash_inputs(inputs or {}),
        "results": None,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
        },
    }
