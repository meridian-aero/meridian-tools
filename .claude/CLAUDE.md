# Hangar Workspace

## What this is
A monorepo for MCP servers that expose engineering analysis tools to AI agents.
Each tool gets its own package under `packages/`. Shared infrastructure lives
in `packages/sdk/`.

## Namespace convention
All packages use the `hangar.*` Python namespace (PEP 420 implicit namespace packages).
- `hangar.sdk` — shared provenance, response envelopes, validation, session management,
  artifacts, telemetry, auth, visualization, CLI framework
- `hangar.oas` — OpenAeroStruct aerostructural analysis server
- PyPI names use hyphens: `hangar-sdk`, `hangar-oas`
- **Critical:** never place an `__init__.py` in `src/hangar/` — only at the leaf
  level (e.g. `src/hangar/oas/__init__.py`). This is what makes the namespace work.

## Source layout
- `packages/sdk/` — hangar-sdk shared infrastructure:
  - `provenance/` — SQLite DB, `@capture_tool` decorator, session graph export
  - `envelope/` — versioned response envelopes (`make_envelope`, `make_error_envelope`)
  - `session/` — session state management (surfaces, caching, pinning)
  - `validation/` — `ValidationFinding` framework + user requirements assertions
  - `artifacts/` — filesystem-backed artifact store for analysis runs
  - `telemetry/` — structured logging with per-run log capture
  - `auth/` — OIDC JWT authentication for MCP servers
  - `viz/` — plotting (matplotlib), widget (Plotly), viewer (Cytoscape.js DAG)
  - `cli/` — generic 3-mode CLI framework (interactive, one-shot, script)
  - `errors.py` — typed error taxonomy (`HangarError`, `UserInputError`, etc.)
  - `state.py` — module-level singletons (`sessions`, `artifacts`)
  - `helpers.py` — shared utilities (`_resolve_run_id`, `_suppress_output`, etc.)

- `packages/oas/` — hangar-oas OpenAeroStruct server:
  - `server.py` — FastMCP entry point, tool registration
  - `config/defaults.py` — flight conditions, mesh, material property defaults
  - `mesh.py` — mesh generation and geometric transforms (sweep, dihedral, taper)
  - `builders.py` — OpenMDAO problem assembly
  - `connections.py` — OpenMDAO connect helpers
  - `results.py` — result extraction from solved problems
  - `summary.py` — physics interpretation and narratives
  - `convergence.py` — optimization iteration tracking
  - `validators.py` — input validation (mesh, flight conditions, DVs)
  - `validation.py` — OAS-specific physics/numerics checks
  - `cli.py` — OAS CLI registry builder
  - `tools/geometry.py` — `create_surface`
  - `tools/analysis.py` — `run_aero_analysis`, `run_aerostruct_analysis`, `compute_drag_polar`, `compute_stability_derivatives`
  - `tools/optimization.py` — `run_optimization`
  - `tools/session.py` — provenance, session, artifact, and observability tools
  - `tools/resources.py` — MCP resources (reference guide, dashboard widget)
  - `tools/prompts.py` — MCP prompts (guided workflows)

- `skills/` — cross-tool process skills (design study, trade study, convergence, multi-tool)
- `upstream/` — local clones of upstream tool repos (read-only reference, git-ignored)

## When implementing or modifying OAS tools
Always read the relevant upstream source before writing tool code.
If `upstream/OpenAeroStruct` exists, the OAS source is there.
Otherwise, it's in the venv at `.venv/lib/python3.11/site-packages/openaerostruct/`.

Key OAS entry points:
- `openaerostruct/aerostruct_groups/` — problem setup classes
- `openaerostruct/functionals/` — objective/constraint functions
- `openaerostruct/structures/` — structural analysis components
- `openaerostruct/aerodynamics/` — VLM and aero components

## When implementing SDK infrastructure
- `@capture_tool` decorator in `provenance/middleware.py` — auto-records every tool call
- `make_envelope()` in `envelope/response.py` — wraps tool results in versioned schema
- `ValidationFinding` in `validation/checks.py` — self-contained check framework
  (intentionally decoupled from provenance/session for future range-safety extraction)
- `ArtifactStore` in `artifacts/store.py` — JSON artifact persistence
- `SessionManager` in `session/manager.py` — in-memory state + caching

## Known OAS failure modes (critical context)
- OAS silently ignores unrecognized design variable names — always validate
  DV names against the known set before optimization
- load_factor has a caching bug — always set it explicitly per analysis
- OAS cannot model TTBW strut load relief — do not attempt strut-braced
  wing studies without documenting this limitation
- Optimizer converging in 1-2 iterations usually means DV bounds are wrong
  or DVs are not being applied

## Running the server
```bash
# Development (from workspace root)
uv sync
uv run python -m hangar.oas.server

# CLI
uv run oas-cli interactive
uv run oas-cli run create_surface --name wing --span 10
uv run oas-cli run-script workflow.json

# Docker
docker compose -f docker/docker-compose.yml up --build
```

## Testing
```bash
# All tests
uv run pytest packages/sdk/tests/ packages/oas/tests/

# SDK only
uv run pytest packages/sdk/tests/

# OAS only (includes golden physics)
uv run pytest packages/oas/tests/

# Skip slow integration tests
uv run pytest -m "not slow"
```

## Skills

Skills live in two places and must be kept in sync:

1. **`.claude/skills/<skill-name>/`** -- active location that Claude Code loads
   at runtime. This directory is gitignored.
2. **`packages/<pkg>/skills/<skill-name>/`** -- git-tracked source of truth.
   Cross-tool skills go in `skills/` at the repo root.

When creating or updating a skill:
1. Edit the files in `.claude/skills/<skill-name>/`
2. Copy the changed files to `packages/<pkg>/skills/<skill-name>/`
3. Commit the `packages/` copies so changes are tracked in git

A sync script populates `.claude/skills/` from the git-tracked copies.
Each skill directory contains `SKILL.md` (main guide), plus supporting files
like `commands.md`, `modes.md`, `provenance.md`, and `examples/`.

## Adding a new tool
1. Create `packages/<toolname>/` following the `oas/` structure
2. Add `src/hangar/<toolname>/` -- no `__init__.py` in `src/hangar/`
3. Add tool-specific skills in `packages/<toolname>/skills/`
4. Import and use `hangar.sdk` for provenance, envelopes, validation
5. Add upstream clone to `scripts/setup-upstream.sh`
6. Add to `docker/docker-compose.yml`
7. See `.claude/commands/new-tool.md` for detailed guide
