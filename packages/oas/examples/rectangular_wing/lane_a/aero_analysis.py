"""Lane A: Single-point aero analysis using raw OpenAeroStruct.

Incompressible inviscid analysis of a flat rectangular wing at alpha=5 deg.

Migrated from: upstream/OpenAeroStruct/oas_mcp/demonstrations/rectangular_wing/lane_a/aero_analysis.py
"""

import numpy as np
import openmdao.api as om

from openaerostruct.meshing.mesh_generator import generate_mesh
from openaerostruct.geometry.geometry_group import Geometry
from openaerostruct.aerodynamics.aero_groups import AeroPoint

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared import MESH, SURFACE_AERO, FLIGHT_AERO


def run() -> dict:
    """Run aero analysis and return CL, CD."""
    prob = om.Problem(reports=False)

    indep_var_comp = om.IndepVarComp()
    indep_var_comp.add_output("v", val=FLIGHT_AERO["v"], units="m/s")
    indep_var_comp.add_output("alpha", val=FLIGHT_AERO["alpha"], units="deg")
    indep_var_comp.add_output("beta", val=0.0, units="deg")
    indep_var_comp.add_output("omega", val=np.zeros(3), units="deg/s")
    indep_var_comp.add_output("Mach_number", val=FLIGHT_AERO["Mach"])
    indep_var_comp.add_output("re", val=FLIGHT_AERO["re"], units="1/m")
    indep_var_comp.add_output("rho", val=FLIGHT_AERO["rho"], units="kg/m**3")
    indep_var_comp.add_output("cg", val=np.zeros(3), units="m")
    prob.model.add_subsystem("flight_vars", indep_var_comp, promotes=["*"])

    mesh = generate_mesh(MESH)

    surface = {
        "name": "wing",
        "type": "aero",
        "symmetry": MESH["symmetry"],
        "S_ref_type": SURFACE_AERO["S_ref_type"],
        "twist_cp": np.zeros(3),
        "mesh": mesh,
        "CL0": SURFACE_AERO["CL0"],
        "CD0": SURFACE_AERO["CD0"],
        "k_lam": SURFACE_AERO["k_lam"],
        "t_over_c": SURFACE_AERO["t_over_c"],
        "c_max_t": SURFACE_AERO["c_max_t"],
        "with_viscous": SURFACE_AERO["with_viscous"],
        "with_wave": SURFACE_AERO["with_wave"],
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

    prob.setup()
    prob.run_model()

    CL = float(prob[f"{point_name}.{name}_perf.CL"][0])
    CD = float(prob[f"{point_name}.{name}_perf.CD"][0])

    return {"CL": CL, "CD": CD}


if __name__ == "__main__":
    import json
    result = run()
    print(json.dumps(result, indent=2))
