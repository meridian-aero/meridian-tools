"""Input validation for OAS tool parameters.

Migrated from: OpenAeroStruct/oas_mcp/core/validators.py
"""

from __future__ import annotations


def validate_positive(value, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_non_negative(value, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def validate_mesh_params(num_x: int, num_y: int) -> None:
    if num_x < 2:
        raise ValueError(f"num_x must be >= 2, got {num_x}")
    if num_y < 3:
        raise ValueError(f"num_y must be >= 3, got {num_y}")
    if num_y % 2 == 0:
        raise ValueError(
            f"num_y must be odd (symmetry requires odd panel count), got {num_y}. "
            f"Try {num_y + 1} or {num_y - 1}."
        )


def validate_wing_type(wing_type: str) -> None:
    valid = {"rect", "CRM", "uCRM_based"}
    if wing_type not in valid:
        raise ValueError(f"wing_type must be one of {valid}, got {wing_type!r}")


def validate_fem_model_type(fem_model_type: str) -> None:
    valid = {"tube", "wingbox", "none", None}
    if fem_model_type not in valid:
        raise ValueError(f"fem_model_type must be one of {valid}, got {fem_model_type!r}")


def validate_flight_conditions(velocity, alpha, Mach_number, reynolds_number, density, beta=0.0) -> None:
    validate_positive(velocity, "velocity")
    validate_non_negative(Mach_number, "Mach_number")
    validate_positive(reynolds_number, "reynolds_number")
    validate_positive(density, "density")
    if not (-90 <= alpha <= 90):
        raise ValueError(f"alpha must be between -90 and 90 deg, got {alpha}")
    if not (-180 <= beta <= 180):
        raise ValueError(f"beta must be between -180 and 180 deg, got {beta}")


def validate_surface_names_exist(names: list[str], session) -> None:
    missing = [n for n in names if n not in session.surfaces]
    if missing:
        available = list(session.surfaces.keys())
        raise ValueError(
            f"Surface(s) not found: {missing}. "
            f"Available surfaces: {available}. "
            f"Use create_surface first."
        )


def validate_design_variables_for_surfaces(
    design_variables: list[dict], surface_dicts: list[dict]
) -> None:
    """Ensure DV names are compatible with the fem_model_type of each surface.

    Tube surfaces expose 'thickness_cp'; wingbox surfaces expose
    'spar_thickness_cp' and 'skin_thickness_cp'.  Catching the mismatch
    here produces a clear error rather than an opaque OpenMDAO KeyError.
    """
    tube_only = {"thickness"}
    wingbox_only = {"spar_thickness", "skin_thickness"}

    for surface in surface_dicts:
        fem_type = surface.get("fem_model_type", "tube")
        name = surface.get("name", "?")
        for dv in design_variables:
            dv_name = dv.get("name", "")
            if fem_type == "wingbox" and dv_name in tube_only:
                raise ValueError(
                    f"Design variable {dv_name!r} maps to 'thickness_cp', which does not exist "
                    f"for wingbox surface {name!r}. "
                    f"Use 'spar_thickness' or 'skin_thickness' for wingbox models."
                )
            if fem_type != "wingbox" and dv_name in wingbox_only:
                raise ValueError(
                    f"Design variable {dv_name!r} is for wingbox surfaces only, "
                    f"but surface {name!r} uses fem_model_type={fem_type!r}. "
                    f"Use 'thickness' for tube models."
                )


def validate_flight_points(flight_points: list[dict]) -> None:
    """Validate a list of multipoint flight condition dicts."""
    required_keys = {"velocity", "Mach_number", "density", "reynolds_number", "speed_of_sound", "load_factor"}
    for i, fp in enumerate(flight_points):
        missing = required_keys - set(fp.keys())
        if missing:
            raise ValueError(
                f"flight_points[{i}] is missing required keys: {sorted(missing)}. "
                f"Required: {sorted(required_keys)}."
            )
        if fp["velocity"] <= 0:
            raise ValueError(f"flight_points[{i}].velocity must be positive, got {fp['velocity']}")
        if fp["Mach_number"] < 0:
            raise ValueError(f"flight_points[{i}].Mach_number must be non-negative, got {fp['Mach_number']}")
        if fp["density"] <= 0:
            raise ValueError(f"flight_points[{i}].density must be positive, got {fp['density']}")
        if fp["reynolds_number"] <= 0:
            raise ValueError(f"flight_points[{i}].reynolds_number must be positive, got {fp['reynolds_number']}")
        if fp["speed_of_sound"] <= 0:
            raise ValueError(f"flight_points[{i}].speed_of_sound must be positive, got {fp['speed_of_sound']}")


import re

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-. ]+$")


def validate_safe_name(value: str, label: str) -> None:
    """Reject path-traversal characters in user-supplied path segments.

    Raises ``ValueError`` if *value* contains ``..``, ``/``, ``\\``,
    or characters outside a conservative allowlist.
    """
    if not value:
        raise ValueError(f"{label} must not be empty")
    if ".." in value:
        raise ValueError(f"{label} must not contain '..' (got {value!r})")
    if not _SAFE_NAME_RE.match(value):
        raise ValueError(
            f"{label} contains invalid characters (got {value!r}). "
            f"Allowed: letters, digits, underscore, hyphen, dot, space."
        )


def validate_composite_params(
    fem_model_type: str | None,
    ply_angles: list[float] | None,
    ply_fractions: list[float] | None,
    E1: float | None,
    E2: float | None,
    nu12: float | None,
    G12: float | None,
    sigma_t1: float | None,
    sigma_c1: float | None,
    sigma_t2: float | None,
    sigma_c2: float | None,
    sigma_12max: float | None,
) -> list[float]:
    """Validate composite material parameters and return normalised ply_fractions.

    Raises ``ValueError`` with a descriptive message on invalid input.
    Returns *ply_fractions* normalised to sum exactly to 1.0 (avoids
    float-precision failures inside OAS's ``compute_composite_stiffness``).
    """
    if fem_model_type != "wingbox":
        raise ValueError(
            f"Composite materials require fem_model_type='wingbox', "
            f"got {fem_model_type!r}. Tube models do not support composites."
        )

    # Check all required params are provided
    required = {
        "ply_angles": ply_angles,
        "ply_fractions": ply_fractions,
        "E1": E1,
        "E2": E2,
        "nu12": nu12,
        "G12": G12,
        "sigma_t1": sigma_t1,
        "sigma_c1": sigma_c1,
        "sigma_t2": sigma_t2,
        "sigma_c2": sigma_c2,
        "sigma_12max": sigma_12max,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise ValueError(
            f"Composite material requires all properties. Missing: {missing}"
        )

    # Ply array checks
    if len(ply_angles) == 0:
        raise ValueError("ply_angles must contain at least one ply")
    if len(ply_angles) != len(ply_fractions):
        raise ValueError(
            f"ply_angles ({len(ply_angles)} plies) and ply_fractions "
            f"({len(ply_fractions)} values) must have the same length"
        )
    frac_sum = sum(ply_fractions)
    if abs(frac_sum - 1.0) > 0.01:
        raise ValueError(
            f"ply_fractions must sum to 1.0 (got {frac_sum:.6f}). "
            f"Tolerance is ±1%."
        )

    # Positive material properties
    for name, val in [
        ("E1", E1), ("E2", E2), ("G12", G12),
        ("sigma_t1", sigma_t1), ("sigma_c1", sigma_c1),
        ("sigma_t2", sigma_t2), ("sigma_c2", sigma_c2),
        ("sigma_12max", sigma_12max),
    ]:
        if val <= 0:
            raise ValueError(f"{name} must be positive, got {val}")
    if nu12 < 0 or nu12 >= 1.0:
        raise ValueError(f"nu12 must be in [0, 1), got {nu12}")

    # Normalise fractions to sum exactly to 1.0 to avoid OAS strict check
    normalised = [f / frac_sum for f in ply_fractions]
    return normalised


def validate_ground_effect_compat(surfaces: list[dict], beta: float) -> None:
    """Ensure ground effect and sideslip are not used simultaneously."""
    has_groundplane = any(s.get("groundplane", False) for s in surfaces)
    if has_groundplane and beta != 0.0:
        raise ValueError(
            "Ground effect (groundplane=True) is incompatible with sideslip (beta != 0). "
            "Set beta=0 or disable groundplane on all surfaces."
        )


def validate_height_agl(height_agl: float) -> None:
    if height_agl <= 0:
        raise ValueError(f"height_agl must be positive, got {height_agl}")


def validate_omega(omega: list[float] | None) -> None:
    if omega is not None and len(omega) != 3:
        raise ValueError(f"omega must be a 3-element list [p, q, r], got {len(omega)} elements")


def validate_struct_props_present(surface: dict) -> None:
    """Ensure structural properties are present for aerostruct analysis."""
    required = ["E", "G", "yield", "mrho", "fem_model_type"]
    missing = [k for k in required if k not in surface]
    if missing:
        raise ValueError(
            f"Surface {surface.get('name', '?')!r} is missing structural properties: {missing}. "
            f"Set fem_model_type and structural parameters in create_surface."
        )
    if surface.get("fem_model_type") in (None, "none"):
        raise ValueError(
            f"Surface {surface.get('name', '?')!r} has fem_model_type=None. "
            f"Set fem_model_type='tube' or 'wingbox' for aerostruct analysis."
        )
