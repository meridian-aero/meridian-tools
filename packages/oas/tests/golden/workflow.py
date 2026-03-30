"""Workflow inspectability helpers for example parity tests.

WorkflowRecorder records MCP tool calls and timing during a test workflow.
WorkflowManifest collects the recorded steps plus OAS vs MCP comparison data
and can render them as text reports or standalone HTML pages.
"""
from __future__ import annotations

import dataclasses
import json
import time
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class WorkflowStep:
    step_number: int
    tool_name: str
    inputs_summary: dict    # key inputs (arrays summarised to shape+range)
    outputs_summary: dict   # key scalar results
    run_id: str | None
    elapsed_s: float
    opt_history: dict | None = None  # populated for run_optimization steps


@dataclasses.dataclass
class WorkflowManifest:
    name: str
    oas_source: str
    oas_code_summary: str
    steps: list[WorkflowStep]
    final_comparison: dict  # {qty: {oas, mcp, rel_diff, tol, status}}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "oas_source": self.oas_source,
            "oas_code_summary": self.oas_code_summary,
            "steps": [dataclasses.asdict(s) for s in self.steps],
            "final_comparison": self.final_comparison,
        }

    def print_report(self) -> None:
        hdr2 = f"  {'#':<3}  {'Tool':<36}  {'Key Inputs':<38}  Time"
        print(f"\n  {self.name}  ({self.oas_source})")
        print(f"  {'='*70}")
        print("\n  MCP Workflow Steps:")
        print(hdr2)
        print(f"  {'-' * (len(hdr2) - 2)}")
        for step in self.steps:
            inputs_str = ", ".join(
                f"{k}={v}" for k, v in list(step.inputs_summary.items())[:3]
            )
            print(
                f"  {step.step_number:<3}  {step.tool_name:<36}  "
                f"{inputs_str[:38]:<38}  {step.elapsed_s:.2f}s"
            )

        if self.oas_code_summary.strip():
            print("\n  Equivalent OAS code:")
            for line in self.oas_code_summary.strip().splitlines():
                print(f"    {line}")

        if self.final_comparison:
            print("\n  Results:")
            col_w = 22
            hdr = (
                f"  {'Quantity':<14}  {'OAS Direct':<{col_w}}  "
                f"{'MCP Result':<{col_w}}  {'Rel Diff':<12}  Status"
            )
            print(hdr)
            print(f"  {'-' * (len(hdr) - 2)}")
            for qty, info in self.final_comparison.items():
                oas_v = info.get("oas")
                mcp_v = info.get("mcp")
                if oas_v is None or mcp_v is None:
                    continue
                print(
                    f"  {qty:<14}  {oas_v:<{col_w}.14g}  "
                    f"{mcp_v:<{col_w}.14g}  {info['rel_diff']:<12.2e}  {info['status']}"
                )

    def to_html(self) -> str:
        """Generate an HTML section for this workflow case."""
        steps_html = ""
        for step in self.steps:
            inputs_html = "".join(
                f"<tr><td>{k}</td><td>{v}</td></tr>"
                for k, v in step.inputs_summary.items()
            )
            outputs_html = "".join(
                f"<tr><td>{k}</td><td>{v}</td></tr>"
                for k, v in step.outputs_summary.items()
            ) or "<tr><td colspan='2'><em>no scalars</em></td></tr>"
            run_id_html = (
                f'<span class="run-id">{step.run_id}</span>' if step.run_id else ""
            )
            conv_html = _convergence_html(step.opt_history) if step.opt_history else ""
            steps_html += f"""<div class="step">
  <div class="step-header" onclick="toggleStep(this)">
    <span class="step-num">#{step.step_number}</span>
    <span class="tool-name">{step.tool_name}</span>
    <span class="step-time">{step.elapsed_s:.2f}s</span>
    {run_id_html}
  </div>
  <div class="step-body" style="display:none">
    <div class="step-cols">
      <div><b>Inputs</b><table>{inputs_html}</table></div>
      <div><b>Outputs</b><table>{outputs_html}</table></div>
    </div>
    {conv_html}
  </div>
</div>"""

        rows_html = ""
        for qty, info in self.final_comparison.items():
            oas_v = info.get("oas")
            mcp_v = info.get("mcp")
            if oas_v is None or mcp_v is None:
                continue
            status_cls = "pass" if info["status"] == "PASS" else "fail"
            rows_html += (
                f"<tr><td>{qty}</td>"
                f"<td>{oas_v:.10g}</td>"
                f"<td>{mcp_v:.10g}</td>"
                f"<td>{info['rel_diff']:.2e}</td>"
                f'<td class="{status_cls}">{info["status"]}</td></tr>'
            )

        code_esc = self.oas_code_summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"""
<section class="workflow-case">
  <h2>{self.name}</h2>
  <p class="source">Source: <code>{self.oas_source}</code></p>
  <h3>MCP Workflow Steps</h3>
  <div class="steps">{steps_html}</div>
  <h3>Equivalent OAS Code</h3>
  <pre class="oas-code"><code>{code_esc}</code></pre>
  <h3>Results Comparison</h3>
  <table class="comparison">
    <thead><tr><th>Quantity</th><th>OAS Direct</th><th>MCP Result</th><th>Rel Diff</th><th>Status</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</section>"""


