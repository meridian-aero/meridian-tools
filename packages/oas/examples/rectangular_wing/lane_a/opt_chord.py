"""Lane A: Chord optimization using raw OpenAeroStruct.

Minimises inviscid CD by varying chord distribution (3 B-spline CPs) and
alpha, subject to CL=0.5 and S_ref=10.0 m^2.  Expected result: elliptical
chord distribution.

Migrated from: upstream/OpenAeroStruct/oas_mcp/demonstrations/rectangular_wing/lane_a/opt_chord.py
"""

import numpy as np
import openmdao.api as om

from openaerostruct.meshing.mesh_generator import generate_mesh
from openaerostruct.geometry.geometry_group import Geometry
from openaerostruct.aerodynamics.aero_groups import AeroPoint

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared import MESH, SURFACE_AERO, FLIGHT_AERO, OPT_CHORD


def run() -> dict:
    """Run chord optimization and return results."""
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
        "chord_cp": np.ones(3),
        "ref_axis_pos": 0.25,
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

    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options["debug_print"] = ["nl_cons", "objs", "desvars"]

    prob.model.add_design_var(
        "alpha",
        lower=OPT_CHORD["alpha_lower"],
        upper=OPT_CHORD["alpha_upper"],
    )
    prob.model.add_design_var(
        "wing.chord_cp",
        lower=OPT_CHORD["chord_cp_lower"],
        upper=OPT_CHORD["chord_cp_upper"],
        units=None,
    )
    prob.model.add_constraint(f"{point_name}.wing_perf.CL", equals=OPT_CHORD["cl_target"])
    prob.model.add_constraint(f"{point_name}.wing.S_ref", equals=OPT_CHORD["sref_target"])
    prob.model.add_objective(f"{point_name}.wing_perf.CD", scaler=OPT_CHORD["scaler"])

    prob.setup()
    prob.run_driver()

    CL = float(prob[f"{point_name}.wing_perf.CL"][0])
    CD = float(prob[f"{point_name}.wing_perf.CD"][0])
    alpha = float(prob["alpha"][0])
    S_ref = float(prob[f"{point_name}.wing.S_ref"][0])
    # OAS internal order is tip-to-root; reverse to root-to-tip
    chord_cp = prob["wing.chord_cp"].flatten().tolist()[::-1]

    return {
        "CL": CL,
        "CD": CD,
        "alpha": alpha,
        "chord_cp": chord_cp,
        "S_ref": S_ref,
        "success": prob.driver.result.success if hasattr(prob.driver, "result") else True,
    }


if __name__ == "__main__":
    import json
    result = run()
    print(json.dumps(result, indent=2))
