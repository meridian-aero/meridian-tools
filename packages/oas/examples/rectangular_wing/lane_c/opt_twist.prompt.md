# Twist Optimization

Minimise inviscid drag of a rectangular wing by optimising the spanwise twist distribution, subject to a lift constraint.

## Parameters

- **Wing**: rectangular, span = 10 m, chord = 1 m
- **Mesh**: 11 chordwise x 35 spanwise nodes, symmetry = true, span_cos_spacing = 1.0, chord_cos_spacing = 1.0
- **Flight**: alpha = 5 deg, Mach = 0.0, V = 248.136 m/s, rho = 0.38 kg/m^3, Re = 1e6 /m
- **Surface**: S_ref_type = "projected", CL0 = 0.0, CD0 = 0.0, with_viscous = false, with_wave = false
- **Design variable**: twist (3 control points), bounds [-10, 15] deg
- **Constraint**: CL = 0.5 (equality)
- **Objective**: minimise CD, scaler = 1e4

## Expected MCP Tool Calls

1. `create_surface(name="wing", wing_type="rect", num_x=11, num_y=35, span=10, root_chord=1, symmetry=true, S_ref_type="projected", twist_cp=[0,0,0], CL0=0, CD0=0, with_viscous=false, with_wave=false)`
2. `run_optimization(surfaces=["wing"], analysis_type="aero", objective="CD", objective_scaler=1e4, design_variables=[{"name":"twist","lower":-10,"upper":15}], constraints=[{"name":"CL","equals":0.5}], velocity=248.136, alpha=5.0, Mach_number=0.0, reynolds_number=1e6, density=0.38)`

## Expected Output

The optimiser should converge. The final twist distribution should produce an approximately elliptical lift distribution. Report the optimised CD, final CL (should be 0.5), and the twist control point values.
