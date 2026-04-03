"""Parity tests: Lane A (direct scripts) vs Lane B (omd plan pipeline).

Verifies that running the same problem through direct OpenMDAO/OAS code
and through the omd plan pipeline produces matching results.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from hangar.omd.assemble import assemble_plan
from hangar.omd.run import run_plan

EXAMPLES_DIR = Path(__file__).parent.parent


class TestParaboloidParity:

    def test_analysis_parity(self, tmp_path):
        sys.path.insert(0, str(EXAMPLES_DIR / "paraboloid"))
        from paraboloid.lane_a.analysis import run as lane_a_run

        lane_a = lane_a_run()

        plan_dir = EXAMPLES_DIR / "paraboloid" / "lane_b" / "analysis"
        out = tmp_path / "plan.yaml"
        assemble_plan(plan_dir, output=out)
        result = run_plan(out, mode="analysis", recording_level="minimal",
                          db_path=tmp_path / "analysis.db")

        assert result["summary"]["f_xy"] == pytest.approx(lane_a["f_xy"], rel=1e-12)

    def test_optimization_parity(self, tmp_path):
        sys.path.insert(0, str(EXAMPLES_DIR / "paraboloid"))
        from paraboloid.lane_a.optimization import run as lane_a_run

        lane_a = lane_a_run()

        plan_dir = EXAMPLES_DIR / "paraboloid" / "lane_b" / "optimization"
        out = tmp_path / "plan.yaml"
        assemble_plan(plan_dir, output=out)
        result = run_plan(out, mode="optimize", recording_level="minimal",
                          db_path=tmp_path / "analysis.db")

        assert result["summary"]["f_xy"] == pytest.approx(lane_a["f_xy"], rel=1e-4)


class TestOASAeroParity:

    @pytest.mark.slow
    def test_aero_analysis_parity(self, tmp_path):
        sys.path.insert(0, str(EXAMPLES_DIR / "oas_aero_rect"))
        from oas_aero_rect.lane_a.aero_analysis import run as lane_a_run

        lane_a = lane_a_run()

        plan_dir = EXAMPLES_DIR / "oas_aero_rect" / "lane_b" / "aero_analysis"
        out = tmp_path / "plan.yaml"
        assemble_plan(plan_dir, output=out)
        result = run_plan(out, mode="analysis", recording_level="minimal",
                          db_path=tmp_path / "analysis.db")

        assert result["summary"]["CL"] == pytest.approx(lane_a["CL"], rel=1e-6)
        assert result["summary"]["CD"] == pytest.approx(lane_a["CD"], rel=1e-6)


class TestOASAerostructParity:

    @pytest.mark.slow
    def test_aerostruct_analysis_parity(self, tmp_path):
        sys.path.insert(0, str(EXAMPLES_DIR / "oas_aerostruct_rect"))
        from oas_aerostruct_rect.lane_a.aerostruct_analysis import run as lane_a_run

        lane_a = lane_a_run()

        plan_dir = EXAMPLES_DIR / "oas_aerostruct_rect" / "lane_b" / "aerostruct_analysis"
        out = tmp_path / "plan.yaml"
        assemble_plan(plan_dir, output=out)
        result = run_plan(out, mode="analysis", recording_level="minimal",
                          db_path=tmp_path / "analysis.db")

        assert result["summary"]["CL"] == pytest.approx(lane_a["CL"], rel=1e-6)
        assert result["summary"]["CD"] == pytest.approx(lane_a["CD"], rel=1e-6)
