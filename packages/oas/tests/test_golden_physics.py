"""
Tier 1 — Physics invariant golden tests.

Migrated from: OpenAeroStruct/oas_mcp/tests/golden/test_golden_physics.py

These should always pass on any platform, Python version, or dependency
version, because they assert fundamental aerodynamic and structural physics
that VLM + beam-FEM must respect regardless of numerical implementation.

Run with:
    pytest packages/oas/tests/test_golden_physics.py -v
    pytest -m golden_physics

Determinism: set OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 before running
to ensure linear-algebra results are identical across threads.
"""

from __future__ import annotations

import pytest
import asyncio


pytestmark = [pytest.mark.slow, pytest.mark.golden_physics]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _r(envelope: dict) -> dict:
    """Extract results payload from a response envelope."""
    return envelope["results"]


async def _make_aero_wing(num_y: int = 7):
    from hangar.oas.server import create_surface, reset
    await reset()
    await create_surface(
        name="wing", wing_type="rect",
        span=10.0, root_chord=1.0,
        num_x=2, num_y=num_y, symmetry=True,
        with_viscous=True, CD0=0.015,
    )


async def _make_struct_wing(num_y: int = 7):
    from hangar.oas.server import create_surface, reset
    await reset()
    await create_surface(
        name="wing", wing_type="rect",
        span=10.0, root_chord=1.0,
        num_x=2, num_y=num_y, symmetry=True,
        with_viscous=True, CD0=0.015,
        fem_model_type="tube",
        E=70e9, G=30e9, yield_stress=500e6,
        safety_factor=2.5, mrho=3000.0,
    )


# ---------------------------------------------------------------------------
# Aerodynamic physics invariants
# ---------------------------------------------------------------------------


class TestAeroPhysicsInvariants:
    """Fundamental VLM aerodynamics that must hold for any valid configuration."""

    @pytest.mark.asyncio
    async def test_cd_always_positive(self):
        """CD > 0 for all angles of attack -- drag is always positive."""
        from hangar.oas.server import run_aero_analysis
        await _make_aero_wing()
        for alpha in [-10.0, -5.0, 0.0, 5.0, 10.0, 15.0]:
            r = _r(await run_aero_analysis(["wing"], alpha=alpha))
            assert r["CD"] > 0, f"CD={r['CD']} should be > 0 at alpha={alpha}"

    @pytest.mark.asyncio
    async def test_cl_monotonically_increases_with_alpha(self):
        """CL must increase monotonically with alpha for an un-stalled VLM wing."""
        from hangar.oas.server import run_aero_analysis
        await _make_aero_wing()
        alphas = [-5.0, 0.0, 5.0, 10.0]
        cls = [_r(await run_aero_analysis(["wing"], alpha=a))["CL"] for a in alphas]
        for i in range(len(cls) - 1):
            assert cls[i] < cls[i + 1], (
                f"CL not monotone: CL({alphas[i]})={cls[i]:.4f} >= CL({alphas[i+1]})={cls[i+1]:.4f}"
            )

    @pytest.mark.asyncio
    async def test_cd_parabolic_polar(self):
        """CD should have a minimum interior to the alpha range (parabolic polar)."""
        from hangar.oas.server import compute_drag_polar
        await _make_aero_wing()
        dp = _r(await compute_drag_polar(
            ["wing"], alpha_start=-5.0, alpha_end=15.0, num_alpha=9
        ))
        cds = dp["CD"]
        min_idx = cds.index(min(cds))
        # Minimum should not be at an endpoint
        assert 0 < min_idx < len(cds) - 1, (
            f"CD minimum at endpoint index {min_idx} -- expected interior minimum"
        )

    @pytest.mark.asyncio
    async def test_ld_positive_at_cruise_alpha(self):
        """L/D > 0 at a reasonable positive cruise angle of attack."""
        from hangar.oas.server import run_aero_analysis
        await _make_aero_wing()
        r = _r(await run_aero_analysis(["wing"], alpha=5.0))
        assert r["L_over_D"] > 0, f"L/D={r['L_over_D']} should be positive at alpha=5 deg"

    @pytest.mark.asyncio
    async def test_cl_zero_at_zero_alpha_symmetric_wing(self):
        """For an un-cambered symmetric wing, CL is approximately 0 at alpha = 0."""
        from hangar.oas.server import run_aero_analysis
        await _make_aero_wing()
        r = _r(await run_aero_analysis(["wing"], alpha=0.0))
        assert abs(r["CL"]) < 0.02, (
            f"Symmetric wing: |CL|={abs(r['CL']):.4f} should be ~0 at alpha=0"
        )

    @pytest.mark.asyncio
    async def test_drag_polar_has_positive_best_ld(self):
        """The drag polar should have a positive maximum L/D."""
        from hangar.oas.server import compute_drag_polar
        await _make_aero_wing()
        dp = _r(await compute_drag_polar(
            ["wing"], alpha_start=0.0, alpha_end=12.0, num_alpha=7
        ))
        best_ld = dp["best_L_over_D"]["L_over_D"]
        assert best_ld is not None and best_ld > 0, (
            f"Best L/D={best_ld} should be positive"
        )

    @pytest.mark.asyncio
    async def test_finer_mesh_changes_results_smoothly(self):
        """Refining the mesh should change CL/CD but not wildly."""
        from hangar.oas.server import run_aero_analysis, create_surface, reset
        from hangar.sdk.state import sessions as _sessions

        results = {}
        for num_y in [5, 7, 11]:
            await reset()
            await create_surface(
                name="wing", wing_type="rect",
                span=10.0, root_chord=1.0,
                num_x=2, num_y=num_y, symmetry=True,
                with_viscous=True, CD0=0.015,
            )
            r = _r(await run_aero_analysis(["wing"], alpha=5.0))
            results[num_y] = r

        # CL should converge -- differences between successive meshes should shrink
        cl5, cl7, cl11 = results[5]["CL"], results[7]["CL"], results[11]["CL"]
        diff_57 = abs(cl7 - cl5)
        diff_711 = abs(cl11 - cl7)
        # Allow generous bounds -- just check convergence direction
        assert diff_711 <= diff_57 * 2.0 or diff_711 < 0.01, (
            f"CL not converging: diff(5->7)={diff_57:.4f}, diff(7->11)={diff_711:.4f}"
        )


