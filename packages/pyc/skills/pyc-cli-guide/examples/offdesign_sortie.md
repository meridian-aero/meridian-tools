# Example: Off-Design Analysis

Off-design analysis evaluates the engine at flight conditions different from
the design point. The engine geometry (areas, map scalars) is frozen from the
design point; the solver adjusts FAR, shaft speed, and mass flow to match the
new thrust target.

## Interactive mode (Python)

```python
# 1. Create and size the engine at SLS design point
call("create_engine", archetype="turbojet", name="tj1",
     comp_PR=13.5, comp_eff=0.83, turb_eff=0.86)
dp = call("run_design_point", engine_name="tj1", alt=0, MN=0.000001,
          Fn_target=11800, T4_target=2370)

# 2. Evaluate at altitude
od = call("run_off_design", engine_name="tj1", alt=5000, MN=0.2,
          Fn_target=8000)
perf = od["results"]["performance"]
design = od["results"]["design_point"]
print(f"Off-design TSFC: {perf['TSFC']:.4f} (design: {design['TSFC']:.4f})")

# 3. Visualize the comparison
viz = call("visualize", run_id="latest", plot_type="design_vs_offdesign",
           output="file")
print(viz[0]["file_path"])
```

## One-shot mode (bash)

```bash
# Create and size
pyc-cli create-engine --archetype turbojet --name tj1 \
        --comp-PR 13.5 --comp-eff 0.83 --turb-eff 0.86
pyc-cli run-design-point --engine-name tj1 \
        --alt 0 --MN 0.000001 --Fn-target 11800 --T4-target 2370

# Off-design
pyc-cli --pretty run-off-design --engine-name tj1 \
        --alt 5000 --MN 0.2 --Fn-target 8000

# Plots
pyc-cli plot latest design_vs_offdesign
pyc-cli plot latest station_properties
```

## Script mode -- multi-point study

Evaluate the same engine at several off-design conditions in a single script:

```json
[
  {"tool": "start_session", "args": {"notes": "Multi-point off-design study"}},
  {"tool": "create_engine", "args": {
    "archetype": "turbojet", "name": "tj1",
    "comp_PR": 13.5, "comp_eff": 0.83, "turb_eff": 0.86
  }},
  {"tool": "run_design_point", "args": {
    "engine_name": "tj1", "alt": 0, "MN": 0.000001,
    "Fn_target": 11800, "T4_target": 2370,
    "run_name": "SLS_design"
  }},
  {"tool": "run_off_design", "args": {
    "engine_name": "tj1", "alt": 5000, "MN": 0.2, "Fn_target": 8000,
    "run_name": "OD_5k_M02"
  }},
  {"tool": "visualize", "args": {
    "run_id": "$prev.run_id", "plot_type": "design_vs_offdesign", "output": "file"
  }},
  {"tool": "run_off_design", "args": {
    "engine_name": "tj1", "alt": 35000, "MN": 0.8, "Fn_target": 3000,
    "run_name": "OD_35k_M08"
  }},
  {"tool": "visualize", "args": {
    "run_id": "$prev.run_id", "plot_type": "design_vs_offdesign", "output": "file"
  }},
  {"tool": "export_session_graph", "args": {}}
]
```

```bash
pyc-cli --pretty run-script multipoint_study.json --save-to multipoint_results.json
```

## Extracting run_id in bash for chaining

```bash
RUN_ID=$(pyc-cli run-off-design --engine-name tj1 \
         --alt 5000 --MN 0.2 --Fn-target 8000 \
         | python -c "import sys,json; print(json.load(sys.stdin)['result']['run_id'])")

pyc-cli visualize --run-id "$RUN_ID" --plot-type design_vs_offdesign --output file
```

## Key differences: design vs off-design

| Aspect | Design point | Off-design |
|--------|-------------|------------|
| Geometry | Sized by solver | Fixed from design |
| Solver adjusts | W (mass flow), FAR, turb PR | FAR, Nmech, W |
| You specify | Fn_target, T4_target | Fn_target only |
| Results include | performance, flow_stations, components | Same + design_point reference |
| Visualization | 4 plot types | 5 plot types (adds design_vs_offdesign) |
