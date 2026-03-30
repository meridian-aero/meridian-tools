"""Tests for new flight condition parameters: beta, ground effect, omega.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/test_flight_conditions.py
Import mapping:
    oas_mcp.server          → hangar.oas.server
    oas_mcp.core.validators → hangar.oas.validators
"""

import pytest
import pytest_asyncio
from hangar.oas.server import (
    create_surface,
    run_aero_analysis,
    run_aerostruct_analysis,
    compute_drag_polar,
    compute_stability_derivatives,
)
from hangar.oas.validators import (
    validate_flight_conditions,
    validate_ground_effect_compat,
    validate_height_agl,
    validate_omega,
)

pytestmark = pytest.mark.slow


def _r(envelope: dict) -> dict:
    assert "results" in envelope
    return envelope["results"]


# ---------------------------------------------------------------------------
# Fixtures — local definitions for ground-effect surface
# ---------------------------------------------------------------------------

SMALL_RECT_GROUND = dict(
    name="wing", wing_type="rect", span=10.0, root_chord=1.0,
    num_x=2, num_y=5, symmetry=True, with_viscous=True,
    groundplane=True,
)

SMALL_RECT_STRUCT_LOCAL = dict(
    name="wing", wing_type="rect", span=10.0, root_chord=1.0,
    num_x=2, num_y=5, symmetry=True, with_viscous=True,
    fem_model_type="tube", E=70.0e9, G=30.0e9,
    yield_stress=500.0e6, safety_factor=2.5, mrho=3.0e3,
    thickness_cp=[0.05, 0.1, 0.05],
)


@pytest_asyncio.fixture
async def ground_wing():
    await create_surface(**SMALL_RECT_GROUND)
    return "wing"


# ---------------------------------------------------------------------------
# Beta (sideslip) tests
# ---------------------------------------------------------------------------


class TestBeta:
    async def test_aero_with_beta_runs(self, aero_wing):
        env = await run_aero_analysis(surfaces=["wing"], beta=5.0)
        r = _r(env)
        assert "CL" in r

    async def test_beta_changes_results(self, aero_wing):
        env0 = await run_aero_analysis(surfaces=["wing"], beta=0.0)
        env5 = await run_aero_analysis(surfaces=["wing"], beta=5.0)
        r0, r5 = _r(env0), _r(env5)
        # Sideslip should change CD (at minimum, due to effective velocity reduction)
        assert r0["CD"] != r5["CD"]

    async def test_drag_polar_with_beta(self, aero_wing):
        env = await compute_drag_polar(
            surfaces=["wing"], alpha_start=0.0, alpha_end=5.0, num_alpha=3, beta=3.0,
        )
        r = _r(env)
        assert len(r["CL"]) == 3

    async def test_stability_with_beta(self, aero_wing):
        env = await compute_stability_derivatives(surfaces=["wing"], beta=5.0)
        r = _r(env)
        assert "CL_alpha" in r

    async def test_aerostruct_with_beta(self, struct_wing):
        env = await run_aerostruct_analysis(surfaces=["wing"], beta=3.0)
        r = _r(env)
        assert "CL" in r


# ---------------------------------------------------------------------------
# Ground effect tests
# ---------------------------------------------------------------------------


class TestGroundEffect:
    async def test_create_surface_with_groundplane(self):
        result = await create_surface(**SMALL_RECT_GROUND)
        assert result["surface_name"] == "wing"

    async def test_groundplane_requires_symmetry(self):
        with pytest.raises(ValueError, match="symmetry"):
            await create_surface(
                name="wing", wing_type="rect", span=10.0, root_chord=1.0,
                num_x=2, num_y=5, symmetry=False, groundplane=True,
            )

    async def test_ground_effect_increases_cl(self, ground_wing):
        # Low height_agl should increase CL due to ground effect
        env_high = await run_aero_analysis(surfaces=["wing"], height_agl=1000.0, alpha=5.0)
        env_low = await run_aero_analysis(surfaces=["wing"], height_agl=5.0, alpha=5.0)
        r_high, r_low = _r(env_high), _r(env_low)
        # Ground effect should increase CL
        assert r_low["CL"] > r_high["CL"]

    async def test_groundplane_incompatible_with_beta(self, ground_wing):
        with pytest.raises(ValueError, match="incompatible"):
            await run_aero_analysis(surfaces=["wing"], beta=5.0)


# ---------------------------------------------------------------------------
# Omega (rotational velocity) tests
# ---------------------------------------------------------------------------


class TestOmega:
    async def test_aero_with_omega_runs(self, aero_wing):
        env = await run_aero_analysis(
            surfaces=["wing"], omega=[10.0, 0.0, 0.0],
        )
        r = _r(env)
        assert "CL" in r

    async def test_omega_changes_results(self, aero_wing):
        env0 = await run_aero_analysis(surfaces=["wing"])
        env_roll = await run_aero_analysis(surfaces=["wing"], omega=[30.0, 0.0, 0.0])
        r0, r_roll = _r(env0), _r(env_roll)
        # Rolling should change the aerodynamic coefficients
        assert r0["CL"] != r_roll["CL"] or r0["CD"] != r_roll["CD"]


# ---------------------------------------------------------------------------
# Validation tests (fast, no OAS computation)
# ---------------------------------------------------------------------------


class TestValidation:
    def test_beta_out_of_range(self):
        with pytest.raises(ValueError, match="beta"):
            validate_flight_conditions(100.0, 5.0, 0.5, 1e6, 1.0, beta=200.0)

    def test_beta_valid(self):
        validate_flight_conditions(100.0, 5.0, 0.5, 1e6, 1.0, beta=-90.0)

    def test_height_agl_positive(self):
        with pytest.raises(ValueError, match="height_agl"):
            validate_height_agl(0.0)

    def test_height_agl_negative(self):
        with pytest.raises(ValueError, match="height_agl"):
            validate_height_agl(-10.0)

    def test_omega_wrong_length(self):
        with pytest.raises(ValueError, match="3-element"):
            validate_omega([1.0, 2.0])

    def test_omega_none_ok(self):
        validate_omega(None)

    def test_omega_correct_length(self):
        validate_omega([1.0, 2.0, 3.0])

    def test_ground_effect_compat_ok(self):
        surfaces = [{"name": "wing", "groundplane": True}]
        validate_ground_effect_compat(surfaces, 0.0)

    def test_ground_effect_compat_rejects_beta(self):
        surfaces = [{"name": "wing", "groundplane": True}]
        with pytest.raises(ValueError, match="incompatible"):
            validate_ground_effect_compat(surfaces, 5.0)

    def test_no_groundplane_any_beta_ok(self):
        surfaces = [{"name": "wing"}]
        validate_ground_effect_compat(surfaces, 30.0)
