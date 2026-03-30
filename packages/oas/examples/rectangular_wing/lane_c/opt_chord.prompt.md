# Chord Optimization

Minimise inviscid drag of an initially rectangular wing by optimising the chord distribution and angle of attack, subject to lift and reference area constraints.

## Parameters

- **Wing**: rectangular, span = 10 m, initial chord = 1 m
- **Mesh**: 11 chordwise x 35 spanwise nodes, symmetry = true, span_cos_spacing = 1.0, chord_cos_spacing = 1.0
- **Flight**: alpha = 5 deg (initial), Mach = 0.0, V = 248.136 m/s, rho = 0.38 kg/m^3, Re = 1e6 /m
- **Surface**: S_ref_type = "projected", CL0 = 0.0, CD0 = 0.0, with_viscous = false, with_wave = false
- **Design variables**:
  - chord (3 control points), bounds [0.001, 5.0]
  - alpha, bounds [-10, 15] deg
- **Constraints**:
  - CL = 0.5 (equality)
  - S_ref = 10.0 m^2 (equality)
- **Objective**: minimise CD, scaler = 1e4

## Expected MCP Tool Calls

1. `create_surface(name="wing", wing_type="rect", num_x=11, num_y=35, span=10, root_chord=1, symmetry=true, S_ref_type="projected", chord_cp=[1,1,1], CL0=0, CD0=0, with_viscous=false, with_wave=false)`
2. `run_optimization(surfaces=["wing"], analysis_type="aero", objective="CD", objective_scaler=1e4, design_variables=[{"name":"alpha","lower":-10,"upper":15}, {"name":"chord","lower":0.001,"upper":5}], constraints=[{"name":"CL","equals":0.5}, {"name":"S_ref","equals":10}], velocity=248.136, alpha=5.0, Mach_number=0.0, reynolds_number=1e6, density=0.38)`

## Expected Output

The optimiser should converge. The final chord distribution should be approximately elliptical. Report the optimised CD, final CL (should be 0.5), final S_ref (should be 10.0), the optimised alpha, and the chord control point values.
