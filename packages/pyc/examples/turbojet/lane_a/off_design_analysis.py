"""Lane A — Direct pyCycle API: multi-point (design + off-design) analysis.

Builds an MPCycle turbojet, runs design + two off-design points, and
returns a dict keyed by point name.
"""

from __future__ import annotations

import os
os.environ.setdefault("OPENMDAO_REPORTS", "0")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openmdao.api as om
import pycycle.api as pyc

from shared import (
    ENGINE_PARAMS, DESIGN_POINT, OFF_DESIGN_POINTS,
    DESIGN_GUESSES, OD_GUESSES, ELEMENT_MN,
)


class Turbojet(pyc.Cycle):
    def setup(self):
        self.options["thermo_method"] = "CEA"
        self.options["thermo_data"] = pyc.species_data.janaf
        design = self.options["design"]

        self.add_subsystem("fc", pyc.FlightConditions())
        self.add_subsystem("inlet", pyc.Inlet())
        self.add_subsystem("comp", pyc.Compressor(map_data=pyc.AXI5, map_extrap=True),
                           promotes_inputs=["Nmech"])
        self.add_subsystem("burner", pyc.Combustor(fuel_type="Jet-A(g)"))
        self.add_subsystem("turb", pyc.Turbine(map_data=pyc.LPT2269),
                           promotes_inputs=["Nmech"])
        self.add_subsystem("nozz", pyc.Nozzle(nozzType="CD", lossCoef="Cv"))
        self.add_subsystem("shaft", pyc.Shaft(num_ports=2), promotes_inputs=["Nmech"])
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
        if design:
            balance.add_balance("W", units="lbm/s", eq_units="lbf", rhs_name="Fn_target")
            self.connect("balance.W", "inlet.Fl_I:stat:W")
            self.connect("perf.Fn", "balance.lhs:W")
            balance.add_balance("FAR", eq_units="degR", lower=1e-4, val=0.017, rhs_name="T4_target")
            self.connect("balance.FAR", "burner.Fl_I:FAR")
            self.connect("burner.Fl_O:tot:T", "balance.lhs:FAR")
            balance.add_balance("turb_PR", val=1.5, lower=1.001, upper=8, eq_units="hp", rhs_val=0.0)
            self.connect("balance.turb_PR", "turb.PR")
            self.connect("shaft.pwr_net", "balance.lhs:turb_PR")
        else:
            balance.add_balance("FAR", eq_units="lbf", lower=1e-4, val=0.3, rhs_name="Fn_target")
            self.connect("balance.FAR", "burner.Fl_I:FAR")
            self.connect("perf.Fn", "balance.lhs:FAR")
            balance.add_balance("Nmech", val=1.5, units="rpm", lower=500.0, eq_units="hp", rhs_val=0.0)
            self.connect("balance.Nmech", "Nmech")
            self.connect("shaft.pwr_net", "balance.lhs:Nmech")
            balance.add_balance("W", val=168.0, units="lbm/s", eq_units="inch**2")
            self.connect("balance.W", "inlet.Fl_I:stat:W")
            self.connect("nozz.Throat:stat:area", "balance.lhs:W")

        newton = self.nonlinear_solver = om.NewtonSolver()
        newton.options["atol"] = 1e-6
        newton.options["rtol"] = 1e-6
        newton.options["maxiter"] = 15
        newton.options["solve_subsystems"] = True
        newton.options["max_sub_solves"] = 100
        newton.options["reraise_child_analysiserror"] = False
        self.linear_solver = om.DirectSolver()
        super().setup()


