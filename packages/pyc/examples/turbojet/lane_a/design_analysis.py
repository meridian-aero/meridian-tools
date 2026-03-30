"""Lane A — Direct pyCycle API: design-point analysis.

Builds and runs a single-spool turbojet at the design point using the
raw pyCycle/OpenMDAO API.  Returns a flat dict of results that can be
compared against Lane B (MCP tools).
"""

from __future__ import annotations

import os
os.environ.setdefault("OPENMDAO_REPORTS", "0")

import openmdao.api as om
import pycycle.api as pyc

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import ENGINE_PARAMS, DESIGN_POINT, DESIGN_GUESSES, ELEMENT_MN


class TurbojetDesign(pyc.Cycle):
    def setup(self):
        self.options["thermo_method"] = "CEA"
        self.options["thermo_data"] = pyc.species_data.janaf

        self.add_subsystem("fc", pyc.FlightConditions())
        self.add_subsystem("inlet", pyc.Inlet())
        self.add_subsystem(
            "comp", pyc.Compressor(map_data=pyc.AXI5, map_extrap=True),
            promotes_inputs=["Nmech"],
        )
        self.add_subsystem("burner", pyc.Combustor(fuel_type="Jet-A(g)"))
        self.add_subsystem(
            "turb", pyc.Turbine(map_data=pyc.LPT2269),
            promotes_inputs=["Nmech"],
        )
        self.add_subsystem("nozz", pyc.Nozzle(nozzType="CD", lossCoef="Cv"))
        self.add_subsystem(
            "shaft", pyc.Shaft(num_ports=2), promotes_inputs=["Nmech"]
        )
        self.add_subsystem("perf", pyc.Performance(num_nozzles=1, num_burners=1))

        self.pyc_connect_flow("fc.Fl_O", "inlet.Fl_I", connect_w=False)
        self.pyc_connect_flow("inlet.Fl_O", "comp.Fl_I")
        self.pyc_connect_flow("comp.Fl_O", "burner.Fl_I")
        self.pyc_connect_flow("burner.Fl_O", "turb.Fl_I")
        self.pyc_connect_flow("turb.Fl_O", "nozz.Fl_I")

        self.connect("comp.trq", "shaft.trq_0")
        self.connect("turb.trq", "shaft.trq_1")
        self.connect("fc.Fl_O:stat:P", "nozz.Ps_exhaust")
        self.connect("inlet.Fl_O:tot:P", "perf.Pt2")
        self.connect("comp.Fl_O:tot:P", "perf.Pt3")
        self.connect("burner.Wfuel", "perf.Wfuel_0")
        self.connect("inlet.F_ram", "perf.ram_drag")
        self.connect("nozz.Fg", "perf.Fg_0")

        balance = self.add_subsystem("balance", om.BalanceComp())
        balance.add_balance("W", units="lbm/s", eq_units="lbf", rhs_name="Fn_target")
        self.connect("balance.W", "inlet.Fl_I:stat:W")
        self.connect("perf.Fn", "balance.lhs:W")
        balance.add_balance("FAR", eq_units="degR", lower=1e-4, val=0.017, rhs_name="T4_target")
        self.connect("balance.FAR", "burner.Fl_I:FAR")
        self.connect("burner.Fl_O:tot:T", "balance.lhs:FAR")
        balance.add_balance("turb_PR", val=1.5, lower=1.001, upper=8, eq_units="hp", rhs_val=0.0)
        self.connect("balance.turb_PR", "turb.PR")
        self.connect("shaft.pwr_net", "balance.lhs:turb_PR")

        newton = self.nonlinear_solver = om.NewtonSolver()
        newton.options["atol"] = 1e-6
        newton.options["rtol"] = 1e-6
        newton.options["maxiter"] = 15
        newton.options["solve_subsystems"] = True
        newton.options["max_sub_solves"] = 100
        newton.options["reraise_child_analysiserror"] = False
        self.linear_solver = om.DirectSolver()
        super().setup()


def run() -> dict:
    """Run design-point analysis, return flat results dict."""
    prob = om.Problem(reports=False)
    prob.model = TurbojetDesign()
    prob.setup(check=False)

    prob.set_val("fc.alt", DESIGN_POINT["alt"], units="ft")
    prob.set_val("fc.MN", DESIGN_POINT["MN"])
    prob.set_val("comp.PR", ENGINE_PARAMS["comp_PR"])
    prob.set_val("comp.eff", ENGINE_PARAMS["comp_eff"])
    prob.set_val("turb.eff", ENGINE_PARAMS["turb_eff"])
    prob.set_val("Nmech", ENGINE_PARAMS["Nmech"], units="rpm")
    prob.set_val("balance.Fn_target", DESIGN_POINT["Fn_target"], units="lbf")
    prob.set_val("balance.T4_target", DESIGN_POINT["T4_target"], units="degR")

    prob["balance.FAR"] = DESIGN_GUESSES["FAR"]
    prob["balance.W"] = DESIGN_GUESSES["W"]
    prob["balance.turb_PR"] = DESIGN_GUESSES["turb_PR"]
    prob["fc.balance.Pt"] = DESIGN_GUESSES["fc_Pt"]
    prob["fc.balance.Tt"] = DESIGN_GUESSES["fc_Tt"]

    prob.set_solver_print(level=-1)
    prob.run_model()

    return {
        "Fn": float(prob["perf.Fn"][0]),
        "TSFC": float(prob["perf.TSFC"][0]),
        "OPR": float(prob["perf.OPR"][0]),
        "Fg": float(prob["perf.Fg"][0]),
        "W": float(prob["inlet.Fl_O:stat:W"][0]),
        "comp.PR": float(prob["comp.PR"][0]),
        "comp.eff": float(prob["comp.eff"][0]),
        "turb.PR": float(prob["turb.PR"][0]),
        "turb.eff": float(prob["turb.eff"][0]),
        "shaft.Nmech": float(prob["shaft.Nmech"][0]),
        "burner.Fl_O:tot:T": float(prob["burner.Fl_O:tot:T"][0]),
        "comp.Fl_O:tot:P": float(prob["comp.Fl_O:tot:P"][0]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
