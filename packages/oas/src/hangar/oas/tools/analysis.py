"""Tools: run_aero_analysis, run_aerostruct_analysis, compute_drag_polar, compute_stability_derivatives.

Migrated from: OpenAeroStruct/oas_mcp/tools/analysis.py
"""

from __future__ import annotations

import asyncio
import time
from typing import Annotated

import numpy as np

from hangar.sdk.artifacts.store import _make_run_id
from hangar.oas.builders import build_aero_problem, build_aerostruct_problem
from hangar.oas.results import (
    extract_aero_results,
    extract_aerostruct_results,
    extract_stability_results,
    extract_standard_detail,
)
from hangar.oas.validation import (
    validate_aero,
    validate_aerostruct,
    validate_drag_polar,
    validate_stability,
)
from hangar.oas.validators import (
    validate_flight_conditions,
    validate_ground_effect_compat,
    validate_height_agl,
    validate_omega,
    validate_struct_props_present,
    validate_surface_names_exist,
)
from hangar.oas.tools._helpers import _finalize_analysis
from hangar.sdk.helpers import _suppress_output
from hangar.sdk.state import sessions as _sessions


def _cache_key(base: str, ground_effect: bool, rotational: bool) -> str:
    """Build a cache key that varies with problem structure.

    Beta is a continuous parameter that can be changed via set_val on a cached
    problem, so it doesn't need its own key variant.  Ground effect and
    rotational change the OpenMDAO model topology and require a fresh build.
    """
    if not ground_effect and not rotational:
        return base
    parts = [base]
    if ground_effect:
        parts.append("ge")
    if rotational:
        parts.append("rot")
    return "_".join(parts)


async def run_aero_analysis(
    surfaces: Annotated[list[str], "Names of surfaces to include (must have been created via create_surface)"],
    velocity: Annotated[float, "Free-stream velocity in m/s"] = 248.136,
    alpha: Annotated[float, "Angle of attack in degrees"] = 5.0,
    Mach_number: Annotated[float, "Mach number"] = 0.84,
    reynolds_number: Annotated[float, "Reynolds number per unit length (1/m)"] = 1.0e6,
    density: Annotated[float, "Air density in kg/m^3"] = 0.38,
    cg: Annotated[list[float] | None, "Centre of gravity [x, y, z] in metres"] = None,
    beta: Annotated[float, "Sideslip angle in degrees (incompatible with ground effect)"] = 0.0,
    height_agl: Annotated[float, "Height above ground in metres (only active when surface has groundplane=True)"] = 8000.0,
    omega: Annotated[list[float] | None, "Angular velocity [p, q, r] in deg/s for rotational effects (None = no rotation)"] = None,
    session_id: Annotated[str, "Session identifier"] = "default",
    run_name: Annotated[str | None, "Optional label for this run (stored in artifact metadata)"] = None,
) -> dict:
    """Run a single-point VLM aerodynamic analysis.

    Computes CL, CD (inviscid + viscous + wave), CM, and L/D for the given
    flight conditions. Per-surface force breakdowns are also returned.
    """
    if cg is None:
        cg = [0.0, 0.0, 0.0]

    validate_flight_conditions(velocity, alpha, Mach_number, reynolds_number, density, beta=beta)
    validate_height_agl(height_agl)
    validate_omega(omega)
    session = _sessions.get(session_id)
    validate_surface_names_exist(surfaces, session)

    surface_dicts = session.get_surfaces(surfaces)
    validate_ground_effect_compat(surface_dicts, beta)
    run_id = _make_run_id()

    # Cache key changes when omega/groundplane are involved — invalidate if
    # the problem structure differs (rotational or ground_effect flags).
    has_ground = any(s.get("groundplane", False) for s in surface_dicts)
    cache_key = _cache_key("aero", has_ground, omega is not None)

    def _run():
        cached = session.get_cached_problem(surfaces, cache_key)
        if cached is not None:
            prob = cached
            prob.set_val("v", velocity, units="m/s")
            prob.set_val("alpha", alpha, units="deg")
            prob.set_val("beta", beta, units="deg")
            prob.set_val("Mach_number", Mach_number)
            prob.set_val("re", reynolds_number, units="1/m")
            prob.set_val("rho", density, units="kg/m**3")
            prob.set_val("cg", np.array(cg), units="m")
            if has_ground:
                prob.set_val("height_agl", height_agl, units="m")
            if omega is not None:
                prob.set_val("omega", np.array(omega) * np.pi / 180.0, units="rad/s")
        else:
            prob = build_aero_problem(
                surface_dicts,
                velocity=velocity,
                alpha=alpha,
                Mach_number=Mach_number,
                reynolds_number=reynolds_number,
                density=density,
                cg=cg,
                beta=beta,
                height_agl=height_agl,
                omega=omega,
            )
            session.store_problem(surfaces, cache_key, prob)

        prob.run_model()
        aero_results = extract_aero_results(prob, surface_dicts, "aero")
        standard = extract_standard_detail(prob, surface_dicts, "aero", "aero")
        return aero_results, standard

    t0 = time.perf_counter()
    cache_hit = session.get_cached_problem(surfaces, cache_key) is not None
    results, standard_detail = await asyncio.to_thread(_suppress_output, _run)

    session.store_mesh_snapshot(run_id, standard_detail.get("mesh_snapshot", {}))

    inputs = {
        "velocity": velocity, "alpha": alpha, "Mach_number": Mach_number,
        "reynolds_number": reynolds_number, "density": density,
        "beta": beta, "height_agl": height_agl,
    }
    if omega is not None:
        inputs["omega"] = omega
    findings = validate_aero(results, context={"alpha": alpha})
    return await _finalize_analysis(
        tool_name="run_aero_analysis", run_id=run_id,
        session=session, session_id=session_id, surfaces=surfaces,
        analysis_type="aero", inputs=inputs, results=results,
        standard_detail=standard_detail, findings=findings,
        t0=t0, cache_hit=cache_hit, run_name=run_name,
        surface_dicts=surface_dicts, auto_plots=True,
    )


