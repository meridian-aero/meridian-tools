# Paraboloid: Full Workflow

Run both paraboloid examples (analysis and optimization) using `omd-cli`,
then verify the results match expected values.

## Analysis

1. Assemble: `omd-cli assemble packages/omd/examples/paraboloid/lane_b/analysis/`
2. Run: `omd-cli run packages/omd/examples/paraboloid/lane_b/analysis/plan.yaml --mode analysis`
3. Results: `omd-cli results <run_id> --summary`
4. Expected: f_xy = 39.0

## Optimization

1. Assemble: `omd-cli assemble packages/omd/examples/paraboloid/lane_b/optimization/`
2. Run: `omd-cli run packages/omd/examples/paraboloid/lane_b/optimization/plan.yaml --mode optimize`
3. Results: `omd-cli results <run_id> --summary`
4. Expected: x ~ 6.667, y ~ -7.333, f_xy ~ -27.333

## Verification

After both runs, check provenance for each plan:
```
omd-cli provenance ex-paraboloid-analysis --format text
omd-cli provenance ex-paraboloid-opt --format text
```

Report a summary table with: analysis f_xy, optimization x/y/f_xy, and
whether the provenance chains are complete.