# ---------------------------------------------------------------------------
# WorkflowRecorder
# ---------------------------------------------------------------------------


def _convergence_html(opt_history: dict) -> str:
    """Render per-iteration convergence data as an HTML block."""
    obj_vals = opt_history.get("objective_values", [])
    dv_hist = opt_history.get("dv_history", {})
    initial_dvs = opt_history.get("initial_dvs", {})
    n_iter = opt_history.get("num_iterations", len(obj_vals))

    if not obj_vals and not dv_hist:
        return f'<p class="conv-empty">No iteration data recorded ({n_iter} iterations).</p>'

    # Objective convergence table (cap at 50 rows for readability)
    obj_rows = ""
    display_vals = obj_vals[:50]
    for i, v in enumerate(display_vals, 1):
        obj_rows += f"<tr><td>{i}</td><td>{v:.8g}</td></tr>"
    if len(obj_vals) > 50:
        obj_rows += f"<tr><td>…</td><td>({len(obj_vals)} total)</td></tr>"

    def _fmt_dv(v) -> str:
        import numpy as np
        a = np.asarray(v).ravel()
        if a.size == 1:
            return f"{float(a[0]):.6g}"
        if a.size <= 5:
            return "[" + ", ".join(f"{x:.4g}" for x in a) + "]"
        return f"[{a[0]:.4g} … {a[-1]:.4g}] (n={a.size})"

    # DV summary: initial vs final for each DV
    dv_rows = ""
    for dv_name, history in dv_hist.items():
        if not history:
            continue
        init = initial_dvs.get(dv_name)
        final = history[-1]
        init_str = _fmt_dv(init) if init is not None else "—"
        final_str = _fmt_dv(final)
        dv_rows += f"<tr><td>{dv_name}</td><td>{init_str}</td><td>{final_str}</td></tr>"

    # Inline sparkline SVG for objective convergence
    sparkline = ""
    if len(obj_vals) >= 2:
        sparkline = _sparkline_svg(obj_vals)

    return f"""<div class="conv-block">
  <b>Optimization Convergence</b> — {n_iter} iterations
  {sparkline}
  <div class="conv-cols">
    <div>
      <b>Objective per iteration</b>
      <table class="conv-table">
        <thead><tr><th>#</th><th>Value</th></tr></thead>
        <tbody>{obj_rows}</tbody>
      </table>
    </div>
    <div>
      <b>Design variables: initial → final</b>
      <table class="conv-table">
        <thead><tr><th>DV</th><th>Initial</th><th>Final</th></tr></thead>
        <tbody>{dv_rows}</tbody>
      </table>
    </div>
  </div>
</div>"""


