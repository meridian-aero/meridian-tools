"""OpenConcept-specific plot generators.

Each plot function accepts ``(run_id, results, case_name, *, save_dir)``
and returns a ``PlotResult``.  The ``generate_ocp_plot`` dispatcher routes
by ``plot_type`` string, mirroring the PYC/SDK pattern.
"""

from __future__ import annotations

from pathlib import Path

from hangar.sdk.viz.plotting import (
    PlotResult,
    _fig_to_response,
    _make_fig,
    _require_mpl,
)

OCP_PLOT_TYPES = frozenset({
    "mission_profile",
    "takeoff_profile",
    "weight_breakdown",
    "performance_summary",
    "energy_budget",
    "sweep_chart",
    "optimization_history",
})

# Canonical phase ordering for concatenation
_PHASE_ORDER = [
    "v0v1", "v1vr", "rotate",
    "climb", "cruise", "descent",
    "reserve_climb", "reserve_cruise", "reserve_descent",
    "loiter",
]

_PHASE_COLORS = {
    "v0v1": "#94a3b8",
    "v1vr": "#64748b",
    "v1v0": "#475569",
    "rotate": "#f59e0b",
    "climb": "#2563eb",
    "cruise": "#059669",
    "descent": "#dc2626",
    "reserve_climb": "#93c5fd",
    "reserve_cruise": "#86efac",
    "reserve_descent": "#fca5a5",
    "loiter": "#c084fc",
}

_PHASE_LABELS = {
    "v0v1": "V0-V1",
    "v1vr": "V1-Vr",
    "v1v0": "Rejected TO",
    "rotate": "Rotate",
    "climb": "Climb",
    "cruise": "Cruise",
    "descent": "Descent",
    "reserve_climb": "Rsv Climb",
    "reserve_cruise": "Rsv Cruise",
    "reserve_descent": "Rsv Descent",
    "loiter": "Loiter",
}


def _phase_label(phase: str) -> str:
    return _PHASE_LABELS.get(phase, phase.replace("_", " ").title())


def _phase_color(phase: str) -> str:
    return _PHASE_COLORS.get(phase, "#6b7280")


def _ordered_phases(trajectory: dict) -> list[str]:
    """Return phase names present in trajectory, in canonical order."""
    ordered = [p for p in _PHASE_ORDER if p in trajectory]
    for p in trajectory:
        if p not in ordered:
            ordered.append(p)
    return ordered


def _concatenate_trajectory(
    trajectory: dict,
    var_name: str,
) -> tuple[list, list, list[tuple[float, str]]]:
    """Concatenate per-phase arrays into a continuous series.

    OpenConcept stores range as cumulative across phases, so no offset
    is needed -- the values connect naturally.

    Returns (x_all, y_all, boundaries) where boundaries is a list of
    (x_position, phase_name) tuples marking phase transitions.
    """
    x_all: list[float] = []
    y_all: list[float] = []
    boundaries: list[tuple[float, str]] = []

    for phase in _ordered_phases(trajectory):
        phase_data = trajectory[phase]
        rng = phase_data.get("range_NM")
        vals = phase_data.get(var_name)
        if rng is None or vals is None:
            continue
        if len(rng) == 0 or len(vals) == 0:
            continue

        boundaries.append((rng[0], phase))
        x_all.extend(rng)
        y_all.extend(vals)

    return x_all, y_all, boundaries


def _plot_trajectory_var(
    ax, trajectory: dict, var_name: str, ylabel: str,
    *, color: str = "tab:blue",
) -> None:
    """Plot a single trajectory variable, matching the upstream OpenConcept style.

    OpenConcept range is cumulative across phases, so each phase is plotted
    at its raw range values with the same color and marker style. The points
    connect naturally across phase boundaries.
    """
    for phase in _ordered_phases(trajectory):
        phase_data = trajectory[phase]
        rng = phase_data.get("range_NM")
        vals = phase_data.get(var_name)
        if rng is None or vals is None:
            continue
        if len(rng) == 0 or len(vals) == 0:
            continue

        ax.plot(
            rng, vals, "-o",
            color=color,
            markersize=2.0,
            linewidth=1.5,
        )

    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.3)


