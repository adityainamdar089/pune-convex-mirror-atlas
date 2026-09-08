"""
boundary.py
===========
Defines the Ganga Dham geographic boundary and provides containment checks.

The boundary is stored as an explicit polygon of (lat, lon) vertices.
It was manually traced from OpenStreetMap and satellite imagery around
Ganga Dham society, Bibwewadi, Pune, Maharashtra, India.

IMPORTANT
---------
- Do NOT silently expand beyond this boundary.
- The boundary is configurable: replace GANGA_DHAM_POLYGON with your own
  vertices to adjust the scan area.
- Coordinates are (latitude, longitude) pairs in WGS-84.

Boundary adjustment
-------------------
To adjust the boundary, update GANGA_DHAM_POLYGON with a list of
(lat, lon) tuples forming a closed polygon.
The polygon will be closed automatically (first == last point).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from shapely.geometry import Point, Polygon

# ── Ganga Dham polygon (WGS-84, lat/lon) ─────────────────────────────────────
#
# These vertices trace the approximate boundary of Ganga Dham / Bibwewadi
# residential area around the Ganga Dham housing societies.
#
# Adjust these coordinates to expand or refine the scan area.
# ─────────────────────────────────────────────────────────────────────────────

GANGA_DHAM_POLYGON: list[tuple[float, float]] = [
    (18.4760, 73.8575),   # NW corner
    (18.4768, 73.8610),   # N
    (18.4760, 73.8640),   # NE corner
    (18.4740, 73.8650),   # E
    (18.4720, 73.8645),   # SE
    (18.4710, 73.8620),   # S
    (18.4715, 73.8585),   # SW
    (18.4730, 73.8570),   # W
    (18.4760, 73.8575),   # close polygon
]

# Approximate center (for map centering)
GANGA_DHAM_CENTER = (18.4739, 73.8601)

# Bounding box (min_lat, min_lon, max_lat, max_lon) — derived from polygon
_lats = [p[0] for p in GANGA_DHAM_POLYGON]
_lons = [p[1] for p in GANGA_DHAM_POLYGON]
GANGA_DHAM_BBOX = (min(_lats), min(_lons), max(_lats), max(_lons))


@dataclass(frozen=True)
class AreaBoundary:
    """
    A named geographic area defined by a polygon.

    Attributes
    ----------
    name:    Human-readable name of the area.
    polygon: Shapely Polygon for spatial operations.
    center:  (lat, lon) center point.
    bbox:    (min_lat, min_lon, max_lat, max_lon) bounding box.
    """

    name: str
    polygon: Polygon
    center: tuple[float, float]
    bbox: tuple[float, float, float, float]

    def contains(self, lat: float, lon: float) -> bool:
        """Return True if (lat, lon) is inside the boundary polygon."""
        # shapely uses (x=lon, y=lat)
        return self.polygon.contains(Point(lon, lat))

    def contains_all(self, points: Sequence[tuple[float, float]]) -> list[bool]:
        """Vectorised containment check for a list of (lat, lon) pairs."""
        return [self.contains(lat, lon) for lat, lon in points]


def build_boundary(
    name: str,
    polygon_coords: list[tuple[float, float]],
    center: tuple[float, float],
) -> AreaBoundary:
    """
    Build an AreaBoundary from a list of (lat, lon) vertices.

    The polygon is automatically closed if the first and last vertex differ.
    """
    coords = list(polygon_coords)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    # shapely Polygon expects (lon, lat) = (x, y)
    shapely_poly = Polygon([(lon, lat) for lat, lon in coords])

    if not shapely_poly.is_valid:
        shapely_poly = shapely_poly.buffer(0)  # attempt auto-repair

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    bbox = (min(lats), min(lons), max(lats), max(lons))

    return AreaBoundary(
        name=name,
        polygon=shapely_poly,
        center=center,
        bbox=bbox,
    )


# ── Default boundary singleton ────────────────────────────────────────────────

def get_ganga_dham_boundary() -> AreaBoundary:
    """Return the pre-configured Ganga Dham boundary."""
    return build_boundary(
        name="Ganga Dham, Bibwewadi, Pune",
        polygon_coords=GANGA_DHAM_POLYGON,
        center=GANGA_DHAM_CENTER,
    )
