# Drag Polar

Compute a viscous drag polar for a rectangular wing by sweeping angle of attack.

## Parameters

- **Wing**: rectangular, span = 10 m, chord = 1 m, no twist
- **Mesh**: 11 chordwise x 35 spanwise nodes, symmetry = true, span_cos_spacing = 1.0, chord_cos_spacing = 1.0
- **Flight**: Mach = 0.84, V = 248.136 m/s, rho = 0.38 kg/m^3, Re = 1e6 /m
- **Sweep**: alpha from -10 deg to 10 deg, 20 points
- **Surface**: S_ref_type = "projected", CL0 = 0.0, CD0 = 0.0, t_over_c_cp = [0.12], with_viscous = true, with_wave = false

## Expected MCP Tool Calls

1. `create_surface(name="wing", wing_type="rect", num_x=11, num_y=35, span=10, root_chord=1, symmetry=true, S_ref_type="projected", twist_cp=[0,0,0], t_over_c_cp=[0.12], CL0=0, CD0=0, with_viscous=true, with_wave=false)`
2. `compute_drag_polar(surfaces=["wing"], alpha_start=-10, alpha_end=10, num_alpha=20, velocity=248.136, Mach_number=0.84, reynolds_number=1e6, density=0.38)`

## Expected Output

Arrays of alpha, CL, CD. The drag polar should show a parabolic shape with minimum CD at an interior alpha value. Report the best L/D and the alpha at which it occurs.
