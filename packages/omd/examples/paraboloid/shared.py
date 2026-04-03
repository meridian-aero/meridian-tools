"""Shared parameters for the paraboloid example.

f(x, y) = (x - 3)^2 + x*y + (y + 4)^2 - 3

Analytic minimum: x = 20/3, y = -22/3, f = -82/3
"""

# Analysis initial conditions
ANALYSIS_X = 1.0
ANALYSIS_Y = 2.0
ANALYSIS_EXPECTED_F = 39.0  # (1-3)^2 + 1*2 + (2+4)^2 - 3

# Optimization bounds
OPT_X_LOWER = -50.0
OPT_X_UPPER = 50.0
OPT_Y_LOWER = -50.0
OPT_Y_UPPER = 50.0

# Analytic optimum
OPT_X = 20.0 / 3.0      # 6.6667
OPT_Y = -22.0 / 3.0     # -7.3333
OPT_F = -82.0 / 3.0     # -27.3333

# Tolerances for parity testing
TOL_ANALYSIS = dict(rtol=1e-12)
TOL_OPTIMIZATION = dict(rtol=1e-4)
