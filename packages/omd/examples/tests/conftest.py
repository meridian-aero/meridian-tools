"""Fixtures for examples parity tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_omd_data(tmp_path, monkeypatch):
    """Redirect all omd data paths to per-test temp directory."""
    monkeypatch.setenv("OMD_DB_PATH", str(tmp_path / "analysis.db"))
    monkeypatch.setenv("OMD_PLAN_STORE", str(tmp_path / "plans"))
    monkeypatch.setenv("OMD_RECORDINGS_DIR", str(tmp_path / "recordings"))
    yield tmp_path
