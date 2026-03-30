"""Unit tests for builders path resolution, solver config, and split builders.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/test_builders.py
Import mapping:
    oas_mcp.core.builders → hangar.oas.builders
"""

import pytest

from hangar.oas.builders import (
    PathKind,
    SolverConfig,
    _SCALAR_DVS,
    _TOPLEVEL_CONSTRAINTS,
    make_om_path,
    resolve_dv_paths,
    resolve_objective_path,
)


# ---------------------------------------------------------------------------
# make_om_path — DV paths
# ---------------------------------------------------------------------------


class TestMakeOmPathDV:
    def test_twist(self):
        assert make_om_path(PathKind.DV, "twist", surface_name="wing") == "wing.twist_cp"

    def test_thickness(self):
        assert make_om_path(PathKind.DV, "thickness", surface_name="wing") == "wing.thickness_cp"

    def test_t_over_c(self):
        assert make_om_path(PathKind.DV, "t_over_c", surface_name="wing") == "wing.geometry.t_over_c_cp"

    def test_alpha_is_scalar(self):
        assert "alpha" in _SCALAR_DVS
        assert make_om_path(PathKind.DV, "alpha") == "alpha"

    def test_alpha_maneuver_is_scalar(self):
        assert make_om_path(PathKind.DV, "alpha_maneuver") == "alpha_maneuver"

    def test_fuel_mass_is_scalar(self):
        assert make_om_path(PathKind.DV, "fuel_mass") == "fuel_mass"

    def test_cp_suffix_alias(self):
        assert make_om_path(PathKind.DV, "twist_cp", surface_name="wing") == "wing.twist_cp"

    def test_spar_thickness_cp_alias(self):
        assert make_om_path(PathKind.DV, "spar_thickness_cp", surface_name="wing") == "wing.spar_thickness_cp"

    def test_unknown_dv_raises(self):
        with pytest.raises(ValueError, match="Unknown design variable"):
            make_om_path(PathKind.DV, "bogus")

    def test_unknown_dv_with_cp_suffix_raises(self):
        with pytest.raises(ValueError, match="Unknown design variable"):
            make_om_path(PathKind.DV, "bogus_cp")


# ---------------------------------------------------------------------------
# make_om_path — constraint paths
# ---------------------------------------------------------------------------


class TestMakeOmPathConstraint:
    def test_cl_aero(self):
        path = make_om_path(
            PathKind.CONSTRAINT, "CL",
            surface_name="wing", point_name="aero", analysis_type="aero",
        )
        assert path == "aero.wing_perf.CL"

    def test_cl_aerostruct(self):
        path = make_om_path(
            PathKind.CONSTRAINT, "CL",
            surface_name="wing", point_name="AS_point_0", analysis_type="aerostruct",
        )
        assert path == "AS_point_0.wing_perf.CL"

    def test_failure_aerostruct(self):
        path = make_om_path(
            PathKind.CONSTRAINT, "failure",
            surface_name="wing", point_name="AS_point_0", analysis_type="aerostruct",
        )
        assert path == "AS_point_0.wing_perf.failure"

    def test_failure_not_in_aero(self):
        with pytest.raises(ValueError, match="Unknown constraint"):
            make_om_path(
                PathKind.CONSTRAINT, "failure",
                surface_name="wing", point_name="aero", analysis_type="aero",
            )

    def test_toplevel_fuel_vol_delta(self):
        assert "fuel_vol_delta" in _TOPLEVEL_CONSTRAINTS
        path = make_om_path(
            PathKind.CONSTRAINT, "fuel_vol_delta", analysis_type="aerostruct",
        )
        assert path == "fuel_vol_delta.fuel_vol_delta"

    def test_toplevel_fuel_diff(self):
        assert "fuel_diff" in _TOPLEVEL_CONSTRAINTS
        path = make_om_path(
            PathKind.CONSTRAINT, "fuel_diff", analysis_type="aerostruct",
        )
        assert path == "fuel_diff"

    def test_l_equals_w(self):
        path = make_om_path(
            PathKind.CONSTRAINT, "L_equals_W",
            surface_name="wing", point_name="AS_point_0", analysis_type="aerostruct",
        )
        assert path == "AS_point_0.L_equals_W"

    def test_unknown_constraint_raises(self):
        with pytest.raises(ValueError, match="Unknown constraint"):
            make_om_path(PathKind.CONSTRAINT, "bogus", analysis_type="aero")


# ---------------------------------------------------------------------------
# make_om_path — objective paths
# ---------------------------------------------------------------------------


