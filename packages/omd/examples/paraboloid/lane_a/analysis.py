"""Lane A: Paraboloid analysis using direct OpenMDAO.

Evaluates f(1, 2) = (1-3)^2 + 1*2 + (2+4)^2 - 3 = 39.0
"""

import sys
import os

import openmdao.api as om

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared import ANALYSIS_X, ANALYSIS_Y


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
    """Run paraboloid analysis and return results."""
    prob = om.Problem(reports=False)
    prob.model.add_subsystem("paraboloid", Paraboloid(), promotes=["*"])
    prob.setup()
    prob.set_val("x", ANALYSIS_X)
    prob.set_val("y", ANALYSIS_Y)
    prob.run_model()
    return {
        "x": float(prob.get_val("x")[0]),
        "y": float(prob.get_val("y")[0]),
        "f_xy": float(prob.get_val("f_xy")[0]),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
