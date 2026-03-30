"""Unit tests for connect_aerostruct_surface branching logic.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/test_connections.py
Import mapping:
    oas_mcp.core.connections → hangar.oas.connections

We don't spin up a real OpenMDAO Problem — we just record which connect()
calls are made and assert the right set is used for each fem_model_type.
"""

from unittest.mock import MagicMock
import pytest
from hangar.oas.connections import connect_aerostruct_surface, connect_aero_surface


def _mock_model():
    """Return a mock om.Group that records connect() calls."""
    model = MagicMock()
    model.connect = MagicMock()
    return model


# ---------------------------------------------------------------------------
# connect_aero_surface
# ---------------------------------------------------------------------------


def test_aero_surface_connects_mesh_and_t_over_c():
    model = _mock_model()
    connect_aero_surface(model, "wing", "aero")
    paths = [c.args[0] for c in model.connect.call_args_list]
    assert "wing.mesh" in paths
    assert "wing.t_over_c" in paths


# ---------------------------------------------------------------------------
# connect_aerostruct_surface — shared connections
# ---------------------------------------------------------------------------


def test_aerostruct_shared_connections_tube():
    model = _mock_model()
    connect_aerostruct_surface(model, "wing", "AS_point_0", fem_model_type="tube")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    assert "wing.local_stiff_transformed" in src_paths
    assert "wing.nodes" in src_paths
    assert "wing.mesh" in src_paths
    assert "wing.cg_location" in src_paths
    assert "wing.structural_mass" in src_paths
    assert "wing.t_over_c" in src_paths


def test_aerostruct_shared_connections_wingbox():
    model = _mock_model()
    connect_aerostruct_surface(model, "wing", "AS_point_0", fem_model_type="wingbox")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    assert "wing.local_stiff_transformed" in src_paths
    assert "wing.nodes" in src_paths
    assert "wing.mesh" in src_paths
    assert "wing.cg_location" in src_paths
    assert "wing.structural_mass" in src_paths
    assert "wing.t_over_c" in src_paths


# ---------------------------------------------------------------------------
# connect_aerostruct_surface — tube-specific connections
# ---------------------------------------------------------------------------


def test_tube_connects_radius_and_thickness():
    model = _mock_model()
    connect_aerostruct_surface(model, "wing", "AS_point_0", fem_model_type="tube")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    assert "wing.radius" in src_paths
    assert "wing.thickness" in src_paths


def test_tube_does_not_connect_wingbox_section_props():
    model = _mock_model()
    connect_aerostruct_surface(model, "wing", "AS_point_0", fem_model_type="tube")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    for wingbox_key in ("wing.Qz", "wing.J", "wing.A_enc", "wing.htop",
                        "wing.hbottom", "wing.hfront", "wing.hrear",
                        "wing.spar_thickness"):
        assert wingbox_key not in src_paths, f"{wingbox_key} should not be connected for tube model"


# ---------------------------------------------------------------------------
# connect_aerostruct_surface — wingbox-specific connections
# ---------------------------------------------------------------------------


def test_wingbox_connects_section_properties():
    model = _mock_model()
    connect_aerostruct_surface(model, "wing", "AS_point_0", fem_model_type="wingbox")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    for wingbox_key in ("wing.Qz", "wing.J", "wing.A_enc", "wing.htop",
                        "wing.hbottom", "wing.hfront", "wing.hrear",
                        "wing.spar_thickness"):
        assert wingbox_key in src_paths, f"{wingbox_key} should be connected for wingbox model"


def test_wingbox_does_not_connect_tube_props():
    model = _mock_model()
    connect_aerostruct_surface(model, "wing", "AS_point_0", fem_model_type="wingbox")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    assert "wing.radius" not in src_paths
    assert "wing.thickness" not in src_paths


# ---------------------------------------------------------------------------
# Default fem_model_type falls back to tube behaviour
# ---------------------------------------------------------------------------


def test_default_fem_model_type_is_tube():
    model_default = _mock_model()
    model_tube = _mock_model()
    connect_aerostruct_surface(model_default, "wing", "AS_point_0")
    connect_aerostruct_surface(model_tube, "wing", "AS_point_0", fem_model_type="tube")
    assert model_default.connect.call_args_list == model_tube.connect.call_args_list


# ---------------------------------------------------------------------------
# Surface name is propagated correctly
# ---------------------------------------------------------------------------


def test_surface_name_used_in_paths():
    model = _mock_model()
    connect_aerostruct_surface(model, "htail", "AS_point_0", fem_model_type="tube")
    src_paths = {c.args[0] for c in model.connect.call_args_list}
    assert all(p.startswith("htail.") for p in src_paths)
