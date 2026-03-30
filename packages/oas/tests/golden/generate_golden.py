#!/usr/bin/env python3
"""
Generate or update golden_values.json with current OAS outputs.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/golden/generate_golden.py
Import mapping:
    oas_mcp.server → hangar.oas.server

Run this when golden values legitimately change (OAS upgrade, algorithm fix):

    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
        python packages/oas/tests/golden/generate_golden.py

The script prints a diff summary of changed values so you can review before
committing the updated baselines.

IMPORTANT: Always review the diff before committing.  A change in CL of >1%
or fuelburn of >2% warrants investigation before updating baselines.
"""

from __future__ import annotations

import asyncio
import json
import platform
import sys
from pathlib import Path

import numpy as np

GOLDEN_PATH = Path(__file__).parent / "golden_values.json"


def _r(envelope: dict) -> dict:
    return envelope["results"]


async def _collect_values() -> dict:
    from hangar.oas.server import (
        create_surface,
        reset,
        run_aero_analysis,
        run_aerostruct_analysis,
    )

    cases: dict = {}

    # Case 1: Rect wing aerodynamic
    await reset()
    await create_surface(
        name="wing", wing_type="rect",
        span=10.0, root_chord=1.0,
        num_x=2, num_y=7, symmetry=True,
        with_viscous=True, CD0=0.015,
    )
    env = await run_aero_analysis(["wing"], alpha=5.0)
    r = _r(env)
    cases["rect_aero_alpha5"] = {
        "inputs": {
            "wing_type": "rect", "alpha": 5.0, "num_y": 7,
            "span": 10.0, "root_chord": 1.0, "with_viscous": True, "CD0": 0.015,
        },
        "outputs": {
            "CL": r["CL"], "CD": r["CD"], "CM": r["CM"], "L_over_D": r["L_over_D"],
        },
        "tolerances": {
            "CL": {"rel": 0.005}, "CD": {"rel": 0.01},
            "CM": {"rel": 0.01}, "L_over_D": {"rel": 0.01},
        },
    }

    # Case 2: Rect wing aerostructural
    await reset()
    await create_surface(
        name="wing", wing_type="rect",
        span=10.0, root_chord=1.0,
        num_x=2, num_y=7, symmetry=True,
        with_viscous=True, CD0=0.015,
        fem_model_type="tube",
        E=70e9, G=30e9, yield_stress=500e6, safety_factor=2.5, mrho=3000.0,
    )
    env2 = await run_aerostruct_analysis(["wing"], alpha=5.0, W0=120000, R=11.165e6)
    r2 = _r(env2)
    cases["rect_aerostruct_alpha5"] = {
        "inputs": {
            "wing_type": "rect", "alpha": 5.0, "W0": 120000, "R": 11165000.0,
            "num_y": 7, "fem_model_type": "tube",
            "E": 70e9, "G": 30e9, "yield_stress": 500e6,
            "safety_factor": 2.5, "mrho": 3000.0,
        },
        "outputs": {
            "CL": r2["CL"], "CD": r2["CD"],
            "fuelburn": r2["fuelburn"], "structural_mass": r2["structural_mass"],
        },
        "tolerances": {
            "CL": {"rel": 0.005}, "CD": {"rel": 0.01},
            "fuelburn": {"rel": 0.02}, "structural_mass": {"rel": 0.02},
        },
    }

    # Case 3: CRM wing aerodynamic
    await reset()
    await create_surface(
        name="wing", wing_type="CRM",
        num_x=2, num_y=7, symmetry=True,
        with_viscous=True, CD0=0.015,
    )
    env3 = await run_aero_analysis(
        ["wing"], alpha=5.0,
        Mach_number=0.84, density=0.38, velocity=248.136,
    )
    r3 = _r(env3)
    cases["crm_aero_alpha5"] = {
        "inputs": {
            "wing_type": "CRM", "alpha": 5.0, "Mach_number": 0.84,
            "velocity": 248.136, "density": 0.38, "num_y": 7,
        },
        "outputs": {
            "CL": r3["CL"], "CD": r3["CD"], "CM": r3["CM"], "L_over_D": r3["L_over_D"],
        },
        "tolerances": {
            "CL": {"rel": 0.005}, "CD": {"rel": 0.01},
            "CM": {"rel": 0.05}, "L_over_D": {"rel": 0.01},
        },
    }

    import openmdao
    import openaerostruct

    return {
        "reproducibility_header": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "openmdao_version": openmdao.__version__,
            "oas_version": openaerostruct.__version__,
            "numpy_version": np.__version__,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "note": "Run with OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 for reproducibility",
        },
        "cases": cases,
    }


def _diff_summary(old: dict, new: dict) -> list[str]:
    """Return human-readable diff lines for changed values."""
    lines: list[str] = []
    old_cases = old.get("cases", {})
    new_cases = new.get("cases", {})
    all_case_names = sorted(set(old_cases) | set(new_cases))

    for case_name in all_case_names:
        if case_name not in old_cases:
            lines.append(f"  + NEW case: {case_name}")
            continue
        if case_name not in new_cases:
            lines.append(f"  - REMOVED case: {case_name}")
            continue
        old_out = old_cases[case_name].get("outputs", {})
        new_out = new_cases[case_name].get("outputs", {})
        for key in sorted(set(old_out) | set(new_out)):
            if key not in old_out:
                lines.append(f"  {case_name}.{key}: NEW = {new_out[key]}")
            elif key not in new_out:
                lines.append(f"  {case_name}.{key}: REMOVED")
            else:
                ov, nv = old_out[key], new_out[key]
                if abs(nv - ov) > 1e-10:
                    pct = (nv - ov) / max(abs(ov), 1e-300) * 100
                    lines.append(
                        f"  {case_name}.{key}: {ov:.6g} → {nv:.6g}  ({pct:+.2f}%)"
                    )
    return lines


def main() -> None:
    print("Generating golden values...")
    new_values = asyncio.run(_collect_values())

    old_values: dict = {}
    if GOLDEN_PATH.exists():
        with GOLDEN_PATH.open() as f:
            old_values = json.load(f)

    diff = _diff_summary(old_values, new_values)
    if diff:
        print("\nChanged values (review before committing):")
        for line in diff:
            print(line)
    else:
        print("\nNo numeric changes detected.")

    with GOLDEN_PATH.open("w") as f:
        json.dump(new_values, f, indent=2)
    print(f"\nWritten to {GOLDEN_PATH}")
    print("\nIMPORTANT: Review the diff above before committing updated baselines.")


if __name__ == "__main__":
    main()
