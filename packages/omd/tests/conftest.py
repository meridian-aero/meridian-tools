"""Shared fixtures for hangar-omd tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Redirect analysis DB to per-test temp directory."""
    monkeypatch.setenv("OMD_DB_PATH", str(tmp_path / "analysis.db"))
    yield tmp_path
