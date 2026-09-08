"""
detector.py
===========
Base interface for convex mirror detectors.

All detectors must implement the MirrorDetector protocol.
This allows swapping in different backends (OpenCV baseline, YOLO, DETR, etc.)
without changing the rest of the pipeline.

IMPORTANT TERMINOLOGY
---------------------
Every detection result is a CANDIDATE MIRROR.
It is NOT confirmed as a convex mirror until a human verifies it.
Use the term "candidate_mirror" throughout, never "mirror" alone.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.streetview.imagery import ImageRecord


# ── Detection result ──────────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    """Pixel-space bounding box within an image."""
    x: int       # left
    y: int       # top
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        if self.height == 0:
            return 0.0
        return self.width / self.height

    def as_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class CandidateMirrorDetection:
    """
    A single candidate convex mirror detection from an image.

    Status is always 'candidate' at this stage — requires human verification.
    """

    detection_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    image_id: str = ""
    candidate_id: str = ""
    panorama_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    heading: int = 0

    # Bounding box in pixels
    bbox_x: int = 0
    bbox_y: int = 0
    bbox_w: int = 0
    bbox_h: int = 0

    # Detection confidence [0.0, 1.0]
    confidence: float = 0.0

    # Which detector produced this
    detector_type: str = "unknown"

    # Always "candidate" — only human review can change this
    status: str = "candidate"

    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def bounding_box(self) -> BoundingBox:
        return BoundingBox(self.bbox_x, self.bbox_y, self.bbox_w, self.bbox_h)

    def as_dict(self) -> dict:
        return asdict(self)


_DETECTION_CSV_FIELDS = [
    "detection_id", "image_id", "candidate_id", "panorama_id",
    "latitude", "longitude", "heading",
    "bbox_x", "bbox_y", "bbox_w", "bbox_h",
    "confidence", "detector_type", "status", "detected_at",
]


# ── Base detector interface ───────────────────────────────────────────────────

class MirrorDetector(ABC):
    """Abstract base class for convex mirror detectors."""

    @property
    @abstractmethod
    def detector_type(self) -> str:
        """Short identifier string for this detector."""
        ...

    @abstractmethod
    def detect(
        self,
        image_path: Path,
        image_record: ImageRecord,
    ) -> list[CandidateMirrorDetection]:
        """
        Run detection on a single image.

        Parameters
        ----------
        image_path:   Path to the image file.
        image_record: Metadata record for the image.

        Returns
        -------
        List of CandidateMirrorDetection objects.
        May be empty if no candidates found.
        All results have status='candidate'.
        """
        ...

    def detect_all(
        self,
        image_records: list[ImageRecord],
        image_dir: Optional[Path] = None,
    ) -> list[CandidateMirrorDetection]:
        """
        Run detection on all image records.

        Skips images that do not exist on disk.
        Errors in individual images do not crash the pipeline.
        """
        from src.logging_config import get_logger
        log = get_logger(__name__)

        all_detections: list[CandidateMirrorDetection] = []

        for rec in image_records:
            path = Path(rec.file_path)
            if not path.exists():
                log.warning("Image not found, skipping: %s", path)
                continue

            try:
                detections = self.detect(path, rec)
                log.info(
                    "Detector '%s': %d candidate(s) in image %s (heading=%d)",
                    self.detector_type, len(detections), rec.image_id, rec.heading,
                )
                all_detections.extend(detections)
            except Exception as e:
                log.error(
                    "Detection failed for image %s: %s", rec.image_id, e,
                    exc_info=True,
                )

        return all_detections