async def run_aerostruct_analysis(
    surfaces: Annotated[list[str], "Names of surfaces (must have fem_model_type set)"],
    velocity: Annotated[float, "Free-stream velocity in m/s"] = 248.136,
    alpha: Annotated[float, "Angle of attack in degrees"] = 5.0,
    Mach_number: Annotated[float, "Mach number"] = 0.84,
    reynolds_number: Annotated[float, "Reynolds number per unit length (1/m)"] = 1.0e6,
    density: Annotated[float, "Air density in kg/m^3"] = 0.38,
    W0: Annotated[float, "Aircraft empty weight (excl. wing structure) in kg"] = 0.4 * 3e5,
    CT: Annotated[float | None, "Specific fuel consumption in 1/s (None = default cruise value)"] = None,
    R: Annotated[float, "Mission range in metres"] = 11.165e6,
    speed_of_sound: Annotated[float, "Speed of sound in m/s"] = 295.4,
    load_factor: Annotated[float, "Load factor (1.0 = 1-g cruise)"] = 1.0,
    empty_cg: Annotated[list[float] | None, "Empty CG location [x, y, z] in metres"] = None,
    beta: Annotated[float, "Sideslip angle in degrees (incompatible with ground effect)"] = 0.0,
    height_agl: Annotated[float, "Height above ground in metres (only active when surface has groundplane=True)"] = 8000.0,
    omega: Annotated[list[float] | None, "Angular velocity [p, q, r] in deg/s for rotational effects (None = no rotation)"] = None,
    session_id: Annotated[str, "Session identifier"] = "default",
    run_name: Annotated[str | None, "Optional label for this run (stored in artifact metadata)"] = None,
) -> dict:
    """Run a coupled aerostructural analysis (VLM + beam FEM).

    Returns aerodynamic coefficients plus structural mass, fuel burn, failure
    metric, and von Mises stress.  Surfaces must have been created with a
    fem_model_type of 'tube' or 'wingbox'.
    """
    if empty_cg is None:
        empty_cg = [0.0, 0.0, 0.0]

    validate_flight_conditions(velocity, alpha, Mach_number, reynolds_number, density, beta=beta)
    validate_height_agl(height_agl)
    validate_omega(omega)
    session = _sessions.get(session_id)
    validate_surface_names_exist(surfaces, session)
    surface_dicts = session.get_surfaces(surfaces)
    validate_ground_effect_compat(surface_dicts, beta)
    for s in surface_dicts:
        validate_struct_props_present(s)
    run_id = _make_run_id()

    from openaerostruct.utils.constants import grav_constant
    ct_val = CT if CT is not None else grav_constant * 17.0e-6

    has_ground = any(s.get("groundplane", False) for s in surface_dicts)
    cache_key = _cache_key("aerostruct", has_ground, omega is not None)

    def _run():
        cached = session.get_cached_problem(surfaces, cache_key)
        if cached is not None:
            prob = cached
            prob.set_val("v", velocity, units="m/s")
            prob.set_val("alpha", alpha, units="deg")
            prob.set_val("beta", beta, units="deg")
            prob.set_val("Mach_number", Mach_number)
            prob.set_val("re", reynolds_number, units="1/m")
            prob.set_val("rho", density, units="kg/m**3")
            prob.set_val("W0", W0, units="kg")
            prob.set_val("CT", ct_val, units="1/s")
            prob.set_val("R", R, units="m")
            prob.set_val("speed_of_sound", speed_of_sound, units="m/s")
            prob.set_val("load_factor", load_factor)
            prob.set_val("empty_cg", np.array(empty_cg), units="m")
            if has_ground:
                prob.set_val("height_agl", height_agl, units="m")
            if omega is not None:
                prob.set_val("omega", np.array(omega) * np.pi / 180.0, units="rad/s")
        else:
            prob = build_aerostruct_problem(
                surface_dicts,
                velocity=velocity,
                alpha=alpha,
                Mach_number=Mach_number,
                reynolds_number=reynolds_number,
                density=density,
                CT=ct_val,
                R=R,
                W0=W0,
                speed_of_sound=speed_of_sound,
                load_factor=load_factor,
                empty_cg=empty_cg,
                beta=beta,
                height_agl=height_agl,
                omega=omega,
            )
            session.store_problem(surfaces, cache_key, prob)

        prob.run_model()
        as_results = extract_aerostruct_results(prob, surface_dicts, "AS_point_0")
        standard = extract_standard_detail(prob, surface_dicts, "aerostruct", "AS_point_0")
        return as_results, standard

    t0 = time.perf_counter()
    cache_hit = session.get_cached_problem(surfaces, cache_key) is not None
    results, standard_detail = await asyncio.to_thread(_suppress_output, _run)

    session.store_mesh_snapshot(run_id, standard_detail.get("mesh_snapshot", {}))

    inputs = {
        "velocity": velocity, "alpha": alpha, "Mach_number": Mach_number,
        "reynolds_number": reynolds_number, "density": density,
        "W0": W0, "R": R, "speed_of_sound": speed_of_sound, "load_factor": load_factor,
        "beta": beta, "height_agl": height_agl,
    }
    if omega is not None:
        inputs["omega"] = omega
    findings = validate_aerostruct(results, context={"alpha": alpha, "W0": W0, "surfaces": surface_dicts})
    return await _finalize_analysis(
        tool_name="run_aerostruct_analysis", run_id=run_id,
        session=session, session_id=session_id, surfaces=surfaces,
        analysis_type="aerostruct", inputs=inputs, results=results,
        standard_detail=standard_detail, findings=findings,
        t0=t0, cache_hit=cache_hit, run_name=run_name,
        surface_dicts=surface_dicts, auto_plots=True,
    )


