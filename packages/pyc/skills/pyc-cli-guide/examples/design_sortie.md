# Example: Design Point Analysis

## Interactive mode (Python)

```python
call("create_engine", archetype="turbojet", name="tj1",
     comp_PR=13.5, comp_eff=0.83, turb_eff=0.86)

dp = call("run_design_point", engine_name="tj1", alt=0, MN=0.000001,
          Fn_target=11800, T4_target=2370)
perf = dp["results"]["performance"]
print(f"Fn   = {perf['Fn']:.1f} lbf")
print(f"TSFC = {perf['TSFC']:.4f} lbm/hr/lbf")
print(f"OPR  = {perf['OPR']:.2f}")

viz = call("visualize", run_id="latest", plot_type="station_properties",
           output="file")
print(viz[0]["file_path"])
```

## One-shot mode (bash)

```bash
pyc-cli create-engine --archetype turbojet --name tj1 \
        --comp-PR 13.5 --comp-eff 0.83 --turb-eff 0.86

pyc-cli --pretty run-design-point --engine-name tj1 \
        --alt 0 --MN 0.000001 --Fn-target 11800 --T4-target 2370

pyc-cli plot latest station_properties
pyc-cli plot latest ts_diagram
pyc-cli plot latest performance_summary
```

## Script mode (JSON)

```json
[
  {"tool": "start_session", "args": {"notes": "SLS turbojet design point"}},
  {"tool": "create_engine", "args": {
    "archetype": "turbojet", "name": "tj1",
    "comp_PR": 13.5, "comp_eff": 0.83, "turb_eff": 0.86
  }},
  {"tool": "log_decision", "args": {
    "decision_type": "archetype_selection",
    "reasoning": "Single-spool turbojet; PR=13.5/eff=0.83 typical for this class",
    "selected_action": "turbojet with standard parameters"
  }},
  {"tool": "run_design_point", "args": {
    "engine_name": "tj1", "alt": 0, "MN": 0.000001,
    "Fn_target": 11800, "T4_target": 2370
  }},
  {"tool": "visualize", "args": {
    "run_id": "$prev.run_id", "plot_type": "ts_diagram", "output": "file"
  }},
  {"tool": "visualize", "args": {
    "run_id": "$3.run_id", "plot_type": "performance_summary", "output": "file"
  }},
  {"tool": "export_session_graph", "args": {}}
]
```

```bash
pyc-cli --pretty run-script design_workflow.json
```

## Cruise design point

For a cruise-designed engine instead of SLS:

```bash
pyc-cli create-engine --archetype turbojet --name cruise_tj
pyc-cli run-design-point --engine-name cruise_tj \
        --alt 35000 --MN 0.8 --Fn-target 5000 --T4-target 2500
```

## Thermo method selection

TABULAR is the default and ~10x faster. Use CEA for higher fidelity:

```bash
pyc-cli create-engine --archetype turbojet --name tj_cea \
        --thermo-method CEA --comp-PR 13.5
```
