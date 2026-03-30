"""Default flight conditions, mesh parameters, and material properties.

Migrated from: OpenAeroStruct/oas_mcp/core/defaults.py
"""

import numpy as np
from openaerostruct.utils.constants import grav_constant

# Default flight conditions for aero analysis
DEFAULT_AERO_CONDITIONS = {
    "velocity": 248.136,  # m/s (~Mach 0.84 at cruise alt)
    "alpha": 5.0,  # deg
    "Mach_number": 0.84,
    "reynolds_number": 1.0e6,  # 1/m
    "density": 0.38,  # kg/m^3
    "cg": [0.0, 0.0, 0.0],  # m
}

# Default extra conditions for aerostruct
DEFAULT_AEROSTRUCT_CONDITIONS = {
    **DEFAULT_AERO_CONDITIONS,
    "CT": grav_constant * 17.0e-6,  # 1/s (specific fuel consumption)
    "R": 11.165e6,  # m (range)
    "W0": 0.4 * 3e5,  # kg (empty weight)
    "speed_of_sound": 295.4,  # m/s
    "load_factor": 1.0,
    "empty_cg": [0.0, 0.0, 0.0],  # m
}

# Default mesh parameters
DEFAULT_MESH_PARAMS = {
    "num_x": 2,
    "num_y": 7,
    "wing_type": "rect",
    "symmetry": True,
    "span": 10.0,
    "root_chord": 1.0,
}

# Default surface properties (aero only)
DEFAULT_AERO_SURFACE = {
    "S_ref_type": "wetted",
    "CL0": 0.0,
    "CD0": 0.015,
    "k_lam": 0.05,
    "t_over_c_cp": np.array([0.15]),
    "c_max_t": 0.303,
    "with_viscous": True,
    "with_wave": False,
}

# Default wingbox airfoil: NASA SC2-0612, 10%–60% chord (same as all OAS wingbox examples).
# dtype=complex128 is required so complex-step derivative checks work correctly.
DEFAULT_WINGBOX_UPPER_X = np.array(
    [0.1, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19,
     0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29,
     0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39,
     0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49,
     0.5, 0.51, 0.52, 0.53, 0.54, 0.55, 0.56, 0.57, 0.58, 0.59, 0.6],
    dtype="complex128",
)
DEFAULT_WINGBOX_LOWER_X = DEFAULT_WINGBOX_UPPER_X.copy()
DEFAULT_WINGBOX_UPPER_Y = np.array(
    [0.0447, 0.046, 0.0472, 0.0484, 0.0495, 0.0505, 0.0514, 0.0523,
     0.0531, 0.0538, 0.0545, 0.0551, 0.0557, 0.0563, 0.0568, 0.0573,
     0.0577, 0.0581, 0.0585, 0.0588, 0.0591, 0.0593, 0.0595, 0.0597,
     0.0599, 0.06, 0.0601, 0.0602, 0.0602, 0.0602, 0.0602, 0.0602,
     0.0601, 0.06, 0.0599, 0.0598, 0.0596, 0.0594, 0.0592, 0.0589,
     0.0586, 0.0583, 0.058, 0.0576, 0.0572, 0.0568, 0.0563, 0.0558,
     0.0553, 0.0547, 0.0541],
    dtype="complex128",
)
DEFAULT_WINGBOX_LOWER_Y = np.array(
    [-0.0447, -0.046, -0.0473, -0.0485, -0.0496, -0.0506, -0.0515, -0.0524,
     -0.0532, -0.054, -0.0547, -0.0554, -0.056, -0.0565, -0.057, -0.0575,
     -0.0579, -0.0583, -0.0586, -0.0589, -0.0592, -0.0594, -0.0595, -0.0596,
     -0.0597, -0.0598, -0.0598, -0.0598, -0.0598, -0.0597, -0.0596, -0.0594,
     -0.0592, -0.0589, -0.0586, -0.0582, -0.0578, -0.0573, -0.0567, -0.0561,
     -0.0554, -0.0546, -0.0538, -0.0529, -0.0519, -0.0509, -0.0497, -0.0485,
     -0.0472, -0.0458, -0.0444],
    dtype="complex128",
)

# Default structural properties (aluminum 7075)
DEFAULT_STRUCT_PROPS = {
    "fem_model_type": "tube",
    "E": 70.0e9,  # Pa
    "G": 30.0e9,  # Pa
    "yield": 500.0e6,  # Pa
    "safety_factor": 2.5,
    "mrho": 3.0e3,  # kg/m^3
    "fem_origin": 0.35,
    "wing_weight_ratio": 2.0,
    "struct_weight_relief": False,
    "distributed_fuel_weight": False,
    "exact_failure_constraint": False,
}
