# Provenance -- Recording Decisions and Tracing Workflows

The CLI has built-in provenance recording: every tool call is automatically
logged to a SQLite database. Three additional tools let you group calls into
named sessions, record reasoning, and export the full DAG.

## When to use provenance

**Always** call `start_session` at the beginning of a multi-step workflow in
interactive or script mode. Use `log_decision` before major choices (archetype
selection, parameter tuning, interpreting surprising results). Call
`export_session_graph` at the end to save the audit trail.

## The three provenance tools

| Tool | Purpose |
|------|---------|
| `start_session` | Begin a named session -- groups all subsequent calls |
| `log_decision` | Record why a choice was made (archetype, parameters, etc.) |
| `export_session_graph` | Export the session DAG as JSON |

## Decision types

Use these standard `decision_type` values with `log_decision`:

| `decision_type` | When to use |
|-----------------|-------------|
| `archetype_selection` | Choosing an engine archetype and why |
| `parameter_choice` | Choosing component parameters (PR, efficiency, etc.) |
| `result_interpretation` | Explaining what a result means and next steps |
| `convergence_assessment` | Assessing solver convergence quality |

## Required decision points

Agents MUST call `log_decision` at each of these points during a workflow:

| After this step | `decision_type` | `prior_call_id`? |
|-----------------|-----------------|------------------|
| `create_engine` | `archetype_selection` | No |
| `run_design_point` | `result_interpretation` | Yes -- from `_provenance.call_id` |
| `run_off_design` | `result_interpretation` | Yes -- from `_provenance.call_id` |

## Chaining prior_call_id

Every successful tool call returns a `_provenance` field in its result dict:

```json
{"ok": true, "result": {"run_id": "...", ..., "_provenance": {"call_id": "uuid-...", "session_id": "sess-..."}}}
```

Pass this `call_id` as `prior_call_id` in `log_decision` to create a causal
link between the analysis result and your decision. This makes the provenance
graph show *which result informed which decision*.

## Interactive mode example (Python)

```python
sess = call("start_session", notes="Turbojet sizing study")

call("create_engine", archetype="turbojet", name="tj1",
     comp_PR=13.5, comp_eff=0.83, turb_eff=0.86)

call("log_decision",
     decision_type="archetype_selection",
     reasoning="Single-spool turbojet for simplicity; PR=13.5, eff=0.83/0.86 typical",
     selected_action="turbojet with default parameters")

dp = call("run_design_point", engine_name="tj1", alt=0, MN=0.000001,
          Fn_target=11800, T4_target=2370)

call("log_decision",
     decision_type="result_interpretation",
     reasoning=f"TSFC={dp['results']['performance']['TSFC']:.4f} -- reasonable for turbojet",
     selected_action="proceed to off-design evaluation",
     prior_call_id=dp["_provenance"]["call_id"])

graph = call("export_session_graph")
```

## Script mode with provenance

```json
[
  {"tool": "start_session", "args": {"notes": "Turbojet design and off-design"}},
  {"tool": "create_engine", "args": {
    "archetype": "turbojet", "name": "tj1",
    "comp_PR": 13.5, "comp_eff": 0.83, "turb_eff": 0.86
  }},
  {"tool": "log_decision", "args": {
    "decision_type": "archetype_selection",
    "reasoning": "Turbojet for simple single-spool analysis",
    "selected_action": "turbojet, PR=13.5"
  }},
  {"tool": "run_design_point", "args": {
    "engine_name": "tj1", "alt": 0, "MN": 0.000001,
    "Fn_target": 11800, "T4_target": 2370
  }},
  {"tool": "run_off_design", "args": {
    "engine_name": "tj1", "alt": 35000, "MN": 0.8, "Fn_target": 5000
  }},
  {"tool": "export_session_graph", "args": {}}
]
```

Note: in script mode you cannot pass `prior_call_id` referencing a previous
step's `_provenance.call_id` because there's no interpolation for nested
fields. The automatic call recording still captures the full sequence; explicit
`prior_call_id` links are only possible in interactive mode (Python) where you
can extract the value from the response dict.

## Cross-tool provenance

pyCycle supports cross-tool workflows with OAS (and other hangar tools). Use
`link_cross_tool_result` to document data handoffs:

```python
# After getting thrust from pyCycle, pass it to OAS for aero analysis
call("link_cross_tool_result",
     source_call_id=pyc_result["_provenance"]["call_id"],
     source_tool="pyc",
     target_tool="oas",
     variables={"Fn": 11800},
     notes="Design thrust used for wing sizing")
```

To share a provenance session between tools, pass the same `session_id` to
both `start_session` calls (one on each tool server).

## One-shot mode limitation

Each one-shot invocation is a separate process, so `start_session` in one call
does not carry over to the next. All calls are still recorded in the provenance
DB under session `"default"`, but they won't be grouped into a named session.
**Use interactive or script mode for provenance-tracked workflows.**

## Viewing the provenance graph

- **CLI**: `pyc-cli viewer` starts the viewer server on localhost:7654
- **Browser**: Open `http://localhost:7654/viewer?session_id=<id>`
- **Offline**: Open the viewer HTML and drop the exported JSON file onto the page
