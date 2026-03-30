"""Physics validation framework — findings model and generic checks.

These checks are intentionally self-contained — they depend only on Python stdlib
and basic data structures, not on any SDK infrastructure like the provenance DB
or session manager. This makes them extractable to the range-safety repo later.

Migrated from: OpenAeroStruct/oas_mcp/core/validation.py (generic parts)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ValidationFinding:
    check_id: str
    category: str  # physics | numerics | constraints | stability
    severity: str  # error | warning | info
    confidence: str  # high | medium | low
    passed: bool
    message: str
    remediation: str = ""

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "passed": self.passed,
            "message": self.message,
            "remediation": self.remediation,
        }


def findings_to_dict(findings: list[ValidationFinding]) -> dict:
    """Aggregate findings into a block suitable for the response envelope."""
    errors = [f for f in findings if not f.passed and f.severity == "error"]
    warnings = [f for f in findings if not f.passed and f.severity == "warning"]
    infos = [f for f in findings if not f.passed and f.severity == "info"]
    return {
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "info_count": len(infos),
        "findings": [f.to_dict() for f in findings if not f.passed],
        "all_findings": [f.to_dict() for f in findings],
    }


# ---------------------------------------------------------------------------
# Generic checks
# ---------------------------------------------------------------------------


def check_cd_positive(CD: float) -> ValidationFinding:
    passed = CD > 0
    return ValidationFinding(
        check_id="physics.cd_positive",
        category="physics",
        severity="error",
        confidence="high",
        passed=passed,
        message=f"CD = {CD:.6f} (must be > 0)" if not passed else f"CD = {CD:.6f} > 0 \u2713",
        remediation="Negative CD violates physics. Check mesh quality and that viscous/wave drag is correctly configured.",
    )


def check_cl_reasonable(CL: float, alpha: float | None) -> ValidationFinding:
    """CL should be reasonable — context-aware for alpha sweeps with negative alpha."""
    # For negative alpha, negative CL is expected
    if alpha is not None and alpha < -5.0:
        # Allow negative CL but check it's not absurdly large
        passed = abs(CL) < 5.0
        message = (
            f"CL = {CL:.4f} at alpha = {alpha:.1f}\u00b0 (negative CL expected for negative alpha)"
            if passed
            else f"|CL| = {abs(CL):.4f} seems unreasonably large at alpha = {alpha:.1f}\u00b0"
        )
        remediation = "Very large |CL| at negative alpha may indicate mesh or solver issue."
    else:
        # Positive alpha: CL should generally be positive and < ~3
        passed = -0.5 <= CL <= 3.0
        message = (
            f"CL = {CL:.4f} is in expected range [-0.5, 3.0]"
            if passed
            else f"CL = {CL:.4f} is outside expected range [-0.5, 3.0]"
        )
        remediation = (
            "CL > 3 may indicate stall or mesh issues. CL < -0.5 at positive alpha is unusual. "
            "Check twist, angle of attack, and mesh quality."
        )
    return ValidationFinding(
        check_id="physics.cl_reasonable",
        category="physics",
        severity="warning",
        confidence="medium",
        passed=passed,
        message=message,
        remediation=remediation if not passed else "",
    )


def check_ld_reasonable(CL: float, CD: float, alpha: float | None) -> ValidationFinding:
    """L/D should be reasonable — positive at moderate positive alpha."""
    if CD <= 0:
        return ValidationFinding(
            check_id="physics.ld_reasonable",
            category="physics",
            severity="info",
            confidence="low",
            passed=True,
            message="L/D check skipped: CD \u2264 0 (see cd_positive check)",
        )
    LD = CL / CD
    # Context-aware: skip check for obviously negative-alpha cases
    if alpha is not None and alpha < 0.0:
        return ValidationFinding(
            check_id="physics.ld_reasonable",
            category="physics",
            severity="info",
            confidence="low",
            passed=True,
            message=f"L/D = {LD:.2f} (skipping positive-L/D check for negative alpha = {alpha:.1f}\u00b0)",
        )
    passed = LD > 0
    return ValidationFinding(
        check_id="physics.ld_reasonable",
        category="physics",
        severity="warning",
        confidence="medium",
        passed=passed,
        message=f"L/D = {LD:.2f}" + (" > 0 \u2713" if passed else " \u2264 0 \u2014 unexpected at positive alpha"),
        remediation="Negative L/D at positive alpha suggests CL < 0. Check wing orientation and twist.",
    )


def check_cd_not_too_large(CD: float) -> ValidationFinding:
    """CD > 1.0 is physically implausible for a lifting wing."""
    passed = CD < 1.0
    return ValidationFinding(
        check_id="physics.cd_not_too_large",
        category="physics",
        severity="error",
        confidence="high",
        passed=passed,
        message=f"CD = {CD:.4f} < 1.0 \u2713" if passed else f"CD = {CD:.4f} \u2265 1.0 \u2014 physically implausible",
        remediation="CD \u2265 1 is physically impossible for a subsonic lifting wing. Check mesh, Mach, and drag model settings.",
    )
