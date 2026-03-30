"""Typed error taxonomy for Hangar tool servers.

Migrated from: OpenAeroStruct/oas_mcp/core/errors.py
"""

from __future__ import annotations


class HangarError(Exception):
    """Base class for all typed Hangar tool server errors."""

    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "code": self.error_code,
            "message": str(self),
            "details": self.details,
        }


class UserInputError(HangarError):
    """Invalid user input — bad parameter values, missing surfaces, etc.

    Agents should inspect `details` for which field is wrong and the
    allowed values before retrying.
    """

    error_code = "USER_INPUT_ERROR"


class SolverConvergenceError(HangarError):
    """OpenMDAO solver failed to converge.

    Agents should consider: coarser mesh, stricter initial alpha range,
    or lower Mach number before retrying.  `details` may include
    `iterations`, `final_residual`, and `solver_type`.
    """

    error_code = "SOLVER_CONVERGENCE_ERROR"


class CacheEvictedError(HangarError):
    """The cached OpenMDAO problem was evicted from session memory.

    The artifact (run_id) is still on disk and can be retrieved via
    get_artifact().  To run further analyses, call create_surface() again
    then rerun the analysis.
    """

    error_code = "CACHE_EVICTED_ERROR"


class InternalError(HangarError):
    """Unexpected internal server error — likely a bug.

    Agents should NOT retry automatically.  Surface the full `message`
    and `details` to the user for reporting.
    """

    error_code = "INTERNAL_ERROR"
