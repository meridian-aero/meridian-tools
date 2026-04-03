# Paraboloid Analysis

Run a paraboloid analysis using `omd-cli`. The function is:

    f(x, y) = (x - 3)^2 + x*y + (y + 4)^2 - 3

## Parameters

- x = 1.0
- y = 2.0

## Steps

1. Assemble the plan:
   ```
   omd-cli assemble packages/omd/examples/paraboloid/lane_b/analysis/
   ```

2. Run the analysis:
   ```
   omd-cli run packages/omd/examples/paraboloid/lane_b/analysis/plan.yaml --mode analysis
   ```

3. Query the results (use the run_id from step 2):
   ```
   omd-cli results <run_id> --summary
   ```

4. View the provenance:
   ```
   omd-cli provenance ex-paraboloid-analysis --format text
   ```

## Expected Output

- f_xy = 39.0 (exact)
- Provenance shows: plan entity -> execute activity -> run record
