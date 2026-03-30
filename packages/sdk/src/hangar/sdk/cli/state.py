"""Workspace state persistence for CLI one-shot mode.

Stores create_surface call arguments in a JSON file so that one-shot
invocations can rebuild session state before running an analysis tool.

State is keyed by workspace name (default: "default").
File location: ~/.hangar/state/<workspace>.json

Migrated from: OpenAeroStruct/oas_mcp/cli_state.py
"""

from __future__ import annotations

import json
from pathlib import Path

from hangar.sdk.cli.runner import _NumpyEncoder

STATE_DIR = Path.home() / ".hangar" / "state"


def _state_path(workspace: str) -> Path:
    return STATE_DIR / f"{workspace}.json"


def save_surfaces(workspace: str, surfaces: dict[str, dict]) -> None:
    """Save surface call arguments to the state file.

    Parameters
    ----------
    workspace:
        Namespace for state isolation (default: "default").
    surfaces:
        Mapping from surface name to the kwargs dict passed to create_surface.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _state_path(workspace)

    # Load existing state to merge
    existing = _load_raw(workspace)
    existing["surfaces"] = {**existing.get("surfaces", {}), **surfaces}

    path.write_text(
        json.dumps(existing, cls=_NumpyEncoder, indent=2),
        encoding="utf-8",
    )


def load_surfaces(workspace: str) -> dict[str, dict]:
    """Load surface call arguments from the state file.

    Returns an empty dict if the workspace state file does not exist.
    """
    return _load_raw(workspace).get("surfaces", {})


def clear_state(workspace: str) -> None:
    """Delete the state file for the given workspace."""
    path = _state_path(workspace)
    if path.exists():
        path.unlink()


def _load_raw(workspace: str) -> dict:
    path = _state_path(workspace)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
