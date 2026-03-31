"""Parity tests: Lane A (direct pyCycle) vs Lane B (hangar-pyc MCP tools).

Verifies that the MCP tool layer produces the same results as calling the
pyCycle API directly.  Both lanes use parameters from shared.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Add the example root to sys.path so we can import shared + lane_a
_EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXAMPLE_ROOT))

from shared import (
    ENGINE_PARAMS, DESIGN_POINT, OFF_DESIGN_POINTS,
    TOL_PERFORMANCE, TOL_OFF_DESIGN, TOL_FLOW_STATION, TOL_COMPONENT,
)

from hangar.pyc.tools.engine import create_engine
from hangar.pyc.tools.analysis import run_design_point, run_off_design


# ---------------------------------------------------------------------------
# Lane A runners (direct pyCycle API)
# ---------------------------------------------------------------------------

def _run_lane_a_design():
    from lane_a.design_analysis import run
    return run()


def _run_lane_a_multipoint():
    from lane_a.off_design_analysis import run
    return run()


# ---------------------------------------------------------------------------
# Lane B runners (MCP tools)
# ---------------------------------------------------------------------------

async def _run_lane_b_design() -> dict:
    await create_engine(
        archetype="turbojet",
        name="tj",
        thermo_method=ENGINE_PARAMS["thermo_method"],
        comp_PR=ENGINE_PARAMS["comp_PR"],
        comp_eff=ENGINE_PARAMS["comp_eff"],
        turb_eff=ENGINE_PARAMS["turb_eff"],
        Nmech=ENGINE_PARAMS["Nmech"],
        burner_dPqP=ENGINE_PARAMS["burner_dPqP"],
        nozz_Cv=ENGINE_PARAMS["nozz_Cv"],
    )
    envelope = await run_design_point(
        engine_name="tj",
        alt=DESIGN_POINT["alt"],
        MN=DESIGN_POINT["MN"],
        Fn_target=DESIGN_POINT["Fn_target"],
        T4_target=DESIGN_POINT["T4_target"],
    )
    return envelope["results"]


async def _run_lane_b_off_design(od_point: dict) -> dict:
    """Run a single off-design point via MCP (engine must already exist)."""
    envelope = await run_off_design(
        engine_name="tj",
        alt=od_point["alt"],
        MN=od_point["MN"],
        Fn_target=od_point["Fn_target"],
    )
    return envelope["results"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_close(a_val, b_val, label: str, **tol_kwargs):
    """Assert two values are close with a descriptive message."""
    np.testing.assert_allclose(
        a_val, b_val,
        err_msg=f"Parity mismatch on '{label}': lane_a={a_val}, lane_b={b_val}",
        **tol_kwargs,
    )


# ---------------------------------------------------------------------------
# Design-point parity
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parity
class TestDesignPointParity:
    """Lane A vs Lane B at the design point."""

    async def test_design_point_performance(self):
        a = _run_lane_a_design()
        b = await _run_lane_b_design()
        perf_b = b["performance"]

        _assert_close(a["Fn"], perf_b["Fn"], "Fn", **TOL_PERFORMANCE)
        _assert_close(a["TSFC"], perf_b["TSFC"], "TSFC", **TOL_PERFORMANCE)
        _assert_close(a["OPR"], perf_b["OPR"], "OPR", **TOL_PERFORMANCE)
        _assert_close(a["Fg"], perf_b["Fg"], "Fg", **TOL_PERFORMANCE)

    async def test_design_point_components(self):
        a = _run_lane_a_design()
        b = await _run_lane_b_design()
        comp_b = b["components"]["comp"]
        turb_b = b["components"]["turb"]

        _assert_close(a["comp.PR"], comp_b["PR"], "comp.PR", **TOL_COMPONENT)
        _assert_close(a["comp.eff"], comp_b["eff"], "comp.eff", **TOL_COMPONENT)
        _assert_close(a["turb.PR"], turb_b["PR"], "turb.PR", **TOL_COMPONENT)
        _assert_close(a["turb.eff"], turb_b["eff"], "turb.eff", **TOL_COMPONENT)

    async def test_design_point_flow_stations(self):
        a = _run_lane_a_design()
        b = await _run_lane_b_design()
        fs_b = b["flow_stations"]

        _assert_close(
            a["burner.Fl_O:tot:T"],
            fs_b["burner.Fl_O"]["tot:T"],
            "burner.Fl_O:tot:T",
            **TOL_FLOW_STATION,
        )
        _assert_close(
            a["comp.Fl_O:tot:P"],
            fs_b["comp.Fl_O"]["tot:P"],
            "comp.Fl_O:tot:P",
            **TOL_FLOW_STATION,
        )


# ---------------------------------------------------------------------------
# Off-design parity
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parity
class TestOffDesignParity:
    """Lane A vs Lane B at off-design conditions."""

    async def test_off_design_od0(self):
        """SLS off-design: alt=0, MN~0, Fn=11000 lbf."""
        a_all = _run_lane_a_multipoint()
        a = a_all["OD0"]

        # Lane B: create engine, design, then off-design
        await create_engine(
            archetype="turbojet", name="tj",
            thermo_method=ENGINE_PARAMS["thermo_method"],
            comp_PR=ENGINE_PARAMS["comp_PR"],
            comp_eff=ENGINE_PARAMS["comp_eff"],
            turb_eff=ENGINE_PARAMS["turb_eff"],
            Nmech=ENGINE_PARAMS["Nmech"],
            burner_dPqP=ENGINE_PARAMS["burner_dPqP"],
            nozz_Cv=ENGINE_PARAMS["nozz_Cv"],
        )
        await run_design_point(
            engine_name="tj",
            alt=DESIGN_POINT["alt"], MN=DESIGN_POINT["MN"],
            Fn_target=DESIGN_POINT["Fn_target"], T4_target=DESIGN_POINT["T4_target"],
        )
        b = await _run_lane_b_off_design(OFF_DESIGN_POINTS[0])
        perf_b = b["performance"]

        _assert_close(a["Fn"], perf_b["Fn"], "OD0.Fn", **TOL_OFF_DESIGN)
        _assert_close(a["TSFC"], perf_b["TSFC"], "OD0.TSFC", **TOL_OFF_DESIGN)
        _assert_close(a["OPR"], perf_b["OPR"], "OD0.OPR", **TOL_OFF_DESIGN)

    async def test_off_design_od1(self):
        """Climb off-design: alt=5000, MN=0.2, Fn=8000 lbf."""
        a_all = _run_lane_a_multipoint()
        a = a_all["OD1"]

        await create_engine(
            archetype="turbojet", name="tj",
            thermo_method=ENGINE_PARAMS["thermo_method"],
            comp_PR=ENGINE_PARAMS["comp_PR"],
            comp_eff=ENGINE_PARAMS["comp_eff"],
            turb_eff=ENGINE_PARAMS["turb_eff"],
            Nmech=ENGINE_PARAMS["Nmech"],
            burner_dPqP=ENGINE_PARAMS["burner_dPqP"],
            nozz_Cv=ENGINE_PARAMS["nozz_Cv"],
        )
        await run_design_point(
            engine_name="tj",
            alt=DESIGN_POINT["alt"], MN=DESIGN_POINT["MN"],
            Fn_target=DESIGN_POINT["Fn_target"], T4_target=DESIGN_POINT["T4_target"],
        )
        b = await _run_lane_b_off_design(OFF_DESIGN_POINTS[1])
        perf_b = b["performance"]

        _assert_close(a["Fn"], perf_b["Fn"], "OD1.Fn", **TOL_OFF_DESIGN)
        _assert_close(a["TSFC"], perf_b["TSFC"], "OD1.TSFC", **TOL_OFF_DESIGN)
        _assert_close(a["OPR"], perf_b["OPR"], "OD1.OPR", **TOL_OFF_DESIGN)
