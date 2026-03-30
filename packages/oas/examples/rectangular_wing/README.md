# Rectangular Wing Demonstration: Three-Lane Comparison

This directory walks through the same four OpenAeroStruct analyses on a
rectangular wing, run three different ways:

| Step | Approach | Files |
|------|----------|-------|
| **Original examples** | Upstream OAS scripts (as-is) | `openaerostruct/examples/rectangular_wing/` |
| **Lane A** | Cleaned-up OAS (importable `run()` functions) | `lane_a/*.py` |
| **Lane B** | MCP tools via `oas-cli` | `lane_b/*.json` |
| **Lane C** | Claude Code agent with MCP server | `lane_c/*.prompt.md` |

The four analyses are:

1. **Single-point aero** --- inviscid, alpha=5 deg, Mach=0.0
2. **Drag polar** --- viscous, alpha sweep -10 to 10 deg, Mach=0.84
3. **Twist optimisation** --- minimise CD, twist DV, CL=0.5 constraint
4. **Chord optimisation** --- minimise CD, chord + alpha DVs, CL=0.5 + S_ref=10

---

## Prerequisites

```bash
# From the workspace root
cd /path/to/the-hangar

# Install all workspace packages (includes hangar-oas and dependencies)
uv sync

# Verify the install
uv run python -c "import openaerostruct; print(openaerostruct.__version__)"
uv run oas-cli --help
```

---

## Step 0: Run the Original Examples

These are the upstream scripts in `openaerostruct/examples/rectangular_wing/`.
They use OpenMDAO directly with no wrappers. Run them from the upstream clone:

```bash
# Single-point aero analysis
uv run python upstream/OpenAeroStruct/openaerostruct/examples/rectangular_wing/run_rect_wing.py

# Drag polar (opens a matplotlib plot at the end)
uv run python upstream/OpenAeroStruct/openaerostruct/examples/rectangular_wing/drag_polar.py

# Twist optimisation (prints optimizer debug output)
uv run python upstream/OpenAeroStruct/openaerostruct/examples/rectangular_wing/opt_twist.py

# Chord optimisation
uv run python upstream/OpenAeroStruct/openaerostruct/examples/rectangular_wing/opt_chord.py
```

> **Note:** These scripts generate `*_out/` report directories (OpenMDAO's
> default reporting). You can suppress this by setting the environment variable
> `OPENMDAO_REPORTS=none` or by passing `reports=False` to `om.Problem()`.
> The Lane A scripts below already do this.

---

## Step 1: Run Lane A (Cleaned-Up OpenAeroStruct)

Lane A wraps the same OpenMDAO logic into importable `run()` functions that
return structured dicts. Parameters are pulled from `shared.py` so they
exactly match Lane B.

```bash
cd packages/oas/examples/rectangular_wing

uv run python lane_a/aero_analysis.py    # prints {"CL": ..., "CD": ...}
uv run python lane_a/drag_polar.py       # prints {"alpha": [...], "CL": [...], "CD": [...]}
uv run python lane_a/opt_twist.py        # prints {"CL": ..., "CD": ..., "twist_cp": [...], ...}
uv run python lane_a/opt_chord.py        # prints {"CL": ..., "CD": ..., "chord_cp": [...], ...}
```

---

## Step 2: Run Lane B (MCP / oas-cli)

Lane B uses JSON scripts executed by `oas-cli run-script`. Each script calls
`create_surface` then an analysis or optimisation tool --- the same parameters
as Lane A, just expressed as MCP tool calls.

Individual scripts:
```bash
uv run oas-cli --pretty run-script lane_b/aero_analysis.json
uv run oas-cli --pretty run-script lane_b/drag_polar.json
uv run oas-cli --pretty run-script lane_b/opt_twist.json
uv run oas-cli --pretty run-script lane_b/opt_chord.json
```

Or run all four with a summary table:
```bash
uv run python lane_b/run_all.py
```

---

## Step 3: Run Lane C (Claude Code Agent)

Lane C provides natural-language prompts that an AI agent executes via the
MCP server. See `lane_c/README.md` for setup instructions.

Quick start with Claude Code CLI:
```bash
# From the workspace root (MCP server auto-discovered)
claude

# Then paste the contents of any prompt file, e.g.:
# lane_c/all_analyses.prompt.md   (runs all four in sequence)
```

The agent calls the same MCP tools as Lane B, so results should be identical.

---

## Verification Tests

Parity tests confirm that Lane A and Lane B produce matching results within
floating-point tolerance:

```bash
# From the workspace root
uv run pytest packages/oas/examples/rectangular_wing/tests/ -v
```

This runs 12 tests (3 per analysis): Lane A sanity check, Lane B sanity
check, and a direct A-vs-B comparison.

---

## Parameter Reference

All parameters are defined in `shared.py`. Key differences between MCP
defaults and the values used in these demonstrations (overridden explicitly
in the Lane B JSON scripts):

| Parameter | MCP Default | Demo Value | Why |
|-----------|------------|------------|-----|
| `num_x` | 2 | 11 | Match original examples |
| `num_y` | 7 | 35 | Match original examples |
| `CD0` | 0.015 | 0.0 | Isolate VLM-computed drag |
| `with_viscous` | true | false (except drag polar) | Match original examples |
| `S_ref_type` | "wetted" | "projected" | Match original examples |
| `span_cos_spacing` | 0.0 | 1.0 | Cosine spacing (bunched at tip) |
| `chord_cos_spacing` | 0.0 | 1.0 | Cosine spacing (bunched at LE/TE) |
