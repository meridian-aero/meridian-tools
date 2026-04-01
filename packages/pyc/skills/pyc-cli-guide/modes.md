# CLI Modes

`pyc-cli` supports three execution modes. All use the same tool registry and
response envelope format.

## Mode 1 -- Interactive (JSON-lines subprocess)

Spawn a single long-lived process. Write JSON commands to stdin, read JSON
responses from stdout -- one object per line.

```bash
pyc-cli interactive
```

### Protocol

Send one JSON object per line:

```json
{"tool": "create_engine", "args": {"archetype": "turbojet", "name": "tj1", "comp_PR": 13.5}}
```

Receive one JSON object per line:

```json
{"ok": true, "result": {"engine_name": "tj1", ...}}
```

### Python example

```python
import subprocess, json

proc = subprocess.Popen(
    ["pyc-cli", "interactive"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    text=True, bufsize=1,
)

def call(tool, **args):
    proc.stdin.write(json.dumps({"tool": tool, "args": args}) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())["result"]

# Workflow
call("start_session", notes="Turbojet design study")
call("create_engine", archetype="turbojet", name="tj1", comp_PR=13.5,
     comp_eff=0.83, turb_eff=0.86)
dp = call("run_design_point", engine_name="tj1", alt=0, MN=0.000001,
          Fn_target=11800, T4_target=2370)
print(f"TSFC = {dp['results']['performance']['TSFC']:.4f}")
print(f"Fn   = {dp['results']['performance']['Fn']:.1f} lbf")
```

### When to use

- Multi-step workflows where you need in-memory state (engine stays cached)
- Agent-driven analysis (Claude spawning pyc-cli as a subprocess)
- Fastest mode since the engine problem is built once and reused

### Special run_id values

- `"latest"` or `"last"` -- resolves to the most recent run_id in the session

## Mode 2 -- One-shot subcommands

Each invocation is a standalone process. Tool names use hyphens instead of
underscores: `create_engine` -> `pyc-cli create-engine`.

```bash
pyc-cli create-engine --archetype turbojet --name tj1 --comp-PR 13.5

pyc-cli --pretty run-design-point --engine-name tj1 --alt 0 --MN 0.000001 \
        --Fn-target 11800 --T4-target 2370
```

### State persistence

Engine definitions are persisted to `~/.hangar/state/<workspace>.json` so
that `run_design_point` in a subsequent invocation can find the engine created
by `create_engine`. The `--workspace` flag namespaces these state files.

**Important**: Since each invocation is a separate process, pyCycle must
rebuild the OpenMDAO problem each time. For off-design, this means the design
point is re-solved before the off-design evaluation. This is slower than
interactive mode but correct.

### When to use

- Quick one-off checks from the terminal
- Shell scripts and CI pipelines
- When you only need a single tool call

## Mode 3 -- Script / batch

Write a JSON array of tool calls and execute them in a single process with
shared in-memory state.

```json
[
  {"tool": "start_session", "args": {"notes": "Turbojet sizing study"}},
  {"tool": "create_engine", "args": {"archetype": "turbojet", "name": "tj1"}},
  {"tool": "run_design_point", "args": {
    "engine_name": "tj1", "alt": 0, "MN": 0.000001,
    "Fn_target": 11800, "T4_target": 2370
  }},
  {"tool": "run_off_design", "args": {
    "engine_name": "tj1", "alt": 35000, "MN": 0.8, "Fn_target": 5000
  }},
  {"tool": "visualize", "args": {
    "run_id": "$prev.run_id", "plot_type": "design_vs_offdesign", "output": "file"
  }},
  {"tool": "export_session_graph", "args": {}}
]
```

Run with:

```bash
pyc-cli --pretty run-script workflow.json
pyc-cli run-script workflow.json --save-to results.json
```

### Variable interpolation

- `$prev.run_id` -- run_id from the immediately preceding step
- `$1.run_id`, `$2.run_id` -- run_id from step 1, step 2 (1-indexed)

### When to use

- Reproducible workflows to share or re-run
- Multi-point studies (design + several off-design conditions)
- Batch execution with full provenance tracking
