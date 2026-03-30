"""Optimization iteration tracking via OpenMDAO SqliteRecorder.

Migrated from: OpenAeroStruct/oas_mcp/core/convergence.py
"""

from __future__ import annotations

import copy
import os
from typing import Any

import numpy as np

from hangar.sdk.telemetry import logger


# ---------------------------------------------------------------------------
# Optimization iteration tracker
# ---------------------------------------------------------------------------


class OptimizationTracker:
    """Capture optimizer iteration history for visualization.

    Attaches an OpenMDAO SqliteRecorder to the driver before ``run_driver()``
    to capture per-iteration objective, design variable, and constraint values.
    Falls back gracefully (with logged warnings) if the recorder is
    unavailable.

    Usage
    -----
        tracker = OptimizationTracker()
        initial_dvs = tracker.record_initial(prob, dv_path_map)
        tracker.attach(prob)
        prob.run_driver()
        history = tracker.extract(dv_path_map, obj_path, constraint_path_map)
    """

    def __init__(self) -> None:
        self._tmp_path: str | None = None
        self._recorder: Any = None
        self._solver_tmp_path: str | None = None
        self._solver_recorder: Any = None

    def record_initial(self, prob: Any, dv_path_map: dict[str, str]) -> dict:
        """Read initial design variable values before optimization.

        Parameters
        ----------
        prob:
            A set-up (but not yet run) ``om.Problem``.
        dv_path_map:
            Mapping of user DV name -> OpenMDAO variable path.

        Returns
        -------
        dict of DV name -> initial value (as Python list)
        """
        initial: dict = {}
        for name, path in dv_path_map.items():
            try:
                val = np.asarray(prob.get_val(path)).tolist()
                initial[name] = val
            except Exception as exc:
                logger.warning("Failed to read initial DV %r (%s): %s", name, path, exc)
        return initial

    def attach(self, prob: Any) -> bool:
        """Attach a SqliteRecorder to ``prob.driver``.

        Must be called *before* ``prob.run_driver()``.  Returns True if
        the recorder was successfully attached, False otherwise.
        """
        import tempfile
        try:
            import openmdao.api as om
            fd, tmp_path = tempfile.mkstemp(suffix=".sql")
            os.close(fd)
            # SqliteRecorder creates the file fresh -- delete the placeholder
            os.unlink(tmp_path)
            self._tmp_path = tmp_path
            self._recorder = om.SqliteRecorder(tmp_path)
            prob.driver.add_recorder(self._recorder)
            return True
        except Exception as exc:
            logger.warning(
                "SqliteRecorder unavailable -- convergence tracking disabled: %s", exc,
            )
            self._tmp_path = None
            self._recorder = None
            return False

    def attach_solver(self, prob: Any, coupled_group_path: str) -> bool:
        """Attach a SqliteRecorder to the nonlinear solver for sub-iteration tracking.

        Parameters
        ----------
        prob:
            A set-up ``om.Problem``.
        coupled_group_path:
            Dot-path to the coupled group, e.g. ``"AS_point_0.coupled"``.

        Returns
        -------
        True if the recorder was successfully attached, False otherwise.
        """
        import tempfile
        try:
            import openmdao.api as om
            group = prob.model
            for attr in coupled_group_path.split("."):
                group = getattr(group, attr)
            fd, tmp_path = tempfile.mkstemp(suffix="_solver.sql")
            os.close(fd)
            os.unlink(tmp_path)
            self._solver_tmp_path = tmp_path
            self._solver_recorder = om.SqliteRecorder(tmp_path)
            group.nonlinear_solver.add_recorder(self._solver_recorder)
            return True
        except Exception as exc:
            logger.warning(
                "Failed to attach solver recorder at %r -- sub-iteration tracking disabled: %s",
                coupled_group_path, exc,
            )
            self._solver_tmp_path = None
            self._solver_recorder = None
            return False

    def extract(
        self,
        dv_path_map: dict[str, str],
        obj_path: str,
        constraint_path_map: dict[str, str] | None = None,
    ) -> dict:
        """Shut down recorder and extract per-iteration history.

        Must be called *after* ``prob.run_driver()``.

        Parameters
        ----------
        dv_path_map:
            Same mapping of user DV name -> OpenMDAO path used in
            :meth:`record_initial`.
        obj_path:
            Full OpenMDAO path of the objective variable
            (e.g. ``"aero.CD"`` or ``"AS_point_0.fuelburn"``).
        constraint_path_map:
            Optional mapping of constraint name -> OpenMDAO path.  When
            provided, per-iteration constraint values are captured.

        Returns
        -------
        dict with:
          - ``num_iterations``: number of driver cases recorded
          - ``objective_values``: list of per-iteration objective floats
          - ``dv_history``: dict of DV name -> list of per-iteration values
          - ``constraint_history``: dict of constraint name -> list of per-iteration scalar values
          - ``solver_history``: dict with sub-iteration data (only if attach_solver was called)
        """
        empty: dict = {
            "num_iterations": 0,
            "objective_values": [],
            "dv_history": {},
            "constraint_history": {},
        }

        if self._recorder is None:
            return empty

        try:
            import openmdao.api as om
            self._recorder.shutdown()

            if not self._tmp_path or not os.path.exists(self._tmp_path):
                return empty

            cr = om.CaseReader(self._tmp_path)
            case_ids = cr.list_cases("driver", out_stream=None)

            objective_values: list[float] = []
            dv_history: dict[str, list] = {name: [] for name in dv_path_map}
            constraint_history: dict[str, list[float]] = {}
            if constraint_path_map:
                constraint_history = {name: [] for name in constraint_path_map}

            for case_id in case_ids:
                case = cr.get_case(case_id)

                # Use the proper CaseReader API so subsystem paths like
                # "wing.twist_cp" are found regardless of promotion level.
                try:
                    case_dvs = case.get_design_vars(scaled=False) or {}
                except Exception:
                    case_dvs = {}
                try:
                    case_objs = case.get_objectives(scaled=False) or {}
                except Exception:
                    case_objs = {}

                # Objective value -- prefer dedicated API, fall back to direct lookup
                if obj_path:
                    obj_val = case_objs.get(obj_path)
                    if obj_val is None:
                        # Fallback: iterate the single objective dict entry
                        for v in case_objs.values():
                            obj_val = v
                            break
                    if obj_val is None:
                        try:
                            obj_val = case[obj_path]
                        except Exception:
                            pass
                    if obj_val is not None:
                        try:
                            objective_values.append(float(np.asarray(obj_val).ravel()[0]))
                        except Exception:
                            pass

                # DV values -- use get_design_vars() dict for reliable lookup
                for dv_name, dv_path in dv_path_map.items():
                    raw = case_dvs.get(dv_path)
                    if raw is None:
                        # Fallback: direct index (works for top-level promoted vars)
                        try:
                            raw = case[dv_path]
                        except Exception:
                            pass
                    if raw is not None:
                        try:
                            dv_history[dv_name].append(np.asarray(raw).tolist())
                        except Exception:
                            pass

                # Constraint values
                if constraint_path_map:
                    try:
                        case_cons = case.get_constraints(scaled=False) or {}
                    except Exception:
                        case_cons = {}
                    for con_name, con_path in constraint_path_map.items():
                        raw = case_cons.get(con_path)
                        if raw is None:
                            try:
                                raw = case[con_path]
                            except Exception:
                                pass
                        if raw is not None:
                            try:
                                arr = np.asarray(raw)
                                # Reduce array-valued constraints (e.g. failure)
                                # to worst-case scalar
                                if arr.size > 1:
                                    scalar = float(np.max(np.abs(arr)))
                                else:
                                    scalar = float(arr.ravel()[0])
                                constraint_history[con_name].append(scalar)
                            except Exception:
                                pass

            result = {
                "num_iterations": len(case_ids),
                "objective_values": objective_values,
                "dv_history": {k: v for k, v in dv_history.items() if v},
                "constraint_history": {k: v for k, v in constraint_history.items() if v},
            }

            # Sub-iteration solver history (if recorded)
            solver_hist = self._extract_solver_history()
            if solver_hist:
                result["solver_history"] = solver_hist

            return result
        except Exception as exc:
            logger.warning("Failed to extract optimization history: %s", exc)
            return empty
        finally:
            self._cleanup_tmp(self._tmp_path)
            self._recorder = None
            self._tmp_path = None

    def _extract_solver_history(self, max_driver_iters: int = 50) -> dict | None:
        """Extract sub-iteration residual norms from the solver recorder.

        Returns None if no solver recorder was attached.
        """
        if self._solver_recorder is None:
            return None

        try:
            import openmdao.api as om
            self._solver_recorder.shutdown()

            if not self._solver_tmp_path or not os.path.exists(self._solver_tmp_path):
                return None

            cr = om.CaseReader(self._solver_tmp_path)
            case_ids = cr.list_cases("root.nonlinear_solver", out_stream=None)
            if not case_ids:
                # Try without specific source -- some OM versions differ
                case_ids = cr.list_cases(out_stream=None)

            if not case_ids:
                return None

            # Group sub-iterations by driver iteration (parent case)
            driver_iters: dict[int, list[float]] = {}
            current_driver_iter = 0

            for case_id in case_ids:
                try:
                    case = cr.get_case(case_id)
                    # Extract residual norm
                    abs_err = None
                    if hasattr(case, "abs_err"):
                        abs_err = float(case.abs_err)
                    elif hasattr(case, "residuals"):
                        # Compute L2 norm of residual vector
                        resids = case.residuals
                        if resids:
                            norms = [float(np.linalg.norm(np.asarray(v))) for v in resids.values()]
                            abs_err = float(np.linalg.norm(norms))

                    if abs_err is not None:
                        # Detect new driver iteration by checking parent
                        parent = getattr(case, "parent", None)
                        if parent and parent != getattr(self, "_last_parent", None):
                            current_driver_iter += 1
                            self._last_parent = parent

                        driver_iters.setdefault(current_driver_iter, []).append(abs_err)
                except Exception:
                    continue

            if not driver_iters:
                return None

            # Cap to most recent N driver iterations
            all_iters = sorted(driver_iters.keys())
            if len(all_iters) > max_driver_iters:
                all_iters = all_iters[-max_driver_iters:]

            solver_iterations = [
                {"driver_iter": i, "residuals": driver_iters[i]}
                for i in all_iters
            ]
            total = sum(len(v) for v in driver_iters.values())

            return {
                "solver_iterations": solver_iterations,
                "total_solver_iters": total,
            }
        except Exception as exc:
            logger.warning("Failed to extract solver sub-iteration history: %s", exc)
            return None
        finally:
            self._cleanup_tmp(self._solver_tmp_path)
            self._solver_recorder = None
            self._solver_tmp_path = None

    @staticmethod
    def _cleanup_tmp(path: str | None) -> None:
        """Remove a temporary file, ignoring errors."""
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Convergence history summarization for MCP response payloads
# ---------------------------------------------------------------------------


def summarize_convergence_history(history: dict, max_iters: int = 50) -> dict:
    """Truncate convergence history for MCP response payload.

    Returns a new dict (does not mutate *history*).  If the history has more
    than *max_iters* iterations, the returned dict keeps only the last
    *max_iters* entries and sets ``truncated=True``.

    Solver sub-iteration data (``solver_history``) is always excluded from the
    summary -- it is artifact-only.
    """
    result = copy.deepcopy(history)

    # Remove solver history from MCP response (artifact-only)
    result.pop("solver_history", None)

    n = result.get("num_iterations", 0)
    if n <= max_iters:
        return result

    # Truncate to last max_iters entries
    obj_vals = result.get("objective_values", [])
    if len(obj_vals) > max_iters:
        result["objective_values"] = obj_vals[-max_iters:]

    for dv_name, iters in result.get("dv_history", {}).items():
        if len(iters) > max_iters:
            result["dv_history"][dv_name] = iters[-max_iters:]

    for con_name, iters in result.get("constraint_history", {}).items():
        if len(iters) > max_iters:
            result["constraint_history"][con_name] = iters[-max_iters:]

    result["truncated"] = True
    result["full_num_iterations"] = n

    return result
