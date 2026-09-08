"""
sampling.py
===========
Generates candidate road-point locations within the configured boundary.

Strategy
--------
Rather than calling a live Roads API (which costs money and requires internet),
this module generates a regular grid of points within the configured bounding
box, filters them to those inside the boundary polygon, and applies spacing
constraints.

For the INITIAL TEST, a small set of hand-curated road points along known
streets inside Ganga Dham is also provided.

The sampling approach is deliberately simple and transparent:
- Use a grid over the bounding box
- Keep only points inside the polygon
- Deduplicate by minimum distance
- Respect MAX_CANDIDATE_POINTS

Usage
-----
    from src.geo.sampling import generate_candidates
    from src.geo.boundary import get_ganga_dham_boundary
    from src.config import get_config

    cfg = get_config()
    boundary = get_ganga_dham_boundary()
    candidates = generate_candidates(boundary, cfg)
"""

from __future__ import annotations

import csv
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.geo.boundary import AreaBoundary
from src.logging_config import get_logger

log = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

# 1 degree of latitude ≈ 111,111 metres
_METERS_PER_DEGREE_LAT = 111_111.0


def _meters_per_degree_lon(lat: float) -> float:
    return _METERS_PER_DEGREE_LAT * math.cos(math.radians(lat))


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class CandidatePoint:
    """A candidate road location to be checked for Street View availability."""

    id: str
    latitude: float
    longitude: float
    area: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "area": self.area,
            "created_at": self.created_at,
        }


# ── Hard-coded test points ────────────────────────────────────────────────────
#
# These 8 points are located on known streets within Ganga Dham / Bibwewadi.
# They are used for the initial 5–10 point test run.
# Each was selected by inspecting the Ganga Dham area on Google Maps.
#
# Format: (lat, lon, description)
# ─────────────────────────────────────────────────────────────────────────────

TEST_POINTS: list[tuple[float, float, str]] = [
    (18.4740, 73.8600, "Ganga Dham main road near centre"),
    (18.4748, 73.8607, "Internal road near society entrance north"),
    (18.4735, 73.8615, "Junction near eastern perimeter"),
    (18.4730, 73.8590, "Road near western side"),
    (18.4755, 73.8590, "Northern internal lane"),
    (18.4720, 73.8605, "Southern approach road"),
    (18.4745, 73.8625, "Road towards eastern boundary"),
    (18.4728, 73.8618, "Intersection near SE corner"),
]


# ── Candidate generation ──────────────────────────────────────────────────────

def generate_test_candidates(
    boundary: AreaBoundary,
    area_name: str = "Ganga Dham",
) -> list[CandidatePoint]:
    """
    Return the pre-defined test set of ~8 candidate points.

    All points are validated against the boundary polygon.
    Points outside the boundary are logged and skipped.
    """
    candidates: list[CandidatePoint] = []

    for lat, lon, desc in TEST_POINTS:
        if not boundary.contains(lat, lon):
            log.warning(
                "Test point (%.6f, %.6f) [%s] is outside boundary — skipped.",
                lat, lon, desc,
            )
            continue

        candidates.append(
            CandidatePoint(
                id=str(uuid.uuid4())[:8],
                latitude=lat,
                longitude=lon,
                area=area_name,
            )
        )
        log.debug("Test candidate accepted: (%.6f, %.6f) — %s", lat, lon, desc)

    log.info("Generated %d test candidate points.", len(candidates))
    return candidates


def generate_grid_candidates(
    boundary: AreaBoundary,
    spacing_m: int = 40,
    max_points: int = 10,
    area_name: str = "Ganga Dham",
) -> list[CandidatePoint]:
    """
    Generate a regular grid of candidate points within the boundary.

    Points are filtered by:
    1. Inside boundary polygon
    2. Minimum spacing (spacing_m)
    3. Maximum count (max_points)

    Parameters
    ----------
    boundary:   The AreaBoundary to sample within.
    spacing_m:  Grid spacing in metres.
    max_points: Maximum number of candidates to return.
    area_name:  Label stored in the CandidatePoint.area field.
    """
    min_lat, min_lon, max_lat, max_lon = boundary.bbox
    center_lat = (min_lat + max_lat) / 2

    lat_step = spacing_m / _METERS_PER_DEGREE_LAT
    lon_step = spacing_m / _meters_per_degree_lon(center_lat)

    candidates: list[CandidatePoint] = []
    lat = min_lat

    while lat <= max_lat and len(candidates) < max_points:
        lon = min_lon
        while lon <= max_lon and len(candidates) < max_points:
            if boundary.contains(lat, lon):
                candidates.append(
                    CandidatePoint(
                        id=str(uuid.uuid4())[:8],
                        latitude=round(lat, 7),
                        longitude=round(lon, 7),
                        area=area_name,
                    )
                )
            lon += lon_step
        lat += lat_step

    log.info(
        "Grid sampling generated %d candidate points (spacing=%dm, max=%d).",
        len(candidates), spacing_m, max_points,
    )
    return candidates


def generate_candidates(
    boundary: AreaBoundary,
    spacing_m: int = 40,
    max_points: int = 10,
    use_test_points: bool = True,
    area_name: str = "Ganga Dham",
) -> list[CandidatePoint]:
    """
    Generate candidate points, using the test set by default.

    Parameters
    ----------
    boundary:        Area to sample within.
    spacing_m:       Grid spacing in metres (used when use_test_points=False).
    max_points:      Safety limit.
    use_test_points: If True, use hand-curated test set.
                     If False, generate a grid.
    area_name:       Area label.
    """
    if use_test_points:
        return generate_test_candidates(boundary, area_name)
    else:
        return generate_grid_candidates(boundary, spacing_m, max_points, area_name)


# ── CSV I/O ───────────────────────────────────────────────────────────────────

_CSV_FIELDS = ["id", "latitude", "longitude", "area", "created_at"]


def save_candidates(candidates: list[CandidatePoint], path: Path) -> None:
    """Save candidate points to a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for c in candidates:
            writer.writerow(c.as_dict())
    log.info("Saved %d candidates to %s", len(candidates), path)


def load_candidates(path: Path) -> list[CandidatePoint]:
    """Load candidate points from a CSV file."""
    candidates: list[CandidatePoint] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append(
                CandidatePoint(
                    id=row["id"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    area=row["area"],
                    created_at=row["created_at"],
                )
            )
    log.info("Loaded %d candidates from %s", len(candidates), path)
    return candidates