class TestMakeOmPathObjective:
    def test_cd_aero(self):
        path = make_om_path(
            PathKind.OBJECTIVE, "CD",
            point_name="aero", analysis_type="aero",
        )
        assert path == "aero.CD"

    def test_fuelburn_aerostruct(self):
        path = make_om_path(
            PathKind.OBJECTIVE, "fuelburn",
            surface_name="wing", point_name="AS_point_0", analysis_type="aerostruct",
        )
        assert path == "AS_point_0.fuelburn"

    def test_structural_mass_aerostruct(self):
        path = make_om_path(
            PathKind.OBJECTIVE, "structural_mass",
            surface_name="wing", point_name="AS_point_0", analysis_type="aerostruct",
        )
        assert path == "wing.structural_mass"

    def test_fuelburn_not_in_aero(self):
        with pytest.raises(ValueError, match="Unknown objective"):
            make_om_path(PathKind.OBJECTIVE, "fuelburn", analysis_type="aero")

    def test_unknown_objective_raises(self):
        with pytest.raises(ValueError, match="Unknown objective"):
            make_om_path(PathKind.OBJECTIVE, "bogus", analysis_type="aero")


# ---------------------------------------------------------------------------
# resolve_dv_paths / resolve_objective_path
# ---------------------------------------------------------------------------


class TestResolveDvPaths:
    def test_single_point(self):
        dvs = [{"name": "twist"}, {"name": "alpha"}]
        result = resolve_dv_paths(dvs, "wing", "aero", "aero")
        assert result == {
            "twist": "wing.twist_cp",
            "alpha": "alpha",
        }

    def test_multipoint_scalars(self):
        dvs = [{"name": "twist"}, {"name": "alpha_maneuver"}, {"name": "fuel_mass"}]
        result = resolve_dv_paths(dvs, "wing", "AS_point_0", "aerostruct")
        assert result["twist"] == "wing.twist_cp"
        assert result["alpha_maneuver"] == "alpha_maneuver"
        assert result["fuel_mass"] == "fuel_mass"


class TestResolveObjectivePath:
    def test_cd_aero(self):
        assert resolve_objective_path("CD", "wing", "aero", "aero") == "aero.CD"

    def test_fuelburn_aerostruct(self):
        assert resolve_objective_path("fuelburn", "wing", "AS_point_0", "aerostruct") == "AS_point_0.fuelburn"


# ---------------------------------------------------------------------------
# SolverConfig
# ---------------------------------------------------------------------------


class TestSolverConfig:
    def test_defaults(self):
        cfg = SolverConfig()
        assert cfg.nonlinear_solver == "default"
        assert cfg.linear_solver == "default"
        assert cfg.use_aitken is True
        assert cfg.linear_maxiter == 30

    def test_frozen(self):
        cfg = SolverConfig()
        with pytest.raises(AttributeError):
            cfg.iprint = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration: build_aero_optimization_problem / build_aerostruct_optimization_problem
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestSplitOptimizationBuilders:
    @pytest.fixture
    def rect_surface(self):
        from openaerostruct.utils.testing import get_default_surfaces
        surfaces = get_default_surfaces()
        return surfaces[0]

    def test_build_aero_optimization_problem_setup(self, rect_surface):
        from hangar.oas.builders import build_aero_optimization_problem
        prob, point_name = build_aero_optimization_problem(
            surfaces=[rect_surface],
            objective="CD",
            design_variables=[{"name": "twist", "lower": -10, "upper": 10}],
            constraints=[{"name": "CL", "equals": 0.5}],
            flight_conditions={"velocity": 248.136, "alpha": 5.0, "Mach_number": 0.84,
                               "reynolds_number": 1e6, "density": 0.38},
        )
        assert point_name == "aero"
        # Problem should be fully set up and runnable
        assert prob.driver is not None

    def test_build_aerostruct_optimization_problem_setup(self, rect_surface):
        from hangar.oas.builders import build_aerostruct_optimization_problem
        # Add structural properties for aerostruct
        rect_surface["fem_model_type"] = "tube"
        rect_surface["E"] = 70.0e9
        rect_surface["G"] = 30.0e9
        rect_surface["yield"] = 500.0e6
        rect_surface["mrho"] = 3.0e3
        rect_surface["thickness_cp"] = [0.01, 0.01]
        rect_surface["exact_failure_constraint"] = False

        prob, point_name = build_aerostruct_optimization_problem(
            surfaces=[rect_surface],
            objective="fuelburn",
            design_variables=[{"name": "twist", "lower": -10, "upper": 10}],
            constraints=[{"name": "CL", "equals": 0.5}],
            flight_conditions={"velocity": 248.136, "alpha": 5.0, "Mach_number": 0.84,
                               "reynolds_number": 1e6, "density": 0.38},
        )
        assert point_name == "AS_point_0"
        assert prob.driver is not None

    def test_dispatcher_matches_aero(self, rect_surface):
        from hangar.oas.builders import build_optimization_problem
        prob, point_name = build_optimization_problem(
            surfaces=[rect_surface],
            analysis_type="aero",
            objective="CD",
            design_variables=[{"name": "twist", "lower": -10, "upper": 10}],
            constraints=[{"name": "CL", "equals": 0.5}],
            flight_conditions={"velocity": 248.136, "alpha": 5.0, "Mach_number": 0.84,
                               "reynolds_number": 1e6, "density": 0.38},
        )
        assert point_name == "aero"
