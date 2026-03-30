"""Tests for CLI visualization features (Layers 1-3).

Migrated from: OpenAeroStruct/oas_mcp/tests/test_cli_visualization.py

Import mapping applied:
  oas_mcp.core.plotting          -> hangar.oas.tools (plotting utilities)
  oas_mcp.core.session           -> hangar.sdk.session.manager
  oas_mcp.provenance.viewer_server -> hangar.sdk.viz.viewer_server
  oas_mcp.core.artifacts         -> hangar.sdk.artifacts.store
  oas_mcp.server                 -> hangar.oas.server
  oas_mcp.core.viewer_routes     -> hangar.sdk.viz.viewer_routes

Layer 1: PNG save-to-disk via save_dir parameter
Layer 2: /dashboard route on viewer servers
Layer 3: visualization_output session setting and per-call output override
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from hangar.sdk.viz.plotting import (
    PlotResult,
    generate_plot,
    plot_lift_distribution,
)
from hangar.sdk.session.manager import Session, SessionDefaults


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_ID = "test-cli-viz-0001"


def _make_lift_results():
    """Minimal results dict with sectional Cl data."""
    return {
        "CL": 0.5,
        "sectional_data": {
            "wing": {
                "Cl": [0.3, 0.4, 0.5, 0.45, 0.35, 0.2],
                "y_span_norm": [0.0, 0.14, 0.29, 0.57, 0.71, 0.86, 1.0],
            }
        },
    }


# ---------------------------------------------------------------------------
# Layer 1: save_dir -- PNGs persisted to disk
# ---------------------------------------------------------------------------


class TestSaveDir:
    """generate_plot saves PNG when save_dir is provided."""

    def test_png_saved_to_disk(self, tmp_path):
        result = generate_plot(
            "lift_distribution", _RUN_ID, _make_lift_results(), save_dir=str(tmp_path)
        )
        assert isinstance(result, PlotResult)
        # file_path should be in metadata
        assert "file_path" in result.metadata
        fp = Path(result.metadata["file_path"])
        assert fp.exists()
        assert fp.suffix == ".png"
        assert fp.stat().st_size > 100
        # Check the directory structure
        assert fp.parent.name == "plots"

    def test_no_save_dir_no_file_path(self):
        result = generate_plot(
            "lift_distribution", _RUN_ID, _make_lift_results()
        )
        assert isinstance(result, PlotResult)
        assert "file_path" not in result.metadata

    def test_save_dir_creates_plots_subdir(self, tmp_path):
        save_dir = tmp_path / "deep" / "nested"
        result = generate_plot(
            "lift_distribution", _RUN_ID, _make_lift_results(), save_dir=str(save_dir)
        )
        assert (save_dir / "plots").is_dir()
        assert Path(result.metadata["file_path"]).exists()

    def test_save_dir_filename_format(self, tmp_path):
        result = generate_plot(
            "lift_distribution", _RUN_ID, _make_lift_results(), save_dir=str(tmp_path)
        )
        fp = Path(result.metadata["file_path"])
        assert fp.name == f"{_RUN_ID}_lift_distribution.png"

    def test_individual_plot_fn_save_dir(self, tmp_path):
        """Individual plot functions also accept save_dir."""
        result = plot_lift_distribution(
            _RUN_ID, _make_lift_results(), save_dir=str(tmp_path)
        )
        assert "file_path" in result.metadata
        assert Path(result.metadata["file_path"]).exists()


# ---------------------------------------------------------------------------
# Layer 2: SessionDefaults.visualization_output
# ---------------------------------------------------------------------------


class TestSessionVisualizationOutput:
    """Session defaults include visualization_output."""

    def test_default_is_inline(self):
        defaults = SessionDefaults()
        assert defaults.visualization_output == "inline"

    def test_to_dict_includes_field(self):
        defaults = SessionDefaults()
        d = defaults.to_dict()
        assert "visualization_output" in d
        assert d["visualization_output"] == "inline"

    def test_configure_sets_visualization_output(self):
        session = Session()
        session.configure(visualization_output="file")
        assert session.defaults.visualization_output == "file"

    def test_configure_url_mode(self):
        session = Session()
        session.configure(visualization_output="url")
        assert session.defaults.visualization_output == "url"

    def test_configure_unknown_key_raises(self):
        session = Session()
        with pytest.raises(ValueError):
            session.configure(nonexistent_key="value")

    def test_clear_resets_visualization_output(self):
        session = Session()
        session.configure(visualization_output="url")
        session.clear()
        assert session.defaults.visualization_output == "inline"


# ---------------------------------------------------------------------------
# Layer 2: Dashboard HTML generation
# ---------------------------------------------------------------------------


class TestDashboardHtml:
    """generate_dashboard_html produces valid HTML."""

    def test_returns_none_for_missing_run(self):
        from hangar.sdk.viz.viewer_server import generate_dashboard_html

        result = generate_dashboard_html("nonexistent-run-id")
        assert result is None

    def test_generates_html_for_valid_artifact(self):
        """Create a mock artifact and verify dashboard HTML is generated."""
        from hangar.sdk.viz.viewer_server import generate_dashboard_html

        run_id = "dash-test-0001"
        artifact_data = {
            "metadata": {
                "analysis_type": "aero",
                "run_name": "test run",
                "timestamp": "2026-03-19T12:00:00",
                "surfaces": ["wing"],
                "session_id": "test-session",
            },
            "results": {
                "CL": 0.5,
                "CD": 0.02,
                "L_over_D": 25.0,
                "alpha": 3.0,
                "velocity": 248.0,
                "Mach_number": 0.84,
                "surfaces": {"wing": {"CL": 0.5, "CD": 0.02}},
            },
            "validation": {"passed": True, "findings": []},
        }

        # Patch ArtifactStore where it's imported inside generate_dashboard_html
        with patch("hangar.sdk.artifacts.store.ArtifactStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.get.return_value = artifact_data
            html = generate_dashboard_html(run_id)

        assert html is not None
        assert "<!DOCTYPE html>" in html
        assert run_id in html
        assert "Aero" in html  # analysis type title-cased
        assert "test run" in html  # run_name
        assert "0.5" in html  # CL value


# ---------------------------------------------------------------------------
# Layer 3: _get_viewer_base_url
# ---------------------------------------------------------------------------


class TestGetViewerBaseUrl:
    """URL computation for viewer/dashboard endpoints."""

    def test_resource_server_url_takes_precedence(self):
        from hangar.oas.server import _get_viewer_base_url

        with patch.dict(os.environ, {"RESOURCE_SERVER_URL": "https://mcp.example.com"}):
            assert _get_viewer_base_url() == "https://mcp.example.com"

    def test_resource_server_url_strips_trailing_slash(self):
        from hangar.oas.server import _get_viewer_base_url

        with patch.dict(os.environ, {"RESOURCE_SERVER_URL": "https://mcp.example.com/"}):
            assert _get_viewer_base_url() == "https://mcp.example.com"

    def test_fallback_to_localhost(self):
        from hangar.oas.server import _get_viewer_base_url

        env = {k: v for k, v in os.environ.items()
               if k not in ("RESOURCE_SERVER_URL", "OAS_PROV_VIEWER")}
        with patch.dict(os.environ, env, clear=True):
            url = _get_viewer_base_url()
            assert url is not None
            assert "localhost" in url
            assert "7654" in url

    def test_custom_prov_port(self):
        from hangar.oas.server import _get_viewer_base_url

        env = {k: v for k, v in os.environ.items()
               if k not in ("RESOURCE_SERVER_URL",)}
        env["OAS_PROV_PORT"] = "9999"
        with patch.dict(os.environ, env, clear=True):
            url = _get_viewer_base_url()
            assert url == "http://localhost:9999"

    def test_viewer_off_returns_none(self):
        from hangar.oas.server import _get_viewer_base_url

        env = {k: v for k, v in os.environ.items()
               if k not in ("RESOURCE_SERVER_URL",)}
        env["OAS_PROV_VIEWER"] = "off"
        with patch.dict(os.environ, env, clear=True):
            assert _get_viewer_base_url() is None


# ---------------------------------------------------------------------------
# Layer 2: /dashboard route in viewer_server daemon
# ---------------------------------------------------------------------------


class TestDashboardRoute:
    """The /dashboard route on the daemon thread HTTP server."""

    def test_dashboard_path_recognized(self):
        """Verify /dashboard is handled (not 404)."""
        from hangar.sdk.viz.viewer_server import generate_dashboard_html
        # The route exists and the function is importable
        assert callable(generate_dashboard_html)


# ---------------------------------------------------------------------------
# Layer 2: /dashboard route in viewer_routes (Starlette)
# ---------------------------------------------------------------------------


class TestDashboardStarletteRoute:
    """The /dashboard route in viewer_routes.py for HTTP transport."""

    def test_viewer_paths_includes_dashboard(self):
        from hangar.sdk.viz.viewer_routes import _VIEWER_PATHS

        assert "/dashboard" in _VIEWER_PATHS
        assert "/dashboard/" in _VIEWER_PATHS

    def test_build_viewer_app_includes_dashboard(self):
        """When auth is configured, /dashboard is in the routes."""
        with patch.dict(os.environ, {
            "OAS_VIEWER_USER": "testuser",
            "OAS_VIEWER_PASSWORD": "testpass",
        }):
            from hangar.sdk.viz.viewer_routes import build_viewer_app

            app, _mode = build_viewer_app()
            assert app is not None
            route_paths = [r.path for r in app.routes]
            assert "/dashboard" in route_paths
