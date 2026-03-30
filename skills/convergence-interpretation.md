# Convergence Interpretation

How to interpret optimization convergence results from Hangar tool servers,
diagnose convergence problems, and decide next steps.

## When to use

Use this skill when:
- An optimization run has completed and you need to assess the result
- The optimizer reported `success: false`
- The user is unsure whether to trust the optimized design
- Results look suspicious (too few iterations, constraints violated, no improvement)

## Convergence assessment checklist

### 1. Check the success flag

- `success: true` -- the optimizer believes it found a local optimum that
  satisfies all constraints. This is necessary but not sufficient.
- `success: false` -- the optimizer failed to converge. See diagnosis below.

### 2. Check iteration count

| Iterations | Interpretation |
|-----------|----------------|
| 1--2 | Almost certainly wrong. DVs not connected, bounds too tight, or scaling issue. See known-squawks. |
| 3--10 | Reasonable for aero-only with 2 DVs. Suspicious for aerostruct. |
| 10--50 | Normal range for well-scaled problems. |
| 50--200 | Normal for aerostruct with many DVs. Check that objective is still decreasing. |
| >200 | May indicate poor scaling or overly tight tolerance. |

### 3. Check constraint satisfaction

For each constraint, verify:
- **Equality constraints** (e.g. `CL=0.5`, `L_equals_W=0`): residual should
  be less than the tolerance (typically 1e-6 to 1e-9)
- **Inequality constraints** (e.g. `failure<=0`): value should be at or below
  the bound with some margin

If constraints are violated at the "optimal" point, the result is infeasible
and should not be trusted.

### 4. Check objective improvement

- Compare the final objective to the baseline value
- `objective_improvement_pct` in `summary.derived_metrics` gives this directly
- Typical improvements:
  - Twist optimization for min drag: 5--20% CD reduction
  - Aerostructural fuel burn: 5--30% reduction depending on DVs
  - Near-zero improvement: either the baseline was already near-optimal or
    the DVs are not effective

### 5. Check DV values

- Are DVs at their bounds? If most DVs hit bounds, the bounds may be too tight
  or the optimizer wants to go further
- Are DVs unchanged from initial values? This means they were not connected
  (silent DV name rejection -- see known-squawks)
- Do DV values make physical sense? Negative thickness, extreme twist angles,
  or taper < 0.1 may indicate a poorly posed problem

### 6. Visualize convergence history

```
visualize(run_id=run_id, plot_type="opt_history", output="file")
```

Look for:
- **Smooth monotonic decrease** -- good convergence
- **Oscillation** -- scaling problem or constraint conflict
- **Flat line** -- DVs not active or bounds too tight
- **Sharp drop then flat** -- converged quickly, may be local minimum

## Diagnosing `success: false`

### Poor scaling

Most common cause. Check:
- Is `objective_scaler` approximately `1/baseline_objective`?
- Are DV scalers appropriate for their magnitude?
- See the `optimization-setup` skill scaling tables

Fix: recompute scalers from baseline, re-run.

### Infeasible constraints

The constraints cannot all be satisfied simultaneously.

Check:
- Is the baseline feasible? If `failure > 0` at the baseline, the initial
  point is already infeasible
- Are equality constraints compatible? (e.g. fixing CL while also fixing alpha
  leaves no freedom)

Fix: relax constraints, add DVs, or accept that the problem is infeasible.

### Insufficient DV freedom

Too few DVs to satisfy all constraints while improving the objective.

Fix: add more DVs (e.g. add `chord` or `thickness` alongside `twist`).

### Tolerance too tight

For aerostruct problems, `tolerance=1e-9` is recommended. For aero-only,
the default is usually fine.

Fix: try `tolerance=1e-7` for a less strict convergence criterion.

## Decision template

After assessing convergence, log:

```
log_decision(
    decision_type="convergence_assessment",
    reasoning="Optimizer converged in N iterations. Objective improved X%.
               All constraints satisfied. DV values physically reasonable.
               Convergence history shows smooth decrease.",
    selected_action="Accept result / Re-run with adjusted scaling / Widen DV bounds",
    prior_call_id="<opt call_id>",
    confidence="high|medium|low"
)
```

## When to re-run

Re-run the optimization if:
- `success: false` and you identified a fixable cause (scaling, bounds, tolerance)
- DVs are at bounds and the user wants to explore further
- Iteration count was suspiciously low (1--2)
- Constraints are violated

Do NOT re-run if:
- `success: true`, constraints satisfied, improvement is reasonable
- The problem is fundamentally infeasible (no amount of re-running will help)
- The user is satisfied with the result
