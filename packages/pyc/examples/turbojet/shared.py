"""Single source of truth for the turbojet parity example.

Both Lane A (direct pyCycle API) and Lane B (hangar-pyc MCP tools)
import parameters and tolerances from here.
"""

# ---------------------------------------------------------------------------
# Engine parameters
# ---------------------------------------------------------------------------

ENGINE_PARAMS = dict(
    comp_PR=13.5,
    comp_eff=0.83,
    turb_eff=0.86,
    Nmech=8070.0,           # rpm
    burner_dPqP=0.03,
    nozz_Cv=0.99,
    thermo_method="CEA",
)

# ---------------------------------------------------------------------------
# Flight conditions
# ---------------------------------------------------------------------------

DESIGN_POINT = dict(
    alt=0.0,                # ft  (sea-level static)
    MN=0.000001,            # near-zero Mach
    Fn_target=11800.0,      # lbf
    T4_target=2370.0,       # degR
)

OFF_DESIGN_POINTS = [
    dict(name="OD0", alt=0.0,    MN=0.000001, Fn_target=11000.0),
    dict(name="OD1", alt=5000.0, MN=0.2,      Fn_target=8000.0),
]

# ---------------------------------------------------------------------------
# Design-point initial guesses (Newton solver)
# ---------------------------------------------------------------------------

DESIGN_GUESSES = dict(
    FAR=0.0175506829934,
    W=168.453135137,
    turb_PR=4.46138725662,
    fc_Pt=14.6955113159,
    fc_Tt=518.665288153,
)

OD_GUESSES = dict(
    W=166.073,
    FAR=0.01680,
    Nmech=8197.38,
    fc_Pt=15.703,
    fc_Tt=558.31,
    turb_PR=4.6690,
)

# ---------------------------------------------------------------------------
# Element Mach number defaults (design point)
# ---------------------------------------------------------------------------

ELEMENT_MN = dict(
    inlet_MN=0.60,
    comp_MN=0.02,
    burner_MN=0.02,
    turb_MN=0.4,
)

# ---------------------------------------------------------------------------
# Tolerances for parity comparison
# ---------------------------------------------------------------------------

# Design-point single-value metrics
TOL_PERFORMANCE = dict(rtol=1e-4)

# Off-design metrics (solver path may differ slightly)
TOL_OFF_DESIGN = dict(rtol=5e-4)

# Flow station properties
TOL_FLOW_STATION = dict(rtol=1e-3)

# Component details
TOL_COMPONENT = dict(rtol=1e-3)
