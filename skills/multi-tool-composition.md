# Multi-Tool Composition

How to compose multiple Hangar MCP tool servers into integrated analysis
workflows. Each tool server runs independently; the agent orchestrates
data flow between them.

## When to use

Use this skill when:
- An analysis requires results from multiple tool servers
- The user wants to chain aerodynamic, structural, propulsion, or other analyses
- A design study needs to combine metrics from different disciplines
- You need to pass outputs from one tool as inputs to another

## Architecture

Each Hangar tool server is an independent MCP server with its own:
- Session state (surfaces, cached problems)
- Provenance tracking (sessions, decisions)
- Artifact storage (run results)

Tools do not share state directly. The agent (Claude) is the integration
layer, reading results from one tool and passing them as inputs to another.

```
Agent (Claude)
  |
  +-- OAS server (aerostruct analysis)
  |     create_surface -> run_aerostruct_analysis -> results
  |
  +-- Propulsion server (engine sizing)  [future]
  |     set_thrust_requirement(drag_from_oas) -> engine_mass
  |
  +-- Mission server (range/endurance)   [future]
        compute_range(fuelburn, engine_sfc) -> range_nm
```

## Composition patterns

### Pattern 1: Sequential handoff

Run one tool, extract results, feed into the next.

```
1. OAS: run_aerostruct_analysis -> get CD, structural_mass, fuelburn
2. Extract: drag = CD * q * S_ref
3. Propulsion: size_engine(thrust_required=drag * safety_margin)
4. Mission: compute_range(fuel_available, sfc)
```

Key: clearly identify the interface variables and their units.

### Pattern 2: Iterative coupling

When tools have circular dependencies (e.g. drag depends on weight, weight
depends on engine size, engine size depends on drag):

```
1. Initialize: assume engine_weight = 5000 kg
2. OAS: run with W0 including engine_weight -> get drag, fuelburn
3. Propulsion: size engine for drag -> get new engine_weight
4. Check: has engine_weight converged? (|new - old| < tolerance)
5. If not, update W0 and go to step 2
6. If yes, record final converged state
```

Typically converges in 3--5 outer iterations for weight-drag coupling.

### Pattern 3: Parallel independent analyses

When tools provide independent metrics that are combined in a comparison:

```
1. OAS: compute drag polar -> aero metrics
2. Structures tool: detailed stress analysis -> structural metrics
3. Cost tool: manufacturing cost estimate -> cost metrics
4. Combine all metrics in a single comparison table
```

### Pattern 4: Sensitivity cascade

Vary a parameter in one tool and propagate the effect through others:

```
For each span in [25, 30, 35, 40] m:
  1. OAS: analyze wing at this span -> CD, mass
  2. Propulsion: size engine for CD -> engine_mass, sfc
  3. Mission: compute range -> range_nm
  Record: {span, CD, mass, engine_mass, range}
```

## Provenance across tools

Each tool server maintains its own provenance. For cross-tool studies:

1. Start a session in each tool server involved
2. Log cross-tool decisions in the primary tool's session:
   ```
   log_decision(
       decision_type="result_interpretation",
       reasoning="OAS drag result CD=0.032 used as thrust requirement for engine sizing",
       selected_action="Pass drag to propulsion tool"
   )
   ```
3. Export each tool's provenance graph separately
4. Reference run_ids from other tools in decision logs to create a cross-tool
   audit trail

## Interface variable conventions

When passing data between tools, use consistent units:

| Variable | Units | Source tool | Consumer tool |
|----------|-------|------------|---------------|
| CD, CL | dimensionless | OAS | mission analysis |
| drag force | N | OAS (CD * q * S) | propulsion |
| structural mass | kg | OAS | weight estimation |
| fuel burn | kg | OAS | mission analysis |
| thrust required | N | propulsion | OAS (via W0) |

## Adding a new tool to the composition

1. Create the tool package: `packages/<toolname>/`
2. Define the tool's MCP interface (inputs, outputs, units)
3. Document the interface variables in the tool's skills
4. Add integration test cases in `tests/integration/`
5. Update `docker/docker-compose.yml` to include the new service
6. See the `new-tool` command for the full scaffolding guide

## Current tool servers

| Server | Package | Status | Key outputs |
|--------|---------|--------|-------------|
| OAS | `hangar.oas` | Active | CL, CD, L/D, fuelburn, structural_mass |

Future tool servers will be added as additional packages under `packages/`.