# ---------------------------------------------------------------------------
# Structural physics invariants
# ---------------------------------------------------------------------------


class TestStructuralPhysicsInvariants:
    """Fundamental structural assertions for aerostructural analysis."""

    @pytest.mark.asyncio
    async def test_structural_mass_always_positive(self):
        """Structural mass must be positive for any valid FEM configuration."""
        from hangar.oas.server import run_aerostruct_analysis
        await _make_struct_wing()
        r = _r(await run_aerostruct_analysis(["wing"], alpha=5.0))
        assert r["structural_mass"] > 0, (
            f"Structural mass={r['structural_mass']} must be > 0"
        )

    @pytest.mark.asyncio
    async def test_fuelburn_always_positive(self):
        """Fuel burn must be positive for any finite mission range."""
        from hangar.oas.server import run_aerostruct_analysis
        await _make_struct_wing()
        r = _r(await run_aerostruct_analysis(
            ["wing"], alpha=5.0, W0=120000, R=11.165e6
        ))
        assert r["fuelburn"] > 0, f"Fuel burn={r['fuelburn']} must be > 0"

    @pytest.mark.asyncio
    async def test_stronger_material_reduces_failure(self):
        """Increasing yield stress should decrease the failure index."""
        from hangar.oas.server import run_aerostruct_analysis, create_surface, reset

        failure_values = {}
        for yield_stress in [250e6, 500e6, 1000e6]:
            await reset()
            await create_surface(
                name="wing", wing_type="rect",
                span=10.0, root_chord=1.0, num_x=2, num_y=7, symmetry=True,
                fem_model_type="tube",
                E=70e9, G=30e9, yield_stress=yield_stress,
                safety_factor=2.5, mrho=3000.0,
            )
            r = _r(await run_aerostruct_analysis(["wing"], alpha=5.0))
            failure_values[yield_stress] = r["surfaces"]["wing"]["failure"]

        # Stronger material -> smaller (more negative) failure index
        f250 = failure_values[250e6]
        f500 = failure_values[500e6]
        f1000 = failure_values[1000e6]
        assert f1000 < f500, (
            f"Stronger material should reduce failure: f(500MPa)={f500:.4f}, f(1000MPa)={f1000:.4f}"
        )
        assert f500 < f250, (
            f"Stronger material should reduce failure: f(250MPa)={f250:.4f}, f(500MPa)={f500:.4f}"
        )

    @pytest.mark.asyncio
    async def test_cg_is_plausible(self):
        """Aircraft CG x-coordinate should be positive and within chord range."""
        from hangar.oas.server import run_aerostruct_analysis
        await _make_struct_wing()
        r = _r(await run_aerostruct_analysis(["wing"], alpha=5.0))
        cg = r.get("cg")
        assert cg is not None, "cg should be present in aerostruct results"
        assert len(cg) == 3, "cg should be a 3-element vector [x, y, z]"
        # For a wing with root_chord=1.0, CG x should be within a reasonable range
        assert cg[0] > -10.0 and cg[0] < 100.0, (
            f"CG x={cg[0]} seems implausible for this geometry"
        )

    @pytest.mark.asyncio
    async def test_tip_deflection_upward_under_lift(self):
        """For a loaded wing at positive alpha, tip should deflect upward (positive z)."""
        from hangar.oas.server import run_aerostruct_analysis
        await _make_struct_wing()
        r = _r(await run_aerostruct_analysis(["wing"], alpha=5.0))
        tip_defl = r["surfaces"]["wing"].get("tip_deflection_m")
        assert tip_defl is not None, "tip_deflection_m should be present"
        assert tip_defl > 0, (
            f"Tip deflection={tip_defl:.6f} should be positive (upward) under lift"
        )

    @pytest.mark.asyncio
    async def test_higher_alpha_increases_failure(self):
        """Higher angle of attack -> larger aerodynamic loads -> higher failure index.

        Note: in OAS, load_factor scales the L=W trim weight, not the aerodynamic
        forces directly.  Alpha is the correct lever to change structural loading.
        """
        from hangar.oas.server import run_aerostruct_analysis
        await _make_struct_wing()
        r1 = _r(await run_aerostruct_analysis(["wing"], alpha=2.0))
        r2 = _r(await run_aerostruct_analysis(["wing"], alpha=12.0))
        f1 = r1["surfaces"]["wing"]["failure"]
        f2 = r2["surfaces"]["wing"]["failure"]
        assert f2 > f1, (
            f"Higher alpha should increase structural failure index: "
            f"f(alpha=2 deg)={f1:.4f}, f(alpha=12 deg)={f2:.4f}"
        )


