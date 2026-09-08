"""
02_check_streetview.py
======================
Step 2: Check Street View availability for candidate points.

⚠️  REQUIRES Google Maps API key in .env
⚠️  Uses Street View METADATA API — check current pricing

Usage
-----
    python scripts/02_check_streetview.py

Output
------
    data/processed/streetview_metadata.csv
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import box

import argparse

from src.config import get_config
from src.logging_config import setup_logging, get_logger
from src.geo.sampling import load_candidates
from src.streetview.metadata import StreetViewMetadataClient, save_metadata

console = Console()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Check Street View availability.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip interactive confirmation.")
    args = parser.parse_args()

    cfg = get_config()
    setup_logging(cfg.log_level)
    log = get_logger(__name__)

    # Validate API key
    try:
        cfg.validate()
    except EnvironmentError as e:
        console.print(f"[red]Configuration error:[/]\n{e}")
        sys.exit(1)

    # Load candidates
    candidates_path = cfg.processed_dir / "candidate_points.csv"
    if not candidates_path.exists():
        console.print(
            f"[red]candidate_points.csv not found at {candidates_path}.[/]\n"
            f"Run [cyan]python scripts/01_generate_candidates.py[/] first."
        )
        sys.exit(1)

    candidates = load_candidates(candidates_path)

    # Pre-flight summary
    expected_requests = len(candidates)
    console.print(f"""
[bold cyan]Pune Convex Mirror Atlas — Step 2: Street View Availability[/]

Candidates to check: [yellow]{len(candidates)}[/]
Expected API requests: [yellow]{expected_requests}[/] (Metadata API)
Max requests limit: [yellow]{cfg.max_api_requests}[/]

[dim]Note: Street View Metadata API calls may be free — check current Google pricing.
https://developers.google.com/maps/documentation/streetview/usage-and-billing[/]
""")

    if expected_requests > cfg.max_api_requests:
        console.print(
            f"[red]Would exceed MAX_API_REQUESTS ({cfg.max_api_requests}). "
            f"Reduce candidate count or increase limit in .env.[/]"
        )
        sys.exit(1)

    if not args.yes and not Confirm.ask(f"Proceed with {expected_requests} metadata requests?"):
        console.print("Aborted.")
        sys.exit(0)

    # Fetch
    cache_path = cfg.processed_dir / "metadata_cache.csv"
    client = StreetViewMetadataClient(
        api_key=cfg.google_maps_api_key,
        cache_path=cache_path,
        radius_m=50,
    )

    results = client.fetch_all(candidates, max_requests=cfg.max_api_requests)

    # Save
    output_path = cfg.processed_dir / "streetview_metadata.csv"
    save_metadata(results, output_path)

    # Summary table
    available = [r for r in results if r.available]
    table = Table(box=box.ROUNDED, border_style="cyan", title="Street View Results")
    table.add_column("Candidate ID", style="dim")
    table.add_column("Status")
    table.add_column("Panorama ID")
    table.add_column("Date")

    for r in results:
        status_str = "[green]OK[/]" if r.available else f"[red]{r.status}[/]"
        table.add_row(r.candidate_id, status_str, r.panorama_id or "—", r.capture_date or "—")

    console.print(table)
    console.print(
        f"\n[green][OK] {len(available)}/{len(results)} candidates have Street View coverage.[/]"
    )
    console.print(f"Saved to: {output_path}")
    console.print(
        "\n[bold]Next step:[/] Run [cyan]python scripts/03_download_imagery.py[/]\n"
        "[dim](This WILL incur API charges — review pricing first)[/]"
    )


if __name__ == "__main__":
    main()
