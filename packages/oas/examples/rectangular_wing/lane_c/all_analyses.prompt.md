# Run All Four Rectangular Wing Analyses

Using the OAS MCP tools, run these four analyses on a rectangular wing. Reset between each analysis. Report CL, CD for each and compare results across all four.

Use these common parameters for all analyses:
- Wing: rectangular, span = 10 m, chord = 1 m
- Mesh: 11 chordwise x 35 spanwise nodes, symmetry = true, span_cos_spacing = 1.0, chord_cos_spacing = 1.0
- S_ref_type = "projected", CL0 = 0.0, CD0 = 0.0, c_max_t = 0.303

## Analysis 1: Single-Point Aero

- Flight: alpha = 5 deg, Mach = 0.0, V = 248.136 m/s, rho = 0.38, Re = 1e6
- Surface: with_viscous = false, with_wave = false, twist_cp = [0, 0, 0]
- Run: create_surface then run_aero_analysis

## Analysis 2: Drag Polar

- Flight: Mach = 0.84, V = 248.136 m/s, rho = 0.38, Re = 1e6
- Sweep alpha from -10 to 10 deg (20 points)
- Surface: with_viscous = true, with_wave = false, twist_cp = [0, 0, 0], t_over_c_cp = [0.12]
- Run: create_surface then compute_drag_polar

## Analysis 3: Twist Optimization

- Flight: alpha = 5 deg, Mach = 0.0, V = 248.136 m/s, rho = 0.38, Re = 1e6
- Surface: with_viscous = false, with_wave = false, twist_cp = [0, 0, 0]
- Design variable: twist, bounds [-10, 15]
- Constraint: CL = 0.5
- Objective: CD, scaler = 1e4
- Run: create_surface then run_optimization (aero)

## Analysis 4: Chord Optimization

- Flight: alpha = 5 deg (initial), Mach = 0.0, V = 248.136 m/s, rho = 0.38, Re = 1e6
- Surface: with_viscous = false, with_wave = false, chord_cp = [1, 1, 1]
- Design variables: chord bounds [0.001, 5], alpha bounds [-10, 15]
- Constraints: CL = 0.5, S_ref = 10.0
- Objective: CD, scaler = 1e4
- Run: create_surface then run_optimization (aero)

## Summary

After all four analyses, provide a comparison table showing CL, CD, and L/D for each.
