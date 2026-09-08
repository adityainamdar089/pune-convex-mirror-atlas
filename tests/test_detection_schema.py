"""
test_detection_schema.py
========================
Tests for the CandidateMirrorDetection data model and schema.
"""

import pytest
from src.detection.detector import (
    CandidateMirrorDetection,
    BoundingBox,
    _DETECTION_CSV_FIELDS,
)


def test_detection_has_required_fields():
    det = CandidateMirrorDetection(
        image_id="img001",
        candidate_id="cand001",
        panorama_id="pano001",
        latitude=18.474,
        longitude=73.860,
        heading=90,
        bbox_x=100, bbox_y=150, bbox_w=80, bbox_h=75,
        confidence=0.72,
        detector_type="opencv_hough_v1",
    )
    assert det.detection_id        # non-empty auto-generated ID
    assert det.image_id == "img001"
    assert det.status == "candidate"   # ALWAYS candidate at this stage
    assert det.confidence == pytest.approx(0.72)
    assert det.detected_at          # non-empty timestamp


def test_detection_status_is_candidate():
    """Detections must start as 'candidate', never auto-confirmed."""
    det = CandidateMirrorDetection()
    assert det.status == "candidate"


def test_bounding_box_properties():
    det = CandidateMirrorDetection(bbox_x=10, bbox_y=20, bbox_w=100, bbox_h=80)
    bb = det.bounding_box
    assert bb.area == 8000
    assert bb.aspect_ratio == pytest.approx(1.25)


def test_bounding_box_zero_height():
    bb = BoundingBox(x=0, y=0, width=50, height=0)
    assert bb.aspect_ratio == 0.0


def test_detection_as_dict_contains_all_csv_fields():
    det = CandidateMirrorDetection()
    d = det.as_dict()
    for field in _DETECTION_CSV_FIELDS:
        assert field in d, f"Field '{field}' missing from as_dict()"


def test_confidence_range():
    """Confidence must be set; the pipeline should keep it in [0, 1]."""
    det = CandidateMirrorDetection(confidence=0.0)
    assert det.confidence == 0.0

    det2 = CandidateMirrorDetection(confidence=1.0)
    assert det2.confidence == 1.0


def test_unique_detection_ids():
    """Each detection should get a unique ID."""
    ids = {CandidateMirrorDetection().detection_id for _ in range(50)}
    assert len(ids) == 50
