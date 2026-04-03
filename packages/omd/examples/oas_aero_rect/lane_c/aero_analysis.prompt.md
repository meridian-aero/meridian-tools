# OAS Rectangular Wing: Aero Analysis

Run a VLM aerodynamic analysis of a rectangular wing using `omd-cli`.

## Parameters

- Wing: rectangular, span=10m, chord=1m, num_y=7, symmetry=true
- Flight: velocity=248.136 m/s, alpha=5 deg, Mach=0.84, Re=1e6, rho=0.38
- with_viscous=true, CD0=0.015

## Steps

1. Assemble the plan:
   ```
   omd-cli assemble packages/omd/examples/oas_aero_rect/lane_b/aero_analysis/
   ```

2. Run the analysis:
   ```
   omd-cli run packages/omd/examples/oas_aero_rect/lane_b/aero_analysis/plan.yaml --mode analysis
   ```

3. Query results:
   ```
   omd-cli results <run_id> --summary
   ```

## Expected Output

- CL > 0 (should be in range 0.3-0.8 for a flat wing at alpha=5)
- CD > 0
- L/D > 1
