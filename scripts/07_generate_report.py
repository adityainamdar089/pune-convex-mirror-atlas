"""
07_generate_report.py
=====================
Step 7: Generate summary statistics report.

Usage
-----
    python scripts/07_generate_report.py

Output
------
    data/results/summary.json
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel

from src.config import get_config
from src.logging_config import setup_logging
from src.review.cli_review import load_mirrors
from src.utils.stats import generate_summary

console = Console()


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    cfg = get_config()
    setup_logging(cfg.log_level)

    mirrors_path = cfg.results_dir / "mirrors.csv"
    mirrors = load_mirrors(mirrors_path) if mirrors_path.exists() else []

    candidate_count = _count_csv_rows(cfg.processed_dir / "candidate_points.csv")
    panorama_count = _count_csv_rows(
        cfg.processed_dir / "streetview_metadata.csv"
    )
    image_count = _count_csv_rows(cfg.raw_dir / "image_index.csv")
    detection_count = _count_csv_rows(cfg.processed_dir / "detections.csv")
    dedup_count = _count_csv_rows(cfg.processed_dir / "deduplicated_mirrors.csv")

    sv_meta_path = cfg.processed_dir / "streetview_metadata.csv"
    sv_available = 0
    sv_unavailable = 0
    if sv_meta_path.exists():
        with open(sv_meta_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("status") == "OK":
                    sv_available += 1
                else:
                    sv_unavailable += 1

    confirmed = sum(1 for m in mirrors if m.status == "confirmed")
    rejected = sum(1 for m in mirrors if m.status == "rejected")
    uncertain = sum(1 for m in mirrors if m.status == "uncertain")
    duplicates_removed = max(0, detection_count - dedup_count)

    output_path = cfg.results_dir / "summary.json"
    summary = generate_summary(
        candidate_points=candidate_count,
        sv_available=sv_available,
        sv_unavailable=sv_unavailable,
        panoramas_processed=panorama_count,
        images_processed=image_count,
        detections_total=detection_count,
        confirmed=confirmed,
        rejected=rejected,
        uncertain=uncertain,
        duplicates_removed=duplicates_removed,
        output_path=output_path,
    )

    console.print(Panel(
        f"[bold]Summary Report[/]\n\n"
        f"Candidate points:    {candidate_count}\n"
        f"Street View found:   {sv_available}\n"
        f"Images processed:    {image_count}\n"
        f"Candidates detected: {detection_count}\n"
        f"Duplicates removed:  {duplicates_removed}\n"
        f"After dedup:         {dedup_count}\n"
        f"\n[green]Confirmed mirrors:   {confirmed}[/]\n"
        f"[yellow]Uncertain:           {uncertain}[/]\n"
        f"[red]Rejected:            {rejected}[/]\n"
        f"\nSaved to: {output_path}",
        border_style="green",
        title="🪞 Pune Convex Mirror Atlas",
    ))


if __name__ == "__main__":
    main()
