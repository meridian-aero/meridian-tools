"""Tests for plan YAML schema validation."""

from __future__ import annotations

import yaml

from hangar.omd.plan_schema import validate_plan, load_and_validate


# ---------------------------------------------------------------------------
# Fixtures: sample plans
# ---------------------------------------------------------------------------

MINIMAL_PLAN = {
    "metadata": {"id": "test-wing-001", "name": "Test Wing Analysis", "version": 1},
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
                    }
                ]
            },
        }
    ],
}

FULL_PLAN = {
    "metadata": {
        "id": "ttbw-opt-001",
        "name": "TTBW Wing Optimization",
        "version": 3,
        "description": "Structural mass minimization for truss-braced wing",
    },
    "requirements": [
        {
            "id": "REQ-001",
            "text": "Structural failure index below 1.0",
            "type": "structural",
            "traces_to": ["CON-failure"],
        },
        {
            "id": "REQ-002",
            "text": "Minimize structural mass",
            "type": "objective",
        },
    ],
    "operating_points": {
        "velocity": 248.136,
        "alpha": 5.0,
        "Mach_number": 0.84,
        "re": 1.0e6,
        "rho": 0.38,
        "CT": 9.81e-6,
        "R": 14.3e6,
        "W0": 25000.0,
        "speed_of_sound": 295.07,
        "load_factor": 1.0,
        "empty_cg": [0.35, 0.0, 0.0],
    },
    "components": [
        {
            "id": "wing",
            "type": "oas/AerostructPoint",
            "source": "openaerostruct",
            "config": {
                "surfaces": [
                    {
                        "name": "wing",
                        "wing_type": "CRM",
                        "num_x": 2,
                        "num_y": 7,
                        "span": 58.7,
                        "root_chord": 11.0,
                        "symmetry": True,
                        "fem_model_type": "tube",
                        "E": 70.0e9,
                        "G": 30.0e9,
                        "yield_stress": 500.0e6,
                        "mrho": 3000.0,
                    }
                ]
            },
        }
    ],
    "connections": [],
    "solvers": {
        "nonlinear": {"type": "NewtonSolver", "options": {"maxiter": 20, "atol": 1e-6}},
        "linear": {"type": "DirectSolver"},
    },
    "design_variables": [
        {"name": "wing.twist_cp", "lower": -10.0, "upper": 15.0, "units": "deg"},
        {
            "name": "wing.thickness_cp",
            "lower": 0.001,
            "upper": 0.5,
            "units": "m",
            "scaler": 100.0,
            "traces_to": ["REQ-001"],
        },
        {"name": "alpha", "lower": -5.0, "upper": 15.0},
    ],
    "constraints": [
        {"name": "AS_point_0.wing_perf.failure", "upper": 0.0, "traces_to": ["REQ-001"]},
        {"name": "AS_point_0.L_equals_W", "equals": 0.0},
    ],
    "objective": {
        "name": "AS_point_0.wing_perf.structural_mass",
        "scaler": 1e-4,
        "traces_to": ["REQ-002"],
    },
    "optimizer": {
        "type": "SLSQP",
        "options": {"maxiter": 200, "ftol": 1e-9},
    },
    "rationale": [
        "Single-point aerostruct optimization for TTBW concept",
        "Tube FEM used for initial sizing before wingbox refinement",
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_minimal_plan_valid():
    errors = validate_plan(MINIMAL_PLAN)
    assert errors == []


def test_full_plan_valid():
    errors = validate_plan(FULL_PLAN)
    assert errors == []


def test_missing_metadata():
    plan = {"components": MINIMAL_PLAN["components"]}
    errors = validate_plan(plan)
    assert len(errors) == 1
    assert "metadata" in errors[0]["message"]


def test_missing_components():
    plan = {"metadata": MINIMAL_PLAN["metadata"]}
    errors = validate_plan(plan)
    assert len(errors) == 1
    assert "components" in errors[0]["message"]


def test_empty_components_rejected():
    plan = {
        "metadata": {"id": "x", "name": "x", "version": 1},
        "components": [],
    }
    errors = validate_plan(plan)
    assert len(errors) >= 1


def test_component_missing_id():
    plan = {
        "metadata": {"id": "x", "name": "x", "version": 1},
        "components": [{"type": "oas/AerostructPoint", "config": {}}],
    }
    errors = validate_plan(plan)
    assert any("id" in e["message"] for e in errors)


def test_invalid_version_type():
    plan = {
        "metadata": {"id": "x", "name": "x", "version": "one"},
        "components": MINIMAL_PLAN["components"],
    }
    errors = validate_plan(plan)
    assert any("version" in e["path"] for e in errors)


def test_invalid_dv_type():
    plan = {
        **MINIMAL_PLAN,
        "design_variables": [{"name": "twist", "lower": "bad"}],
    }
    errors = validate_plan(plan)
    assert any("lower" in e["path"] for e in errors)


def test_unknown_top_level_key():
    plan = {**MINIMAL_PLAN, "unknown_key": "value"}
    errors = validate_plan(plan)
    assert len(errors) >= 1


def test_load_and_validate(tmp_path):
    plan_path = tmp_path / "plan.yaml"
    plan_path.write_text(yaml.dump(MINIMAL_PLAN))
    plan, errors = load_and_validate(plan_path)
    assert errors == []
    assert plan["metadata"]["id"] == "test-wing-001"


def test_load_and_validate_invalid(tmp_path):
    plan_path = tmp_path / "bad.yaml"
    plan_path.write_text(yaml.dump({"metadata": {"id": "x"}}))
    plan, errors = load_and_validate(plan_path)
    assert len(errors) >= 1


def test_load_and_validate_non_dict(tmp_path):
    plan_path = tmp_path / "list.yaml"
    plan_path.write_text("- item1\n- item2\n")
    plan, errors = load_and_validate(plan_path)
    assert len(errors) == 1
    assert "mapping" in errors[0]["message"]
