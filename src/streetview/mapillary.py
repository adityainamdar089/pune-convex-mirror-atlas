"""
mapillary.py
============
Client for querying and downloading open street-level imagery from Mapillary API v4.
Mapillary requires NO credit card or billing account.

API Documentation:
https://www.mapillary.com/developer/api-documentation
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.logging_config import get_logger
from src.streetview.imagery import ImageRecord, _IMAGE_CSV_FIELDS

log = get_logger(__name__)

_MAPILLARY_IMAGES_URL = "https://graph.mapillary.com/images"
_TIMEOUT_S = 15
_RETRY_ATTEMPTS = 3


@dataclass
class MapillaryImageMetadata:
    id: str
    latitude: float
    longitude: float
    compass_angle: int
    captured_at: str
    thumb_url: str


class MapillaryClient:
    """Queries Mapillary API v4 for street-level imagery."""

    def __init__(self, client_token: str, output_dir: Path):
        self.client_token = client_token.strip()
        self.output_dir = output_dir

    @retry(
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def search_images(
        self,
        bbox: tuple[float, float, float, float],
        limit: int = 50,
    ) -> list[MapillaryImageMetadata]:
        """
        Search for images within a bounding box.

        Parameters
        ----------
        bbox: (min_lat, min_lon, max_lat, max_lon)
        limit: Maximum number of images to return.
        """
        min_lat, min_lon, max_lat, max_lon = bbox
        # Mapillary expects bbox as: min_lon,min_lat,max_lon,max_lat
        bbox_str = f"{min_lon:.6f},{min_lat:.6f},{max_lon:.6f},{max_lat:.6f}"

        headers = {"Authorization": f"OAuth {self.client_token}"}
        params = {
            "bbox": bbox_str,
            "fields": "id,geometry,compass_angle,captured_at,thumb_1024_url",
            "limit": limit,
        }

        log.debug("Querying Mapillary API for bbox %s", bbox_str)
        response = requests.get(_MAPILLARY_IMAGES_URL, headers=headers, params=params, timeout=_TIMEOUT_S)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("data", []):
            img_id = str(item.get("id"))
            geom = item.get("geometry", {})
            coords = geom.get("coordinates", [0.0, 0.0])
            lon, lat = coords[0], coords[1]
            angle = int(round(item.get("compass_angle", 0)))
            captured = str(item.get("captured_at", ""))
            thumb_url = item.get("thumb_1024_url", "")

            if thumb_url and lat != 0.0:
                results.append(
                    MapillaryImageMetadata(
                        id=img_id,
                        latitude=lat,
                        longitude=lon,
                        compass_angle=angle,
                        captured_at=captured,
                        thumb_url=thumb_url,
                    )
                )

        log.info("Found %d images on Mapillary within bounding box.", len(results))
        return results

    def download_image(self, meta: MapillaryImageMetadata, candidate_id: str = "mapillary") -> Optional[ImageRecord]:
        """Download a single image from Mapillary and save it locally."""
        dest_dir = self.output_dir / candidate_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"mapillary_{meta.id}.jpg"
        dest_file = dest_dir / filename

        # Cache check
        if not dest_file.exists():
            log.debug("Downloading Mapillary image %s", meta.id)
            try:
                resp = requests.get(meta.thumb_url, timeout=_TIMEOUT_S)
                resp.raise_for_status()
                with open(dest_file, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                log.warning("Failed to download Mapillary image %s: %s", meta.id, e)
                return None

        # Build relative path
        rel_path = f"data/raw/{candidate_id}/{filename}"

        return ImageRecord(
            image_id=f"mapillary_{meta.id}",
            candidate_id=candidate_id,
            panorama_id=meta.id,
            latitude=meta.latitude,
            longitude=meta.longitude,
            heading=meta.compass_angle,
            pitch=0,
            field_of_view=90,
            capture_date=meta.captured_at[:7] if meta.captured_at else "2024",
            source="mapillary",
            file_path=rel_path,
        )

    def download_all(
        self,
        images_meta: list[MapillaryImageMetadata],
        max_images: int = 50,
    ) -> list[ImageRecord]:
        records = []
        for meta in images_meta[:max_images]:
            rec = self.download_image(meta)
            if rec:
                records.append(rec)
            time.sleep(0.1)  # polite rate limit

        # Save to image_index.csv
        index_path = self.output_dir / "image_index.csv"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_IMAGE_CSV_FIELDS)
            writer.writeheader()
            for r in records:
                writer.writerow(r.as_dict())

        return records