def _sparkline_svg(values: list[float], width: int = 300, height: int = 60) -> str:
    """Generate an inline SVG sparkline of the given values."""
    n = len(values)
    if n < 2:
        return ""
    vmin = min(values)
    vmax = max(values)
    span = vmax - vmin or abs(vmin) * 0.01 or 1.0
    pad = 4

    def _x(i: int) -> float:
        return pad + (i / (n - 1)) * (width - 2 * pad)

    def _y(v: float) -> float:
        return pad + (1 - (v - vmin) / span) * (height - 2 * pad)

    points = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, v in enumerate(values))
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{points}" fill="none" stroke="#0d6efd" stroke-width="1.5"/>'
        f'</svg>'
    )


def _summarize_value(v: Any) -> Any:
    """Convert arrays / long lists to compact shape+range strings."""
    try:
        import numpy as np
        if isinstance(v, np.ndarray):
            if v.size <= 4:
                return v.tolist()
            return f"array(shape={list(v.shape)}, range=[{v.min():.4g}, {v.max():.4g}])"
    except ImportError:
        pass
    if isinstance(v, list) and len(v) > 6:
        return f"list(len={len(v)})"
    return v


def _summarize_inputs(kwargs: dict) -> dict:
    """Produce a compact representation of tool kwargs."""
    skip = {"session_id", "run_name"}
    return {k: _summarize_value(v) for k, v in kwargs.items() if k not in skip}


class WorkflowRecorder:
    """Records MCP tool calls during a workflow for later inspection."""

    def __init__(self, name: str, oas_source: str):
        self.name = name
        self.oas_source = oas_source
        self._steps: list[WorkflowStep] = []

    async def call(self, tool_fn: Callable, **kwargs) -> dict:
        """Call an async MCP tool, record timing + I/O summary, return result."""
        step_num = len(self._steps) + 1
        t0 = time.perf_counter()
        result = await tool_fn(**kwargs)
        elapsed = time.perf_counter() - t0

        run_id: str | None = None
        outputs_summary: dict = {}
        opt_history: dict | None = None
        if isinstance(result, dict):
            run_id = result.get("run_id")
            res = result.get("results", result)
            if isinstance(res, dict):
                # Check top-level and final_results sub-dict (optimization)
                inner = res.get("final_results", {}) if isinstance(res, dict) else {}
                for k in ["CL", "CD", "CM", "fuelburn", "CL_alpha", "CM_alpha",
                          "static_margin", "success"]:
                    src = res if k in res else inner
                    if k in src:
                        v = src[k]
                        if isinstance(v, bool):
                            outputs_summary[k] = v
                        elif isinstance(v, (int, float)):
                            outputs_summary[k] = round(float(v), 6)
                # Extract optimization iteration history for run_optimization steps
                raw_hist = res.get("optimization_history")
                if raw_hist and isinstance(raw_hist, dict):
                    n_iter = raw_hist.get("num_iterations", 0)
                    obj_vals = raw_hist.get("objective_values", [])
                    dv_hist = raw_hist.get("dv_history", {})
                    initial_dvs = raw_hist.get("initial_dvs", {})
                    if n_iter or obj_vals:
                        outputs_summary["n_iter"] = n_iter
                    opt_history = {
                        "num_iterations": n_iter,
                        "objective_values": obj_vals,
                        "dv_history": dv_hist,
                        "initial_dvs": initial_dvs,
                    }

        self._steps.append(WorkflowStep(
            step_number=step_num,
            tool_name=tool_fn.__name__,
            inputs_summary=_summarize_inputs(kwargs),
            outputs_summary=outputs_summary,
            run_id=run_id,
            elapsed_s=elapsed,
            opt_history=opt_history,
        ))
        return result

    def finalize(
        self,
        oas_results: dict,
        mcp_results: dict,
        tolerances: dict,
        oas_code_summary: str,
    ) -> WorkflowManifest:
        """Build the manifest with OAS vs MCP comparison data."""
        comparison: dict = {}
        for qty, tol in tolerances.items():
            oas_val = oas_results.get(qty)
            mcp_val = mcp_results.get(qty)
            if oas_val is None or mcp_val is None:
                continue
            denom = max(abs(oas_val), abs(mcp_val), 1e-300)
            rel_diff = abs(oas_val - mcp_val) / denom
            comparison[qty] = {
                "oas": oas_val,
                "mcp": mcp_val,
                "rel_diff": rel_diff,
                "tol": tol,
                "status": "PASS" if rel_diff <= tol else "FAIL",
            }
        return WorkflowManifest(
            name=self.name,
            oas_source=self.oas_source,
            oas_code_summary=oas_code_summary,
            steps=self._steps,
            final_comparison=comparison,
        )