async def compute_drag_polar(
    surfaces: Annotated[list[str], "Names of surfaces to include"],
    alpha_start: Annotated[float, "Starting angle of attack in degrees"] = -5.0,
    alpha_end: Annotated[float, "Ending angle of attack in degrees"] = 15.0,
    num_alpha: Annotated[int, "Number of alpha points to compute"] = 21,
    velocity: Annotated[float, "Free-stream velocity in m/s"] = 248.136,
    Mach_number: Annotated[float, "Mach number"] = 0.84,
    reynolds_number: Annotated[float, "Reynolds number per unit length (1/m)"] = 1.0e6,
    density: Annotated[float, "Air density in kg/m^3"] = 0.38,
    cg: Annotated[list[float] | None, "Centre of gravity [x, y, z] in metres"] = None,
    beta: Annotated[float, "Sideslip angle in degrees"] = 0.0,
    session_id: Annotated[str, "Session identifier"] = "default",
    run_name: Annotated[str | None, "Optional label for this run (stored in artifact metadata)"] = None,
) -> dict:
    """Compute a drag polar by sweeping angle of attack.

    Returns arrays of alpha, CL, CD, CM, and L/D.  The point of maximum L/D
    is highlighted.
    """
    if cg is None:
        cg = [0.0, 0.0, 0.0]
    if num_alpha < 2:
        raise ValueError("num_alpha must be >= 2")

    validate_flight_conditions(velocity, alpha_start, Mach_number, reynolds_number, density, beta=beta)
    session = _sessions.get(session_id)
    validate_surface_names_exist(surfaces, session)
    surface_dicts = session.get_surfaces(surfaces)
    validate_ground_effect_compat(surface_dicts, beta)

    alphas = list(np.linspace(alpha_start, alpha_end, num_alpha))

    def _run():
        # Build problem once with first alpha value
        prob = build_aero_problem(
            surface_dicts,
            velocity=velocity,
            alpha=alphas[0],
            Mach_number=Mach_number,
            reynolds_number=reynolds_number,
            density=density,
            cg=cg,
            beta=beta,
        )

        CLs, CDs, CMs = [], [], []
        for a in alphas:
            prob.set_val("alpha", a, units="deg")
            prob.run_model()
            CLs.append(float(np.asarray(prob.get_val("aero.CL")).ravel()[0]))
            CDs.append(float(np.asarray(prob.get_val("aero.CD")).ravel()[0]))
            cm = np.asarray(prob.get_val("aero.CM")).ravel()
            CMs.append(float(cm[1]) if len(cm) > 1 else float(cm[0]))

        return CLs, CDs, CMs

    run_id = _make_run_id()
    t0 = time.perf_counter()
    CLs, CDs, CMs = await asyncio.to_thread(_suppress_output, _run)

    LoDs = [cl / cd if cd > 0 else None for cl, cd in zip(CLs, CDs)]
    valid_LoDs = [(i, v) for i, v in enumerate(LoDs) if v is not None]
    best_idx, best_LoD = max(valid_LoDs, key=lambda x: x[1]) if valid_LoDs else (0, None)

    polar_results = {
        "alpha_deg": [round(float(a), 4) for a in alphas],
        "CL": [round(v, 6) for v in CLs],
        "CD": [round(v, 6) for v in CDs],
        "CM": [round(v, 6) for v in CMs],
        "L_over_D": [round(v, 4) if v is not None else None for v in LoDs],
        "best_L_over_D": {
            "alpha_deg": round(float(alphas[best_idx]), 4),
            "CL": round(CLs[best_idx], 6),
            "CD": round(CDs[best_idx], 6),
            "L_over_D": round(best_LoD, 4) if best_LoD else None,
        },
    }
    inputs = {
        "alpha_start": alpha_start, "alpha_end": alpha_end, "num_alpha": num_alpha,
        "velocity": velocity, "Mach_number": Mach_number,
        "reynolds_number": reynolds_number, "density": density,
        "beta": beta,
    }

    findings = validate_drag_polar(polar_results, context={"alpha_start": alpha_start})
    return await _finalize_analysis(
        tool_name="compute_drag_polar", run_id=run_id,
        session=session, session_id=session_id, surfaces=surfaces,
        analysis_type="drag_polar", inputs=inputs, results=polar_results,
        standard_detail=None, findings=findings,
        t0=t0, cache_hit=False, run_name=run_name,
        surface_dicts=None, auto_plots=True,
    )


