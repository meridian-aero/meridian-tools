# Paraboloid Optimization

Optimize the paraboloid function using `omd-cli`:

    f(x, y) = (x - 3)^2 + x*y + (y + 4)^2 - 3

Minimize f subject to -50 <= x, y <= 50.

## Steps

1. Assemble the optimization plan:
   ```
   omd-cli assemble packages/omd/examples/paraboloid/lane_b/optimization/
   ```

2. Run the optimization:
   ```
   omd-cli run packages/omd/examples/paraboloid/lane_b/optimization/plan.yaml --mode optimize
   ```

3. Query the results:
   ```
   omd-cli results <run_id> --summary
   ```

## Expected Output

- x ~ 6.667 (= 20/3)
- y ~ -7.333 (= -22/3)
- f_xy ~ -27.333 (= -82/3)
- Status: converged
