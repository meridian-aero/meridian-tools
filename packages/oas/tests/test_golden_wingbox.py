"""Golden physics invariant tests for wingbox aerostructural analysis.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/golden/test_golden_wingbox.py
Import mapping:
    oas_mcp.server → hangar.oas.server

These tests verify fundamental physical relationships that must hold
regardless of platform or implementation details. No golden_values.json
baseline needed — these are invariants, not numeric comparisons.
"""

import pytest
from hangar.oas.server import create_surface, reset, run_aerostruct_analysis

pytestmark = [pytest.mark.slow, pytest.mark.golden_physics]


def _r(envelope: dict) -> dict:
    """Extract the results payload from a versioned response envelope."""
    assert "schema_version" in envelope
    return envelope["results"]


_WINGBOX_SURFACE = dict(
    name="wing",
    wing_type="rect",
    span=10.0,
    root_chord=1.0,
    num_x=2,
    num_y=7,
    symmetry=True,
    with_viscous=True,
    fem_model_type="wingbox",
    E=73.1e9,
    G=27.5e9,
    yield_stress=420.0e6,
    safety_factor=1.5,
    mrho=2.78e3,
)


async def _run_wingbox(alpha=5.0, **overrides):
    """Create a wingbox surface and run aerostruct analysis."""
    await reset()
    surface_args = {**_WINGBOX_SURFACE, **overrides}
    await create_surface(**surface_args)
    return _r(await run_aerostruct_analysis(["wing"], alpha=alpha))


class TestWingboxPhysicsInvariants:
    async def test_cd_always_positive(self):
        for alpha in (0.0, 3.0, 5.0):
            r = await _run_wingbox(alpha=alpha)
            assert r["CD"] > 0, f"CD should be positive at alpha={alpha}"

    async def test_cl_monotonic_with_alpha(self):
        """CL should increase with angle of attack."""
        cl_values = []
        for alpha in (0.0, 3.0, 6.0):
            r = await _run_wingbox(alpha=alpha)
            cl_values.append(r["CL"])
        for i in range(len(cl_values) - 1):
            assert cl_values[i] < cl_values[i + 1], (
                f"CL not monotonic: {cl_values}"
            )

    async def test_failure_is_finite(self):
        """Failure ratio (max_stress/yield - 1) should be finite and < 1.0 (safe).

        In OAS, failure < 0 means below yield (safe), failure > 0 approaching 1.0
        means nearing yield, failure > 1.0 means structural failure.
        """
        r = await _run_wingbox(alpha=5.0)
        failure = r["surfaces"]["wing"]["failure"]
        assert isinstance(failure, float)
        assert failure < 1.0, "Wingbox should not fail at moderate alpha"

    async def test_structural_mass_positive(self):
        r = await _run_wingbox(alpha=5.0)
        assert r["structural_mass"] > 0

    async def test_thicker_spar_increases_mass(self):
        """A wingbox with thicker spar/skin should weigh more."""
        r_thin = await _run_wingbox(alpha=5.0)
        r_thick = await _run_wingbox(
            alpha=5.0,
            spar_thickness_cp=[0.05, 0.05, 0.05, 0.05],
            skin_thickness_cp=[0.05, 0.05, 0.05, 0.05],
        )
        assert r_thick["structural_mass"] > r_thin["structural_mass"]

    async def test_fuelburn_positive(self):
        r = await _run_wingbox(alpha=5.0)
        assert r["fuelburn"] > 0
