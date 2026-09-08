"""
run_demo.py
===========
Demo runner that executes the entire pipeline with synthetic Street View
data and realistic convex mirror visual features, requiring ZERO API calls.

Generates:
  1. Candidate road points in Ganga Dham
  2. Mock Street View metadata
  3. Synthetic directional images with drawn convex mirrors
  4. Runs OpenCV detector
  5. Deduplication & verification
  6. Interactive HTML map, gallery, and presentation
  7. Summary statistics report
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from rich.console import Console
from rich.panel import Panel

from src.config import get_config
from src.geo.boundary import get_ganga_dham_boundary
from src.geo.sampling import generate_candidates, save_candidates
from src.streetview.metadata import PanoramaMetadata, save_metadata
from src.streetview.imagery import ImageRecord, _IMAGE_CSV_FIELDS
from src.detection.opencv_detector import OpenCVMirrorDetector
from src.detection.deduplication import deduplicate_detections
from src.detection.detector import _DETECTION_CSV_FIELDS
from src.review.cli_review import MirrorRecord, _save_results
from src.mapping.map_builder import build_map
from src.mapping.gallery import build_gallery
from src.mapping.presentation import build_presentation
from src.utils.stats import generate_summary

console = Console()


def create_synthetic_image(output_path: Path, heading: int, has_mirror: bool = False) -> None:
    """Create a synthetic street view image (640x640) with road, buildings, and optional convex mirror."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = np.zeros((640, 640, 3), dtype=np.uint8)

    # Sky (gradient blue)
    for y in range(260):
        b = int(220 - y * 0.3)
        g = int(180 - y * 0.2)
        r = 130
        img[y, :] = [b, g, r]

    # Ground / road (gray)
    img[260:, :] = [90, 95, 100]

    # Road perspective lines
    cv2.line(img, (200, 640), (320, 260), (140, 140, 140), 3)
    cv2.line(img, (440, 640), (320, 260), (140, 140, 140), 3)

    # Some roadside trees and building blocks
    cv2.rectangle(img, (30, 180), (160, 280), (110, 120, 140), -1)
    cv2.rectangle(img, (480, 160), (610, 290), (120, 130, 150), -1)

    # If mirror present, draw a realistic convex mirror (circular orange frame + bright reflective convex disc)
    if has_mirror:
        center = (220, 310)
        radius = 45

        # Pole
        cv2.line(img, (center[0], center[1] + radius), (center[0], 520), (50, 55, 60), 6)

        # Orange protective rim / hood
        cv2.circle(img, center, radius + 8, (20, 110, 240), -1)

        # Inner reflective mirror surface (bright silvery gradient with fish-eye reflection)
        cv2.circle(img, center, radius, (230, 235, 240), -1)

        # Concentric highlight to trigger multi-cue reflective convex score
        cv2.circle(img, (center[0] - 10, center[1] - 10), int(radius * 0.5), (250, 252, 255), -1)
        cv2.ellipse(img, center, (radius, int(radius * 0.85)), 0, 0, 360, (200, 210, 220), 3)

    cv2.imwrite(str(output_path), img)


