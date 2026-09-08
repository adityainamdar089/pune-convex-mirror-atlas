"""
test_boundary.py
================
Tests for Ganga Dham boundary polygon and containment checks.
"""

import pytest
from src.geo.boundary import (
    get_ganga_dham_boundary,
    build_boundary,
    GANGA_DHAM_POLYGON,
    GANGA_DHAM_CENTER,
    GANGA_DHAM_BBOX,
)


@pytest.fixture
def boundary():
    return get_ganga_dham_boundary()


def test_boundary_loads(boundary):
    assert boundary is not None
    assert boundary.name == "Ganga Dham, Bibwewadi, Pune"


def test_boundary_polygon_is_valid(boundary):
    assert boundary.polygon.is_valid


def test_center_is_inside_boundary(boundary):
    lat, lon = GANGA_DHAM_CENTER
    assert boundary.contains(lat, lon), (
        f"Center point ({lat}, {lon}) should be inside the boundary."
    )


def test_point_clearly_inside(boundary):
    # Approximate interior point
    assert boundary.contains(18.4740, 73.8610)


def test_point_outside_pune(boundary):
    # Mumbai — far outside
    assert not boundary.contains(19.0760, 72.8777)


def test_point_outside_in_kondhwa(boundary):
    # Kondhwa — nearby but explicitly excluded
    assert not boundary.contains(18.4534, 73.8875)


def test_point_outside_near_edge(boundary):
    # Just outside the bbox — should be outside
    min_lat, min_lon, max_lat, max_lon = GANGA_DHAM_BBOX
    assert not boundary.contains(min_lat - 0.01, min_lon - 0.01)


def test_bbox_derived_correctly():
    min_lat, min_lon, max_lat, max_lon = GANGA_DHAM_BBOX
    assert min_lat < max_lat
    assert min_lon < max_lon
    # Rough sanity: should be within Pune's lat range
    assert 18.0 < min_lat < 19.0
    assert 73.0 < min_lon < 75.0


def test_custom_boundary():
    """build_boundary() should correctly handle a custom polygon."""
    # A small square
    coords = [
        (18.00, 73.00),
        (18.01, 73.00),
        (18.01, 73.01),
        (18.00, 73.01),
    ]
    b = build_boundary("Test Area", coords, center=(18.005, 73.005))
    assert b.contains(18.005, 73.005)  # centre
    assert not b.contains(18.02, 73.02)  # outside


def test_boundary_auto_closes_polygon():
    """Polygon should be automatically closed even if first != last."""
    coords = [
        (18.47, 73.86),
        (18.48, 73.86),
        (18.48, 73.87),
        (18.47, 73.87),
    ]
    # Not explicitly closed
    b = build_boundary("Open Polygon", coords, center=(18.475, 73.865))
    assert b.polygon.is_valid


def test_contains_all(boundary):
    points = [
        (18.4740, 73.8610),   # inside
        (19.0760, 72.8777),   # Mumbai — outside
    ]
    results = boundary.contains_all(points)
    assert results[0] is True
    assert results[1] is False
