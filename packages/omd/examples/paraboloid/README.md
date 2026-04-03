# Paraboloid: Smoke Test

The classic OpenMDAO paraboloid: `f(x,y) = (x-3)^2 + x*y + (y+4)^2 - 3`

Two analyses:
1. **Analysis** -- evaluate f(1, 2) = 39.0
2. **Optimization** -- minimize f subject to -50 <= x,y <= 50; optimal at x=6.667, y=-7.333, f=-27.333

## Lane A: Direct OpenMDAO

```bash
uv run python packages/omd/examples/paraboloid/lane_a/analysis.py
uv run python packages/omd/examples/paraboloid/lane_a/optimization.py
```

## Lane B: omd Plan Pipeline

```bash
# Analysis
uv run omd-cli assemble packages/omd/examples/paraboloid/lane_b/analysis/
uv run omd-cli run packages/omd/examples/paraboloid/lane_b/analysis/plan.yaml --mode analysis
uv run omd-cli results <run_id> --summary

# Optimization
uv run omd-cli assemble packages/omd/examples/paraboloid/lane_b/optimization/
uv run omd-cli run packages/omd/examples/paraboloid/lane_b/optimization/plan.yaml --mode optimize
uv run omd-cli results <run_id> --summary
```

## Lane C: Agent Prompt

```bash
claude
# Paste the contents of lane_c/analysis.prompt.md or lane_c/all.prompt.md
```
