"""Shared parameters for the OAS rectangular wing aero example."""

# Wing geometry
WING = {
    "name": "wing",
    "wing_type": "rect",
    "num_x": 2,
    "num_y": 7,
    "span": 10.0,
    "root_chord": 1.0,
    "symmetry": True,
    "with_viscous": True,
    "CD0": 0.015,
}

# Flight conditions
FLIGHT = {
    "velocity": 248.136,
    "alpha": 5.0,
    "Mach_number": 0.84,
    "re": 1.0e6,
    "rho": 0.38,
}

# Optimization
OPT_TWIST_LOWER = -10.0
OPT_TWIST_UPPER = 15.0
OPT_CL_TARGET = 0.5

# Tolerances for parity testing
TOL_ANALYSIS = dict(rtol=1e-6)
TOL_OPTIMIZATION = dict(rtol=1e-3)