def _has_battery_data(trajectory: dict) -> bool:
    """Check if any phase has battery_SOC data."""
    for phase_data in trajectory.values():
        if phase_data.get("battery_SOC") is not None:
            return True
    return False


def _fmt(val, decimals: int = 1) -> str:
    if val is None:
        return "N/A"
    return f"{float(val):.{decimals}f}"


# ---------------------------------------------------------------------------
# Plot: mission_profile (2x3 grid)
# ---------------------------------------------------------------------------


def plot_mission_profile(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """2x3 grid: altitude, V/S, TAS, throttle, fuel used, battery SOC vs range."""
    _, plt = _require_mpl()

    trajectory = results.get("trajectory", {})
    if not trajectory:
        raise ValueError("No trajectory data in results")

    has_battery = _has_battery_data(trajectory)

    title = "Mission Profile"
    if case_name:
        title = f"{title} -- {case_name}"

    nrows, ncols = 2, 3
    fig, axes = plt.subplots(nrows, ncols, figsize=(10.0, 6.0))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)

    panels = [
        ("altitude_ft", "Altitude (ft)"),
        ("vertical_speed_ftmin", "Vertical Speed (ft/min)"),
        ("airspeed_kn", "Airspeed (kn)"),
        ("throttle", "Throttle"),
        ("fuel_used_kg", "Fuel Used (kg)"),
    ]

    if has_battery:
        panels.append(("battery_SOC", "Battery SOC"))

    for idx, (var, ylabel) in enumerate(panels):
        ax = axes.flat[idx]
        _plot_trajectory_var(ax, trajectory, var, ylabel)
        ax.set_xlabel("Range (NM)", fontsize=7)

    # If no battery data, hide the 6th panel
    if not has_battery:
        axes.flat[5].set_visible(False)

    # Add phase boundary annotations on the altitude panel
    _, _, boundaries = _concatenate_trajectory(trajectory, "altitude_ft")
    for bx, phase_name in boundaries:
        for ax in axes.flat[:len(panels)]:
            ax.axvline(bx, color="#94a3b8", linestyle=":", linewidth=0.6, alpha=0.4)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "mission_profile", save_dir)


# ---------------------------------------------------------------------------
# Plot: takeoff_profile (1x3 grid)
# ---------------------------------------------------------------------------


def plot_takeoff_profile(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """1x3 grid: altitude, airspeed, throttle for takeoff phases."""
    _, plt = _require_mpl()

    trajectory = results.get("trajectory", {})
    takeoff_phases = [p for p in ["v0v1", "v1vr", "rotate"] if p in trajectory]

    if not takeoff_phases:
        raise ValueError(
            "No takeoff phases found in trajectory. "
            "Takeoff plots require mission_type='full'."
        )

    # Build a sub-trajectory with only takeoff phases
    to_traj = {p: trajectory[p] for p in takeoff_phases}

    title = "Takeoff Profile"
    if case_name:
        title = f"{title} -- {case_name}"

    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.5))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)

    panels = [
        ("altitude_ft", "Altitude (ft)"),
        ("airspeed_kn", "Airspeed (kn)"),
        ("throttle", "Throttle"),
    ]

    # Takeoff phases use different colors to distinguish ground roll vs rotate
    to_colors = {"v0v1": "#64748b", "v1vr": "#64748b", "rotate": "#f59e0b"}
    for idx, (var, ylabel) in enumerate(panels):
        ax = axes[idx]
        for phase in takeoff_phases:
            pd = to_traj[phase]
            rng = pd.get("range_NM")
            vals = pd.get(var)
            if rng is None or vals is None:
                continue
            ax.plot(
                rng, vals, "-o",
                color=to_colors.get(phase, "tab:blue"),
                markersize=2.0, linewidth=1.5,
                label=_phase_label(phase),
            )
        ax.set_ylabel(ylabel, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Range (NM)", fontsize=7)

    # Legend on first panel
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        axes[0].legend(handles, labels, fontsize=6, loc="best", framealpha=0.7)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "takeoff_profile", save_dir)


