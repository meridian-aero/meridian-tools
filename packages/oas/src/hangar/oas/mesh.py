"""Mesh generation and geometric transformations.

Migrated from: OpenAeroStruct/oas_mcp/core/mesh.py
"""

import numpy as np
from openaerostruct.meshing.mesh_generator import generate_mesh


def build_mesh(
    wing_type: str,
    num_x: int,
    num_y: int,
    span: float,
    root_chord: float,
    symmetry: bool,
    offset=None,
    num_twist_cp: int | None = None,
    span_cos_spacing: float = 0.0,
    chord_cos_spacing: float = 0.0,
) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Generate a mesh and optional initial twist array.

    Returns
    -------
    mesh : np.ndarray shape (num_x, num_y, 3)
    twist_cp : np.ndarray or None  (only for CRM)
    """
    mesh_dict = {
        "num_x": num_x,
        "num_y": num_y,
        "wing_type": wing_type,
        "symmetry": symmetry,
        "span": span,
        "root_chord": root_chord,
        "span_cos_spacing": span_cos_spacing,
        "chord_cos_spacing": chord_cos_spacing,
    }
    if offset is not None:
        mesh_dict["offset"] = np.asarray(offset, dtype=float)

    if "CRM" in wing_type:
        # generate_mesh returns (mesh, twist_cp) for CRM and uCRM_based
        # (mesh is already chopped for symmetry if symmetry=True)
        mesh_dict["num_twist_cp"] = num_twist_cp if num_twist_cp is not None else max(2, min(5, (num_y + 1) // 2))
        mesh, twist_out = generate_mesh(mesh_dict)
        return mesh, twist_out
    else:
        # rect: generate_mesh returns just mesh (already chopped for symmetry)
        mesh = generate_mesh(mesh_dict)
        if isinstance(mesh, tuple):
            mesh = mesh[0]
        return mesh, None


def apply_sweep(mesh: np.ndarray, sweep_deg: float) -> np.ndarray:
    """Shear mesh in x direction to apply leading-edge sweep."""
    if sweep_deg == 0.0:
        return mesh
    mesh = mesh.copy()
    sweep_rad = np.deg2rad(sweep_deg)
    # Leading edge is mesh[0,:,:]
    # Shift x by y * tan(sweep)
    y_coords = mesh[0, :, 1]
    x_shift = np.abs(y_coords) * np.tan(sweep_rad)
    for ix in range(mesh.shape[0]):
        mesh[ix, :, 0] += x_shift
    return mesh


def apply_dihedral(mesh: np.ndarray, dihedral_deg: float) -> np.ndarray:
    """Shift mesh z coords to apply dihedral."""
    if dihedral_deg == 0.0:
        return mesh
    mesh = mesh.copy()
    dih_rad = np.deg2rad(dihedral_deg)
    y_coords = mesh[0, :, 1]
    z_shift = np.abs(y_coords) * np.tan(dih_rad)
    for ix in range(mesh.shape[0]):
        mesh[ix, :, 2] += z_shift
    return mesh


def apply_taper(mesh: np.ndarray, taper: float) -> np.ndarray:
    """Scale chord linearly from root (taper=1) to tip (taper=taper)."""
    if taper == 1.0:
        return mesh
    mesh = mesh.copy()
    num_y = mesh.shape[1]
    ny2 = (num_y + 1) // 2
    # For symmetry, half span goes from root (index ny2-1) to tip (index 0)
    # taper ratio applied relative to root chord
    y_abs = np.abs(mesh[0, :, 1])
    y_max = y_abs.max()
    if y_max == 0.0:
        return mesh
    scale = 1.0 - (1.0 - taper) * y_abs / y_max
    # Scale chord by moving leading edge forward and trailing edge backward
    # Chord center = midpoint of LE and TE in x
    le_x = mesh[0, :, 0]
    te_x = mesh[-1, :, 0]
    mid_x = 0.5 * (le_x + te_x)
    chord = te_x - le_x
    for ix in range(mesh.shape[0]):
        frac = ix / (mesh.shape[0] - 1)
        mesh[ix, :, 0] = mid_x + (frac - 0.5) * chord * scale
    return mesh
