"""
test_sampling.py
================
Tests for candidate point generation and CSV I/O.
"""

import csv
import pytest
from pathlib import Path

from src.geo.boundary import get_ganga_dham_boundary, build_boundary
from src.geo.sampling import (
    generate_test_candidates,
    generate_grid_candidates,
    generate_candidates,
    save_candidates,
    load_candidates,
    CandidatePoint,
    TEST_POINTS,
)


@pytest.fixture
def boundary():
    return get_ganga_dham_boundary()


def test_test_candidates_within_boundary(boundary):
    """All hand-curated test points should be inside the boundary."""
    candidates = generate_test_candidates(boundary)
    assert len(candidates) > 0
    for c in candidates:
        assert boundary.contains(c.latitude, c.longitude), (
            f"Candidate ({c.latitude}, {c.longitude}) is outside boundary."
        )


def test_test_candidates_count(boundary):
    """Should generate approximately 5–10 test candidates."""
    candidates = generate_test_candidates(boundary)
    assert 5 <= len(candidates) <= len(TEST_POINTS)


def test_grid_candidates_within_boundary(boundary):
    """Grid candidates should all be inside the boundary."""
    candidates = generate_grid_candidates(boundary, spacing_m=40, max_points=20)
    for c in candidates:
        assert boundary.contains(c.latitude, c.longitude)


def test_grid_respects_max_points(boundary):
    """Grid sampling should respect the max_points limit."""
    max_pts = 5
    candidates = generate_grid_candidates(boundary, spacing_m=10, max_points=max_pts)
    assert len(candidates) <= max_pts


def test_candidate_point_has_required_fields(boundary):
    candidates = generate_test_candidates(boundary)
    for c in candidates:
        assert c.id
        assert c.latitude != 0.0
        assert c.longitude != 0.0
        assert c.area
        assert c.created_at


def test_generate_candidates_uses_test_points_by_default(boundary):
    """generate_candidates() should use test points when use_test_points=True."""
    candidates = generate_candidates(boundary, use_test_points=True)
    assert len(candidates) > 0


def test_generate_candidates_uses_grid(boundary):
    """generate_candidates() should use grid when use_test_points=False."""
    candidates = generate_candidates(
        boundary, spacing_m=40, max_points=5, use_test_points=False
    )
    assert len(candidates) <= 5


def test_save_and_load_candidates(boundary, tmp_path):
    """save_candidates / load_candidates should be round-trip compatible."""
    candidates = generate_test_candidates(boundary)
    path = tmp_path / "test_candidates.csv"

    save_candidates(candidates, path)
    assert path.exists()

    loaded = load_candidates(path)
    assert len(loaded) == len(candidates)

    for orig, loaded_c in zip(candidates, loaded):
        assert orig.id == loaded_c.id
        assert abs(orig.latitude - loaded_c.latitude) < 1e-6
        assert abs(orig.longitude - loaded_c.longitude) < 1e-6
        assert orig.area == loaded_c.area


def test_saved_csv_has_correct_columns(boundary, tmp_path):
    candidates = generate_test_candidates(boundary)
    path = tmp_path / "test_candidates.csv"
    save_candidates(candidates, path)

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
    assert "id" in fields
    assert "latitude" in fields
    assert "longitude" in fields
    assert "area" in fields
    assert "created_at" in fields
