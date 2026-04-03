# Paraboloid Workflow

Step-by-step paraboloid analysis and optimization via omd-cli.

## Analysis

```bash
# Assemble the plan
omd-cli assemble packages/omd/examples/paraboloid/lane_b/analysis/

# Run analysis
omd-cli run packages/omd/examples/paraboloid/lane_b/analysis/plan.yaml --mode analysis

# View results (use run_id from output above)
omd-cli results <run_id> --summary

# Check provenance
omd-cli provenance ex-paraboloid-analysis --format text
```

Expected: `f_xy = 39.0`

## Optimization

```bash
omd-cli assemble packages/omd/examples/paraboloid/lane_b/optimization/
omd-cli run packages/omd/examples/paraboloid/lane_b/optimization/plan.yaml --mode optimize
omd-cli results <run_id> --summary
```

Expected: `x ~ 6.667, y ~ -7.333, f_xy ~ -27.333`

## Export

```bash
omd-cli export packages/omd/examples/paraboloid/lane_b/analysis/plan.yaml --output /tmp/paraboloid.py
python /tmp/paraboloid.py
```
