"""
metadata.py
===========
Queries the Google Street View Metadata API to check availability
and retrieve panorama information for candidate locations.

Street View Metadata API
------------------------
- Endpoint: https://maps.googleapis.com/maps/api/streetview/metadata
- Does NOT charge per request (as of 2024 — verify current pricing).
- Returns: panorama ID, location, date, copyright, status.
- Status values: OK | ZERO_RESULTS | NOT_FOUND | REQUEST_DENIED | UNKNOWN_ERROR

Documentation
-------------
https://developers.google.com/maps/documentation/streetview/metadata

IMPORTANT
---------
- Never log the full URL (contains API key).
- Cache results to avoid repeated calls.
- Respect rate limits.
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.geo.sampling import CandidatePoint
from src.logging_config import get_logger

log = get_logger(__name__)

_METADATA_URL = "https://maps.googleapis.com/maps/api/streetview/metadata"
_TIMEOUT_S = 10
_RETRY_ATTEMPTS = 3


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class PanoramaMetadata:
    """Metadata for a single Street View panorama."""

    candidate_id: str
    latitude: float
    longitude: float
    panorama_id: str
    capture_date: str       # e.g. "2023-06"
    source: str             # "outdoor" | "indoor" | etc.
    status: str             # "OK" | "ZERO_RESULTS" | etc.
    pano_lat: Optional[float] = None   # actual panorama lat (may differ from query)
    pano_lon: Optional[float] = None
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def available(self) -> bool:
        return self.status == "OK" and bool(self.panorama_id)

    def as_dict(self) -> dict:
        return asdict(self)


_META_CSV_FIELDS = [
    "candidate_id", "latitude", "longitude", "panorama_id",
    "capture_date", "source", "status", "pano_lat", "pano_lon", "fetched_at",
]


# ── Cache ─────────────────────────────────────────────────────────────────────

class MetadataCache:
    """Simple disk-based cache for panorama metadata keyed by candidate_id."""

    def __init__(self, cache_path: Path):
        self._path = cache_path
        self._data: dict[str, PanoramaMetadata] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    meta = PanoramaMetadata(
                        candidate_id=row["candidate_id"],
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        panorama_id=row["panorama_id"],
                        capture_date=row["capture_date"],
                        source=row["source"],
                        status=row["status"],
                        pano_lat=float(row["pano_lat"]) if row["pano_lat"] else None,
                        pano_lon=float(row["pano_lon"]) if row["pano_lon"] else None,
                        fetched_at=row["fetched_at"],
                    )
                    self._data[meta.candidate_id] = meta
            log.debug("Metadata cache loaded: %d entries from %s", len(self._data), self._path)
        except Exception as e:
            log.warning("Could not load metadata cache: %s", e)

    def get(self, candidate_id: str) -> Optional[PanoramaMetadata]:
        return self._data.get(candidate_id)

    def set(self, meta: PanoramaMetadata) -> None:
        self._data[meta.candidate_id] = meta
        self._flush()

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_META_CSV_FIELDS)
            writer.writeheader()
            for meta in self._data.values():
                writer.writerow(meta.as_dict())


# ── API client ────────────────────────────────────────────────────────────────

class StreetViewMetadataClient:
    """
    Fetches Street View metadata for candidate locations.

    Parameters
    ----------
    api_key:      Google Maps API key.
    cache_path:   Path to the CSV cache file.
    radius_m:     Search radius in metres (default 50).
    rate_delay_s: Minimum seconds between API requests.
    """

    def __init__(
        self,
        api_key: str,
        cache_path: Path,
        radius_m: int = 50,
        rate_delay_s: float = 0.3,
    ):
        self._api_key = api_key
        self._cache = MetadataCache(cache_path)
        self._radius_m = radius_m
        self._rate_delay_s = rate_delay_s
        self._request_count = 0

    @property
    def request_count(self) -> int:
        return self._request_count

    def fetch(
        self,
        candidate: CandidatePoint,
        force_refresh: bool = False,
    ) -> PanoramaMetadata:
        """
        Fetch metadata for a single candidate point.

        Uses cache if available. If force_refresh=True, always re-fetches.
        """
        if not force_refresh:
            cached = self._cache.get(candidate.id)
            if cached is not None:
                log.debug("Cache hit for candidate %s", candidate.id)
                return cached

        meta = self._fetch_from_api(candidate)
        self._cache.set(meta)
        return meta

    def fetch_all(
        self,
        candidates: list[CandidatePoint],
        max_requests: int = 100,
        force_refresh: bool = False,
    ) -> list[PanoramaMetadata]:
        """
        Fetch metadata for all candidates, respecting the request limit.
        """
        results: list[PanoramaMetadata] = []
        api_calls = 0

        for candidate in candidates:
            cached = None if force_refresh else self._cache.get(candidate.id)

            if cached is not None:
                log.debug("Cache hit for candidate %s", candidate.id)
                results.append(cached)
                continue

            if api_calls >= max_requests:
                log.warning(
                    "Reached max_requests=%d — stopping metadata fetch early.",
                    max_requests,
                )
                break

            meta = self._fetch_from_api(candidate)
            self._cache.set(meta)
            results.append(meta)
            api_calls += 1
            time.sleep(self._rate_delay_s)

        available = sum(1 for m in results if m.available)
        log.info(
            "Metadata: %d/%d candidates have Street View coverage.",
            available, len(results),
        )
        return results

    @retry(
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _fetch_from_api(self, candidate: CandidatePoint) -> PanoramaMetadata:
        """Make the actual Metadata API request (with retry logic)."""
        self._request_count += 1

        params = {
            "location": f"{candidate.latitude},{candidate.longitude}",
            "radius": self._radius_m,
            "key": self._api_key,
        }

        log.info(
            "Metadata API request #%d for candidate %s (%.6f, %.6f)",
            self._request_count, candidate.id, candidate.latitude, candidate.longitude,
        )

        try:
            response = requests.get(_METADATA_URL, params=params, timeout=_TIMEOUT_S)
            response.raise_for_status()
        except requests.RequestException as e:
            log.error("Metadata request failed for candidate %s: %s", candidate.id, e)
            raise

        data = response.json()
        status = data.get("status", "UNKNOWN_ERROR")

        if status == "OK":
            location = data.get("location", {})
            return PanoramaMetadata(
                candidate_id=candidate.id,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                panorama_id=data.get("pano_id", ""),
                capture_date=data.get("date", ""),
                source=data.get("copyright", ""),
                status=status,
                pano_lat=location.get("lat"),
                pano_lon=location.get("lng"),
            )
        else:
            log.warning(
                "Street View unavailable for candidate %s: status=%s",
                candidate.id, status,
            )
            return PanoramaMetadata(
                candidate_id=candidate.id,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                panorama_id="",
                capture_date="",
                source="",
                status=status,
            )


def save_metadata(metadata_list: list[PanoramaMetadata], path: Path) -> None:
    """Save a list of PanoramaMetadata objects to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_META_CSV_FIELDS)
        writer.writeheader()
        for m in metadata_list:
            writer.writerow(m.as_dict())
    log.info("Saved %d metadata records to %s", len(metadata_list), path)
