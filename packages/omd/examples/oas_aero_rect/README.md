# OAS Rectangular Wing: Aero-Only

VLM aerodynamic analysis and twist optimization of a rectangular wing.

Two analyses:
1. **Aero analysis** -- single-point CL/CD at alpha=5 deg
2. **Twist optimization** -- minimize CD with CL=0.5 constraint

## Lane A: Direct OpenAeroStruct

```bash
uv run python packages/omd/examples/oas_aero_rect/lane_a/aero_analysis.py
uv run python packages/omd/examples/oas_aero_rect/lane_a/twist_optimization.py
```

## Lane B: omd Plan Pipeline

```bash
# Analysis
uv run omd-cli assemble packages/omd/examples/oas_aero_rect/lane_b/aero_analysis/
uv run omd-cli run packages/omd/examples/oas_aero_rect/lane_b/aero_analysis/plan.yaml --mode analysis

# Optimization
uv run omd-cli assemble packages/omd/examples/oas_aero_rect/lane_b/twist_optimization/
uv run omd-cli run packages/omd/examples/oas_aero_rect/lane_b/twist_optimization/plan.yaml --mode optimize
```

## Lane C: Agent Prompt

```bash
claude
# Paste lane_c/all.prompt.md
```
