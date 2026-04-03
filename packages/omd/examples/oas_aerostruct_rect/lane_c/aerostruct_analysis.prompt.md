# OAS Rectangular Wing: Aerostructural Analysis

Run a coupled aero+struct analysis of a rectangular wing using `omd-cli`.

## Parameters

- Wing: rectangular, span=10m, chord=1m, num_y=7, tube FEM
- Material: aluminum (E=70 GPa, G=30 GPa, yield=500 MPa, rho=3000 kg/m^3)
- thickness_cp: [0.01, 0.02, 0.01] m
- Flight: velocity=248.136 m/s, alpha=5 deg, Mach=0.84
- Solvers: Newton (coupled) + DirectSolver (linear)

## Steps

1. Assemble:
   ```
   omd-cli assemble packages/omd/examples/oas_aerostruct_rect/lane_b/aerostruct_analysis/
   ```

2. Run:
   ```
   omd-cli run .../plan.yaml --mode analysis
   ```

3. Results:
   ```
   omd-cli results <run_id> --summary
   ```

## Expected Output

- CL > 0, CD > 0
- structural_mass > 0
- Failure index < 0 (structure is safe)
- Provenance chain recorded
