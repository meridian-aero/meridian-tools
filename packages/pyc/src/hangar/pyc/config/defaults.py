"""Default parameters and initial guesses for pyCycle archetypes."""

# ---------------------------------------------------------------------------
# Flight conditions
# ---------------------------------------------------------------------------

DEFAULT_DESIGN_CONDITIONS = {
    "alt": 0.0,         # ft (sea-level static for turbojet)
    "MN": 0.000001,     # Mach (near-zero for SLS)
    "Fn_target": 11800, # lbf
    "T4_target": 2370,  # degR
}

DEFAULT_CRUISE_CONDITIONS = {
    "alt": 35000,       # ft
    "MN": 0.8,
    "Fn_target": 5800,  # lbf
    "T4_target": 3200,  # degR
}

# ---------------------------------------------------------------------------
# Turbojet
# ---------------------------------------------------------------------------

DEFAULT_TURBOJET_PARAMS = {
    "thermo_method": "CEA",  # "TABULAR" or "CEA"
    "comp_PR": 13.5,
    "comp_eff": 0.83,
    "turb_eff": 0.86,
    "Nmech": 8070.0,       # rpm
    "burner_dPqP": 0.03,
    "nozz_Cv": 0.99,
    # Element MN defaults (design point)
    "inlet_MN": 0.60,
    "comp_MN": 0.02,
    "burner_MN": 0.02,
    "turb_MN": 0.4,
}

DEFAULT_TURBOJET_DESIGN_GUESSES = {
    "FAR": 0.0175506829934,
    "W": 168.453135137,
    "turb_PR": 4.46138725662,
    "fc_Pt": 14.6955113159,
    "fc_Tt": 518.665288153,
}

DEFAULT_TURBOJET_OD_GUESSES = {
    "W": 166.073,
    "FAR": 0.01680,
    "Nmech": 8197.38,
    "fc_Pt": 15.703,
    "fc_Tt": 558.31,
    "turb_PR": 4.6690,
}

# ---------------------------------------------------------------------------
# High-bypass turbofan (HBTF)
# ---------------------------------------------------------------------------

DEFAULT_HBTF_PARAMS = {
    "thermo_method": "CEA",
    "fan_PR": 1.685,
    "fan_eff": 0.8948,
    "lpc_PR": 1.935,
    "lpc_eff": 0.9243,
    "hpc_PR": 9.369,
    "hpc_eff": 0.8707,
    "hpt_eff": 0.8888,
    "lpt_eff": 0.8996,
    "BPR": 5.105,
    "LP_Nmech": 4666.1,   # rpm
    "HP_Nmech": 14705.7,   # rpm
    "design_T4": 2857.0,    # degR
    "design_Fn": 5900.0,    # lbf
    "burner_dPqP": 0.054,
    # Duct losses
    "duct4_dPqP": 0.0048,
    "duct6_dPqP": 0.0101,
    "duct11_dPqP": 0.0051,
    "duct13_dPqP": 0.0107,
    "duct15_dPqP": 0.0149,
    # Nozzle coefficients
    "core_nozz_Cv": 0.9933,
    "byp_nozz_Cv": 0.9939,
    # Bleed fractions
    "cool1_frac_W": 0.050708,
    "cool2_frac_W": 0.020274,
    "cool3_frac_W": 0.067214,
    "cool4_frac_W": 0.101256,
    "cust_frac_W": 0.0445,
    # Inlet
    "inlet_ram_recovery": 0.9990,
}

DEFAULT_HBTF_DESIGN_GUESSES = {
    "FAR": 0.025,
    "W": 100.0,
    "lpt_PR": 4.0,
    "hpt_PR": 3.0,
    "fc_Pt": 5.2,
    "fc_Tt": 440.0,
}

DEFAULT_HBTF_OD_GUESSES = {
    "FAR": 0.02467,
    "W": 300.0,
    "BPR": 5.105,
    "lp_Nmech": 5000.0,
    "hp_Nmech": 15000.0,
    "hpt_PR": 3.0,
    "lpt_PR": 4.0,
    "fan_RlineMap": 2.0,
    "lpc_RlineMap": 2.0,
    "hpc_RlineMap": 2.0,
}