def run_demo() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    cfg = get_config()

    console.print(Panel(
        "[bold green]Pune Convex Mirror Atlas — End-to-End Demo[/]\n\n"
        "Runs all 7 pipeline steps using synthetic Street View scenes\n"
        "No API key required — perfect for testing and presentation previews!",
        title="Demo Mode",
        border_style="cyan",
    ))

    # 1. Candidates
    boundary = get_ganga_dham_boundary()
    candidates = generate_candidates(boundary=boundary, max_points=8, use_test_points=True, area_name=cfg.area_name)
    cand_path = cfg.processed_dir / "candidate_points.csv"
    save_candidates(candidates, cand_path)
    console.print(f"[green][Step 1][/] Generated {len(candidates)} candidates.")

    # 2. Mock Metadata
    meta_results = []
    for c in candidates:
        meta_results.append(PanoramaMetadata(
            candidate_id=c.id,
            latitude=c.latitude,
            longitude=c.longitude,
            panorama_id=f"pano_{c.id}",
            capture_date="2024-03",
            source="outdoor",
            status="OK",
            pano_lat=c.latitude + 0.00002,
            pano_lon=c.longitude + 0.00002,
        ))
    meta_path = cfg.processed_dir / "streetview_metadata.csv"
    save_metadata(meta_results, meta_path)
    console.print(f"[green][Step 2][/] Generated metadata for {len(meta_results)} panoramas.")

    # 3. Synthetic Imagery
    records = []
    headings = [0, 90, 180, 270]  # 4 cardinal headings for demo speed
    console.print(f"[green][Step 3][/] Rendering synthetic directional imagery...")

    for i, meta in enumerate(meta_results):
        for h_idx, heading in enumerate(headings):
            img_id = f"demo_{meta.candidate_id}_h{heading}"
            rel_file = Path("data") / "raw" / meta.candidate_id / f"{img_id}.jpg"
            abs_file = cfg.project_root / rel_file

            # Place mirror on a few select candidate panoramas (e.g. index 0, 2, 4 at heading 90)
            has_mirror = (i in (0, 2, 4, 6) and heading == 90)
            create_synthetic_image(abs_file, heading, has_mirror=has_mirror)

            records.append(ImageRecord(
                image_id=img_id,
                candidate_id=meta.candidate_id,
                panorama_id=meta.panorama_id,
                latitude=meta.latitude,
                longitude=meta.longitude,
                heading=heading,
                pitch=0,
                field_of_view=90,
                capture_date="2024-03",
                source="outdoor",
                file_path=str(rel_file).replace("\\", "/"),
            ))

    index_path = cfg.raw_dir / "image_index.csv"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_IMAGE_CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.as_dict())
    console.print(f"[green][Step 3][/] Saved {len(records)} images.")

    # 4. Detection
    console.print(f"[green][Step 4][/] Running OpenCV mirror detection...")
    detector = OpenCVMirrorDetector()
    detections = detector.detect_all(records)

    det_path = cfg.processed_dir / "detections.csv"
    with open(det_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_DETECTION_CSV_FIELDS)
        writer.writeheader()
        for d in detections:
            writer.writerow(d.as_dict())

    unique = deduplicate_detections(detections)
    dedup_path = cfg.processed_dir / "deduplicated_mirrors.csv"
    with open(dedup_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(unique[0].as_dict().keys()) if unique else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if unique:
            writer.writeheader()
            for u in unique:
                writer.writerow(u.as_dict())
    console.print(f"[green][Step 4][/] Detected {len(detections)} candidates ({len(unique)} after deduplication).")

    # 5. Review & Confirm
    confirmed_records = []
    output_mirrors_path = cfg.results_dir / "mirrors.csv"
    for idx, u in enumerate(unique, start=1):
        det = u.best_detection
        confirmed_records.append(
            MirrorRecord(
                mirror_id=u.mirror_id,
                latitude=u.latitude,
                longitude=u.longitude,
                area=cfg.area_name,
                status="confirmed",
                confidence=u.best_confidence,
                image_reference=det.image_id if det else "",
                panorama_id=det.panorama_id if det else "",
                heading=det.heading if det else 0,
                capture_date="2024-03",
                description=f"Convex safety mirror at Ganga Dham bend #{idx}",
                sequence_number=idx,
            )
        )
    _save_results(confirmed_records, output_mirrors_path)
    console.print(f"[green][Step 5][/] Confirmed {len(confirmed_records)} mirrors.")

    # 6. Build Interactive Map, Gallery & Presentation
    console.print(f"[green][Step 6][/] Building interactive HTML maps & gallery...")
    map_path = cfg.results_dir / "ganga_dham_convex_mirror_map.html"
    build_map(confirmed_records, map_path, boundary=boundary, show_uncertain=True, show_rejected=False)

    gallery_path = cfg.results_dir / "mirror_gallery.html"
    build_gallery(confirmed_records, gallery_path, processed_dir=cfg.processed_dir)

    pres_path = cfg.results_dir / "presentation.html"
    build_presentation(confirmed_records, pres_path, map_path=map_path)
    console.print(f"[green][Step 6][/] Generated map, gallery, and presentation HTML.")

    # 7. Summary Report
    console.print(f"[green][Step 7][/] Generating summary report...")
    summary_path = cfg.results_dir / "summary.json"
    generate_summary(
        candidate_points=len(candidates),
        sv_available=len(meta_results),
        sv_unavailable=0,
        panoramas_processed=len(meta_results),
        images_processed=len(records),
        detections_total=len(detections),
        confirmed=len(confirmed_records),
        rejected=0,
        uncertain=0,
        duplicates_removed=max(0, len(detections) - len(unique)),
        output_path=summary_path,
    )

    console.print(Panel(
        f"[bold green]Demo Atlas Generated Successfully![/]\n\n"
        f"📍 [cyan]Interactive Map:[/]  {map_path}\n"
        f"🖼️  [cyan]Image Gallery:[/]    {gallery_path}\n"
        f"📊 [cyan]Presentation:[/]     {pres_path}\n"
        f"📋 [cyan]Summary JSON:[/]     {summary_path}",
        title="Demo Complete",
        border_style="green",
    ))


if __name__ == "__main__":
    run_demo()
