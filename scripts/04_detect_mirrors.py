"""
04_detect_mirrors.py
====================
Step 4: Run convex mirror detection on downloaded imagery.

Uses the baseline OpenCV detector.
All results are labelled CANDIDATE until human review (Step 5).

Usage
-----
    python scripts/04_detect_mirrors.py

Output
------
    data/processed/detections.csv
    data/processed/deduplicated_mirrors.csv
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich import box
from rich.table import Table

from src.config import get_config
from src.logging_config import setup_logging, get_logger
from src.streetview.imagery import ImageRecord, _IMAGE_CSV_FIELDS
from src.detection.opencv_detector import OpenCVMirrorDetector
from src.detection.deduplication import deduplicate_detections
from src.detection.detector import _DETECTION_CSV_FIELDS

console = Console()


def _load_image_records(path: Path) -> list[ImageRecord]:
    records = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rec = ImageRecord(
                image_id=row["image_id"],
                candidate_id=row["candidate_id"],
                panorama_id=row["panorama_id"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                heading=int(row["heading"]),
                pitch=int(row["pitch"]),
                field_of_view=int(row["field_of_view"]),
                capture_date=row["capture_date"],
                source=row["source"],
                file_path=row["file_path"],
                fetched_at=row.get("fetched_at", ""),
            )
            records.append(rec)
    return records


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    cfg = get_config()
    setup_logging(cfg.log_level)
    log = get_logger(__name__)

    index_path = cfg.raw_dir / "image_index.csv"
    if not index_path.exists():
        console.print(
            f"[red]image_index.csv not found at {index_path}.[/]\n"
            f"Run [cyan]python scripts/03_download_imagery.py[/] first."
        )
        sys.exit(1)

    records = _load_image_records(index_path)
    console.print(
        f"\n[bold cyan]Pune Convex Mirror Atlas — Step 4: Mirror Detection[/]\n"
        f"Images to process: [yellow]{len(records)}[/]\n"
        f"Detector: [green]OpenCV Hough + multi-cue scoring[/]\n"
        f"[dim]All results are CANDIDATES — human review required.[/]\n"
    )

    detector = OpenCVMirrorDetector()
    detections = detector.detect_all(records)

    # Save detections
    det_path = cfg.processed_dir / "detections.csv"
    det_path.parent.mkdir(parents=True, exist_ok=True)
    with open(det_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_DETECTION_CSV_FIELDS)
        writer.writeheader()
        for d in detections:
            writer.writerow(d.as_dict())

    # Deduplicate
    unique = deduplicate_detections(detections)

    dedup_path = cfg.processed_dir / "deduplicated_mirrors.csv"
    with open(dedup_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(unique[0].as_dict().keys()) if unique else [])
        if unique:
            writer.writeheader()
            for u in unique:
                writer.writerow(u.as_dict())

    # Summary
    console.print(
        f"[green][OK] Detection complete.[/]\n"
        f"  Total candidate detections: [yellow]{len(detections)}[/]\n"
        f"  After deduplication:        [yellow]{len(unique)}[/]\n\n"
        f"[bold]Next step:[/] Run [cyan]python scripts/05_review.py[/] "
        f"to manually verify candidates."
    )


if __name__ == "__main__":
    main()
