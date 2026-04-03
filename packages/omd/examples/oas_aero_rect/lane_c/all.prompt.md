# OAS Rectangular Wing: Full Aero Workflow

Run aero analysis and twist optimization, then compare results.

## Analysis

1. `omd-cli assemble packages/omd/examples/oas_aero_rect/lane_b/aero_analysis/`
2. `omd-cli run .../plan.yaml --mode analysis`
3. `omd-cli results <run_id> --summary`

## Optimization

1. `omd-cli assemble packages/omd/examples/oas_aero_rect/lane_b/twist_optimization/`
2. `omd-cli run .../plan.yaml --mode optimize`
3. `omd-cli results <run_id> --summary`

## Report

Compare baseline CD vs optimized CD. The optimization should reduce drag
while maintaining CL = 0.5. Report CL, CD, L/D for both cases.
