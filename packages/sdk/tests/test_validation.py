"""Unit tests for the generic validation framework (ValidationFinding, findings_to_dict)
and the requirements checking system.

Migrated from: OpenAeroStruct/oas_mcp/tests/test_validation.py (generic parts)

Import mapping applied:
  - oas_mcp.core.validation.ValidationFinding -> hangar.sdk.validation.checks.ValidationFinding
  - oas_mcp.core.validation.findings_to_dict -> hangar.sdk.validation.checks.findings_to_dict
  - oas_mcp.core.requirements.check_requirements -> hangar.sdk.validation.requirements.check_requirements
"""

from __future__ import annotations

import pytest
from hangar.sdk.validation.checks import (
    ValidationFinding,
    findings_to_dict,
)
from hangar.sdk.validation.requirements import check_requirements


# ---------------------------------------------------------------------------
# ValidationFinding
# ---------------------------------------------------------------------------


class TestValidationFinding:
    def test_to_dict_has_all_keys(self):
        f = ValidationFinding(
            check_id="physics.cd_positive",
            category="physics",
            severity="error",
            confidence="high",
            passed=False,
            message="CD < 0",
            remediation="fix it",
        )
        d = f.to_dict()
        assert d["check_id"] == "physics.cd_positive"
        assert d["severity"] == "error"
        assert d["passed"] is False
        assert d["remediation"] == "fix it"

    def test_findings_to_dict_all_passed(self):
        findings = [
            ValidationFinding("a.b", "physics", "error", "high", True, "OK"),
            ValidationFinding("a.c", "physics", "warning", "medium", True, "OK"),
        ]
        d = findings_to_dict(findings)
        assert d["passed"] is True
        assert d["error_count"] == 0
        assert d["warning_count"] == 0
        assert d["findings"] == []  # no failed findings

    def test_findings_to_dict_with_failures(self):
        findings = [
            ValidationFinding("a", "physics", "error", "high", False, "bad"),
            ValidationFinding("b", "physics", "warning", "medium", False, "warn"),
            ValidationFinding("c", "physics", "info", "low", False, "info"),
            ValidationFinding("d", "physics", "info", "low", True, "ok"),
        ]
        d = findings_to_dict(findings)
        assert d["passed"] is False
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert d["info_count"] == 1
        assert len(d["findings"]) == 3   # only failed findings
        assert len(d["all_findings"]) == 4


# ---------------------------------------------------------------------------
# check_requirements
# ---------------------------------------------------------------------------


class TestCheckRequirements:
    def _results(self):
        return {
            "CL": 0.5,
            "CD": 0.035,
            "L_over_D": 14.3,
            "surfaces": {"wing": {"failure": -0.3, "CL": 0.5}},
        }

    def test_satisfied_requirement_passes(self):
        reqs = [{"path": "CL", "operator": ">=", "value": 0.4, "label": "min_CL"}]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is True
        assert report["results"][0]["passed"] is True

    def test_violated_requirement_fails(self):
        reqs = [{"path": "CL", "operator": ">=", "value": 0.6, "label": "high_CL"}]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is False
        assert report["results"][0]["passed"] is False
        assert report["results"][0]["actual"] == pytest.approx(0.5)

    def test_nested_path_resolves(self):
        reqs = [{"path": "surfaces.wing.failure", "operator": "<", "value": 0.0}]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is True

    def test_missing_path_fails(self):
        reqs = [{"path": "surfaces.tail.failure", "operator": "<", "value": 0.0}]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is False
        assert "not found" in report["results"][0].get("error", "")

    def test_unknown_operator_fails(self):
        reqs = [{"path": "CL", "operator": "~=", "value": 0.5}]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is False
        assert "Unknown operator" in report["results"][0].get("error", "")

    def test_multiple_requirements_all_pass(self):
        reqs = [
            {"path": "CL", "operator": ">=", "value": 0.4},
            {"path": "CD", "operator": "<", "value": 0.1},
            {"path": "L_over_D", "operator": ">", "value": 10.0},
        ]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is True
        assert report["passed_count"] == 3

    def test_partial_pass_partial_fail(self):
        reqs = [
            {"path": "CL", "operator": ">=", "value": 0.4},  # passes
            {"path": "CL", "operator": ">=", "value": 0.8},  # fails
        ]
        report = check_requirements(reqs, self._results())
        assert report["passed"] is False
        assert report["passed_count"] == 1
        assert report["total"] == 2

    def test_empty_requirements_passes(self):
        report = check_requirements([], self._results())
        assert report["passed"] is True
        assert report["total"] == 0