# ---------------------------------------------------------------------------
# Plot: weight_breakdown (horizontal bar chart)
# ---------------------------------------------------------------------------


def plot_weight_breakdown(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """Horizontal bar chart decomposing MTOW into OEW, fuel, payload, battery."""
    _, plt = _require_mpl()
    import numpy as np

    mtow = results.get("MTOW_kg")
    oew = results.get("OEW_kg")
    fuel = results.get("fuel_burn_kg") or results.get("total_fuel_with_reserve_kg")

    if mtow is None or oew is None:
        raise ValueError("MTOW_kg and OEW_kg required for weight breakdown")

    mtow, oew = float(mtow), float(oew)
    fuel = float(fuel) if fuel is not None else 0.0

    # Estimate battery weight from results if available
    battery_weight = 0.0
    # Battery weight is part of OEW in OpenConcept, so we don't subtract it
    # separately unless explicitly provided
    has_battery = results.get("battery_SOC_final") is not None

    payload = mtow - oew - fuel
    if payload < 0:
        payload = 0.0

    categories = ["OEW", "Fuel", "Payload"]
    values = [oew, fuel, payload]
    colors = ["#2563eb", "#dc2626", "#059669"]

    if has_battery and "MTOW_margin_lb" in results:
        margin_lb = results["MTOW_margin_lb"]
        if margin_lb is not None:
            margin_kg = float(margin_lb) * 0.453592
            categories.append("MTOW Margin")
            values.append(margin_kg)
            colors.append("#f59e0b")

    title = "Weight Breakdown"
    if case_name:
        title = f"{title} -- {case_name}"

    fig, ax = plt.subplots(figsize=(7.0, 2.5 + 0.4 * len(categories)))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)

    y_pos = np.arange(len(categories))
    bars = ax.barh(y_pos, values, color=colors, height=0.6, alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=8)
    ax.set_xlabel("Weight (kg)", fontsize=8)
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(True, axis="x", alpha=0.3)

    # Value labels
    for bar, val in zip(bars, values):
        pct = val / mtow * 100 if mtow > 0 else 0
        ax.text(
            bar.get_width() + mtow * 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.0f} kg ({pct:.1f}%)",
            va="center", fontsize=7,
        )

    # MTOW annotation
    ax.axvline(mtow, color="#334155", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.text(
        mtow, len(categories) - 0.3,
        f"  MTOW: {mtow:.0f} kg",
        fontsize=7, color="#334155", va="bottom",
    )

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "weight_breakdown", save_dir)


# ---------------------------------------------------------------------------
# Plot: performance_summary (table card)
# ---------------------------------------------------------------------------


