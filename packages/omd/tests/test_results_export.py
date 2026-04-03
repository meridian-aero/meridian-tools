"""Tests for results query and plan export."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

from hangar.omd.db import init_analysis_db, record_entity, record_run_case
from hangar.omd.results import get_results
from hangar.omd.export import export_plan_to_script


# ---------------------------------------------------------------------------
# Results tests
# ---------------------------------------------------------------------------


def test_get_results_not_found(tmp_path):
    init_analysis_db(tmp_path / "test.db")
    result = get_results("nonexistent", db_path=tmp_path / "test.db")
    assert "error" in result


def test_get_results(tmp_path):
    db_path = tmp_path / "test.db"
    init_analysis_db(db_path)

    record_entity("run-test-001", "run_record", "omd", plan_id="test")
    record_run_case("run-test-001", 0, "driver", {"x": 1.0, "y": 2.0})
    record_run_case("run-test-001", 1, "final", {"x": 2.0, "y": 1.5})

    result = get_results("run-test-001", db_path=db_path)
    assert result["run_id"] == "run-test-001"
    assert len(result["cases"]) == 2


def test_get_results_summary(tmp_path):
    db_path = tmp_path / "test.db"
    init_analysis_db(db_path)

    record_entity("run-test-002", "run_record", "omd", plan_id="test")
    record_run_case("run-test-002", 0, "driver", {"x": 1.0})
    record_run_case("run-test-002", 1, "final", {"x": 2.0, "y": 1.5})

    result = get_results("run-test-002", summary=True, db_path=db_path)
    assert "final" in result
    assert result["final"]["x"] == 2.0
    assert result["case_count"] == 2


def test_get_results_variable_filter(tmp_path):
    db_path = tmp_path / "test.db"
    init_analysis_db(db_path)

    record_entity("run-test-003", "run_record", "omd", plan_id="test")
    record_run_case("run-test-003", 0, "final", {"x": 1.0, "y": 2.0, "z": 3.0})

    result = get_results("run-test-003", variables=["x", "z"], db_path=db_path)
    data = result["cases"][0]["data"]
    assert set(data.keys()) == {"x", "z"}


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------


def test_export_generates_valid_python(tmp_path):
    plan = {
        "metadata": {"id": "export-test", "name": "Export Test", "version": 1},
        "components": [
            {
                "id": "wing",
                "type": "oas/AerostructPoint",
                "config": {
                    "surfaces": [
                        {
                            "name": "wing",
                            "wing_type": "rect",
                            "num_x": 2,
                            "num_y": 5,
                            "span": 10.0,
                            "root_chord": 1.0,
                            "symmetry": True,
                            "fem_model_type": "tube",
                            "E": 70.0e9,
                            "G": 30.0e9,
                            "yield_stress": 500.0e6,
                            "mrho": 3000.0,
                            "thickness_cp": [0.05, 0.1, 0.05],
                        }
                    ]
                },
            }
        ],
        "operating_points": {"velocity": 248.136, "alpha": 5.0},
    }

    plan_path = tmp_path / "plan.yaml"
    with open(plan_path, "w") as f:
        yaml.dump(plan, f)

    output = tmp_path / "standalone.py"
    export_plan_to_script(plan_path, output)

    assert output.exists()

    # Verify it's valid Python by parsing the AST
    source = output.read_text()
    ast.parse(source)  # Raises SyntaxError if invalid


def test_export_missing_components(tmp_path):
    import pytest

    plan_path = tmp_path / "empty.yaml"
    with open(plan_path, "w") as f:
        yaml.dump({"metadata": {"id": "x"}, "components": []}, f)

    with pytest.raises(ValueError, match="at least one component"):
        export_plan_to_script(plan_path, tmp_path / "out.py")
