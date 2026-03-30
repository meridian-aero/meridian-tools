"""Physics and numerics validation for pyCycle results.

Each check returns a ValidationFinding from the SDK.
"""

from __future__ import annotations

from hangar.sdk.validation.checks import ValidationFinding, findings_to_dict  # noqa: F401


# ---------------------------------------------------------------------------
# TSFC checks
# ---------------------------------------------------------------------------

def _check_tsfc_positive(tsfc: float | None) -> ValidationFinding:
    if tsfc is None:
        return ValidationFinding(
            check_id="tsfc.available",
            category="numerics",
            severity="warning",
            confidence="high",
            passed=False,
            message="TSFC not available in results.",
            remediation="Check that Performance element is connected.",
        )
    if tsfc <= 0:
        return ValidationFinding(
            check_id="tsfc.positive",
            category="physics",
            severity="error",
            confidence="high",
            passed=False,
            message=f"TSFC is non-positive ({tsfc:.6f}).",
            remediation="Check combustor FAR and fuel flow connections.",
        )
    return ValidationFinding(
        check_id="tsfc.positive",
        category="physics",
        severity="info",
        confidence="high",
        passed=True,
        message=f"TSFC = {tsfc:.5f} lbm/hr/lbf.",
    )


def _check_tsfc_reasonable(
    tsfc: float | None, archetype: str = "turbojet"
) -> ValidationFinding:
    if tsfc is None:
        return ValidationFinding(
            check_id="tsfc.reasonable",
            category="physics",
            severity="info",
            confidence="low",
            passed=True,
            message="TSFC not available; skipping range check.",
        )
    ranges = {
        "turbojet": (0.5, 2.5),
        "hbtf": (0.3, 1.2),
        "turboshaft": (0.3, 1.0),
    }
    lo, hi = ranges.get(archetype, (0.1, 3.0))
    if lo <= tsfc <= hi:
        return ValidationFinding(
            check_id="tsfc.reasonable",
            category="physics",
            severity="info",
            confidence="medium",
            passed=True,
            message=f"TSFC = {tsfc:.5f} is within typical {archetype} range [{lo}, {hi}].",
        )
    return ValidationFinding(
        check_id="tsfc.reasonable",
        category="physics",
        severity="warning",
        confidence="medium",
        passed=False,
        message=f"TSFC = {tsfc:.5f} outside typical {archetype} range [{lo}, {hi}].",
        remediation="Verify component efficiencies and pressure ratios.",
    )


# ---------------------------------------------------------------------------
# Thrust checks
# ---------------------------------------------------------------------------

def _check_thrust_positive(fn: float | None) -> ValidationFinding:
    if fn is None:
        return ValidationFinding(
            check_id="thrust.available",
            category="numerics",
            severity="warning",
            confidence="high",
            passed=False,
            message="Net thrust not available in results.",
        )
    if fn <= 0:
        return ValidationFinding(
            check_id="thrust.positive",
            category="physics",
            severity="error",
            confidence="high",
            passed=False,
            message=f"Net thrust is non-positive ({fn:.1f} lbf).",
            remediation="Check nozzle expansion, inlet ram drag, flight conditions.",
        )
    return ValidationFinding(
        check_id="thrust.positive",
        category="physics",
        severity="info",
        confidence="high",
        passed=True,
        message=f"Fn = {fn:.1f} lbf.",
    )


# ---------------------------------------------------------------------------
# OPR checks
# ---------------------------------------------------------------------------

def _check_opr_reasonable(opr: float | None) -> ValidationFinding:
    if opr is None:
        return ValidationFinding(
            check_id="opr.available",
            category="numerics",
            severity="info",
            confidence="low",
            passed=True,
            message="OPR not available; skipping check.",
        )
    if 2.0 <= opr <= 60.0:
        return ValidationFinding(
            check_id="opr.reasonable",
            category="physics",
            severity="info",
            confidence="medium",
            passed=True,
            message=f"OPR = {opr:.2f} is within typical range [2, 60].",
        )
    return ValidationFinding(
        check_id="opr.reasonable",
        category="physics",
        severity="warning",
        confidence="medium",
        passed=False,
        message=f"OPR = {opr:.2f} is outside typical range [2, 60].",
        remediation="Verify compressor pressure ratios.",
    )


# ---------------------------------------------------------------------------
# T4 checks
# ---------------------------------------------------------------------------

def _check_t4_within_limits(t4: float | None) -> ValidationFinding:
    if t4 is None:
        return ValidationFinding(
            check_id="t4.available",
            category="numerics",
            severity="info",
            confidence="low",
            passed=True,
            message="T4 not available; skipping check.",
        )
    if t4 <= 3600:
        return ValidationFinding(
            check_id="t4.within_limits",
            category="physics",
            severity="info",
            confidence="medium",
            passed=True,
            message=f"T4 = {t4:.0f} degR is below material limit (3600 degR).",
        )
    return ValidationFinding(
        check_id="t4.within_limits",
        category="physics",
        severity="warning",
        confidence="medium",
        passed=False,
        message=f"T4 = {t4:.0f} degR exceeds typical material limit (3600 degR).",
        remediation="Reduce T4 target or improve turbine cooling.",
    )


# ---------------------------------------------------------------------------
# Shaft balance check
# ---------------------------------------------------------------------------

def _check_shaft_balance(pwr_net: float | None) -> ValidationFinding:
    if pwr_net is None:
        return ValidationFinding(
            check_id="shaft.balance",
            category="numerics",
            severity="info",
            confidence="low",
            passed=True,
            message="Shaft net power not available; skipping check.",
        )
    if abs(pwr_net) < 1.0:  # hp
        return ValidationFinding(
            check_id="shaft.balance",
            category="physics",
            severity="info",
            confidence="high",
            passed=True,
            message=f"Shaft power balanced (net = {pwr_net:.4f} hp).",
        )
    return ValidationFinding(
        check_id="shaft.balance",
        category="physics",
        severity="warning",
        confidence="high",
        passed=False,
        message=f"Shaft power imbalance: net = {pwr_net:.2f} hp.",
        remediation="Check that turbine PR balance converged.",
    )


# ---------------------------------------------------------------------------
# Composite validation runners
# ---------------------------------------------------------------------------

def validate_cycle_results(
    results: dict,
    archetype: str = "turbojet",
) -> list[ValidationFinding]:
    """Run all physics/numerics checks on a cycle result set."""
    perf = results.get("performance", {})
    comps = results.get("components", {})

    findings = [
        _check_tsfc_positive(perf.get("TSFC")),
        _check_tsfc_reasonable(perf.get("TSFC"), archetype),
        _check_thrust_positive(perf.get("Fn")),
        _check_opr_reasonable(perf.get("OPR")),
    ]

    # T4 from burner exit
    flow_stations = results.get("flow_stations", {})
    burner_exit = flow_stations.get("burner.Fl_O", {})
    t4 = burner_exit.get("tot:T")
    findings.append(_check_t4_within_limits(t4))

    # Shaft balance
    for shaft_name, shaft_data in comps.items():
        if "pwr_net" in shaft_data:
            findings.append(_check_shaft_balance(shaft_data.get("pwr_net")))

    return findings
