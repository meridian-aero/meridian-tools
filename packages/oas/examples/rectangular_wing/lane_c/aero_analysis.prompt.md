# Single-Point Aerodynamic Analysis

Run an incompressible inviscid aerodynamic analysis on a rectangular wing.

## Parameters

- **Wing**: rectangular, span = 10 m, chord = 1 m, no twist
- **Mesh**: 11 chordwise x 35 spanwise nodes, symmetry = true, span_cos_spacing = 1.0, chord_cos_spacing = 1.0
- **Flight**: alpha = 5 deg, Mach = 0.0, V = 248.136 m/s, rho = 0.38 kg/m^3, Re = 1e6 /m
- **Surface**: S_ref_type = "projected", CL0 = 0.0, CD0 = 0.0, with_viscous = false, with_wave = false

## Expected MCP Tool Calls

1. `create_surface(name="wing", wing_type="rect", num_x=11, num_y=35, span=10, root_chord=1, symmetry=true, S_ref_type="projected", twist_cp=[0,0,0], CL0=0, CD0=0, with_viscous=false, with_wave=false)`
2. `run_aero_analysis(surfaces=["wing"], alpha=5.0, velocity=248.136, Mach_number=0.0, reynolds_number=1e6, density=0.38)`

## Expected Output

Report CL and CD. Both should be positive. CL should be around 0.45-0.55 for alpha=5 deg on a rectangular wing.
