"""Shared parameters for the OAS aerostructural example."""

# Wing geometry + structural properties
WING = {
    "name": "wing",
    "wing_type": "rect",
    "num_x": 2,
    "num_y": 7,
    "span": 10.0,
    "root_chord": 1.0,
    "symmetry": True,
    "fem_model_type": "tube",
    "E": 7.0e10,
    "G": 3.0e10,
    "yield_stress": 5.0e8,
    "mrho": 3000.0,
    "thickness_cp": [0.01, 0.02, 0.01],
    "with_viscous": True,
}

# Flight conditions
FLIGHT = {
    "velocity": 248.136,
    "alpha": 5.0,
    "Mach_number": 0.84,
    "re": 1.0e6,
    "rho": 0.38,
}

# Solver configuration
SOLVERS = {
    "nonlinear": {"type": "NewtonSolver", "options": {"maxiter": 20, "atol": 1e-6, "solve_subsystems": True}},
    "linear": {"type": "DirectSolver"},
}

# Tolerances for parity testing
TOL_ANALYSIS = dict(rtol=1e-6)
