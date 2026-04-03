"""OpenMDAO recorder configuration and data import.

Reads data from OpenMDAO's SqliteRecorder output via the CaseReader
API and imports it into the omd analysis database.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from hangar.omd.db import record_run_case, record_run_cases_batch

logger = logging.getLogger(__name__)


def import_recorder_data(
    recorder_path: Path,
    run_id: str,
) -> dict:
    """Import data from OpenMDAO's SqliteRecorder into the analysis DB.

    Uses the CaseReader API for cross-version compatibility.

    Args:
        recorder_path: Path to the OpenMDAO recorder SQLite file.
        run_id: Run entity ID in the analysis DB.

    Returns:
        Dict with case_count and storage_bytes.
    """
    import openmdao.api as om

    reader = om.CaseReader(str(recorder_path))

    cases = []
    iteration = 0

    # Import driver cases
    driver_cases = reader.list_cases("driver", recurse=False, out_stream=None)
    for case_id in driver_cases:
        case = reader.get_case(case_id)
        data = _extract_case_data(case)
        cases.append({
            "iteration": iteration,
            "case_type": "driver",
            "data": data,
        })
        iteration += 1

    # Import problem (final) cases
    problem_cases = reader.list_cases("problem", recurse=False, out_stream=None)
    for case_id in problem_cases:
        case = reader.get_case(case_id)
        data = _extract_case_data(case)
        cases.append({
            "iteration": iteration,
            "case_type": "final",
            "data": data,
        })
        iteration += 1

    if cases:
        record_run_cases_batch(run_id, cases)

    storage_bytes = os.path.getsize(recorder_path) if recorder_path.exists() else 0

    logger.info(
        "Imported %d cases for run %s (%.1f KB)",
        len(cases), run_id, storage_bytes / 1024,
    )

    return {
        "case_count": len(cases),
        "storage_bytes": storage_bytes,
    }


def _extract_case_data(case) -> dict:
    """Extract variable data from an OpenMDAO Case object.

    Args:
        case: OpenMDAO Case object from CaseReader.

    Returns:
        Dict of variable_name -> value.
    """
    import numpy as np

    data = {}

    # Get all outputs
    try:
        outputs = case.list_outputs(out_stream=None, return_format="dict")
        for name, info in outputs.items():
            val = info.get("val", info.get("value"))
            if val is not None:
                if isinstance(val, np.ndarray):
                    if val.size == 1:
                        data[name] = float(val.flat[0])
                    else:
                        data[name] = val.tolist()
                else:
                    data[name] = val
    except Exception as exc:
        logger.debug("Could not list outputs for case: %s", exc)

    return data
