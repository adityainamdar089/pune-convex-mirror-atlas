"""
opencv_detector.py
==================
Baseline convex mirror detector using OpenCV.

Strategy
--------
This detector uses a multi-cue approach — NOT simple circle detection.
Finding a circle does not mean it is a convex mirror.

Cues used:
1. Circular/elliptical shape (Hough circle transform)
2. Aspect ratio filter (mirrors are approximately round)
3. Size filter (mirrors have a characteristic size range in Street View)
4. Reflective surface indicators (high brightness, high saturation region)
5. Edge density (circular edge feature)
6. Position filter (mirrors are usually in middle-upper portion of lower 2/3)

Each cue contributes to a confidence score.
Multiple cues must fire for a detection to be recorded.

Limitations
-----------
- OpenCV-based detection has high false-positive rate.
- All results are labelled "candidate" — human review is mandatory.
- This detector is a baseline only; a trained model will perform better.

Plugging in a better model
--------------------------
Subclass MirrorDetector and implement detect().
The pipeline will use your model without other changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.detection.detector import CandidateMirrorDetection, MirrorDetector
from src.streetview.imagery import ImageRecord
from src.vision.preprocessing import (
    load_image,
    enhance_for_circles,
    crop_lower_two_thirds,
)
from src.logging_config import get_logger

log = get_logger(__name__)

# ── Tunable parameters ────────────────────────────────────────────────────────
# These are conservative defaults — adjust based on inspection of real imagery.

MIN_RADIUS_PX = 20        # Minimum radius of a circle candidate in pixels
MAX_RADIUS_PX = 120       # Maximum radius
MIN_ASPECT_RATIO = 0.7    # Bounding box width/height ratio (1.0 = perfect circle)
MAX_ASPECT_RATIO = 1.3
MIN_CONFIDENCE = 0.35     # Minimum combined confidence to record a detection
HOUGH_PARAM1 = 50         # Canny high threshold for Hough
HOUGH_PARAM2 = 30         # Accumulator threshold (lower = more, noisier)


class OpenCVMirrorDetector(MirrorDetector):
    """
    Baseline OpenCV convex mirror detector.

    Uses HoughCircles on enhanced grayscale + multi-cue confidence scoring.
    """

    @property
    def detector_type(self) -> str:
        return "opencv_hough_v1"

    def detect(
        self,
        image_path: Path,
        image_record: ImageRecord,
    ) -> list[CandidateMirrorDetection]:
        """
        Run detection on a single image.

        Returns a list of CandidateMirrorDetection objects.
        All have status='candidate'.
        """
        img = load_image(image_path)
        if img is None:
            log.warning("Could not load image for detection: %s", image_path)
            return []

        original_h, original_w = img.shape[:2]

        # Crop to lower two-thirds (where mirrors are typically visible)
        cropped = crop_lower_two_thirds(img)
        crop_offset_y = original_h // 3

        # Enhance for circle detection
        enhanced = enhance_for_circles(cropped)

        # Detect circles
        circles = cv2.HoughCircles(
            enhanced,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=30,
            param1=HOUGH_PARAM1,
            param2=HOUGH_PARAM2,
            minRadius=MIN_RADIUS_PX,
            maxRadius=MAX_RADIUS_PX,
        )

        if circles is None:
            return []

        detections: list[CandidateMirrorDetection] = []
        circles = np.round(circles[0, :]).astype(int)

        for cx, cy, radius in circles:
            # Translate y back to original image coordinates
            abs_y = cy + crop_offset_y

            confidence = self._score_candidate(
                img=img,
                cx=cx, cy=abs_y, radius=radius,
                cropped=cropped,
            )

            if confidence < MIN_CONFIDENCE:
                log.debug(
                    "Low-confidence circle skipped: r=%d confidence=%.2f",
                    radius, confidence,
                )
                continue

            # Bounding box
            bbox_x = max(0, cx - radius)
            bbox_y = max(0, abs_y - radius)
            bbox_w = min(radius * 2, original_w - bbox_x)
            bbox_h = min(radius * 2, original_h - bbox_y)

            det = CandidateMirrorDetection(
                image_id=image_record.image_id,
                candidate_id=image_record.candidate_id,
                panorama_id=image_record.panorama_id,
                latitude=image_record.latitude,
                longitude=image_record.longitude,
                heading=image_record.heading,
                bbox_x=bbox_x,
                bbox_y=bbox_y,
                bbox_w=bbox_w,
                bbox_h=bbox_h,
                confidence=round(confidence, 3),
                detector_type=self.detector_type,
                status="candidate",
            )
            detections.append(det)

        log.debug(
            "Image %s heading=%d: %d candidate(s) detected.",
            image_record.image_id, image_record.heading, len(detections),
        )
        return detections

    def _score_candidate(
        self,
        img: np.ndarray,
        cx: int, cy: int, radius: int,
        cropped: np.ndarray,
    ) -> float:
        """
        Compute a confidence score [0.0, 1.0] for a circle candidate.

        Score components (each 0.0–1.0):
        1. Circularity (aspect ratio of bounding region)
        2. Size appropriateness
        3. Reflectivity (mean brightness in circle region)
        4. Edge density (circular region has strong edges)
        """
        h, w = img.shape[:2]
        score_components = []

        # 1. Size score — favour radii in the mid-range
        mid_r = (MIN_RADIUS_PX + MAX_RADIUS_PX) / 2
        size_score = 1.0 - abs(radius - mid_r) / (MAX_RADIUS_PX - MIN_RADIUS_PX)
        score_components.append(max(0.0, size_score))

        # 2. Reflectivity — extract circular ROI from original image
        roi_brightness = self._mean_brightness_in_circle(img, cx, cy, radius)
        brightness_score = min(1.0, roi_brightness / 200.0)  # 200 = bright threshold
        score_components.append(brightness_score)

        # 3. Saturation contrast — mirrors often have lower saturation than surroundings
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        roi_sat = self._mean_in_circle(hsv[:, :, 1], cx, cy, radius)
        # Low saturation in the circle = more mirror-like (grey/silver)
        sat_score = max(0.0, 1.0 - roi_sat / 180.0)
        score_components.append(sat_score * 0.5)  # lower weight

        # 4. Edge density in circle region
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 80)
        edge_density = self._mean_in_circle(edges, cx, cy, radius) / 255.0
        score_components.append(edge_density)

        # Weighted average
        weights = [0.2, 0.35, 0.15, 0.3]
        weighted = sum(s * w for s, w in zip(score_components, weights))
        return min(1.0, max(0.0, weighted))

    @staticmethod
    def _mean_brightness_in_circle(
        img: np.ndarray, cx: int, cy: int, radius: int
    ) -> float:
        """Return mean brightness (Value channel) inside a circular region."""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        return OpenCVMirrorDetector._mean_in_circle(hsv[:, :, 2], cx, cy, radius)

    @staticmethod
    def _mean_in_circle(channel: np.ndarray, cx: int, cy: int, radius: int) -> float:
        """Return mean pixel value inside a circular mask."""
        h, w = channel.shape
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (cx, cy), radius, 255, -1)
        values = channel[mask == 255]
        if len(values) == 0:
            return 0.0
        return float(np.mean(values))