def plot_performance_summary(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """Styled table card summarizing all key mission metrics."""
    _, plt = _require_mpl()

    rows: list[tuple[str, str, str]] = []
    _add = rows.append

    # Weight section
    _add(("Weight", "MTOW", f"{_fmt(results.get('MTOW_kg'))} kg"))
    _add(("", "OEW", f"{_fmt(results.get('OEW_kg'))} kg"))

    mtow = results.get("MTOW_kg")
    oew = results.get("OEW_kg")
    if mtow and oew:
        _add(("", "OEW Fraction", f"{float(oew) / float(mtow) * 100:.1f}%"))

    # Fuel section
    fuel = results.get("fuel_burn_kg")
    _add(("Fuel", "Fuel Burn", f"{_fmt(fuel)} kg"))
    if fuel and mtow:
        _add(("", "Fuel Fraction", f"{float(fuel) / float(mtow) * 100:.1f}%"))
    total_fuel = results.get("total_fuel_with_reserve_kg")
    if total_fuel is not None:
        _add(("", "Total w/ Reserve", f"{_fmt(total_fuel)} kg"))

    # Performance section
    tofl = results.get("TOFL_ft")
    if tofl is not None:
        _add(("Performance", "TOFL", f"{_fmt(tofl)} ft"))
    stall = results.get("stall_speed_kn")
    if stall is not None:
        _add(("", "Stall Speed", f"{_fmt(stall)} kn"))

    # Phase breakdown
    phase_results = results.get("phase_results", {})
    for phase_name in ["climb", "cruise", "descent"]:
        pr = phase_results.get(phase_name, {})
        fuel_used = pr.get("fuel_used_kg")
        dur = pr.get("duration_s")
        section = phase_name.title() if phase_name == "climb" else ""
        if fuel_used is not None:
            _add((section or "Phases", f"{phase_name.title()} Fuel", f"{_fmt(fuel_used)} kg"))
        if dur is not None:
            _add(("", f"{phase_name.title()} Duration", f"{float(dur) / 60:.1f} min"))

    # Hybrid section
    soc = results.get("battery_SOC_final")
    if soc is not None:
        _add(("Hybrid", "Final Battery SOC", _fmt(soc, 3)))
    margin = results.get("MTOW_margin_lb")
    if margin is not None:
        _add(("", "MTOW Margin", f"{_fmt(margin)} lb"))

    # Optimization section (if applicable)
    if "objective_value" in results:
        _add(("Optimization", "Objective", results.get("objective", "N/A")))
        _add(("", "Objective Value", _fmt(results.get("objective_value"), 4)))
        _add(("", "Converged", str(results.get("optimization_successful", "N/A"))))
        iters = results.get("num_iterations")
        if iters is not None:
            _add(("", "Iterations", str(iters)))

    title = "Performance Summary"
    if case_name:
        title = f"{title} -- {case_name}"

    fig, ax = plt.subplots(figsize=(6.0, 0.3 * len(rows) + 1.2))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)
    ax.set_axis_off()

    cell_text = []
    cell_colors = []
    section_color = "#e2e8f0"
    normal_color = "#ffffff"

    for section, label, value in rows:
        if section:
            cell_text.append([section, label, value])
            cell_colors.append([section_color, section_color, section_color])
        else:
            cell_text.append(["", label, value])
            cell_colors.append([normal_color, normal_color, normal_color])

    table = ax.table(
        cellText=cell_text,
        colLabels=["Section", "Parameter", "Value"],
        cellColours=cell_colors,
        colColours=[section_color] * 3,
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.2)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "performance_summary", save_dir)


# ---------------------------------------------------------------------------
# Plot: energy_budget (dual Y-axis, hybrid only)
# ---------------------------------------------------------------------------


def plot_energy_budget(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """Dual Y-axis: battery SOC (left) + cumulative fuel used (right) vs range."""
    _, plt = _require_mpl()

    trajectory = results.get("trajectory", {})
    if not trajectory:
        raise ValueError("No trajectory data in results")

    if not _has_battery_data(trajectory):
        raise ValueError(
            "No battery_SOC data in trajectory. "
            "energy_budget requires a hybrid or electric architecture."
        )

    title = "Energy Budget"
    if case_name:
        title = f"{title} -- {case_name}"

    fig, ax1 = plt.subplots(figsize=(8.0, 4.0))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)

    # Battery SOC on left axis
    x_soc, y_soc, boundaries = _concatenate_trajectory(trajectory, "battery_SOC")
    if x_soc:
        ax1.fill_between(x_soc, y_soc, alpha=0.2, color="#2563eb")
        ax1.plot(x_soc, y_soc, "-o", color="#2563eb", markersize=2.0,
                 linewidth=1.5, label="Battery SOC")
    ax1.set_xlabel("Range (NM)", fontsize=8)
    ax1.set_ylabel("Battery SOC", fontsize=8, color="#2563eb")
    ax1.tick_params(axis="y", labelcolor="#2563eb", labelsize=7)
    ax1.tick_params(axis="x", labelsize=7)
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(True, alpha=0.3)

    # Fuel used on right axis
    ax2 = ax1.twinx()
    x_fuel, y_fuel, _ = _concatenate_trajectory(trajectory, "fuel_used_kg")
    if x_fuel:
        ax2.plot(x_fuel, y_fuel, "-s", color="#dc2626", markersize=2.0,
                 linewidth=1.5, label="Fuel Used")
    ax2.set_ylabel("Fuel Used (kg)", fontsize=8, color="#dc2626")
    ax2.tick_params(axis="y", labelcolor="#dc2626", labelsize=7)

    # Phase boundary markers
    for bx, phase_name in boundaries:
        ax1.axvline(bx, color="#94a3b8", linestyle=":", linewidth=0.8, alpha=0.5)
        ax1.text(
            bx, 1.02, _phase_label(phase_name),
            fontsize=6, color="#64748b", rotation=45,
            ha="left", va="bottom",
            transform=ax1.get_xaxis_transform(),
        )

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="center left")

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "energy_budget", save_dir)