# ---------------------------------------------------------------------------
# Optimization physics invariants
# ---------------------------------------------------------------------------


class TestOptimizationPhysicsInvariants:
    """Optimizer must satisfy constraints and produce physically valid results."""

    @pytest.mark.asyncio
    async def test_optimized_cd_less_than_baseline(self):
        """CD minimization must not increase CD relative to the baseline alpha-only run."""
        from hangar.oas.server import run_aero_analysis, run_optimization
        await _make_aero_wing()
        baseline = _r(await run_aero_analysis(["wing"], alpha=5.0))
        result = _r(await run_optimization(
            surfaces=["wing"],
            analysis_type="aero",
            objective="CD",
            design_variables=[
                {"name": "twist", "lower": -10.0, "upper": 10.0},
                {"name": "alpha", "lower": -5.0, "upper": 15.0},
            ],
            constraints=[{"name": "CL", "equals": baseline["CL"]}],
        ))
        if result["success"]:
            opt_cd = result["final_results"]["CD"]
            assert opt_cd <= baseline["CD"] * 1.01, (
                f"Optimized CD={opt_cd:.4f} should be <= baseline CD={baseline['CD']:.4f}"
            )

    @pytest.mark.asyncio
    async def test_cl_constraint_satisfied_after_optimization(self):
        """The CL constraint must be satisfied to within tolerance."""
        from hangar.oas.server import run_optimization
        await _make_aero_wing()
        target_cl = 0.4
        result = _r(await run_optimization(
            surfaces=["wing"],
            analysis_type="aero",
            objective="CD",
            design_variables=[{"name": "alpha", "lower": -10.0, "upper": 20.0}],
            constraints=[{"name": "CL", "equals": target_cl}],
        ))
        assert result["success"] is True
        final_cl = result["final_results"]["CL"]
        assert abs(final_cl - target_cl) < 0.01, (
            f"CL constraint not satisfied: target={target_cl}, final={final_cl:.4f}"
        )
