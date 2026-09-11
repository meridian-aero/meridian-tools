# Reproducing the tables

Every number in `lane_parity.*` and `sandboxed_evals.*`, in the order it has
to be produced. Run all commands from the repo root unless stated otherwise.
Background on what each lane means is in `paper/README.md`; this file is the
runbook only.

## Prerequisites (once)

```bash
bash scripts/dev-setup.sh          # pinned upstreams + all packages
colima start                       # container runtime for the sandboxed arms
```

The sandboxed anchor authenticates with a Claude Code subscription token
(`claude setup-token`) stored in 1Password as the `claude-code` item's `token`
field. `op run` resolves it once per launch and scopes it to that process tree
— never export it into your shell.

## 1. Lane A / B / C parity — `lane_parity.*`

```bash
uv run python paper/run_lanes.py                      # ~30-40 min
```

Drives the pytest parity suites with the `PARITY_RESULTS_JSONL` hook, so the
tests stay the single source of truth. Writes `paper/results/lane_parity.jsonl`
plus a meta file stamping the git SHA and pytest exit code — **check that the
exit code is 0**; it is stamped into the table comment either way.
`ocp_pyc_coupled` is deselected by design (`--include-known-gaps` to override).

## 2. Lane C agent column

```bash
uv run --with claude-agent-sdk \
    packages/omd/examples/agent_eval/eval_lane_c.py all \
    --save-json paper/results/lane_c_agent.json       # ~30 min, ~$17 API
```

## 3. Sandboxed arms — `sandboxed_evals.*`

From the sibling `hangar-evals` checkout. One unlock covers the whole bundle:

```bash
cd ../hangar-evals
op run --env-file=op.env -- bash scripts/run_anchor.sh   # 11 cases x 3 seeds, ~5 h
op run --env-file=op.env -- bash scripts/run_gemma.sh    # local arm, ~14 h
```

Both scripts skip cases that already have a complete summary for that
`(case, model)`, so re-running continues rather than restarts. The anchor
re-probes auth between cases and halts cleanly if the plan's usage window
closes — re-run the same command to pick up where it stopped.

Seeds that died on a transient (`API Error: Connection closed mid-response`)
are recorded as retryable error rows. Retry just those:

```bash
uv run --project ../the-hangar --with-editable ".[anchor]" \
    python -m hangar.evals.run --resume results/<case>_<stamp>.jsonl
```

## 4. Re-derive summaries

```bash
uv run --project ../the-hangar --with-editable ".[anchor]" \
    python -m hangar.evals.regrade                    # -> results/regraded/
```

Recomputes every cell summary from the stored records and adds `n_ambiguous`
and `n_report_disagrees`. It changes no verdict — it makes visible the seeds
whose score turned on run **order**, because the oracle grades the last
successful run of the matching mode and several prompts ask for a comparison
run. Any case with `n_ambiguous > 0` needs a look before it goes in the paper
(see `ocp_caravan_full`, which fails on every seed of both anchor arms while
reporting the Lane A value exactly).

## 5. Render

```bash
cd ../the-hangar
uv run python paper/make_tables.py \
    --evals-dir ../hangar-evals/results/regraded
```

Writes `{lane_parity,sandboxed_evals}.{csv,md,tex}` here. The sandboxed table
keeps the latest summary per `(case, harness, model)`, so arms accumulate
across runs and old model generations stay in for comparison.

## 6. Before using the output

- `lane_parity.md` header comment: pytest exit 0, and a git SHA that matches
  the code the numbers should describe.
- Every case you expect is present — a missing arm shows up as an absent row,
  not an error.
- No cell with `n_ambiguous > 0` is being read as a clean fail.
