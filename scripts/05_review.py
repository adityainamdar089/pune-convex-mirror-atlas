"""
05_review.py
============
Step 5: Human verification of candidate mirrors.

Launches the interactive terminal review interface.

Usage
-----
    python scripts/05_review.py

Output
------
    data/results/mirrors.csv
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from src.config import get_config
from src.logging_config import setup_logging
from src.detection.deduplication import DeduplicatedMirror
from src.detection.detector import CandidateMirrorDetection
from src.review.cli_review import run_review_session

console = Console()


def _load_dedup(path: Path) -> list[DeduplicatedMirror]:
    """Load deduplicated mirrors from CSV."""
    mirrors = []
    if not path.exists():
        return mirrors

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            det = CandidateMirrorDetection(
                detection_id=row.get("best_detection_id", ""),
                image_id=row.get("best_image_id", ""),
                candidate_id=row.get("best_candidate_id", ""),
                panorama_id=row.get("best_panorama_id", ""),
                latitude=float(row.get("best_latitude", row.get("latitude", 0))),
                longitude=float(row.get("best_longitude", row.get("longitude", 0))),
                heading=int(row.get("best_heading", 0)),
                bbox_x=int(row.get("best_bbox_x", 0)),
                bbox_y=int(row.get("best_bbox_y", 0)),
                bbox_w=int(row.get("best_bbox_w", 0)),
                bbox_h=int(row.get("best_bbox_h", 0)),
                confidence=float(row.get("best_confidence", row.get("best_confidence", 0))),
                detector_type=row.get("best_detector_type", "unknown"),
            )
            m = DeduplicatedMirror(
                mirror_id=row["mirror_id"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                best_confidence=float(row["best_confidence"]),
                detection_count=int(row.get("detection_count", 1)),
                best_detection=det,
                all_detections=[det],
            )
            mirrors.append(m)
    return mirrors


import argparse
from src.review.cli_review import MirrorRecord, _save_results


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Human verification of candidate mirrors.")
    parser.add_argument("--auto-confirm", action="store_true", help="Auto-confirm all candidates for automated testing.")
    args = parser.parse_args()

    cfg = get_config()
    setup_logging(cfg.log_level)

    dedup_path = cfg.processed_dir / "deduplicated_mirrors.csv"
    output_path = cfg.results_dir / "mirrors.csv"

    if not dedup_path.exists():
        console.print(
            f"[red]deduplicated_mirrors.csv not found at {dedup_path}.[/]\n"
            f"Run [cyan]python scripts/04_detect_mirrors.py[/] first."
        )
        sys.exit(1)

    candidates = _load_dedup(dedup_path)

    if not candidates:
        console.print("[yellow]No candidates to review. Detection may have found nothing.[/]")
        sys.exit(0)

    if args.auto_confirm:
        console.print(f"[yellow]Auto-confirming {len(candidates)} candidates...[/]")
        records = []
        for idx, c in enumerate(candidates, start=1):
            det = c.best_detection
            records.append(
                MirrorRecord(
                    mirror_id=c.mirror_id,
                    latitude=c.latitude,
                    longitude=c.longitude,
                    area=cfg.area_name,
                    status="confirmed",
                    confidence=c.best_confidence,
                    image_reference=det.image_id if det else "",
                    panorama_id=det.panorama_id if det else "",
                    heading=det.heading if det else 0,
                    capture_date="",
                    description=f"Candidate mirror near {cfg.area_name}",
                    sequence_number=idx,
                )
            )
        _save_results(records, output_path)
        console.print(f"[green]Saved {len(records)} confirmed mirrors to:[/] {output_path}")
    else:
        results = run_review_session(
            candidates=candidates,
            output_path=output_path,
            area_name=cfg.area_name,
            resume=True,
        )

    console.print(
        f"\n[bold]Next step:[/] Run [cyan]python scripts/06_build_map.py[/] "
        f"to generate the interactive map."
    )


if __name__ == "__main__":
    main()
