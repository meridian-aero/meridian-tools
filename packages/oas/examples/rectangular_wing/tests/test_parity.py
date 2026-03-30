"""Parity tests: verify Lane A (raw OAS) and Lane B (MCP) produce matching results.

Run with:
    uv run pytest packages/oas/examples/rectangular_wing/tests/ -v

Migrated from: upstream/OpenAeroStruct/oas_mcp/demonstrations/rectangular_wing/tests/test_parity.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# Make the demonstrations package importable
DEMO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEMO_DIR))

from shared import TOL_ANALYSIS, TOL_POLAR, TOL_OPT_OBJ, TOL_OPT_CON, TOL_OPT_DV

LANE_B_DIR = DEMO_DIR / "lane_b"


# ── Helpers ───────────────────────────────────────────────────────────────

async def run_lane_b(script_name: str) -> dict:
    """Run a Lane B JSON script in-process and return the last step's results."""
    from hangar.sdk.cli.runner import run_tool

    script_path = LANE_B_DIR / f"{script_name}.json"
    steps = json.loads(script_path.read_text())
    last_result = None
    for step in steps:
        resp = await run_tool(step["tool"], step.get("args", {}))
        assert resp.get("ok"), f"Lane B step {step['tool']} failed: {resp.get('error')}"
        last_result = resp.get("result", {})

    if last_result and "results" in last_result:
        return last_result["results"]
    return last_result


def run_lane_a(script_name: str) -> dict:
    """Import and run a Lane A script, return its result dict."""
    import importlib
    mod = importlib.import_module(f"lane_a.{script_name}")
    return mod.run()


# ── Aero Analysis ────────────────────────────────────────────────────────

class TestAeroAnalysis:
    """Compare single-point aero results across lanes."""

    def test_lane_a(self):
        r = run_lane_a("aero_analysis")
        assert r["CL"] > 0, "CL should be positive at alpha=5"
        assert r["CD"] > 0, "CD should always be positive"

    @pytest.mark.asyncio
    async def test_lane_b(self):
        r = await run_lane_b("aero_analysis")
        assert r["CL"] > 0
        assert r["CD"] > 0

    @pytest.mark.asyncio
    async def test_a_vs_b(self):
        a = run_lane_a("aero_analysis")
        b = await run_lane_b("aero_analysis")
        np.testing.assert_allclose(a["CL"], b["CL"], **TOL_ANALYSIS)
        np.testing.assert_allclose(a["CD"], b["CD"], **TOL_ANALYSIS)


# ── Drag Polar ───────────────────────────────────────────────────────────

class TestDragPolar:
    """Compare drag polar sweep results across lanes."""

    def test_lane_a(self):
        r = run_lane_a("drag_polar")
        assert len(r["CL"]) == 20
        assert len(r["CD"]) == 20
        # CD has interior minimum (parabolic)
        cds = r["CD"]
        min_idx = cds.index(min(cds))
        assert 0 < min_idx < len(cds) - 1

    @pytest.mark.asyncio
    async def test_lane_b(self):
        r = await run_lane_b("drag_polar")
        assert len(r["CL"]) == 20
        assert len(r["CD"]) == 20

    @pytest.mark.asyncio
    async def test_a_vs_b(self):
        a = run_lane_a("drag_polar")
        b = await run_lane_b("drag_polar")
        np.testing.assert_allclose(a["CL"], b["CL"], **TOL_POLAR)
        np.testing.assert_allclose(a["CD"], b["CD"], **TOL_POLAR)


# ── Twist Optimization ───────────────────────────────────────────────────

class TestOptTwist:
    """Compare twist optimisation results across lanes."""

    def test_lane_a(self):
        r = run_lane_a("opt_twist")
        assert r["success"]
        np.testing.assert_allclose(r["CL"], 0.5, **TOL_OPT_CON)

    @pytest.mark.asyncio
    async def test_lane_b(self):
        r = await run_lane_b("opt_twist")
        assert r["success"]
        final = r["final_results"]
        np.testing.assert_allclose(final["CL"], 0.5, **TOL_OPT_CON)

    @pytest.mark.asyncio
    async def test_a_vs_b(self):
        a = run_lane_a("opt_twist")
        b = await run_lane_b("opt_twist")
        b_final = b["final_results"]
        # Objectives should match
        np.testing.assert_allclose(a["CD"], b_final["CD"], **TOL_OPT_OBJ)
        # Both satisfy constraint
        np.testing.assert_allclose(a["CL"], 0.5, **TOL_OPT_CON)
        np.testing.assert_allclose(b_final["CL"], 0.5, **TOL_OPT_CON)
        # DV values should be close (MCP returns root-to-tip, Lane A already reversed)
        b_twist = b["optimized_design_variables"]["twist"]
        np.testing.assert_allclose(a["twist_cp"], b_twist, **TOL_OPT_DV)


# ── Chord Optimization ───────────────────────────────────────────────────

class TestOptChord:
    """Compare chord optimisation results across lanes."""

    def test_lane_a(self):
        r = run_lane_a("opt_chord")
        assert r["success"]
        np.testing.assert_allclose(r["CL"], 0.5, **TOL_OPT_CON)
        np.testing.assert_allclose(r["S_ref"], 10.0, atol=0.01)

    @pytest.mark.asyncio
    async def test_lane_b(self):
        r = await run_lane_b("opt_chord")
        assert r["success"]
        final = r["final_results"]
        np.testing.assert_allclose(final["CL"], 0.5, **TOL_OPT_CON)

    @pytest.mark.asyncio
    async def test_a_vs_b(self):
        a = run_lane_a("opt_chord")
        b = await run_lane_b("opt_chord")
        b_final = b["final_results"]
        # Objectives should match
        np.testing.assert_allclose(a["CD"], b_final["CD"], **TOL_OPT_OBJ)
        # Both satisfy constraints
        np.testing.assert_allclose(a["CL"], 0.5, **TOL_OPT_CON)
        np.testing.assert_allclose(b_final["CL"], 0.5, **TOL_OPT_CON)
        # DV values (MCP returns root-to-tip, Lane A already reversed)
        b_chord = b["optimized_design_variables"]["chord"]
        np.testing.assert_allclose(a["chord_cp"], b_chord, **TOL_OPT_DV)
