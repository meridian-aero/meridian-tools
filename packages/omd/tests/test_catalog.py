"""Tests for component catalog YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

CATALOG_DIR = Path(__file__).resolve().parents[3] / "catalog"


def test_oas_aerostruct_point_loads():
    path = CATALOG_DIR / "oas" / "AerostructPoint.yaml"
    assert path.exists(), f"Catalog file not found: {path}"
    with open(path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict)


def test_oas_aerostruct_point_required_fields():
    path = CATALOG_DIR / "oas" / "AerostructPoint.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)

    required = ["type", "source", "description", "inputs", "outputs", "partials"]
    for field in required:
        assert field in data, f"Missing required field: {field}"


def test_oas_aerostruct_point_has_known_issues():
    path = CATALOG_DIR / "oas" / "AerostructPoint.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)

    assert "known_issues" in data
    assert len(data["known_issues"]) > 0


def test_oas_aerostruct_point_type():
    path = CATALOG_DIR / "oas" / "AerostructPoint.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)

    assert data["type"] == "oas/AerostructPoint"
    assert data["source"] == "openaerostruct"
