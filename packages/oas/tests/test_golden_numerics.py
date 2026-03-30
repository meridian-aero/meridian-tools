"""Tier 2 — Numeric baseline golden tests.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/golden/test_golden_numerics.py
Import mapping:
    oas_mcp.server → hangar.oas.server
    golden_values.json path → packages/oas/tests/golden/golden_values.json

These compare OAS results against stored golden values in golden_values.json.
They may shift when platform, dependencies (BLAS, NumPy), or OAS internals
change.  Tolerances are intentionally loose (rel=0.5-2%) to allow minor
platform variation while still catching large regressions.

When golden values legitimately change (OAS upgrade, algorithm fix), run:
    python packages/oas/tests/golden/generate_golden.py

Review the diff summary before committing updated baselines.

CI determinism requirements:
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

Run with:
    pytest packages/oas/tests/test_golden_numerics.py -v
    pytest -m golden_numerics
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.golden_numerics]

_GOLDEN_PATH = Path(__file__).parent / "golden" / "golden_values.json"


def _r(envelope: dict) -> dict:
    return envelope["results"]


@pytest.fixture(scope="module")
def golden() -> dict:
    if not _GOLDEN_PATH.exists():
        pytest.skip("golden_values.json not found — run generate_golden.py first")
    with _GOLDEN_PATH.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Rect wing aerodynamic baseline
# ---------------------------------------------------------------------------


class TestRectAeroBaseline:
    @pytest.fixture(autouse=True)
    async def setup_wing(self):
        from hangar.oas.server import create_surface, reset
        await reset()
        await create_surface(
            name="wing", wing_type="rect",
            span=10.0, root_chord=1.0,
            num_x=2, num_y=7, symmetry=True,
            with_viscous=True, CD0=0.015,
        )

    @pytest.mark.asyncio
    async def test_cl_matches_golden(self, golden):
        from hangar.oas.server import run_aero_analysis
        case = golden["cases"]["rect_aero_alpha5"]
        r = _r(await run_aero_analysis(["wing"], alpha=5.0))
        expected = case["outputs"]["CL"]
        tol = case["tolerances"]["CL"]["rel"]
        assert r["CL"] == pytest.approx(expected, rel=tol), (
            f"CL regression: got {r['CL']:.6f}, expected {expected:.6f} ± {tol*100:.1f}%"
        )

    @pytest.mark.asyncio
    async def test_cd_matches_golden(self, golden):
        from hangar.oas.server import run_aero_analysis
        case = golden["cases"]["rect_aero_alpha5"]
        r = _r(await run_aero_analysis(["wing"], alpha=5.0))
        expected = case["outputs"]["CD"]
        tol = case["tolerances"]["CD"]["rel"]
        assert r["CD"] == pytest.approx(expected, rel=tol), (
            f"CD regression: got {r['CD']:.6f}, expected {expected:.6f} ± {tol*100:.1f}%"
        )

    @pytest.mark.asyncio
    async def test_ld_matches_golden(self, golden):
        from hangar.oas.server import run_aero_analysis
        case = golden["cases"]["rect_aero_alpha5"]
        r = _r(await run_aero_analysis(["wing"], alpha=5.0))
        expected = case["outputs"]["L_over_D"]
        tol = case["tolerances"]["L_over_D"]["rel"]
        assert r["L_over_D"] == pytest.approx(expected, rel=tol), (
            f"L/D regression: got {r['L_over_D']:.4f}, expected {expected:.4f}"
        )


# ---------------------------------------------------------------------------
# Rect wing aerostructural baseline
# ---------------------------------------------------------------------------


class TestRectAerostructBaseline:
    @pytest.fixture(autouse=True)
    async def setup_wing(self):
        from hangar.oas.server import create_surface, reset
        await reset()
        await create_surface(
            name="wing", wing_type="rect",
            span=10.0, root_chord=1.0,
            num_x=2, num_y=7, symmetry=True,
            with_viscous=True, CD0=0.015,
            fem_model_type="tube",
            E=70e9, G=30e9, yield_stress=500e6,
            safety_factor=2.5, mrho=3000.0,
        )

    @pytest.mark.asyncio
    async def test_fuelburn_matches_golden(self, golden):
        from hangar.oas.server import run_aerostruct_analysis
        case = golden["cases"]["rect_aerostruct_alpha5"]
        r = _r(await run_aerostruct_analysis(["wing"], alpha=5.0, W0=120000, R=11.165e6))
        expected = case["outputs"]["fuelburn"]
        tol = case["tolerances"]["fuelburn"]["rel"]
        assert r["fuelburn"] == pytest.approx(expected, rel=tol), (
            f"Fuelburn regression: got {r['fuelburn']:.1f}, expected {expected:.1f} ± {tol*100:.1f}%"
        )

    @pytest.mark.asyncio
    async def test_structural_mass_matches_golden(self, golden):
        from hangar.oas.server import run_aerostruct_analysis
        case = golden["cases"]["rect_aerostruct_alpha5"]
        r = _r(await run_aerostruct_analysis(["wing"], alpha=5.0, W0=120000, R=11.165e6))
        expected = case["outputs"]["structural_mass"]
        tol = case["tolerances"]["structural_mass"]["rel"]
        assert r["structural_mass"] == pytest.approx(expected, rel=tol), (
            f"Structural mass regression: got {r['structural_mass']:.2f}, expected {expected:.2f}"
        )


# ---------------------------------------------------------------------------
# CRM wing aerodynamic baseline
# ---------------------------------------------------------------------------


class TestCRMAeroBaseline:
    @pytest.fixture(autouse=True)
    async def setup_wing(self):
        from hangar.oas.server import create_surface, reset
        await reset()
        await create_surface(
            name="wing", wing_type="CRM",
            num_x=2, num_y=7, symmetry=True,
            with_viscous=True, CD0=0.015,
        )

    @pytest.mark.asyncio
    async def test_crm_cl_matches_golden(self, golden):
        from hangar.oas.server import run_aero_analysis
        case = golden["cases"]["crm_aero_alpha5"]
        r = _r(await run_aero_analysis(
            ["wing"], alpha=5.0,
            Mach_number=0.84, density=0.38, velocity=248.136,
        ))
        expected = case["outputs"]["CL"]
        tol = case["tolerances"]["CL"]["rel"]
        assert r["CL"] == pytest.approx(expected, rel=tol), (
            f"CRM CL regression: got {r['CL']:.6f}, expected {expected:.6f}"
        )

    @pytest.mark.asyncio
    async def test_crm_cd_matches_golden(self, golden):
        from hangar.oas.server import run_aero_analysis
        case = golden["cases"]["crm_aero_alpha5"]
        r = _r(await run_aero_analysis(
            ["wing"], alpha=5.0,
            Mach_number=0.84, density=0.38, velocity=248.136,
        ))
        expected = case["outputs"]["CD"]
        tol = case["tolerances"]["CD"]["rel"]
        assert r["CD"] == pytest.approx(expected, rel=tol), (
            f"CRM CD regression: got {r['CD']:.6f}, expected {expected:.6f}"
        )
