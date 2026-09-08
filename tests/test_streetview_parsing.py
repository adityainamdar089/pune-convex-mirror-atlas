"""
test_streetview_parsing.py
==========================
Tests for Street View metadata response parsing.
Uses mocked HTTP responses — no real API credentials required.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.geo.sampling import CandidatePoint
from src.streetview.metadata import StreetViewMetadataClient, PanoramaMetadata


def _make_candidate() -> CandidatePoint:
    return CandidatePoint(
        id="test001",
        latitude=18.474,
        longitude=73.860,
        area="Ganga Dham",
    )


def _make_client(tmp_path: Path) -> StreetViewMetadataClient:
    return StreetViewMetadataClient(
        api_key="fake-key-for-testing",
        cache_path=tmp_path / "metadata_cache.csv",
        radius_m=50,
        rate_delay_s=0,  # no delay in tests
    )


def test_ok_response_parsed_correctly(tmp_path):
    """An OK API response should produce an available PanoramaMetadata."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "pano_id": "PANO123ABC",
        "date": "2023-06",
        "copyright": "© 2023 Google",
        "location": {"lat": 18.4741, "lng": 73.8601},
    }
    mock_response.raise_for_status = MagicMock()

    client = _make_client(tmp_path)
    with patch("requests.get", return_value=mock_response):
        result = client.fetch(_make_candidate())

    assert result.available
    assert result.status == "OK"
    assert result.panorama_id == "PANO123ABC"
    assert result.capture_date == "2023-06"
    assert result.pano_lat == pytest.approx(18.4741)


def test_zero_results_response(tmp_path):
    """A ZERO_RESULTS response should produce an unavailable PanoramaMetadata."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ZERO_RESULTS"}
    mock_response.raise_for_status = MagicMock()

    client = _make_client(tmp_path)
    with patch("requests.get", return_value=mock_response):
        result = client.fetch(_make_candidate())

    assert not result.available
    assert result.status == "ZERO_RESULTS"
    assert result.panorama_id == ""


def test_not_found_response(tmp_path):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "NOT_FOUND"}
    mock_response.raise_for_status = MagicMock()

    client = _make_client(tmp_path)
    with patch("requests.get", return_value=mock_response):
        result = client.fetch(_make_candidate())

    assert not result.available


def test_cache_prevents_repeated_api_call(tmp_path):
    """Second call for the same candidate should use cache, not call API again."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "pano_id": "PANO_CACHED",
        "date": "2023-01",
        "copyright": "© Google",
        "location": {"lat": 18.474, "lng": 73.860},
    }
    mock_response.raise_for_status = MagicMock()

    candidate = _make_candidate()
    client = _make_client(tmp_path)

    with patch("requests.get", return_value=mock_response) as mock_get:
        result1 = client.fetch(candidate)
        result2 = client.fetch(candidate)  # should hit cache

    assert mock_get.call_count == 1  # only called once
    assert result1.panorama_id == result2.panorama_id == "PANO_CACHED"


def test_metadata_available_property():
    meta = PanoramaMetadata(
        candidate_id="x",
        latitude=0, longitude=0,
        panorama_id="VALID_PANO",
        capture_date="2023-01",
        source="outdoor",
        status="OK",
    )
    assert meta.available

    meta_bad = PanoramaMetadata(
        candidate_id="x",
        latitude=0, longitude=0,
        panorama_id="",
        capture_date="",
        source="",
        status="ZERO_RESULTS",
    )
    assert not meta_bad.available
