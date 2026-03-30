"""Validation limits for pyCycle results."""

# TSFC ranges by archetype (lbm/hr/lbf)
TSFC_RANGES = {
    "turbojet": (0.5, 2.5),
    "hbtf": (0.3, 1.2),
    "mixedflow_turbofan": (0.3, 1.2),
    "turboshaft": (0.3, 1.0),
    "electric_propulsor": (0.0, 0.0),  # no fuel
}

# Overall pressure ratio
OPR_MIN = 2.0
OPR_MAX = 60.0

# Turbine inlet temperature (degR)
T4_MAX = 3600.0

# Shaft power balance tolerance (hp)
SHAFT_BALANCE_TOL = 1.0

# Component efficiency bounds
EFF_MIN = 0.60
EFF_MAX = 0.98
