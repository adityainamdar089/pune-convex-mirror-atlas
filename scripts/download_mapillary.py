"""
download_mapillary.py
=====================
Downloads street-level imagery from Mapillary for the Ganga Dham / Pune area.
100% Free - Requires NO credit card or billing account.

Usage:
    python scripts/download_mapillary.py
    python scripts/download_mapillary.py --max 20

Output:
    data/raw/mapillary/<image_id>.jpg
    data/raw/image_index.csv
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel

from src.config import get_config
from src.geo.boundary import get_ganga_dham_boundary
from src.logging_config import setup_logging, get_logger
from src.streetview.mapillary import MapillaryClient

console = Console()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Download street-level images from Mapillary.")
    parser.add_argument("--max", type=int, default=30, help="Maximum images to download (default: 30).")
    parser.add_argument("--token", type=str, default="", help="Override Mapillary Client Token.")
    args = parser.parse_args()

    cfg = get_config()
    setup_logging(cfg.log_level)
    log = get_logger(__name__)

    token = args.token or cfg.mapillary_client_token
    if not token:
        console.print(Panel(
            "[bold red]Mapillary Client Token Missing![/]\n\n"
            "To get a free Mapillary Client Token (no credit card required):\n"
            "1. Visit: [cyan]https://www.mapillary.com/dashboard/developers[/]\n"
            "2. Sign up/in (Free) -> Click 'Register Application'\n"
            "3. Copy your Client Token (starts with 'MLY|...')\n"
            "4. Add to [yellow].env[/]:\n"
            "   [green]MAPILLARY_CLIENT_TOKEN=MLY|...[/]",
            title="Authentication Required",
            border_style="red",
        ))
        sys.exit(1)

    console.print(Panel(
        f"[bold cyan]Pune Convex Mirror Atlas — Mapillary Street Imagery[/]\n\n"
        f"Area: [yellow]{cfg.area_name}, {cfg.area_city}[/]\n"
        f"Max images: [yellow]{args.max}[/]\n"
        f"Source: [green]Mapillary API v4 (Free Open Data)[/]",
        title="Mapillary Downloader",
        border_style="cyan",
    ))

    boundary = get_ganga_dham_boundary()
    client = MapillaryClient(client_token=token, output_dir=cfg.raw_dir)

    console.print("[cyan]Searching for Mapillary street photos within Ganga Dham boundary...[/]")
    images_meta = client.search_images(bbox=boundary.bbox, limit=args.max * 2)

    if not images_meta:
        # Expand slightly to broader Bibwewadi / Pune area if Ganga Dham sub-polygon has few direct uploads
        console.print("[yellow]Expanding search radius to broader Pune/Bibwewadi area...[/]")
        expanded_bbox = (
            boundary.bbox[0] - 0.015,
            boundary.bbox[1] - 0.015,
            boundary.bbox[2] + 0.015,
            boundary.bbox[3] + 0.015,
        )
        images_meta = client.search_images(bbox=expanded_bbox, limit=args.max * 2)

    if not images_meta:
        console.print("[yellow]No Mapillary photos found in this immediate bounding box.[/]")
        sys.exit(0)

    console.print(f"[green]Found {len(images_meta)} images. Downloading up to {args.max}...[/]")
    records = client.download_all(images_meta, max_images=args.max)

    console.print(Panel(
        f"[bold green]Download Complete![/]\n\n"
        f"Downloaded: [yellow]{len(records)}[/] images\n"
        f"Stored in:  [cyan]{cfg.raw_dir / 'mapillary'}[/]\n"
        f"Index file: [cyan]{cfg.raw_dir / 'image_index.csv'}[/]\n\n"
        f"[bold]Next step:[/] Run [cyan]python scripts/04_detect_mirrors.py[/] to detect convex mirrors!",
        title="Ready for Detection",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
