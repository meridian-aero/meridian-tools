"""Engine archetype registry.

Each archetype defines a pyCycle Cycle subclass with hardcoded element
topology, flow connections, and balance equations.  Agents select an
archetype by name and configure it through a flat parameter dict.
"""

from hangar.pyc.archetypes.turbojet import Turbojet, MPTurbojet

ARCHETYPES = {
    "turbojet": {
        "class": Turbojet,
        "mp_class": MPTurbojet,
        "description": "Single-spool turbojet (compressor, burner, turbine, nozzle)",
        "elements": ["fc", "inlet", "comp", "burner", "turb", "nozz", "shaft", "perf"],
        "valid_design_vars": ["comp_PR", "comp_eff", "turb_eff", "burner_dPqP"],
        "flow_stations": [
            "fc.Fl_O", "inlet.Fl_O", "comp.Fl_O",
            "burner.Fl_O", "turb.Fl_O", "nozz.Fl_O",
        ],
        "compressors": ["comp"],
        "turbines": ["turb"],
        "burners": ["burner"],
        "shafts": ["shaft"],
        "nozzles": ["nozz"],
    },
}


def get_archetype(name: str) -> dict:
    """Look up an archetype by name, raising ValueError if unknown."""
    if name not in ARCHETYPES:
        valid = ", ".join(sorted(ARCHETYPES))
        raise ValueError(
            f"Unknown archetype {name!r}. Valid archetypes: {valid}"
        )
    return ARCHETYPES[name]
