#!/usr/bin/env python3
"""
Generate or update parity_values.json by running the real OAS integration tests.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/golden/generate_parity.py
Import mapping:
    REPO_ROOT path updated for hangar layout

Each runner in this module loads the actual integration test file, intercepts
its assert_near_equal calls to capture computed values, and returns the results.
This ensures the ground truth always comes from the canonical OAS test code —
no duplication, no drift.

Run this when OAS internals change (upgrade, algorithm fix) and you need to
refresh the reference values:

    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
        python packages/oas/tests/golden/generate_parity.py

The script prints a diff summary so you can review changes before committing.

Sources (relative to upstream/OpenAeroStruct):
  rect_aero_parity      — tests/integration_tests/test_simple_rect_aero.py
  crm_aero_parity       — tests/integration_tests/test_aero_analysis.py
  crm_aerostruct_parity — tests/integration_tests/test_aerostruct_analysis.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

import numpy as np

PARITY_PATH = Path(__file__).parent / "parity_values.json"
# golden/ → tests/ → oas/ → packages/ → repo root → upstream/OpenAeroStruct
REPO_ROOT = Path(__file__).parents[4] / "upstream" / "OpenAeroStruct"

# Tolerances are policy decisions — not derived from runs.
_TOLERANCES = {
    "rect_aero_parity": {
        "CL": {"rel": 1e-6},
        "CD": {"rel": 1e-6},
        "CM": {"rel": 1e-6},
    },
    "crm_aero_parity": {
        "CL": {"rel": 1e-6},
        "CD": {"rel": 1e-6},
        "CM": {"rel": 1e-6},
    },
    "crm_aerostruct_parity": {
        "fuelburn": {"rel": 1e-4},
        "CM": {"rel": 1e-5},
    },
}


@contextlib.contextmanager
def _quiet():
    """Suppress stdout/stderr from OAS/OpenMDAO during a run."""
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            yield


def _load_integration_test(rel_path: str):
    """Load an OAS integration test module without adding it to sys.modules."""
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location("_oas_integ_test", path)
    mod = importlib.util.module_from_spec(spec)
    with _quiet():
        spec.loader.exec_module(mod)
    return mod


def _capture_and_run(mod) -> list[dict]:
    """Replace mod.assert_near_equal with a recorder and run Test().test().

    assert_near_equal is imported at module level via
        from openmdao.utils.assert_utils import assert_near_equal
    so after exec_module it lives in mod.__dict__. Replacing it there means
    every call inside test() uses our recorder instead.

    Returns a list of {"actual": float, "desired": float, "tol": float}
    in call order.
    """
    captured: list[dict] = []

    def _record(actual, desired, tolerance=1e-6):
        captured.append({
            "actual": float(np.atleast_1d(actual)[0]) if hasattr(actual, "__len__") else float(actual),
            "desired": float(desired),
            "tol": float(tolerance),
        })

    mod.assert_near_equal = _record

    test_instance = mod.Test()
    with _quiet():
        test_instance.test()

    return captured


# ---------------------------------------------------------------------------
# Public runners — called by test_parity.py __main__ and main() below
# ---------------------------------------------------------------------------


def run_oas_rect_aero() -> dict:
    """Run tests/integration_tests/test_simple_rect_aero.py and return results.

    assert_near_equal call order (lines 104-108):
      [0] CD    [1] CL    [2] CM[0]=0    [3] CM[1]    [4] CM[2]=0
    """
    mod = _load_integration_test("tests/integration_tests/test_simple_rect_aero.py")
    c = _capture_and_run(mod)
    return {
        "CD": c[0]["actual"],
        "CL": c[1]["actual"],
        "CM": c[3]["actual"],  # CM[1] (pitching moment)
    }


def run_oas_crm_aero() -> dict:
    """Run tests/integration_tests/test_aero_analysis.py and return results.

    assert_near_equal call order (lines 104-106):
      [0] CD    [1] CL    [2] CM[1]
    """
    mod = _load_integration_test("tests/integration_tests/test_aero_analysis.py")
    c = _capture_and_run(mod)
    return {
        "CD": c[0]["actual"],
        "CL": c[1]["actual"],
        "CM": c[2]["actual"],  # CM[1]
    }


def run_oas_crm_aerostruct() -> dict:
    """Run tests/integration_tests/test_aerostruct_analysis.py and return results.

    assert_near_equal call order (lines 141-142):
      [0] fuelburn    [1] CM[1]
    """
    mod = _load_integration_test("tests/integration_tests/test_aerostruct_analysis.py")
    c = _capture_and_run(mod)
    return {
        "fuelburn": c[0]["actual"],
        "CM": c[1]["actual"],  # CM[1]
    }


# ---------------------------------------------------------------------------
# Collect + diff + write
# ---------------------------------------------------------------------------


def _collect_oas_values() -> dict:
    """Run all three integration tests and return the full parity_values dict."""
    import openaerostruct
    import openmdao

    cases: dict = {}

    print("  [1/3] Rect aero  (test_simple_rect_aero.py)...", end="", flush=True)
    r1 = run_oas_rect_aero()
    cases["rect_aero_parity"] = {
        "source": "tests/integration_tests/test_simple_rect_aero.py:104-108",
        "surface_config": {
            "name": "wing", "wing_type": "rect", "num_x": 2, "num_y": 5,
            "symmetry": True, "twist_cp": [0.0], "CD0": 0.015,
            "with_viscous": True, "with_wave": False,
        },
        "flight_config": {
            "surfaces": ["wing"], "velocity": 248.136, "alpha": 5.0,
            "Mach_number": 0.84, "reynolds_number": 1000000.0, "density": 0.38,
        },
        "expected": r1,
        "tolerances": _TOLERANCES["rect_aero_parity"],
    }
    print(f"  CL={r1['CL']:.10g}  CD={r1['CD']:.10g}  CM={r1['CM']:.10g}")

    print("  [2/3] CRM aero   (test_aero_analysis.py)...", end="", flush=True)
    r2 = run_oas_crm_aero()
    cases["crm_aero_parity"] = {
        "source": "tests/integration_tests/test_aero_analysis.py:104-106",
        "surface_config": {
            "name": "wing", "wing_type": "CRM", "num_x": 3, "num_y": 7,
            "num_twist_cp": 5, "symmetry": True, "CD0": 0.015,
            "with_viscous": True, "with_wave": False,
        },
        "flight_config": {
            "surfaces": ["wing"], "velocity": 248.136, "alpha": 5.0,
            "Mach_number": 0.84, "reynolds_number": 1000000.0, "density": 0.38,
        },
        "expected": r2,
        "tolerances": _TOLERANCES["crm_aero_parity"],
    }
    print(f"  CL={r2['CL']:.10g}  CD={r2['CD']:.10g}  CM={r2['CM']:.10g}")

    print("  [3/3] CRM aerostruct  (test_aerostruct_analysis.py)...", end="", flush=True)
    r3 = run_oas_crm_aerostruct()
    cases["crm_aerostruct_parity"] = {
        "source": "tests/integration_tests/test_aerostruct_analysis.py:141-142",
        "surface_config": {
            "name": "wing", "wing_type": "CRM", "num_x": 2, "num_y": 5,
            "num_twist_cp": 5, "symmetry": True, "CD0": 0.015,
            "with_viscous": True, "with_wave": False,
            "fem_model_type": "tube",
            "thickness_cp": [0.3, 0.2, 0.1],
            "E": 70000000000.0, "G": 30000000000.0,
            "yield_stress": 500000000.0, "safety_factor": 2.5, "mrho": 3000.0,
            "wing_weight_ratio": 2.0, "struct_weight_relief": False,
            "distributed_fuel_weight": False,
        },
        "flight_config": {
            "surfaces": ["wing"], "velocity": 248.136, "alpha": 5.0,
            "Mach_number": 0.84, "reynolds_number": 1000000.0, "density": 0.38,
            "W0": 120000.0, "R": 11165000.0, "speed_of_sound": 295.4,
        },
        "expected": r3,
        "tolerances": _TOLERANCES["crm_aerostruct_parity"],
    }
    print(f"  fuelburn={r3['fuelburn']:.8g}  CM={r3['CM']:.10g}")

    return {
        "schema_version": "1.0",
        "description": "OAS integration test reference values for MCP parity tests",
        "reproducibility_header": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "openmdao_version": openmdao.__version__,
            "oas_version": openaerostruct.__version__,
            "numpy_version": np.__version__,
            "note": "Run with OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1",
        },
        "cases": cases,
    }


def _diff_summary(old: dict, new: dict) -> list[str]:
    lines: list[str] = []
    old_cases = old.get("cases", {})
    new_cases = new.get("cases", {})
    for case_name in sorted(set(old_cases) | set(new_cases)):
        if case_name not in old_cases:
            lines.append(f"  + NEW case: {case_name}")
            continue
        if case_name not in new_cases:
            lines.append(f"  - REMOVED case: {case_name}")
            continue
        old_exp = old_cases[case_name].get("expected", {})
        new_exp = new_cases[case_name].get("expected", {})
        for key in sorted(set(old_exp) | set(new_exp)):
            if key not in old_exp:
                lines.append(f"  {case_name}.{key}: NEW = {new_exp[key]}")
            elif key not in new_exp:
                lines.append(f"  {case_name}.{key}: REMOVED")
            else:
                ov, nv = old_exp[key], new_exp[key]
                if abs(nv - ov) > 1e-12:
                    pct = (nv - ov) / max(abs(ov), 1e-300) * 100
                    lines.append(
                        f"  {case_name}.{key}: {ov:.10g} → {nv:.10g}  ({pct:+.4f}%)"
                    )
    return lines


def main() -> None:
    print("Generating parity reference values by running OAS integration tests...")
    print()
    new_values = _collect_oas_values()

    old_values: dict = {}
    if PARITY_PATH.exists():
        with PARITY_PATH.open() as f:
            old_values = json.load(f)

    diff = _diff_summary(old_values, new_values)
    if diff:
        print("\nChanged values (review before committing):")
        for line in diff:
            print(line)
    else:
        print("\nNo numeric changes detected.")

    with PARITY_PATH.open("w") as f:
        json.dump(new_values, f, indent=2)
    print(f"\nWritten to {PARITY_PATH}")
    print("\nIMPORTANT: Review the diff above before committing updated baselines.")


if __name__ == "__main__":
    main()
