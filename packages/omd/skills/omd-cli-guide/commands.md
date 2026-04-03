# omd-cli Command Reference

## assemble

Merge modular YAML files from a plan directory into a canonical `plan.yaml`.

```bash
omd-cli assemble <plan_dir> [--output PATH]
```

**Arguments:**
- `plan_dir` -- path to directory containing modular YAML files

**Options:**
- `--output`, `-o` -- output path for assembled plan (default: `<plan_dir>/plan.yaml`)

**Behavior:**
- Reads metadata.yaml, requirements.yaml, operating_points.yaml, solvers.yaml, optimization.yaml, decisions.yaml
- Collects all `*.yaml` files from `components/` subdirectory
- Validates against the plan JSON Schema
- Computes SHA256 content hash
- Auto-increments version number from `history/` directory
- Writes `plan.yaml` + `history/vN.yaml` + copy to `hangar_data/omd/plans/{plan-id}/vN.yaml`

## validate

Check an assembled plan against the JSON Schema.

```bash
omd-cli validate <plan_path>
```

Returns structured error messages with field paths if invalid.

## run

Materialize an OpenMDAO problem from a plan and execute it.

```bash
omd-cli run <plan_path> --mode analysis|optimize [--recording-level LEVEL] [--db PATH]
```

**Options:**
- `--mode` -- `analysis` (run_model) or `optimize` (run_driver). Default: analysis.
- `--recording-level` -- `minimal`, `driver`, `solver`, or `full`. Default: driver.
- `--db` -- path to analysis DB. Default: `hangar_data/omd/analysis.db`.

**Output:**
```
Run complete: run-20260403T130457-6f5287cc
  Status: completed
  CL: 0.452177
  CD: 0.035087
  L/D: 12.89
  Recording: 1 cases, 76.0 KB
```

**Recording levels:**
- `minimal` -- final values only (smallest storage)
- `driver` -- DVs + objective + constraints per optimizer iteration (default)
- `solver` -- above + nonlinear solver iterations
- `full` -- everything including residuals (largest)

## results

Query results for a completed run.

```bash
omd-cli results <run_id> [--summary] [--variables v1,v2,...] [--db PATH]
```

**Options:**
- `--summary` -- return only the final case with condensed output
- `--variables`, `-v` -- filter to specific variable names
- `--db` -- path to analysis DB

## export

Generate a standalone Python script from a plan.

```bash
omd-cli export <plan_path> --output <script.py>
```

The script uses only openmdao/openaerostruct imports (no hangar dependency).
Useful for sharing, archiving, or debugging.

## provenance

View the provenance chain for a plan.

```bash
omd-cli provenance <plan_id> [--format text|html|json] [--diff V1 V2] [--output PATH] [--db PATH]
```

**Options:**
- `--format` -- `text` (timeline), `html` (Cytoscape.js DAG), or `json` (raw data)
- `--diff V1 V2` -- compare two plan versions
- `--output`, `-o` -- output file path (required for html format)

**Example output (text):**
```
Provenance timeline for: plan-paraboloid-analysis
============================================================
  [2026-04-03T13:04:57] plan v1 (plan-paraboloid-analysis/v1) by have-agent
  [2026-04-03T13:04:57] EXECUTE (act-execute-run-...) by omd -- completed
  [2026-04-03T13:04:58] run_record (run-...) by omd

Edges:
  run-... --wasGeneratedBy--> act-execute-run-...
  act-execute-run-... --used--> plan-paraboloid-analysis/v1
```
