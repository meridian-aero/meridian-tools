# OAS Rectangular Wing: Twist Optimization

Optimize twist distribution to minimize drag at a target CL using `omd-cli`.

## Parameters

- Same wing and flight conditions as the aero analysis
- Design variable: twist_cp, bounds [-10, 15] deg
- Constraint: CL = 0.5
- Objective: minimize CD (scaler=10000)
- Optimizer: SLSQP, maxiter=100

## Steps

1. Assemble:
   ```
   omd-cli assemble packages/omd/examples/oas_aero_rect/lane_b/twist_optimization/
   ```

2. Run optimization:
   ```
   omd-cli run packages/omd/examples/oas_aero_rect/lane_b/twist_optimization/plan.yaml --mode optimize
   ```

3. Query results:
   ```
   omd-cli results <run_id> --summary
   ```

## Expected Output

- Status: converged
- CL ~ 0.5 (constraint satisfied)
- CD should decrease from baseline analysis
