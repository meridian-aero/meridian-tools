---
name: omd-cli-guide
description: >
  How to run MDAO analyses using the omd-cli command-line tool. Use this skill
  whenever the user asks you to assemble a plan, run an analysis or optimization,
  query results, view provenance, or export a standalone script via omd.
---

# omd CLI Guide

omd materializes YAML analysis plans into OpenMDAO problems, runs them, and
records results with PROV-Agent provenance tracking.

## Prerequisites

```bash
uv sync
uv run omd-cli --help
```

## Commands Overview

| Command | Purpose |
|---------|---------|
| `omd-cli assemble <plan_dir>` | Merge modular YAML files into canonical plan.yaml |
| `omd-cli validate <plan.yaml>` | Check plan against JSON Schema |
| `omd-cli run <plan.yaml>` | Materialize and execute (analysis or optimize) |
| `omd-cli results <run_id>` | Query results from analysis DB |
| `omd-cli export <plan.yaml>` | Generate standalone Python script |
| `omd-cli provenance <plan_id>` | View provenance timeline or DAG |

## Plan Directory Structure

```
my-plan/
  metadata.yaml              # id, name (version auto-set)
  components/
    wing.yaml                 # id, type, config
  operating_points.yaml       # flight conditions
  solvers.yaml                # nonlinear + linear solver config (optional)
  optimization.yaml           # DVs, constraints, objective, optimizer (optional)
```

## Component Types

| Type | Description |
|------|-------------|
| `paraboloid/Paraboloid` | Trivial test component: f(x,y) |
| `oas/AeroPoint` | OAS aero-only VLM analysis |
| `oas/AerostructPoint` | OAS coupled aero+struct analysis |

## Quick Start

```bash
# 1. Create a plan directory with YAML files
# 2. Assemble
omd-cli assemble my-plan/

# 3. Run
omd-cli run my-plan/plan.yaml --mode analysis

# 4. View results
omd-cli results <run_id> --summary

# 5. Check provenance
omd-cli provenance <plan_id> --format text
```

## Data Artifacts

All runtime data is stored in `hangar_data/omd/`:
- `analysis.db` -- SQLite provenance + run case database
- `plans/{plan-id}/v{N}.yaml` -- assembled plan versions
- `recordings/{run-id}.sql` -- OpenMDAO recorder output files

See `commands.md` for full parameter reference and `examples/` for workflows.
