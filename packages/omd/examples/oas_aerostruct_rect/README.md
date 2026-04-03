# OAS Rectangular Wing: Aerostructural

Coupled VLM + beam FEM analysis and optimization.

Two analyses:
1. **Aerostruct analysis** -- single-point coupled analysis
2. **Aerostruct optimization** -- minimize structural mass with twist + thickness DVs

## Lane A: Direct OpenAeroStruct

```bash
uv run python packages/omd/examples/oas_aerostruct_rect/lane_a/aerostruct_analysis.py
```

## Lane B: omd Plan Pipeline

```bash
uv run omd-cli assemble packages/omd/examples/oas_aerostruct_rect/lane_b/aerostruct_analysis/
uv run omd-cli run .../plan.yaml --mode analysis
```

## Lane C: Agent Prompt

```bash
claude
# Paste lane_c/all.prompt.md
```
