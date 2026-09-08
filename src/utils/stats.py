"""
stats.py
========
Generates a summary statistics report.

Output: data/results/summary.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.review.cli_review import MirrorRecord
from src.logging_config import get_logger

log = get_logger(__name__)


def generate_summary(
    candidate_points: int,
    sv_available: int,
    sv_unavailable: int,
    panoramas_processed: int,
    images_processed: int,
    detections_total: int,
    confirmed: int,
    rejected: int,
    uncertain: int,
    duplicates_removed: int,
    output_path: Path,
) -> dict:
    """
    Calculate and save summary statistics.

    Returns the summary dict.
    """
    unique_mirrors = confirmed + uncertain  # excludes rejected

    detection_rate = (
        round(detections_total / images_processed, 4)
        if images_processed > 0
        else 0.0
    )
    confirmation_rate = (
        round(confirmed / detections_total, 4)
        if detections_total > 0
        else 0.0
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "area": "Ganga Dham, Bibwewadi, Pune, Maharashtra, India",
        "pipeline_stats": {
            "total_candidate_points": candidate_points,
            "street_view_available": sv_available,
            "street_view_unavailable": sv_unavailable,
            "panoramas_processed": panoramas_processed,
            "images_processed": images_processed,
        },
        "detection_stats": {
            "mirror_candidates_detected": detections_total,
            "duplicates_removed": duplicates_removed,
            "unique_candidates_after_dedup": detections_total - duplicates_removed,
        },
        "verification_stats": {
            "confirmed_mirrors": confirmed,
            "rejected_candidates": rejected,
            "uncertain_candidates": uncertain,
        },
        "rates": {
            "detection_rate_per_image": detection_rate,
            "confirmation_rate": confirmation_rate,
            "unique_mirror_count": confirmed,
        },
        "caveats": [
            "Detection uses a baseline OpenCV algorithm. False positives are expected.",
            "All candidates require human verification before being counted as mirrors.",
            "Coverage is limited to panoramas available in Google Street View.",
            "The scan area is restricted to the configured Ganga Dham boundary polygon.",
            "Not all convex mirrors in the area may have been found.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    log.info("Summary saved to %s", output_path)
    log.info(
        "Results: %d confirmed | %d rejected | %d uncertain | "
        "%d duplicates removed.",
        confirmed, rejected, uncertain, duplicates_removed,
    )
    return summary