# ---------------------------------------------------------------------------
# HTML report builder (full standalone page from multiple manifests)
# ---------------------------------------------------------------------------

_CSS = """
body{font-family:'Segoe UI',system-ui,sans-serif;max-width:1100px;margin:2em auto;background:#f8f9fa;color:#212529}
h1{border-bottom:3px solid #0d6efd;padding-bottom:.4em}
h2{background:#e9ecef;padding:.4em .8em;border-left:4px solid #0d6efd;margin-top:2em}
h3{color:#495057;margin-top:1.5em}
.source code{background:#e9ecef;padding:.15em .4em;border-radius:3px}
.steps{margin-left:1em}
.step{border:1px solid #dee2e6;border-radius:6px;margin:.4em 0;overflow:hidden}
.step-header{display:flex;align-items:center;gap:1em;padding:.5em .8em;background:#f1f3f5;cursor:pointer;user-select:none}
.step-header:hover{background:#e2e6ea}
.step-num{font-weight:700;color:#6c757d;min-width:2em}
.tool-name{font-family:monospace;font-weight:600;flex:1}
.step-time{font-size:.85em;color:#6c757d}
.run-id{font-size:.75em;font-family:monospace;color:#868e96}
.step-body{padding:.8em 1em;background:#fff}
.step-cols{display:grid;grid-template-columns:1fr 1fr;gap:1.5em}
table{border-collapse:collapse;font-size:.9em}
td,th{padding:.3em .7em;border:1px solid #dee2e6}
th{background:#f1f3f5;font-weight:600}
.comparison{width:100%}
.pass{color:#198754;font-weight:700}
.fail{color:#dc3545;font-weight:700}
pre.oas-code{background:#1e1e1e;color:#d4d4d4;padding:1em;border-radius:6px;overflow-x:auto;font-size:.9em}
.summary{font-size:1.1em;font-weight:600;padding:.6em 1em;border-radius:6px;margin-top:2em}
.summary.all-pass{background:#d1e7dd;color:#0f5132}
.summary.has-fail{background:#f8d7da;color:#842029}
.conv-block{margin-top:1em;padding:.6em .8em;background:#f8f9fa;border-radius:6px;border:1px solid #dee2e6}
.conv-cols{display:grid;grid-template-columns:1fr 1fr;gap:1.5em;margin-top:.6em}
.conv-table{font-size:.85em;max-height:260px;overflow-y:auto;display:block}
.sparkline{display:block;margin:.4em 0;border:1px solid #dee2e6;border-radius:4px;background:#fff}
.conv-empty{color:#6c757d;font-style:italic;font-size:.9em}
"""

_JS = """
function toggleStep(h){const b=h.nextElementSibling;b.style.display=b.style.display==='none'?'block':'none'}
"""


def build_html_report(
    manifests: list[WorkflowManifest],
    title: str = "Example Workflow Parity Report",
) -> str:
    """Build a single-file HTML report from a list of WorkflowManifests."""
    total = sum(len(m.final_comparison) for m in manifests)
    passed = sum(
        1 for m in manifests for info in m.final_comparison.values()
        if info["status"] == "PASS"
    )
    summary_cls = "all-pass" if passed == total else "has-fail"
    sections = "\n".join(m.to_html() for m in manifests)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{_CSS}</style><script>{_JS}</script></head>
<body>
<h1>{title}</h1>
<p>Comparing OpenAeroStruct example workflows run directly vs via the MCP server.</p>
{sections}
<div class="summary {summary_cls}">Summary: {passed}/{total} checks passed</div>
</body>
</html>"""
