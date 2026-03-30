"""Lane A: Drag polar using raw OpenAeroStruct.

Sweeps alpha from -10 to 10 deg (20 points) with viscous drag at Mach=0.84.

Migrated from: upstream/OpenAeroStruct/oas_mcp/demonstrations/rectangular_wing/lane_a/drag_polar.py
"""

import numpy as np
import openmdao.api as om

from openaerostruct.meshing.mesh_generator import generate_mesh
from openaerostruct.geometry.geometry_group import Geometry
from openaerostruct.aerodynamics.aero_groups import AeroPoint

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared import MESH, SURFACE_POLAR, FLIGHT_POLAR


def run() -> dict:
    """Run drag polar sweep and return alpha, CL, CD arrays."""
    prob = om.Problem(reports=False)

    indep_var_comp = om.IndepVarComp()
    indep_var_comp.add_output("v", val=FLIGHT_POLAR["v"], units="m/s")
    indep_var_comp.add_output("alpha", val=5.0, units="deg")
    indep_var_comp.add_output("beta", val=0.0, units="deg")
    indep_var_comp.add_output("omega", val=np.zeros(3), units="deg/s")
    indep_var_comp.add_output("Mach_number", val=FLIGHT_POLAR["Mach"])
    indep_var_comp.add_output("re", val=FLIGHT_POLAR["re"], units="1/m")
    indep_var_comp.add_output("rho", val=FLIGHT_POLAR["rho"], units="kg/m**3")
    indep_var_comp.add_output("cg", val=np.zeros(3), units="m")
    prob.model.add_subsystem("flight_vars", indep_var_comp, promotes=["*"])

    mesh = generate_mesh(MESH)

    surface = {
        "name": "wing",
        "type": "aero",
        "symmetry": MESH["symmetry"],
        "S_ref_type": SURFACE_POLAR["S_ref_type"],
        "twist_cp": np.zeros(3),
        "mesh": mesh,
        "CL0": SURFACE_POLAR["CL0"],
        "CD0": SURFACE_POLAR["CD0"],
        "k_lam": SURFACE_POLAR["k_lam"],
        "t_over_c_cp": np.array([SURFACE_POLAR["t_over_c"]]),
        "c_max_t": SURFACE_POLAR["c_max_t"],
        "with_viscous": SURFACE_POLAR["with_viscous"],
        "with_wave": SURFACE_POLAR["with_wave"],
    }

    name = surface["name"]
    geom_group = Geometry(surface=surface)
    prob.model.add_subsystem(name, geom_group)

    aero_group = AeroPoint(surfaces=[surface], rotational=True)
    point_name = "aero_point_0"
    prob.model.add_subsystem(
        point_name, aero_group,
        promotes_inputs=["v", "alpha", "beta", "omega", "Mach_number", "re", "rho", "cg"],
    )

    prob.model.connect(f"{name}.mesh", f"{point_name}.{name}.def_mesh")
    prob.model.connect(f"{name}.mesh", f"{point_name}.aero_states.{name}_def_mesh")
    prob.model.connect(f"{name}.t_over_c", f"{point_name}.{name}_perf.t_over_c")

    prob.setup()

    alphas = np.linspace(
        FLIGHT_POLAR["alpha_start"],
        FLIGHT_POLAR["alpha_end"],
        FLIGHT_POLAR["num_alpha"],
    )
    CL = np.zeros_like(alphas)
    CD = np.zeros_like(alphas)

    for i, a in enumerate(alphas):
        prob["alpha"] = a
        prob.run_model()
        CL[i] = prob[f"{point_name}.{name}_perf.CL"][0]
        CD[i] = prob[f"{point_name}.{name}_perf.CD"][0]

    return {
        "alpha": alphas.tolist(),
        "CL": CL.tolist(),
        "CD": CD.tolist(),
    }


if __name__ == "__main__":
    import json
    result = run()
    print(json.dumps(result, indent=2))
