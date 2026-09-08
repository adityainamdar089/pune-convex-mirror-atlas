"""
preprocessing.py
================
Image preprocessing utilities for convex mirror detection.

Functions
---------
- load_image           — Load a JPEG from disk into numpy array.
- resize_image         — Resize to detection target size.
- normalize_image      — Normalize pixel values to [0, 1].
- enhance_for_circles  — Enhance circular feature detection.
- crop_lower_half      — Focus on road-level area (mirrors are typically
                         in the lower two-thirds of the frame).
- generate_thumbnail   — Create a small thumbnail for the review UI.
- save_processed       — Save a processed image to the processed directory.

All functions operate on numpy arrays (BGR, uint8) for OpenCV compatibility.
Original source images are NEVER modified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image as PILImage

from src.logging_config import get_logger

log = get_logger(__name__)

# Target size for detection input
DETECT_WIDTH = 640
DETECT_HEIGHT = 640

# Thumbnail size for review UI
THUMB_WIDTH = 320
THUMB_HEIGHT = 320


def load_image(path: Path) -> Optional[np.ndarray]:
    """
    Load an image from disk as a BGR numpy array.

    Returns None if the file cannot be read.
    """
    try:
        img = cv2.imread(str(path))
        if img is None:
            log.warning("OpenCV could not load image: %s", path)
            return None
        return img
    except Exception as e:
        log.error("Error loading image %s: %s", path, e)
        return None


def resize_image(
    img: np.ndarray,
    width: int = DETECT_WIDTH,
    height: int = DETECT_HEIGHT,
) -> np.ndarray:
    """Resize image to target dimensions, preserving aspect ratio with padding."""
    h, w = img.shape[:2]
    scale = min(width / w, height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Pad to exact target size
    top = (height - new_h) // 2
    bottom = height - new_h - top
    left = (width - new_w) // 2
    right = width - new_w - left
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                cv2.BORDER_CONSTANT, value=(0, 0, 0))
    return padded


def normalize_image(img: np.ndarray) -> np.ndarray:
    """Return a float32 array with pixel values in [0, 1]."""
    return img.astype(np.float32) / 255.0


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert BGR to grayscale."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def enhance_for_circles(img: np.ndarray) -> np.ndarray:
    """
    Enhance image for circular feature detection.

    Steps:
    1. Convert to grayscale.
    2. Apply bilateral filter (edge-preserving smoothing).
    3. Equalise histogram (improve contrast in dark scenes).
    """
    gray = to_grayscale(img)
    filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    equalized = cv2.equalizeHist(filtered)
    return equalized


def crop_lower_two_thirds(img: np.ndarray) -> np.ndarray:
    """
    Crop image to the lower two-thirds of the frame.

    Convex mirrors in Street View typically appear in the lower portion
    of the image, mounted on poles at the road edge.
    """
    h = img.shape[0]
    start = h // 3
    return img[start:, :]


def generate_thumbnail(
    source_path: Path,
    thumbnail_path: Path,
    width: int = THUMB_WIDTH,
    height: int = THUMB_HEIGHT,
) -> Optional[Path]:
    """
    Generate a thumbnail from the source image using Pillow.

    Does NOT modify the source image.
    Returns the thumbnail path on success, None on failure.
    """
    try:
        with PILImage.open(source_path) as im:
            im.thumbnail((width, height), PILImage.LANCZOS)
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            im.save(str(thumbnail_path), format="JPEG", quality=75)
        log.debug("Thumbnail created: %s", thumbnail_path)
        return thumbnail_path
    except Exception as e:
        log.error("Failed to create thumbnail for %s: %s", source_path, e)
        return None


def save_processed(
    img: np.ndarray,
    output_path: Path,
) -> Optional[Path]:
    """
    Save a processed numpy image to disk as JPEG.

    Returns the path on success, None on failure.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if img.dtype != np.uint8:
            img = (img * 255).clip(0, 255).astype(np.uint8)
        cv2.imwrite(str(output_path), img)
        log.debug("Saved processed image: %s", output_path)
        return output_path
    except Exception as e:
        log.error("Failed to save processed image %s: %s", output_path, e)
        return None