# ---------------------------------------------------------------------------
# Plot: sweep_chart (2x2 grid of metrics vs parameter)
# ---------------------------------------------------------------------------


def plot_sweep_chart(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """2x2 grid showing key metrics vs the swept parameter."""
    _, plt = _require_mpl()
    import numpy as np

    sweep_results = results.get("sweep_results")
    sweep_param = results.get("sweep_parameter")
    if not sweep_results or not sweep_param:
        raise ValueError(
            "No sweep_results in artifact. "
            "sweep_chart requires a run_parameter_sweep artifact."
        )

    title = f"Parameter Sweep: {sweep_param}"
    if case_name:
        title = f"{title} -- {case_name}"

    # Extract converged vs failed points
    param_vals = []
    converged_mask = []
    for pt in sweep_results:
        param_vals.append(float(pt.get(sweep_param, 0)))
        converged_mask.append(pt.get("converged", True))

    # Metrics to plot (pick the first 4 that have data)
    candidate_metrics = [
        ("fuel_burn_kg", "Fuel Burn (kg)"),
        ("OEW_kg", "OEW (kg)"),
        ("MTOW_kg", "MTOW (kg)"),
        ("battery_SOC_final", "Final Battery SOC"),
        ("TOFL_ft", "TOFL (ft)"),
        ("MTOW_margin_lb", "MTOW Margin (lb)"),
    ]

    # Filter to metrics that exist in at least one converged point
    available_metrics = []
    for key, label in candidate_metrics:
        for pt in sweep_results:
            if pt.get("converged") and pt.get(key) is not None:
                available_metrics.append((key, label))
                break
        if len(available_metrics) >= 4:
            break

    if not available_metrics:
        raise ValueError("No plottable metrics found in sweep results")

    n_panels = len(available_metrics)
    cols = min(n_panels, 2)
    rows = (n_panels + 1) // 2

    fig, axes = plt.subplots(rows, cols, figsize=(9.0, 3.5 * rows))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)

    if n_panels == 1:
        axes_flat = [axes]
    else:
        axes_flat = list(np.array(axes).flat)

    x_label = sweep_param.replace("_", " ").title()

    for idx, (metric_key, metric_label) in enumerate(available_metrics):
        ax = axes_flat[idx]
        x_conv, y_conv = [], []
        x_fail, y_fail = [], []

        for i, pt in enumerate(sweep_results):
            val = pt.get(metric_key)
            if val is None:
                continue
            if converged_mask[i]:
                x_conv.append(param_vals[i])
                y_conv.append(float(val))
            else:
                x_fail.append(param_vals[i])
                y_fail.append(float(val))

        if x_conv:
            ax.plot(x_conv, y_conv, "o-", color="#2563eb", markersize=5,
                    linewidth=1.5, label="Converged")
        if x_fail:
            ax.plot(x_fail, y_fail, "x", color="#dc2626", markersize=8,
                    markeredgewidth=2.0, label="Failed")

        ax.set_xlabel(x_label, fontsize=8)
        ax.set_ylabel(metric_label, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        if x_fail:
            ax.legend(fontsize=7)

    # Hide unused axes
    for j in range(n_panels, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "sweep_chart", save_dir)


# ---------------------------------------------------------------------------
# Plot: optimization_history (1x2: objective + DV comparison)
# ---------------------------------------------------------------------------


def plot_optimization_history(
    run_id: str,
    results: dict,
    case_name: str = "",
    *,
    save_dir: str | Path | None = None,
) -> PlotResult:
    """1x2: objective convergence + initial vs optimized DV values."""
    _, plt = _require_mpl()
    import numpy as np

    if "objective_value" not in results:
        raise ValueError(
            "No optimization data in artifact. "
            "optimization_history requires a run_optimization artifact."
        )

    opt_dvs = results.get("optimized_values", {})
    obj_name = results.get("objective", "objective")
    obj_val = results.get("objective_value")
    converged = results.get("optimization_successful", False)
    n_iters = results.get("num_iterations")

    title = "Optimization Results"
    if case_name:
        title = f"{title} -- {case_name}"

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0))
    fig.suptitle(f"{title}\n(run_id: {run_id})", fontsize=9, y=0.99)

    # Left panel: objective summary card
    ax_obj = axes[0]
    ax_obj.set_axis_off()

    status_color = "#059669" if converged else "#dc2626"
    status_text = "Converged" if converged else "Not Converged"

    summary_lines = [
        f"Objective: {obj_name}",
        f"Final Value: {_fmt(obj_val, 4)}",
        f"Status: {status_text}",
        f"Iterations: {n_iters if n_iters is not None else 'N/A'}",
    ]

    text_y = 0.85
    for line in summary_lines:
        color = status_color if "Status:" in line else "#334155"
        ax_obj.text(
            0.1, text_y, line,
            fontsize=10, color=color,
            transform=ax_obj.transAxes,
            fontfamily="monospace",
        )
        text_y -= 0.15

    ax_obj.set_title("Objective Summary", fontsize=9, pad=10)

    # Right panel: optimized DV values bar chart
    ax_dv = axes[1]
    if opt_dvs:
        dv_names = []
        dv_values = []
        for name, val in opt_dvs.items():
            # Shorten long DV names
            short = name.split("|")[-1] if "|" in name else name.split(".")[-1]
            dv_names.append(short)
            dv_values.append(float(val))

        y_pos = np.arange(len(dv_names))
        bars = ax_dv.barh(y_pos, dv_values, color="#2563eb", height=0.6, alpha=0.85)
        ax_dv.set_yticks(y_pos)
        ax_dv.set_yticklabels(dv_names, fontsize=8)
        ax_dv.set_xlabel("Optimized Value", fontsize=8)
        ax_dv.tick_params(axis="x", labelsize=7)
        ax_dv.grid(True, axis="x", alpha=0.3)

        for bar, val in zip(bars, dv_values):
            ax_dv.text(
                bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f"  {val:.4g}", va="center", fontsize=7,
            )

        ax_dv.set_title("Design Variables", fontsize=9, pad=10)
    else:
        ax_dv.set_axis_off()
        ax_dv.text(
            0.5, 0.5, "No design variable data",
            ha="center", va="center", fontsize=10, color="#94a3b8",
            transform=ax_dv.transAxes,
        )

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    return _fig_to_response(fig, run_id, "optimization_history", save_dir)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_DISPATCHERS = {
    "mission_profile": plot_mission_profile,
    "takeoff_profile": plot_takeoff_profile,
    "weight_breakdown": plot_weight_breakdown,
    "performance_summary": plot_performance_summary,
    "energy_budget": plot_energy_budget,
    "sweep_chart": plot_sweep_chart,
    "optimization_history": plot_optimization_history,
}


def generate_ocp_plot(
    plot_type: str,
    run_id: str,
    results: dict,
    case_name: str = "",
    save_dir: str | Path | None = None,
) -> PlotResult:
    """Generate an OpenConcept plot by type. Returns a PlotResult."""
    if plot_type not in OCP_PLOT_TYPES:
        raise ValueError(
            f"Unknown ocp plot_type {plot_type!r}. "
            f"Supported: {sorted(OCP_PLOT_TYPES)}"
        )
    fn = _DISPATCHERS[plot_type]
    return fn(run_id, results, case_name, save_dir=save_dir)
