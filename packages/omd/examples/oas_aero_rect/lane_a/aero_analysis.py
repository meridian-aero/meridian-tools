"""Lane A: OAS aero-only analysis using direct OpenAeroStruct."""

import sys
import os

import numpy as np
import openmdao.api as om
from openaerostruct.meshing.mesh_generator import generate_mesh
from openaerostruct.geometry.geometry_group import Geometry
from openaerostruct.aerodynamics.aero_groups import AeroPoint

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared import WING, FLIGHT


def run() -> dict:
    """Run aero analysis and return CL, CD."""
    mesh_dict = {k: WING[k] for k in ("num_x", "num_y", "wing_type", "symmetry", "span", "root_chord")}
    mesh = generate_mesh(mesh_dict)
    if isinstance(mesh, tuple):
        mesh = mesh[0]

    n_cp = (WING["num_y"] + 1) // 2
    surface = {
        "name": "wing", "mesh": mesh, "symmetry": True,
        "S_ref_type": "wetted", "CL0": 0.0, "CD0": WING["CD0"],
        "k_lam": 0.05, "t_over_c_cp": np.array([0.15]),
        "c_max_t": 0.303, "with_viscous": WING["with_viscous"],
        "with_wave": False, "twist_cp": np.zeros(n_cp),
    }

    prob = om.Problem(reports=False)
    indep = om.IndepVarComp()
    indep.add_output("v", val=FLIGHT["velocity"], units="m/s")
    indep.add_output("alpha", val=FLIGHT["alpha"], units="deg")
    indep.add_output("beta", val=0.0, units="deg")
    indep.add_output("Mach_number", val=FLIGHT["Mach_number"])
    indep.add_output("re", val=FLIGHT["re"], units="1/m")
    indep.add_output("rho", val=FLIGHT["rho"], units="kg/m**3")
    indep.add_output("cg", val=np.zeros(3), units="m")
    prob.model.add_subsystem("prob_vars", indep, promotes=["*"])
    prob.model.add_subsystem("wing", Geometry(surface=surface))
    prob.model.add_subsystem(
        "aero", AeroPoint(surfaces=[surface]),
        promotes_inputs=["v", "alpha", "beta", "Mach_number", "re", "rho", "cg"],
    )
    prob.model.connect("wing.mesh", "aero.wing.def_mesh")
    prob.model.connect("wing.mesh", "aero.aero_states.wing_def_mesh")
    prob.model.connect("wing.t_over_c", "aero.wing_perf.t_over_c")
    prob.setup()
    prob.run_model()

    return {
        "CL": float(prob.get_val("aero.CL")[0]),
        "CD": float(prob.get_val("aero.CD")[0]),
    }


if __name__ == "__main__":
    import json
    r = run()
    r["L_over_D"] = r["CL"] / r["CD"]
    print(json.dumps(r, indent=2))
