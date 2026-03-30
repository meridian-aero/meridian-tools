"""Tool: create_surface — define lifting surface geometry.

Migrated from: OpenAeroStruct/oas_mcp/tools/surfaces.py
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import numpy as np

from hangar.oas.config.defaults import (
    DEFAULT_WINGBOX_LOWER_X,
    DEFAULT_WINGBOX_LOWER_Y,
    DEFAULT_WINGBOX_UPPER_X,
    DEFAULT_WINGBOX_UPPER_Y,
)
from hangar.oas.mesh import apply_dihedral, apply_sweep, apply_taper, build_mesh
from hangar.oas.validators import (
    validate_composite_params,
    validate_fem_model_type,
    validate_mesh_params,
    validate_wing_type,
)
from hangar.sdk.helpers import _suppress_output
from hangar.oas.tools._helpers import _to_oas_order
from hangar.sdk.state import sessions as _sessions


async def create_surface(
    name: Annotated[str, "Unique surface name (e.g. 'wing', 'tail')"] = "wing",
    wing_type: Annotated[str, "Mesh type: 'rect', 'CRM', or 'uCRM_based'"] = "rect",
    span: Annotated[float, "Full wingspan in metres"] = 10.0,
    root_chord: Annotated[float, "Root chord length in metres"] = 1.0,
    taper: Annotated[float, "Taper ratio (tip_chord / root_chord), 1.0 = no taper"] = 1.0,
    sweep: Annotated[float, "Leading-edge sweep angle in degrees"] = 0.0,
    dihedral: Annotated[float, "Dihedral angle in degrees"] = 0.0,
    num_x: Annotated[int, "Number of chordwise mesh nodes (>= 2)"] = 2,
    num_y: Annotated[int, "Number of spanwise mesh nodes (must be odd, >= 3)"] = 7,
    symmetry: Annotated[bool, "If True, model only one half of the wing"] = True,
    span_cos_spacing: Annotated[float, "Spanwise spacing blend: 0=uniform, 1=cosine (bunches at tip), 2-3=cosine at root+tip"] = 0.0,
    chord_cos_spacing: Annotated[float, "Chordwise spacing blend: 0=uniform, 1=cosine (bunches at LE/TE)"] = 0.0,
    twist_cp: Annotated[list[float] | None, "Twist control-point values in degrees, ordered root-to-tip (None = zero twist)"] = None,
    chord_cp: Annotated[list[float] | None, "Chord control-point scale factors, ordered root-to-tip (None = unit chord)"] = None,
    t_over_c_cp: Annotated[list[float] | None, "Thickness-to-chord ratio control points, ordered root-to-tip (None = [0.15])"] = None,
    CL0: Annotated[float, "Lift coefficient at alpha=0 (profile)"] = 0.0,
    CD0: Annotated[float, "Zero-lift drag coefficient (profile)"] = 0.015,
    with_viscous: Annotated[bool, "Include viscous (skin-friction) drag"] = True,
    with_wave: Annotated[bool, "Include wave drag"] = False,
    fem_model_type: Annotated[str | None, "Structural model: 'tube', 'wingbox', or None for aero-only"] = None,
    thickness_cp: Annotated[list[float] | None, "Tube wall thickness control points in metres, ordered root-to-tip (tube model only)"] = None,
    spar_thickness_cp: Annotated[list[float] | None, "Wingbox spar thickness control points in metres, ordered root-to-tip (wingbox model only)"] = None,
    skin_thickness_cp: Annotated[list[float] | None, "Wingbox skin thickness control points in metres, ordered root-to-tip (wingbox model only)"] = None,
    original_wingbox_airfoil_t_over_c: Annotated[float, "Thickness-to-chord ratio of the reference airfoil used for wingbox cross-section geometry (wingbox model only)"] = 0.12,
    E: Annotated[float, "Young's modulus in Pa (default: aluminium 7075, 70 GPa)"] = 70.0e9,
    G: Annotated[float, "Shear modulus in Pa (default: aluminium 7075, 30 GPa)"] = 30.0e9,
    yield_stress: Annotated[float, "Yield stress in Pa (default: 500 MPa)"] = 500.0e6,
    safety_factor: Annotated[float, "Safety factor applied to yield stress"] = 2.5,
    mrho: Annotated[float, "Material density in kg/m^3 (default: Al 7075, 3000 kg/m^3)"] = 3.0e3,
    offset: Annotated[list[float] | None, "3-element [x, y, z] offset of the surface origin in metres"] = None,
    S_ref_type: Annotated[str, "Reference area type: 'wetted' or 'projected'"] = "wetted",
    c_max_t: Annotated[float, "Chordwise location of maximum thickness (fraction of chord)"] = 0.303,
    wing_weight_ratio: Annotated[float, "Ratio of total wing weight to structural wing weight"] = 2.0,
    struct_weight_relief: Annotated[bool, "If True, include structural weight relief in the load distribution"] = False,
    distributed_fuel_weight: Annotated[bool, "If True, include distributed fuel weight in the load distribution"] = False,
    fuel_density: Annotated[float, "Fuel density in kg/m^3 (needed for fuel volume constraint)"] = 803.0,
    Wf_reserve: Annotated[float, "Reserve fuel mass in kg (subtracted from fuel volume constraint)"] = 15000.0,
    n_point_masses: Annotated[int, "Number of point masses (e.g. engines) attached to this surface"] = 0,
    use_composite: Annotated[bool, "Enable composite laminate model with Tsai-Wu failure (requires fem_model_type='wingbox')"] = False,
    ply_angles: Annotated[list[float] | None, "Ply orientation angles in degrees (e.g. [0, 45, -45, 90])"] = None,
    ply_fractions: Annotated[list[float] | None, "Volume fraction of each ply (must sum to 1.0)"] = None,
    E1: Annotated[float | None, "Longitudinal modulus of elasticity in Pa (fiber direction)"] = None,
    E2: Annotated[float | None, "Transverse modulus of elasticity in Pa"] = None,
    nu12: Annotated[float | None, "Major Poisson's ratio (fiber direction)"] = None,
    G12: Annotated[float | None, "In-plane shear modulus in Pa"] = None,
    sigma_t1: Annotated[float | None, "Longitudinal tensile strength in Pa"] = None,
    sigma_c1: Annotated[float | None, "Longitudinal compressive strength in Pa"] = None,
    sigma_t2: Annotated[float | None, "Transverse tensile strength in Pa"] = None,
    sigma_c2: Annotated[float | None, "Transverse compressive strength in Pa"] = None,
    sigma_12max: Annotated[float | None, "Maximum shear strength in Pa"] = None,
    groundplane: Annotated[bool, "Enable ground-effect modelling (requires symmetry=True, incompatible with beta/sideslip)"] = False,
    num_twist_cp: Annotated[int | None, "Number of twist control points for CRM/uCRM_based mesh generation (None = auto)"] = None,
    session_id: Annotated[str, "Session identifier"] = "default",
) -> dict:
    """Define a lifting surface (wing, tail, canard) and store it in the session.

    Must be called before any analysis tools. The surface geometry (mesh, sweep,
    dihedral, taper) is computed immediately and cached for reuse.
    """
    # Validate inputs
    validate_wing_type(wing_type)
    validate_mesh_params(num_x, num_y)
    validate_fem_model_type(fem_model_type)
    if root_chord <= 0:
        raise ValueError(f"root_chord must be positive, got {root_chord}")
    if span <= 0:
        raise ValueError(f"span must be positive, got {span}")
    if groundplane and not symmetry:
        raise ValueError("Ground effect (groundplane=True) requires symmetry=True")

    # Validate and normalise composite params early (before expensive mesh build)
    normalised_ply_fractions = None
    if use_composite:
        normalised_ply_fractions = validate_composite_params(
            fem_model_type, ply_angles, ply_fractions,
            E1, E2, nu12, G12,
            sigma_t1, sigma_c1, sigma_t2, sigma_c2, sigma_12max,
        )

    def _build():
        mesh, crm_twist = build_mesh(
            wing_type=wing_type,
            num_x=num_x,
            num_y=num_y,
            span=span,
            root_chord=root_chord,
            symmetry=symmetry,
            offset=offset,
            num_twist_cp=num_twist_cp,
            span_cos_spacing=span_cos_spacing,
            chord_cos_spacing=chord_cos_spacing,
        )

        # Apply geometric modifications
        if sweep != 0.0:
            mesh = apply_sweep(mesh, sweep)
        if dihedral != 0.0:
            mesh = apply_dihedral(mesh, dihedral)
        if taper != 1.0:
            mesh = apply_taper(mesh, taper)

        # Determine twist_cp
        # User-provided arrays are root-to-tip; reverse to OAS tip-to-root.
        # CRM twist from generate_mesh() is already in OAS order — do NOT reverse.
        if twist_cp is not None:
            tcp = _to_oas_order(np.array(twist_cp, dtype=float))
        elif crm_twist is not None:
            tcp = crm_twist
        else:
            tcp = np.zeros(2)

        # Build surface dict
        surface = {
            "name": name,
            "symmetry": symmetry,
            "S_ref_type": S_ref_type,
            "mesh": mesh,
            "twist_cp": tcp,
            "CL0": CL0,
            "CD0": CD0,
            "k_lam": 0.05,
            "t_over_c_cp": (
                _to_oas_order(np.array(t_over_c_cp, dtype=float))
                if t_over_c_cp is not None
                else np.array([0.15])
            ),
            "c_max_t": c_max_t,
            "with_viscous": with_viscous,
            "with_wave": with_wave,
            "groundplane": groundplane,
        }

        if chord_cp is not None:
            surface["chord_cp"] = _to_oas_order(np.array(chord_cp, dtype=float))

        if fem_model_type and fem_model_type != "none":
            surface["fem_model_type"] = fem_model_type
            surface["E"] = E
            surface["G"] = G
            surface["yield"] = yield_stress
            surface["safety_factor"] = safety_factor
            surface["mrho"] = mrho
            surface["fem_origin"] = 0.35
            surface["wing_weight_ratio"] = wing_weight_ratio
            surface["struct_weight_relief"] = struct_weight_relief
            surface["distributed_fuel_weight"] = distributed_fuel_weight
            surface["exact_failure_constraint"] = False
            surface["fuel_density"] = fuel_density
            surface["Wf_reserve"] = Wf_reserve
            if n_point_masses > 0:
                surface["n_point_masses"] = n_point_masses

            if fem_model_type == "wingbox":
                # Wingbox-specific thickness control points
                ny2 = (num_y + 1) // 2
                n_cp = max(2, min(6, ny2 // 2))
                surface["spar_thickness_cp"] = (
                    _to_oas_order(np.array(spar_thickness_cp, dtype=float))
                    if spar_thickness_cp is not None
                    else np.linspace(0.004, 0.01, n_cp)
                )
                surface["skin_thickness_cp"] = (
                    _to_oas_order(np.array(skin_thickness_cp, dtype=float))
                    if skin_thickness_cp is not None
                    else np.linspace(0.005, 0.026, n_cp)
                )
                # Airfoil geometry for wingbox cross-section calculations
                surface["original_wingbox_airfoil_t_over_c"] = original_wingbox_airfoil_t_over_c
                surface["strength_factor_for_upper_skin"] = 1.0
                surface["data_x_upper"] = DEFAULT_WINGBOX_UPPER_X
                surface["data_y_upper"] = DEFAULT_WINGBOX_UPPER_Y
                surface["data_x_lower"] = DEFAULT_WINGBOX_LOWER_X
                surface["data_y_lower"] = DEFAULT_WINGBOX_LOWER_Y
            else:
                # Tube model thickness control points
                if thickness_cp is not None:
                    surface["thickness_cp"] = _to_oas_order(np.array(thickness_cp, dtype=float))
                else:
                    ny2 = (num_y + 1) // 2
                    n_cp = max(3, min(5, ny2 // 2))
                    surface["thickness_cp"] = np.ones(n_cp) * 0.1 * root_chord

            # Composite laminate properties
            if use_composite:
                from openaerostruct.structures.utils import compute_composite_stiffness

                surface["useComposite"] = True
                surface["ply_angles"] = ply_angles
                surface["ply_fractions"] = normalised_ply_fractions
                surface["E1"] = E1
                surface["E2"] = E2
                surface["nu12"] = nu12
                surface["G12"] = G12
                surface["sigma_t1"] = sigma_t1
                surface["sigma_c1"] = sigma_c1
                surface["sigma_t2"] = sigma_t2
                surface["sigma_c2"] = sigma_c2
                surface["sigma_12max"] = sigma_12max
                # Compute effective E and G from laminate theory (overwrites E/G in-place)
                compute_composite_stiffness(surface)

        return surface

    session = _sessions.get(session_id)
    surface = await asyncio.to_thread(_suppress_output, _build)
    session.add_surface(surface)

    mesh = surface["mesh"]
    nx, ny, _ = mesh.shape
    # Estimate span and area from mesh
    y_coords = mesh[0, :, 1]
    actual_span = float(y_coords.max() - y_coords.min())
    if symmetry:
        actual_span *= 2.0
    # Rough panel area estimate
    chord_avg = float(np.mean(mesh[-1, :, 0] - mesh[0, :, 0]))

    result = {
        "surface_name": name,
        "mesh_shape": [nx, ny, 3],
        "span_m": round(actual_span, 4),
        "mean_chord_m": round(chord_avg, 4),
        "estimated_area_m2": round(actual_span * chord_avg / (2.0 if symmetry else 1.0), 4),
        "twist_cp_shape": list(surface["twist_cp"].shape),
        "has_structure": fem_model_type is not None and fem_model_type != "none",
        "use_composite": use_composite,
        "session_id": session_id,
        "status": "Surface created successfully",
    }
    if use_composite:
        result["effective_E"] = float(surface["E"])
        result["effective_G"] = float(surface["G"])
    return result
