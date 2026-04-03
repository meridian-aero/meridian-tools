"""Lane A: Paraboloid optimization using direct OpenMDAO.

Minimizes f(x,y) subject to -50 <= x,y <= 50.
Optimal at x = 20/3, y = -22/3, f = -82/3.
"""

import sys
import os

import openmdao.api as om

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared import OPT_X_LOWER, OPT_X_UPPER, OPT_Y_LOWER, OPT_Y_UPPER


class Paraboloid(om.ExplicitComponent):
    def setup(self):
        self.add_input("x", val=0.0)
        self.add_input("y", val=0.0)
        self.add_output("f_xy", val=0.0)
        self.declare_partials("*", "*")

    def compute(self, inputs, outputs):
        x, y = inputs["x"], inputs["y"]
        outputs["f_xy"] = (x - 3.0) ** 2 + x * y + (y + 4.0) ** 2 - 3.0

    def compute_partials(self, inputs, J):
        x, y = inputs["x"], inputs["y"]
        J["f_xy", "x"] = 2.0 * x - 6.0 + y
        J["f_xy", "y"] = 2.0 * y + 8.0 + x


def run() -> dict:
    """Run paraboloid optimization and return results."""
    prob = om.Problem(reports=False)
    prob.model.add_subsystem("paraboloid", Paraboloid(), promotes=["*"])

    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options["optimizer"] = "SLSQP"
    prob.driver.options["disp"] = False

    prob.model.add_design_var("x", lower=OPT_X_LOWER, upper=OPT_X_UPPER)
    prob.model.add_design_var("y", lower=OPT_Y_LOWER, upper=OPT_Y_UPPER)
    prob.model.add_objective("f_xy")

    prob.setup()
    prob.run_driver()

    return {
        "x": float(prob.get_val("x")[0]),
        "y": float(prob.get_val("y")[0]),
        "f_xy": float(prob.get_val("f_xy")[0]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
