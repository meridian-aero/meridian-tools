Run the OpenAeroStruct MCP server locally for development.

## Steps

0. **Start provenance session** -- call `start_session(notes="$ARGUMENTS")` and save the returned `session_id`. If no arguments provided, use `notes="wing analysis sortie"`.

1. **Create the surface** -- call `create_surface` with the user's parameters (or defaults below).
   Use `wing_type="CRM"` for a realistic transport wing, `wing_type="rect"` for a clean rectangular wing.
   Default: `num_x=2, num_y=7, symmetry=True, with_viscous=True, CD0=0.015`.

2. **Single-point analysis** -- call `run_aero_analysis` at the target condition.
   Default cruise: `velocity=248.136, alpha=5.0, Mach_number=0.84, density=0.38`.

3. **Interpret the summary** -- read `envelope.summary.narrative` and check `validation.passed`.
   Note any flags in `summary.flags` (e.g. `tip_loaded`, `induced_drag_dominant`).
   Call `log_decision(decision_type="result_interpretation", reasoning="<your interpretation>", selected_action="<next step>", prior_call_id=<run_aero call_id>)`.

4. **Visualize lift distribution** -- call `visualize(run_id, "lift_distribution", output="file")` to see
   the spanwise Cl distribution. Use `output="file"` for CLI environments.

5. **Drag polar** -- call `compute_drag_polar` with `alpha_start=-5.0, alpha_end=15.0, num_alpha=21`
   to map out the full polar and find the alpha that gives the target CL.
   Check `results.best_L_over_D` for the optimum operating point.
   Call `log_decision(decision_type="result_interpretation", reasoning="<polar interpretation>", selected_action="<operating point>", prior_call_id=<drag polar call_id>)`.

6. **Report results** -- summarize:
   - Operating point: CL, CD, L/D at cruise alpha
   - Best L/D point: alpha, CL, L/D
   - Lift distribution balance (from summary.derived_metrics)
   - Drag breakdown: CDi%, CDv%, CDw% (from summary.derived_metrics.drag_breakdown_pct)
   - Any validation warnings

7. **Export provenance** -- call `export_session_graph(session_id=<session_id>)` to capture the
   full decision audit trail.

## Defaults (use if not specified by user)
- `wing_type`: "CRM"
- `span`: default (CRM standard)
- `alpha`: 5.0 deg
- `Mach_number`: 0.84
- `density`: 0.38 kg/m3
- Target `CL`: 0.5

## Example invocation
"Analyze a CRM wing at Mach 0.84 and find the operating point for CL=0.5."