class MPTurbojet(pyc.MPCycle):
    def setup(self):
        self.pyc_add_pnt("DESIGN", Turbojet())
        self.set_input_defaults("DESIGN.Nmech", ENGINE_PARAMS["Nmech"], units="rpm")
        self.set_input_defaults("DESIGN.inlet.MN", ELEMENT_MN["inlet_MN"])
        self.set_input_defaults("DESIGN.comp.MN", ELEMENT_MN["comp_MN"])
        self.set_input_defaults("DESIGN.burner.MN", ELEMENT_MN["burner_MN"])
        self.set_input_defaults("DESIGN.turb.MN", ELEMENT_MN["turb_MN"])

        self.pyc_add_cycle_param("burner.dPqP", ENGINE_PARAMS["burner_dPqP"])
        self.pyc_add_cycle_param("nozz.Cv", ENGINE_PARAMS["nozz_Cv"])

        self.od_pts = []
        for od in OFF_DESIGN_POINTS:
            pt = od["name"]
            self.od_pts.append(pt)
            self.pyc_add_pnt(pt, Turbojet(design=False))
            self.set_input_defaults(f"{pt}.fc.MN", val=od["MN"])
            self.set_input_defaults(f"{pt}.fc.alt", od["alt"], units="ft")
            self.set_input_defaults(f"{pt}.balance.Fn_target", od["Fn_target"], units="lbf")

        self.pyc_use_default_des_od_conns()
        self.pyc_connect_des_od("nozz.Throat:stat:area", "balance.rhs:W")
        super().setup()


def _extract_point(prob, pt: str) -> dict:
    """Extract results for a single operating point."""
    return {
        "Fn": float(prob[f"{pt}.perf.Fn"][0]),
        "TSFC": float(prob[f"{pt}.perf.TSFC"][0]),
        "OPR": float(prob[f"{pt}.perf.OPR"][0]),
        "Fg": float(prob[f"{pt}.perf.Fg"][0]),
        "W": float(prob[f"{pt}.inlet.Fl_O:stat:W"][0]),
        "comp.PR": float(prob[f"{pt}.comp.PR"][0]),
        "comp.eff": float(prob[f"{pt}.comp.eff"][0]),
        "turb.PR": float(prob[f"{pt}.turb.PR"][0]),
        "turb.eff": float(prob[f"{pt}.turb.eff"][0]),
        "shaft.Nmech": float(prob[f"{pt}.shaft.Nmech"][0]),
        "burner.Fl_O:tot:T": float(prob[f"{pt}.burner.Fl_O:tot:T"][0]),
        "comp.Fl_O:tot:P": float(prob[f"{pt}.comp.Fl_O:tot:P"][0]),
    }


def run() -> dict:
    """Run multi-point analysis, return {DESIGN: {...}, OD0: {...}, OD1: {...}}."""
    prob = om.Problem(reports=False)
    prob.model = MPTurbojet()
    prob.setup(check=False)

    prob.set_val("DESIGN.fc.alt", DESIGN_POINT["alt"], units="ft")
    prob.set_val("DESIGN.fc.MN", DESIGN_POINT["MN"])
    prob.set_val("DESIGN.comp.PR", ENGINE_PARAMS["comp_PR"])
    prob.set_val("DESIGN.comp.eff", ENGINE_PARAMS["comp_eff"])
    prob.set_val("DESIGN.turb.eff", ENGINE_PARAMS["turb_eff"])
    prob.set_val("DESIGN.balance.Fn_target", DESIGN_POINT["Fn_target"], units="lbf")
    prob.set_val("DESIGN.balance.T4_target", DESIGN_POINT["T4_target"], units="degR")

    # Design guesses
    prob["DESIGN.balance.FAR"] = DESIGN_GUESSES["FAR"]
    prob["DESIGN.balance.W"] = DESIGN_GUESSES["W"]
    prob["DESIGN.balance.turb_PR"] = DESIGN_GUESSES["turb_PR"]
    prob["DESIGN.fc.balance.Pt"] = DESIGN_GUESSES["fc_Pt"]
    prob["DESIGN.fc.balance.Tt"] = DESIGN_GUESSES["fc_Tt"]

    # Off-design guesses
    for od in OFF_DESIGN_POINTS:
        pt = od["name"]
        prob[f"{pt}.balance.W"] = OD_GUESSES["W"]
        prob[f"{pt}.balance.FAR"] = OD_GUESSES["FAR"]
        prob[f"{pt}.balance.Nmech"] = OD_GUESSES["Nmech"]
        prob[f"{pt}.fc.balance.Pt"] = OD_GUESSES["fc_Pt"]
        prob[f"{pt}.fc.balance.Tt"] = OD_GUESSES["fc_Tt"]
        prob[f"{pt}.turb.PR"] = OD_GUESSES["turb_PR"]

    prob.set_solver_print(level=-1)
    prob.run_model()

    results = {"DESIGN": _extract_point(prob, "DESIGN")}
    for od in OFF_DESIGN_POINTS:
        results[od["name"]] = _extract_point(prob, od["name"])
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
