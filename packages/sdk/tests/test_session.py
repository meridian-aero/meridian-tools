"""Unit tests for Session/SessionManager -- no OAS computation needed.

Migrated from: OpenAeroStruct/oas_mcp/tests/test_session.py

Import mapping applied:
  - oas_mcp.core.session -> hangar.sdk.session.manager
"""

import numpy as np
import pytest
from hangar.sdk.session.manager import Session, SessionManager, _surface_fingerprint


def _make_surface(name="wing", span=10.0):
    return {
        "name": name,
        "mesh": np.zeros((2, 5, 3)),
        "twist_cp": np.zeros(2),
        "span": span,
    }


class TestSurfaceFingerprint:
    def test_same_surface_same_hash(self):
        s = _make_surface()
        assert _surface_fingerprint(s) == _surface_fingerprint(s)

    def test_different_span_different_hash(self):
        s1 = _make_surface(span=10.0)
        s2 = _make_surface(span=20.0)
        assert _surface_fingerprint(s1) != _surface_fingerprint(s2)

    def test_different_mesh_different_hash(self):
        s1 = _make_surface()
        s2 = _make_surface()
        s2["mesh"][0, 0, 0] = 99.0
        assert _surface_fingerprint(s1) != _surface_fingerprint(s2)


class TestSession:
    def test_add_and_retrieve_surface(self):
        session = Session()
        s = _make_surface()
        session.add_surface(s)
        assert "wing" in session.surfaces
        retrieved = session.get_surfaces(["wing"])
        assert retrieved[0] is s

    def test_add_surface_invalidates_cache(self):
        session = Session()
        s = _make_surface()
        session.add_surface(s)

        # Manually plant a fake cached problem
        key = "aero:wing"
        from hangar.sdk.session.manager import _CachedProblem
        fp = _surface_fingerprint(s)
        session._cache[key] = _CachedProblem(
            prob=object(),
            analysis_type="aero",
            surface_fingerprints={"wing": fp},
        )
        assert session.get_cached_problem(["wing"], "aero") is not None

        # Re-adding same name with different surface should clear cache
        s2 = _make_surface(span=20.0)
        session.add_surface(s2)
        assert session.get_cached_problem(["wing"], "aero") is None

    def test_cache_stale_when_surface_modified(self):
        session = Session()
        s = _make_surface()
        session.add_surface(s)

        from hangar.sdk.session.manager import _CachedProblem
        old_fp = _surface_fingerprint(s)
        key = "aero:wing"
        session._cache[key] = _CachedProblem(
            prob=object(),
            analysis_type="aero",
            surface_fingerprints={"wing": old_fp},
        )

        # Mutate the stored surface directly
        session.surfaces["wing"]["span"] = 99.0
        # Cache should now be stale -- returns None and evicts entry
        assert session.get_cached_problem(["wing"], "aero") is None
        assert key not in session._cache

    def test_clear_removes_everything(self):
        session = Session()
        session.add_surface(_make_surface("wing"))
        session.add_surface(_make_surface("tail"))
        session.clear()
        assert session.surfaces == {}
        assert session._cache == {}


class TestSessionManager:
    def test_default_session_always_exists(self):
        mgr = SessionManager()
        s = mgr.get("default")
        assert isinstance(s, Session)

    def test_unknown_session_auto_created(self):
        mgr = SessionManager()
        s = mgr.get("new_session")
        assert isinstance(s, Session)

    def test_same_id_returns_same_session(self):
        mgr = SessionManager()
        assert mgr.get("default") is mgr.get("default")

    def test_reset_clears_all_sessions(self):
        mgr = SessionManager()
        mgr.get("default").add_surface(_make_surface())
        mgr.reset()
        assert len(mgr.get("default").surfaces) == 0


# ---------------------------------------------------------------------------
# Cache pinning (unit level -- no OAS computation)
# ---------------------------------------------------------------------------


class TestSessionPinning:
    def test_pin_adds_to_pinned_by(self):
        session = Session()
        session.add_surface(_make_surface())
        from hangar.sdk.session.manager import _CachedProblem, _surface_fingerprint
        fp = _surface_fingerprint(session.surfaces["wing"])
        session._cache["aero:wing"] = _CachedProblem(
            prob=object(), analysis_type="aero",
            surface_fingerprints={"wing": fp},
        )
        result = session.pin_run("run-1", ["wing"], "aero")
        assert result is True
        assert "run-1" in session._cache["aero:wing"].pinned_by

    def test_unpin_removes_from_pinned_by(self):
        session = Session()
        session.add_surface(_make_surface())
        from hangar.sdk.session.manager import _CachedProblem, _surface_fingerprint
        fp = _surface_fingerprint(session.surfaces["wing"])
        session._cache["aero:wing"] = _CachedProblem(
            prob=object(), analysis_type="aero",
            surface_fingerprints={"wing": fp},
        )
        session.pin_run("run-1", ["wing"], "aero")
        result = session.unpin_run("run-1")
        assert result is True
        assert "run-1" not in session._cache["aero:wing"].pinned_by

    def test_is_pinned_returns_true(self):
        session = Session()
        session.add_surface(_make_surface())
        from hangar.sdk.session.manager import _CachedProblem, _surface_fingerprint
        fp = _surface_fingerprint(session.surfaces["wing"])
        session._cache["aero:wing"] = _CachedProblem(
            prob=object(), analysis_type="aero",
            surface_fingerprints={"wing": fp},
        )
        session.pin_run("run-1", ["wing"], "aero")
        assert session.is_pinned("run-1") is True
        assert session.is_pinned("run-2") is False

    def test_pinned_prevents_cache_eviction(self):
        """A pinned problem should survive add_surface with a new fingerprint."""
        session = Session()
        session.add_surface(_make_surface())
        from hangar.sdk.session.manager import _CachedProblem, _surface_fingerprint
        fp = _surface_fingerprint(session.surfaces["wing"])
        session._cache["aero:wing"] = _CachedProblem(
            prob=object(), analysis_type="aero",
            surface_fingerprints={"wing": fp},
        )
        session.pin_run("run-1", ["wing"], "aero")

        # Re-add surface with different span -- should NOT evict pinned cache
        session.add_surface(_make_surface(span=20.0))
        assert "aero:wing" in session._cache


# ---------------------------------------------------------------------------
# Session configure (unit level)
# ---------------------------------------------------------------------------


class TestSessionConfigure:
    def test_configure_sets_detail_level(self):
        session = Session()
        session.configure(default_detail_level="standard")
        assert session.defaults.default_detail_level == "standard"

    def test_configure_sets_project(self):
        session = Session()
        session.configure(project="my_project")
        assert session.project == "my_project"

    def test_configure_sets_retention_max_count(self):
        session = Session()
        session.configure(retention_max_count=10)
        assert session.defaults.retention_max_count == 10

    def test_retention_max_count_in_to_dict(self):
        session = Session()
        session.configure(retention_max_count=5)
        d = session.defaults.to_dict()
        assert d["retention_max_count"] == 5
