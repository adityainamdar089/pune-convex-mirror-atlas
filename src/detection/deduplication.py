"""
deduplication.py
================
Clusters candidate mirror detections to remove duplicates.

Why deduplication is necessary
-------------------------------
The same physical convex mirror may be detected in:
- Multiple headings from the same panorama (e.g. 315° and 0°).
- Multiple panoramas from nearby road points.
- Multiple candidate points within the sampling grid.

Without deduplication, the map would show multiple pins for a single mirror.

Clustering strategy
-------------------
1. Geographic clustering: detections within CLUSTER_RADIUS_M metres of each
   other are considered potentially the same physical mirror.
2. Within a geographic cluster, keep the detection with the highest confidence.
3. Store all detections that contributed to a cluster as "evidence".

The result is a list of DeduplicatedMirror objects — one per physical mirror.

NOTE: Deduplication is imperfect. A reviewer must confirm via human review.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Optional

from geopy.distance import geodesic

from src.detection.detector import CandidateMirrorDetection
from src.logging_config import get_logger

log = get_logger(__name__)

# Maximum distance between two detections to be considered the same physical mirror
CLUSTER_RADIUS_M = 15.0


@dataclass
class DeduplicatedMirror:
    """
    A candidate mirror after deduplication.

    Represents a potential unique physical mirror.
    Status is still 'candidate' until human-verified.
    """
    mirror_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    latitude: float = 0.0
    longitude: float = 0.0
    best_confidence: float = 0.0
    detection_count: int = 0
    best_detection: Optional[CandidateMirrorDetection] = None
    all_detections: list[CandidateMirrorDetection] = field(default_factory=list)
    status: str = "candidate"  # candidate | confirmed | rejected | uncertain

    def as_dict(self) -> dict:
        d = self.best_detection.as_dict() if self.best_detection else {}
        return {
            "mirror_id": self.mirror_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "best_confidence": self.best_confidence,
            "detection_count": self.detection_count,
            "status": self.status,
            **{f"best_{k}": v for k, v in d.items()},
        }


def deduplicate_detections(
    detections: list[CandidateMirrorDetection],
    cluster_radius_m: float = CLUSTER_RADIUS_M,
) -> list[DeduplicatedMirror]:
    """
    Cluster detections by geographic proximity.

    Returns one DeduplicatedMirror per physical mirror candidate.
    The 'best' detection (highest confidence) is used as the representative.
    """
    if not detections:
        log.info("No detections to deduplicate.")
        return []

    # Sort by confidence descending so we process best first
    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)

    clusters: list[DeduplicatedMirror] = []

    for det in sorted_dets:
        assigned = False

        for cluster in clusters:
            dist = geodesic(
                (det.latitude, det.longitude),
                (cluster.latitude, cluster.longitude),
            ).meters

            if dist <= cluster_radius_m:
                # Add to existing cluster
                cluster.all_detections.append(det)
                cluster.detection_count += 1
                # Update best if higher confidence
                if det.confidence > cluster.best_confidence:
                    cluster.best_confidence = det.confidence
                    cluster.best_detection = det
                    cluster.latitude = det.latitude
                    cluster.longitude = det.longitude
                assigned = True
                break

        if not assigned:
            # New cluster
            clusters.append(
                DeduplicatedMirror(
                    latitude=det.latitude,
                    longitude=det.longitude,
                    best_confidence=det.confidence,
                    detection_count=1,
                    best_detection=det,
                    all_detections=[det],
                )
            )

    removed = len(detections) - len(clusters)
    log.info(
        "Deduplication: %d detections → %d unique candidates "
        "(%d duplicates removed, radius=%.0fm).",
        len(detections), len(clusters), removed, cluster_radius_m,
    )
    return clusters
