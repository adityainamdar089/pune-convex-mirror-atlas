"""
imagery.py
==========
Downloads Street View static imagery through the official
Google Street View Static API for panoramas that are confirmed available.

Street View Static API
----------------------
- Endpoint: https://maps.googleapis.com/maps/api/streetview
- Charges apply per image request — see current pricing at:
  https://developers.google.com/maps/documentation/streetview/usage-and-billing
- Image is returned as JPEG bytes.
- Maximum resolution: 640×640 (standard) / 1280×1280 (premium).

Usage
-----
    from src.streetview.imagery import StreetViewImageryClient
    client = StreetViewImageryClient(api_key=cfg.effective_street_view_key,
                                     output_dir=cfg.raw_dir)
    images = client.fetch_all_headings(metadata, candidate)

Attribution
-----------
Images obtained via the Street View Static API must display
Google attribution as required by the API ToS.
The gallery and map always show: © [year] Google
"""

from __future__ import annotations

import csv
import hashlib
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

from src.streetview.metadata import PanoramaMetadata
from src.geo.sampling import CandidatePoint
from src.logging_config import get_logger

log = get_logger(__name__)

_STATIC_URL = "https://maps.googleapis.com/maps/api/streetview"
_TIMEOUT_S = 15
_RETRY_ATTEMPTS = 3


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ImageRecord:
    """Record for a single downloaded Street View image."""

    image_id: str
    candidate_id: str
    panorama_id: str
    latitude: float
    longitude: float
    heading: int
    pitch: int
    field_of_view: int
    capture_date: str
    source: str
    file_path: str          # Relative path from project root
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_dict(self) -> dict:
        return asdict(self)


_IMAGE_CSV_FIELDS = [
    "image_id", "candidate_id", "panorama_id",
    "latitude", "longitude", "heading", "pitch", "field_of_view",
    "capture_date", "source", "file_path", "fetched_at",
]


# ── Client ────────────────────────────────────────────────────────────────────

class StreetViewImageryClient:
    """
    Downloads directional Street View images for panoramas.

    Safety
    ------
    - Never re-downloads an image already on disk (cache-first).
    - Respects max_images limit.
    - Rate-limits requests.
    - Logs request counts but never the full URL (contains API key).
    """

    def __init__(
        self,
        api_key: str,
        output_dir: Path,
        index_path: Optional[Path] = None,
        width: int = 640,
        height: int = 640,
        pitch: int = 0,
        fov: int = 90,
        rate_delay_s: float = 0.5,
    ):
        self._api_key = api_key
        self._output_dir = output_dir
        self._width = width
        self._height = height
        self._pitch = pitch
        self._fov = fov
        self._rate_delay_s = rate_delay_s
        self._request_count = 0
        self._index_path = index_path or (output_dir / "image_index.csv")
        self._index: dict[str, ImageRecord] = {}
        self._load_index()

    @property
    def request_count(self) -> int:
        return self._request_count

    def _load_index(self) -> None:
        if not self._index_path.exists():
            return
        try:
            with open(self._index_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rec = ImageRecord(**{k: row[k] for k in _IMAGE_CSV_FIELDS})
                    rec.heading = int(rec.heading)
                    rec.pitch = int(rec.pitch)
                    rec.field_of_view = int(rec.field_of_view)
                    self._index[rec.image_id] = rec
            log.debug("Image index loaded: %d entries", len(self._index))
        except Exception as e:
            log.warning("Could not load image index: %s", e)

    def _save_index(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_IMAGE_CSV_FIELDS)
            writer.writeheader()
            for rec in self._index.values():
                writer.writerow(rec.as_dict())

    def _make_image_id(self, panorama_id: str, heading: int) -> str:
        return hashlib.md5(f"{panorama_id}:{heading}".encode()).hexdigest()[:12]

    def fetch_all_headings(
        self,
        meta: PanoramaMetadata,
        candidate: CandidatePoint,
        headings: list[int],
        max_images: int = 80,
    ) -> list[ImageRecord]:
        """
        Download images at each heading for a panorama.

        Returns a list of ImageRecord objects (some may be cached).
        """
        records: list[ImageRecord] = []

        for heading in headings:
            image_id = self._make_image_id(meta.panorama_id, heading)

            # Cache hit
            if image_id in self._index:
                existing = self._index[image_id]
                if Path(existing.file_path).exists():
                    log.debug("Cache hit: image %s (heading=%d)", image_id, heading)
                    records.append(existing)
                    continue

            # Safety limit
            if self._request_count >= max_images:
                log.warning(
                    "Reached max_images=%d — stopping imagery download early.",
                    max_images,
                )
                break

            rec = self._download_image(meta, candidate, heading, image_id)
            if rec:
                records.append(rec)
                self._index[image_id] = rec
                self._save_index()
            time.sleep(self._rate_delay_s)

        return records

    @retry(
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _download_image(
        self,
        meta: PanoramaMetadata,
        candidate: CandidatePoint,
        heading: int,
        image_id: str,
    ) -> Optional[ImageRecord]:
        """Download a single directional image."""
        self._request_count += 1

        params = {
            "size": f"{self._width}x{self._height}",
            "pano": meta.panorama_id,
            "heading": heading,
            "pitch": self._pitch,
            "fov": self._fov,
            "key": self._api_key,
        }

        log.info(
            "Image API request #%d: pano=%s heading=%d",
            self._request_count, meta.panorama_id, heading,
        )

        try:
            response = requests.get(_STATIC_URL, params=params, timeout=_TIMEOUT_S)
            response.raise_for_status()
        except requests.RequestException as e:
            log.error("Image download failed: pano=%s heading=%d: %s",
                      meta.panorama_id, heading, e)
            raise

        # Check for error image (Google returns a 200 with a grey image for errors)
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            log.warning("Non-image response for pano=%s heading=%d", meta.panorama_id, heading)
            return None

        # Save to disk
        filename = f"{image_id}_h{heading:03d}.jpg"
        subdir = self._output_dir / meta.candidate_id
        subdir.mkdir(parents=True, exist_ok=True)
        file_path = subdir / filename

        file_path.write_bytes(response.content)
        log.debug("Saved image: %s (%d bytes)", file_path, len(response.content))

        return ImageRecord(
            image_id=image_id,
            candidate_id=candidate.id,
            panorama_id=meta.panorama_id,
            latitude=meta.pano_lat or candidate.latitude,
            longitude=meta.pano_lon or candidate.longitude,
            heading=heading,
            pitch=self._pitch,
            field_of_view=self._fov,
            capture_date=meta.capture_date,
            source=meta.source,
            file_path=str(file_path),
        )
