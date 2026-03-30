"""Unit tests for mesh building and geometric transforms.

Migration: upstream/OpenAeroStruct/oas_mcp/tests/test_mesh.py
Import mapping:
    oas_mcp.core.mesh → hangar.oas.mesh
"""

import numpy as np
import pytest
from hangar.oas.mesh import apply_dihedral, apply_sweep, apply_taper, build_mesh


class TestBuildMesh:
    def test_rect_shape(self):
        mesh, twist = build_mesh("rect", num_x=2, num_y=5, span=10.0, root_chord=1.0, symmetry=True)
        # symmetry=True → ny2 = (5+1)//2 = 3
        assert mesh.shape == (2, 3, 3)
        assert twist is None

    def test_rect_no_symmetry_shape(self):
        mesh, twist = build_mesh("rect", num_x=2, num_y=5, span=10.0, root_chord=1.0, symmetry=False)
        assert mesh.shape == (2, 5, 3)
        assert twist is None

    def test_rect_span(self):
        mesh, _ = build_mesh("rect", num_x=2, num_y=5, span=10.0, root_chord=1.0, symmetry=False)
        y_span = mesh[0, :, 1].max() - mesh[0, :, 1].min()
        assert abs(y_span - 10.0) < 0.1

    def test_rect_chord(self):
        mesh, _ = build_mesh("rect", num_x=2, num_y=5, span=10.0, root_chord=2.0, symmetry=False)
        chord = abs(mesh[-1, 0, 0] - mesh[0, 0, 0])
        assert abs(chord - 2.0) < 1e-6

    def test_crm_returns_twist(self):
        mesh, twist = build_mesh("CRM", num_x=2, num_y=5, span=60.0, root_chord=10.0, symmetry=True)
        assert twist is not None
        assert len(twist) >= 2

    def test_crm_mesh_shape(self):
        mesh, _ = build_mesh("CRM", num_x=2, num_y=5, span=60.0, root_chord=10.0, symmetry=True)
        # ny2 = (5+1)//2 = 3
        assert mesh.shape[0] == 2
        assert mesh.shape[2] == 3

    def test_ucrm_based_returns_twist(self):
        mesh, twist = build_mesh("uCRM_based", num_x=3, num_y=7, span=60.0, root_chord=10.0, symmetry=True)
        assert twist is not None
        assert len(twist) >= 2

    def test_ucrm_based_mesh_shape(self):
        mesh, _ = build_mesh("uCRM_based", num_x=3, num_y=7, span=60.0, root_chord=10.0, symmetry=True)
        assert mesh.shape[0] == 3
        assert mesh.shape[2] == 3

    def test_crm_num_twist_cp_explicit(self):
        # With num_y=7 auto gives max(2,min(5,(7+1)//2))=4; explicit 5 should override
        _, twist_auto = build_mesh("CRM", num_x=2, num_y=7, span=60.0, root_chord=10.0, symmetry=True)
        _, twist_explicit = build_mesh("CRM", num_x=2, num_y=7, span=60.0, root_chord=10.0, symmetry=True, num_twist_cp=5)
        assert len(twist_auto) == 4
        assert len(twist_explicit) == 5

    def test_crm_num_twist_cp_default_unchanged(self):
        # Default auto-calculation: num_y=5 → max(2,min(5,(5+1)//2))=3
        _, twist = build_mesh("CRM", num_x=2, num_y=5, span=60.0, root_chord=10.0, symmetry=True)
        assert len(twist) == 3

    def test_offset_shifts_mesh(self):
        m1, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        m2, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False, offset=[50.0, 0.0, 0.0])
        np.testing.assert_allclose(m2[:, :, 0] - m1[:, :, 0], 50.0, atol=1e-6)


class TestApplySweep:
    def test_zero_sweep_unchanged(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        swept = apply_sweep(mesh.copy(), 0.0)
        np.testing.assert_array_equal(mesh, swept)

    def test_sweep_increases_le_x_at_tip(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        swept = apply_sweep(mesh.copy(), 30.0)
        # Leading edge x at tip > leading edge x at root (for positive sweep)
        tip_idx = 0  # y = -5 (most negative)
        root_idx = mesh.shape[1] // 2  # y = 0
        assert swept[0, tip_idx, 0] > swept[0, root_idx, 0]

    def test_sweep_modifies_x_not_y_z(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        swept = apply_sweep(mesh.copy(), 20.0)
        np.testing.assert_array_equal(mesh[:, :, 1], swept[:, :, 1])
        np.testing.assert_array_equal(mesh[:, :, 2], swept[:, :, 2])


class TestApplyDihedral:
    def test_zero_dihedral_unchanged(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        result = apply_dihedral(mesh.copy(), 0.0)
        np.testing.assert_array_equal(mesh, result)

    def test_dihedral_raises_tip_z(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        result = apply_dihedral(mesh.copy(), 10.0)
        tip_idx = 0
        root_idx = mesh.shape[1] // 2
        assert result[0, tip_idx, 2] > result[0, root_idx, 2]


class TestApplyTaper:
    def test_taper_one_unchanged(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        result = apply_taper(mesh.copy(), 1.0)
        np.testing.assert_array_equal(mesh, result)

    def test_taper_reduces_tip_chord(self):
        mesh, _ = build_mesh("rect", 2, 5, 10.0, 1.0, symmetry=False)
        result = apply_taper(mesh.copy(), 0.5)
        # Root chord (center of span, index ny//2)
        root_idx = mesh.shape[1] // 2
        tip_idx = 0
        root_chord = abs(result[-1, root_idx, 0] - result[0, root_idx, 0])
        tip_chord = abs(result[-1, tip_idx, 0] - result[0, tip_idx, 0])
        assert tip_chord < root_chord