async def compute_stability_derivatives(
    surfaces: Annotated[list[str], "Names of surfaces to include"],
    alpha: Annotated[float, "Angle of attack in degrees"] = 5.0,
    velocity: Annotated[float, "Free-stream velocity in m/s"] = 248.136,
    Mach_number: Annotated[float, "Mach number"] = 0.84,
    reynolds_number: Annotated[float, "Reynolds number per unit length (1/m)"] = 1.0e6,
    density: Annotated[float, "Air density in kg/m^3"] = 0.38,
    cg: Annotated[list[float] | None, "Centre of gravity [x, y, z] in metres — affects CM and static margin"] = None,
    beta: Annotated[float, "Sideslip angle in degrees (sets operating point for derivative computation)"] = 0.0,
    session_id: Annotated[str, "Session identifier"] = "default",
    run_name: Annotated[str | None, "Optional label for this run (stored in artifact metadata)"] = None,
) -> dict:
    """Compute stability derivatives: CL_alpha, CM_alpha, and static margin.

    Uses two AeroPoint instances and finite differencing in alpha (1e-4 deg step)
    to compute lift-curve slope and pitching-moment slope.  Static margin is
    -CM_alpha / CL_alpha.
    """
    if cg is None:
        cg = [0.0, 0.0, 0.0]

    validate_flight_conditions(velocity, alpha, Mach_number, reynolds_number, density, beta=beta)
    session = _sessions.get(session_id)
    validate_surface_names_exist(surfaces, session)
    surface_dicts = session.get_surfaces(surfaces)

    def _run():
        import openmdao.api as om
        from openaerostruct.aerodynamics.aero_groups import AeroPoint
        from openaerostruct.geometry.geometry_group import Geometry

        alpha_FD_stepsize = 1e-4  # deg

        prob = om.Problem(reports=False)

        indep = om.IndepVarComp()
        indep.add_output("v", val=velocity, units="m/s")
        indep.add_output("alpha", val=alpha, units="deg")
        indep.add_output("beta", val=beta, units="deg")
        indep.add_output("Mach_number", val=Mach_number)
        indep.add_output("re", val=reynolds_number, units="1/m")
        indep.add_output("rho", val=density, units="kg/m**3")
        indep.add_output("cg", val=np.array(cg), units="m")
        prob.model.add_subsystem("prob_vars", indep, promotes=["*"])

        # FD alpha offset
        alpha_perturb = om.ExecComp(
            "alpha_plus_delta = alpha + delta_alpha",
            units="deg",
            delta_alpha={"val": alpha_FD_stepsize, "constant": True},
        )
        prob.model.add_subsystem("alpha_for_FD", alpha_perturb, promotes=["*"])

        # Geometry groups
        for surface in surface_dicts:
            s_name = surface["name"]
            geom = Geometry(surface=surface)
            prob.model.add_subsystem(s_name + "_geom", geom)

        # Two AeroPoints
        point_names = ["aero_point", "aero_point_FD"]
        for i, pname in enumerate(point_names):
            ag = AeroPoint(surfaces=surface_dicts)
            prob.model.add_subsystem(pname, ag)
            prob.model.connect("v", pname + ".v")
            prob.model.connect("beta", pname + ".beta")
            prob.model.connect("Mach_number", pname + ".Mach_number")
            prob.model.connect("re", pname + ".re")
            prob.model.connect("rho", pname + ".rho")
            prob.model.connect("cg", pname + ".cg")
            alpha_src = "alpha" if i == 0 else "alpha_plus_delta"
            prob.model.connect(alpha_src, pname + ".alpha")
            for surface in surface_dicts:
                s_name = surface["name"]
                prob.model.connect(s_name + "_geom.mesh", pname + "." + s_name + ".def_mesh")
                prob.model.connect(s_name + "_geom.mesh", pname + ".aero_states." + s_name + "_def_mesh")
                prob.model.connect(s_name + "_geom.t_over_c", pname + "." + s_name + "_perf.t_over_c")

        # Stability derivatives via ExecComp
        stab_comp = om.ExecComp(
            ["CL_alpha = (CL_FD - CL) / delta_alpha", "CM_alpha = (CM_FD - CM) / delta_alpha"],
            delta_alpha={"val": alpha_FD_stepsize, "constant": True},
            CL_alpha={"val": 0.0, "units": "1/deg"},
            CL_FD={"val": 0.0, "units": None},
            CL={"val": 0.0, "units": None},
            CM_alpha={"val": np.zeros(3), "units": "1/deg"},
            CM_FD={"val": np.zeros(3), "units": None},
            CM={"val": np.zeros(3), "units": None},
        )
        prob.model.add_subsystem("stability_derivs", stab_comp, promotes_outputs=["*"])
        prob.model.connect("aero_point.CL", "stability_derivs.CL")
        prob.model.connect("aero_point.CM", "stability_derivs.CM")
        prob.model.connect("aero_point_FD.CL", "stability_derivs.CL_FD")
        prob.model.connect("aero_point_FD.CM", "stability_derivs.CM_FD")

        # Static margin
        sm_comp = om.ExecComp(
            "static_margin = -CM_alpha / CL_alpha",
            CM_alpha={"val": 0.0, "units": "1/deg"},
            CL_alpha={"val": 0.0, "units": "1/deg"},
            static_margin={"val": 0.0, "units": None},
        )
        prob.model.add_subsystem("static_margin", sm_comp, promotes_outputs=["*"])
        prob.model.connect("CL_alpha", "static_margin.CL_alpha")
        prob.model.connect("CM_alpha", "static_margin.CM_alpha", src_indices=1)

        prob.setup(force_alloc_complex=False)
        prob.set_val("v", velocity, units="m/s")
        prob.set_val("alpha", alpha, units="deg")
        prob.set_val("Mach_number", Mach_number)
        prob.set_val("re", reynolds_number, units="1/m")
        prob.set_val("rho", density, units="kg/m**3")
        prob.set_val("cg", np.array(cg), units="m")

        prob.run_model()
        return extract_stability_results(prob)

    run_id = _make_run_id()
    t0 = time.perf_counter()
    results = await asyncio.to_thread(_suppress_output, _run)
    inputs = {
        "alpha": alpha, "velocity": velocity, "Mach_number": Mach_number,
        "reynolds_number": reynolds_number, "density": density,
        "beta": beta,
    }

    findings = validate_stability(results, context={"alpha": alpha})
    return await _finalize_analysis(
        tool_name="compute_stability_derivatives", run_id=run_id,
        session=session, session_id=session_id, surfaces=surfaces,
        analysis_type="stability", inputs=inputs, results=results,
        standard_detail=None, findings=findings,
        t0=t0, cache_hit=False, run_name=run_name,
        surface_dicts=surface_dicts, auto_plots=False,
    )
