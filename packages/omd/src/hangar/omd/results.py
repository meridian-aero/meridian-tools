"""Query and format analysis results from the analysis DB."""

from __future__ import annotations

from pathlib import Path

from hangar.omd.db import (
    init_analysis_db,
    query_run_results as _query_cases,
    query_entity,
)


def get_results(
    run_id: str,
    variables: list[str] | None = None,
    summary: bool = False,
    db_path: Path | None = None,
) -> dict:
    """Query results for a run.

    Args:
        run_id: The run entity ID to query.
        variables: Specific variable names to return. None = all.
        summary: If True, return only the final case with condensed output.
        db_path: Path to analysis DB (initializes if needed).

    Returns:
        Dict with run_id, entity info, and cases (or summary).
    """
    init_analysis_db(db_path)

    entity = query_entity(run_id)
    if entity is None:
        return {"run_id": run_id, "error": "Run not found"}

    cases = _query_cases(run_id, variables=variables)

    if summary:
        # Return only the final case
        final_cases = [c for c in cases if c["case_type"] == "final"]
        if final_cases:
            return {
                "run_id": run_id,
                "entity": entity,
                "case_count": len(cases),
                "final": final_cases[-1]["data"],
            }
        elif cases:
            return {
                "run_id": run_id,
                "entity": entity,
                "case_count": len(cases),
                "final": cases[-1]["data"],
            }
        else:
            return {
                "run_id": run_id,
                "entity": entity,
                "case_count": 0,
                "final": {},
            }

    return {
        "run_id": run_id,
        "entity": entity,
        "cases": cases,
    }
