"""
test_deduplication.py
=====================
Tests for the geographic deduplication of candidate mirror detections.
"""

import pytest
from src.detection.detector import CandidateMirrorDetection
from src.detection.deduplication import (
    deduplicate_detections,
    DeduplicatedMirror,
    CLUSTER_RADIUS_M,
)


def _make_detection(lat: float, lon: float, confidence: float = 0.7) -> CandidateMirrorDetection:
    return CandidateMirrorDetection(
        image_id="img001",
        candidate_id="cand001",
        panorama_id="pano001",
        latitude=lat,
        longitude=lon,
        heading=0,
        bbox_x=100, bbox_y=100, bbox_w=50, bbox_h=50,
        confidence=confidence,
        detector_type="test",
    )


def test_empty_input():
    result = deduplicate_detections([])
    assert result == []


def test_single_detection():
    det = _make_detection(18.474, 73.860)
    result = deduplicate_detections([det])
    assert len(result) == 1
    assert result[0].best_confidence == pytest.approx(0.7)


def test_identical_location_deduped():
    """Two detections at the same location → one cluster."""
    dets = [
        _make_detection(18.474, 73.860, confidence=0.7),
        _make_detection(18.474, 73.860, confidence=0.6),
    ]
    result = deduplicate_detections(dets)
    assert len(result) == 1
    assert result[0].detection_count == 2
    assert result[0].best_confidence == pytest.approx(0.7)  # highest


def test_nearby_locations_deduped():
    """Detections within CLUSTER_RADIUS_M should be merged."""
    # ~5 metres apart — well within cluster radius
    dets = [
        _make_detection(18.47400, 73.86000, confidence=0.8),
        _make_detection(18.47401, 73.86001, confidence=0.6),
    ]
    result = deduplicate_detections(dets, cluster_radius_m=15.0)
    assert len(result) == 1


def test_far_locations_not_deduped():
    """Detections far apart → separate clusters."""
    dets = [
        _make_detection(18.474, 73.860),   # Ganga Dham
        _make_detection(18.530, 73.920),   # Far away
    ]
    result = deduplicate_detections(dets)
    assert len(result) == 2


def test_best_detection_selected():
    """The best_detection should be the one with the highest confidence."""
    dets = [
        _make_detection(18.474, 73.860, confidence=0.5),
        _make_detection(18.474, 73.860, confidence=0.9),
        _make_detection(18.474, 73.860, confidence=0.7),
    ]
    result = deduplicate_detections(dets)
    assert len(result) == 1
    assert result[0].best_confidence == pytest.approx(0.9)


def test_all_detections_preserved_in_cluster():
    """All contributing detections should be stored in all_detections."""
    dets = [_make_detection(18.474, 73.860, confidence=c) for c in [0.5, 0.8, 0.6]]
    result = deduplicate_detections(dets)
    assert len(result) == 1
    assert len(result[0].all_detections) == 3


def test_status_is_candidate():
    """Deduplicated mirrors should always start as 'candidate'."""
    dets = [_make_detection(18.474, 73.860)]
    result = deduplicate_detections(dets)
    for r in result:
        assert r.status == "candidate"


def test_mirror_has_id():
    """Each deduplicated mirror should have a non-empty ID."""
    dets = [_make_detection(18.474, 73.860)]
    result = deduplicate_detections(dets)
    assert result[0].mirror_id
    assert len(result[0].mirror_id) >= 4


def test_three_clusters():
    """Three distinct locations → three separate clusters."""
    dets = [
        _make_detection(18.4740, 73.8600),
        _make_detection(18.4760, 73.8620),
        _make_detection(18.4780, 73.8640),
    ]
    result = deduplicate_detections(dets, cluster_radius_m=10.0)
    assert len(result) == 3
