# omd Examples: Three-Lane Comparison

Each example runs the same analysis three different ways:

| Lane | Approach | Files |
|------|----------|-------|
| **Lane A** | Direct OpenMDAO/OAS scripts (importable `run()` functions) | `lane_a/*.py` |
| **Lane B** | omd plan YAML + `omd-cli` | `lane_b/*/` plan directories |
| **Lane C** | Claude Code agent prompts | `lane_c/*.prompt.md` |

## Examples

| Problem | Type | Description |
|---------|------|-------------|
| `paraboloid/` | Smoke test | Trivial `f(x,y)` analysis + optimization |
| `oas_aero_rect/` | Aero-only | Rectangular wing VLM analysis + twist optimization |
| `oas_aerostruct_rect/` | Coupled | Aerostructural analysis + mass optimization |

## Prerequisites

```bash
cd /path/to/the-hangar
uv sync
uv run omd-cli --help
```

## Quick Start

```bash
# Lane A: direct script
uv run python packages/omd/examples/paraboloid/lane_a/analysis.py

# Lane B: omd plan pipeline
uv run omd-cli assemble packages/omd/examples/paraboloid/lane_b/analysis/
uv run omd-cli run packages/omd/examples/paraboloid/lane_b/analysis/plan.yaml --mode analysis

# Lane C: paste prompt into Claude Code
claude
# Then paste the contents of lane_c/analysis.prompt.md
```

## Data Artifacts

All omd runtime data is stored in `hangar_data/omd/`:
- `analysis.db` -- provenance and run case data (SQLite)
- `plans/{plan-id}/v{N}.yaml` -- assembled plan versions
- `recordings/{run-id}.sql` -- OpenMDAO recorder output (inspectable with CaseReader)

## Verification Tests

```bash
uv run pytest packages/omd/examples/tests/ -v
```
