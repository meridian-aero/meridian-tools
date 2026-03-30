"""Shared constants for rectangular wing demonstration.

Single source of truth for parameters used across Lane A (raw OAS),
Lane B (MCP / oas-cli), and the parity tests.

Migrated from: upstream/OpenAeroStruct/oas_mcp/demonstrations/rectangular_wing/shared.py
"""

import numpy as np

# ── Mesh ──────────────────────────────────────────────────────────────────
MESH = dict(
    num_y=35,
    num_x=11,
    wing_type="rect",
    symmetry=True,
    span=10.0,
    root_chord=1.0,
    span_cos_spacing=1.0,
    chord_cos_spacing=1.0,
)

# ── Common surface properties ────────────────────────────────────────────
SURFACE_COMMON = dict(
    S_ref_type="projected",
    CL0=0.0,
    CD0=0.0,
    k_lam=0.05,
    t_over_c=0.12,
    c_max_t=0.303,
)

# ── Flight conditions ────────────────────────────────────────────────────
FLIGHT_BASE = dict(
    v=248.136,      # m/s
    rho=0.38,       # kg/m^3
    re=1.0e6,       # 1/m
)

FLIGHT_AERO = dict(**FLIGHT_BASE, alpha=5.0, Mach=0.0)
FLIGHT_POLAR = dict(**FLIGHT_BASE, Mach=0.84, alpha_start=-10.0, alpha_end=10.0, num_alpha=20)

# ── Surface variants ─────────────────────────────────────────────────────
SURFACE_AERO = dict(**SURFACE_COMMON, with_viscous=False, with_wave=False)
SURFACE_POLAR = dict(**SURFACE_COMMON, with_viscous=True, with_wave=False)

# ── Optimization parameters ──────────────────────────────────────────────
OPT_TWIST = dict(
    twist_cp_lower=-10.0,
    twist_cp_upper=15.0,
    cl_target=0.5,
    scaler=1e4,
)

OPT_CHORD = dict(
    chord_cp_lower=1e-3,
    chord_cp_upper=5.0,
    alpha_lower=-10.0,
    alpha_upper=15.0,
    cl_target=0.5,
    sref_target=10.0,
    scaler=1e4,
)

# ── Tolerances for parity tests ──────────────────────────────────────────
TOL_ANALYSIS = dict(rtol=1e-6)       # CL/CD for analysis runs
TOL_POLAR = dict(rtol=5e-5)          # CL/CD arrays for drag polar (slightly wider due to loop vs batch)
TOL_OPT_OBJ = dict(rtol=1e-3)       # Optimized objective (CD)
TOL_OPT_CON = dict(atol=1e-4)       # Constraint satisfaction (CL, S_ref)
TOL_OPT_DV = dict(atol=0.05)        # Design variable values
