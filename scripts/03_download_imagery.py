"""
03_download_imagery.py
======================
Step 3: Download Street View directional imagery for available panoramas.

⚠️  REQUIRES Google Maps API key in .env
⚠️  Street View Static API CHARGES PER IMAGE — check current pricing
⚠️  With 8 headings × 10 panoramas = 80 images

    Current pricing: https://developers.google.com/maps/documentation/streetview/usage-and-billing

Usage
-----
    python scripts/03_download_imagery.py

Output
------
    data/raw/<candidate_id>/<image_id>_h<heading>.jpg
    data/raw/image_index.csv
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.prompt import Confirm
from rich import box
from rich.table import Table

import argparse

from src.config import get_config
from src.logging_config import setup_logging, get_logger
from src.geo.sampling import load_candidates
from src.streetview.metadata import save_metadata
from src.streetview.imagery import StreetViewImageryClient

console = Console()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Download Street View imagery.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip interactive confirmation.")
    args = parser.parse_args()

    cfg = get_config()
    setup_logging(cfg.log_level)
    log = get_logger(__name__)

    try:
        cfg.validate()
    except EnvironmentError as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)

    # Load metadata
    import csv
    from src.streetview.metadata import PanoramaMetadata

    metadata_path = cfg.processed_dir / "streetview_metadata.csv"
    if not metadata_path.exists():
        console.print(
            f"[red]streetview_metadata.csv not found.[/]\n"
            f"Run [cyan]python scripts/02_check_streetview.py[/] first."
        )
        sys.exit(1)

    from src.streetview.metadata import save_metadata
    import csv

    available_meta = []
    with open(metadata_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "OK":
                available_meta.append(
                    PanoramaMetadata(
                        candidate_id=row["candidate_id"],
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                        panorama_id=row["panorama_id"],
                        capture_date=row["capture_date"],
                        source=row["source"],
                        status=row["status"],
                        pano_lat=float(row["pano_lat"]) if row["pano_lat"] else None,
                        pano_lon=float(row["pano_lon"]) if row["pano_lon"] else None,
                    )
                )

    candidates = load_candidates(cfg.processed_dir / "candidate_points.csv")
    candidate_map = {c.id: c for c in candidates}

    headings = cfg.headings
    expected_images = len(available_meta) * len(headings)
    expected_images = min(expected_images, cfg.max_images)

    console.print(f"""
[bold cyan]Pune Convex Mirror Atlas — Step 3: Download Imagery[/]

Available panoramas:  [yellow]{len(available_meta)}[/]
Headings per pano:    [yellow]{len(headings)}[/] {headings}
Expected images:      [yellow]{expected_images}[/] (capped at MAX_IMAGES={cfg.max_images})

[bold red]⚠️  WARNING: Street View Static API charges per image.[/]
[dim]See: https://developers.google.com/maps/documentation/streetview/usage-and-billing[/]
""")

    if not args.yes and not Confirm.ask(
        f"Proceed with downloading up to {expected_images} images?",
        default=False,
    ):
        console.print("Aborted.")
        sys.exit(0)

    client = StreetViewImageryClient(
        api_key=cfg.effective_street_view_key,
        output_dir=cfg.raw_dir,
        width=cfg.image_width,
        height=cfg.image_height,
        pitch=cfg.pitch,
        fov=cfg.fov,
    )

    all_records = []
    for meta in available_meta[:cfg.max_panoramas]:
        candidate = candidate_map.get(meta.candidate_id)
        if candidate is None:
            log.warning("Candidate %s not found — skipping.", meta.candidate_id)
            continue

        records = client.fetch_all_headings(
            meta=meta,
            candidate=candidate,
            headings=headings,
            max_images=cfg.max_images,
        )
        all_records.extend(records)

    console.print(
        f"\n[green][OK] Downloaded {len(all_records)} images.[/]\n"
        f"Stored in: {cfg.raw_dir}\n\n"
        f"[bold]Next step:[/] Run [cyan]python scripts/04_detect_mirrors.py[/]"
    )


if __name__ == "__main__":
    main()
