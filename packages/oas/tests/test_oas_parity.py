"""Tier 3 — OAS parity tests.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/golden/test_parity.py
Import mapping:
    oas_mcp.server → hangar.oas.server
    parity_values.json path → packages/oas/tests/golden/parity_values.json

Verify that the MCP server produces identical results to direct OAS usage.
Each test class maps to one OAS integration test script and cites the source
file and line numbers for traceability.

Run with pytest:
    pytest packages/oas/tests/test_oas_parity.py -v
    pytest -m parity
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow, pytest.mark.parity]

_PARITY_PATH = Path(__file__).parent / "golden" / "parity_values.json"


def _r(envelope: dict) -> dict:
    return envelope["results"]


@pytest.fixture(scope="module")
def parity() -> dict:
    with _PARITY_PATH.open() as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Module-level async runners — used by both pytest and __main__
# ---------------------------------------------------------------------------


async def _mcp_rect_aero() -> dict:
    """MCP: rect wing aero (test_simple_rect_aero.py:104-108)."""
    from hangar.oas.server import create_surface, reset, run_aero_analysis
    await reset()
    await create_surface(
        name="wing", wing_type="rect",
        num_x=2, num_y=5, symmetry=True,
        twist_cp=[0.0], CD0=0.015,
        with_viscous=True, with_wave=False,
    )
    return _r(await run_aero_analysis(
        ["wing"],
        velocity=248.136, alpha=5.0, Mach_number=0.84,
        reynolds_number=1e6, density=0.38,
    ))


async def _mcp_crm_aero() -> dict:
    """MCP: CRM aero (test_aero_analysis.py:104-106)."""
    from hangar.oas.server import create_surface, reset, run_aero_analysis
    await reset()
    await create_surface(
        name="wing", wing_type="CRM",
        num_x=3, num_y=7, num_twist_cp=5, symmetry=True,
        CD0=0.015, with_viscous=True, with_wave=False,
    )
    return _r(await run_aero_analysis(
        ["wing"],
        velocity=248.136, alpha=5.0, Mach_number=0.84,
        reynolds_number=1e6, density=0.38,
    ))


async def _mcp_crm_aerostruct() -> dict:
    """MCP: CRM tube aerostruct (test_aerostruct_analysis.py:141-142).

    OAS thickness_cp=[0.1,0.2,0.3] is tip-to-root; MCP root-to-tip → [0.3,0.2,0.1].
    """
    from hangar.oas.server import create_surface, reset, run_aerostruct_analysis
    await reset()
    await create_surface(
        name="wing", wing_type="CRM",
        num_x=2, num_y=5, num_twist_cp=5, symmetry=True,
        CD0=0.015, with_viscous=True, with_wave=False,
        fem_model_type="tube",
        thickness_cp=[0.3, 0.2, 0.1],
        E=70e9, G=30e9, yield_stress=500e6, safety_factor=2.5, mrho=3e3,
        wing_weight_ratio=2.0, struct_weight_relief=False, distributed_fuel_weight=False,
    )
    return _r(await run_aerostruct_analysis(
        ["wing"],
        velocity=248.136, alpha=5.0, Mach_number=0.84,
        reynolds_number=1e6, density=0.38,
        W0=120000.0, R=11.165e6, speed_of_sound=295.4,
    ))


# ---------------------------------------------------------------------------
# Case 1: Rect wing forward aero
# Source: tests/integration_tests/test_simple_rect_aero.py:104-108
# ---------------------------------------------------------------------------


class TestRectAeroParity:
    """Parity: tests/integration_tests/test_simple_rect_aero.py"""

    @pytest.mark.asyncio
    async def test_cl_matches_oas(self, parity):
        r = await _mcp_rect_aero()
        case = parity["cases"]["rect_aero_parity"]
        expected = case["expected"]["CL"]
        tol = case["tolerances"]["CL"]["rel"]
        assert r["CL"] == pytest.approx(expected, rel=tol), (
            f"CL mismatch: got {r['CL']:.10f}, expected {expected:.10f}"
        )

    @pytest.mark.asyncio
    async def test_cd_matches_oas(self, parity):
        r = await _mcp_rect_aero()
        case = parity["cases"]["rect_aero_parity"]
        expected = case["expected"]["CD"]
        tol = case["tolerances"]["CD"]["rel"]
        assert r["CD"] == pytest.approx(expected, rel=tol), (
            f"CD mismatch: got {r['CD']:.10f}, expected {expected:.10f}"
        )

    @pytest.mark.asyncio
    async def test_cm_matches_oas(self, parity):
        r = await _mcp_rect_aero()
        case = parity["cases"]["rect_aero_parity"]
        expected = case["expected"]["CM"]
        tol = case["tolerances"]["CM"]["rel"]
        assert r["CM"] == pytest.approx(expected, rel=tol), (
            f"CM mismatch: got {r['CM']:.10f}, expected {expected:.10f}"
        )


# ---------------------------------------------------------------------------
# Case 2: CRM wing forward aero
# Source: tests/integration_tests/test_aero_analysis.py:104-106
# ---------------------------------------------------------------------------


class TestCRMAeroParity:
    """Parity: tests/integration_tests/test_aero_analysis.py"""

    @pytest.mark.asyncio
    async def test_cl_matches_oas(self, parity):
        r = await _mcp_crm_aero()
        case = parity["cases"]["crm_aero_parity"]
        expected = case["expected"]["CL"]
        tol = case["tolerances"]["CL"]["rel"]
        assert r["CL"] == pytest.approx(expected, rel=tol), (
            f"CRM CL mismatch: got {r['CL']:.10f}, expected {expected:.10f}"
        )

    @pytest.mark.asyncio
    async def test_cd_matches_oas(self, parity):
        r = await _mcp_crm_aero()
        case = parity["cases"]["crm_aero_parity"]
        expected = case["expected"]["CD"]
        tol = case["tolerances"]["CD"]["rel"]
        assert r["CD"] == pytest.approx(expected, rel=tol), (
            f"CRM CD mismatch: got {r['CD']:.10f}, expected {expected:.10f}"
        )

    @pytest.mark.asyncio
    async def test_cm_matches_oas(self, parity):
        r = await _mcp_crm_aero()
        case = parity["cases"]["crm_aero_parity"]
        expected = case["expected"]["CM"]
        tol = case["tolerances"]["CM"]["rel"]
        assert r["CM"] == pytest.approx(expected, rel=tol), (
            f"CRM CM mismatch: got {r['CM']:.10f}, expected {expected:.10f}"
        )


# ---------------------------------------------------------------------------
# Case 3: CRM tube aerostructural forward analysis
# Source: tests/integration_tests/test_aerostruct_analysis.py:141-142
# ---------------------------------------------------------------------------


class TestCRMAerostructParity:
    """Parity: tests/integration_tests/test_aerostruct_analysis.py"""

    @pytest.mark.asyncio
    async def test_fuelburn_matches_oas(self, parity):
        r = await _mcp_crm_aerostruct()
        case = parity["cases"]["crm_aerostruct_parity"]
        expected = case["expected"]["fuelburn"]
        tol = case["tolerances"]["fuelburn"]["rel"]
        assert r["fuelburn"] == pytest.approx(expected, rel=tol), (
            f"Fuelburn mismatch: got {r['fuelburn']:.4f}, expected {expected:.4f}"
        )

    @pytest.mark.asyncio
    async def test_cm_matches_oas(self, parity):
        r = await _mcp_crm_aerostruct()
        case = parity["cases"]["crm_aerostruct_parity"]
        expected = case["expected"]["CM"]
        tol = case["tolerances"]["CM"]["rel"]
        assert r["CM"] == pytest.approx(expected, rel=tol), (
            f"Aerostruct CM mismatch: got {r['CM']:.10f}, expected {expected:.10f}"
        )


# ---------------------------------------------------------------------------
# Direct execution: side-by-side OAS vs MCP comparison
# ---------------------------------------------------------------------------


def _rel_diff(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def _status(diff: float, tol: float) -> str:
    return "PASS" if diff <= tol else "FAIL"


async def _run_parity_report() -> int:
    """Run all 3 cases and print a side-by-side OAS vs MCP comparison table."""
    import sys
    from pathlib import Path

    # Import OAS-direct runners from generate_parity.py (same directory)
    sys.path.insert(0, str(Path(__file__).parent / "golden"))
    import generate_parity  # noqa: PLC0415

    with _PARITY_PATH.open() as f:
        ref = json.load(f)

    cases = [
        {
            "label": "Rect Aero",
            "source": "test_simple_rect_aero.py:104-108",
            "oas_fn": generate_parity.run_oas_rect_aero,
            "mcp_fn": _mcp_rect_aero,
            "ref_key": "rect_aero_parity",
            "quantities": ["CL", "CD", "CM"],
        },
        {
            "label": "CRM Aero",
            "source": "test_aero_analysis.py:104-106",
            "oas_fn": generate_parity.run_oas_crm_aero,
            "mcp_fn": _mcp_crm_aero,
            "ref_key": "crm_aero_parity",
            "quantities": ["CL", "CD", "CM"],
        },
        {
            "label": "CRM Aerostruct",
            "source": "test_aerostruct_analysis.py:141-142",
            "oas_fn": generate_parity.run_oas_crm_aerostruct,
            "mcp_fn": _mcp_crm_aerostruct,
            "ref_key": "crm_aerostruct_parity",
            "quantities": ["fuelburn", "CM"],
        },
    ]

    total = 0
    passed = 0
    sep = "=" * 70

    print(sep)
    print("OAS Parity Report — OAS direct vs MCP server")
    print(sep)

    for i, case in enumerate(cases, 1):
        ref_case = ref["cases"][case["ref_key"]]
        quantities = case["quantities"]

        print(f"\n[{i}/{len(cases)}] {case['label']}  ({case['source']})")

        print("  Running OAS direct...", end="", flush=True)
        oas_results = case["oas_fn"]()
        print(" done")

        print("  Running MCP server...", end="", flush=True)
        mcp_results = await case["mcp_fn"]()
        print(" done")

        col_w = 26
        delta_label = "\u0394 rel"
        hdr = (
            f"  {'Quantity':<12}  {'OAS Direct':<{col_w}}  "
            f"{'MCP Result':<{col_w}}  {delta_label:<12}  Status"
        )
        print()
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for qty in quantities:
            oas_val = oas_results[qty]
            mcp_val = mcp_results[qty]
            tol = ref_case["tolerances"][qty]["rel"]
            diff = _rel_diff(oas_val, mcp_val)
            status = _status(diff, tol)
            total += 1
            if status == "PASS":
                passed += 1
            print(
                f"  {qty:<12}  {oas_val:<{col_w}.16g}  "
                f"{mcp_val:<{col_w}.16g}  {diff:<12.2e}  {status}"
            )

    print()
    print(sep)
    print(f"Summary: {passed}/{total} passed")
    print(sep)

    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(_run_parity_report()))
