"""Shared fixtures for hangar-omd tests."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolate_omd_data(tmp_path, monkeypatch):
    """Redirect all omd data paths to per-test temp directory."""
    monkeypatch.setenv("OMD_DB_PATH", str(tmp_path / "analysis.db"))
    monkeypatch.setenv("OMD_PLAN_STORE", str(tmp_path / "plans"))
    monkeypatch.setenv("OMD_RECORDINGS_DIR", str(tmp_path / "recordings"))
    yield tmp_path


@pytest.fixture
def fixtures_dir():
    """Return the path to test fixture plan directories."""
    return FIXTURES_DIR
