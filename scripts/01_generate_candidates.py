"""
01_generate_candidates.py
=========================
Step 1: Generate candidate road points within the Ganga Dham boundary.

Usage
-----
    python scripts/01_generate_candidates.py

    # To use grid sampling instead of test points:
    python scripts/01_generate_candidates.py --grid

    # To expand grid density:
    python scripts/01_generate_candidates.py --grid --spacing 25

Output
------
    data/processed/candidate_points.csv
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table
from rich import box

from src.config import get_config
from src.logging_config import setup_logging, get_logger
from src.geo.boundary import get_ganga_dham_boundary
from src.geo.sampling import generate_candidates, save_candidates

console = Console()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Generate candidate points within Ganga Dham."
    )
    parser.add_argument(
        "--grid", action="store_true",
        help="Use grid sampling instead of hand-curated test points."
    )
    parser.add_argument(
        "--spacing", type=int, default=40,
        help="Grid spacing in metres (default: 40)."
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Override MAX_CANDIDATE_POINTS from config."
    )
    args = parser.parse_args()

    cfg = get_config()
    setup_logging(cfg.log_level)
    log = get_logger(__name__)

    max_points = args.max or cfg.max_candidate_points

    console.print(
        f"\n[bold cyan]Pune Convex Mirror Atlas — Step 1: Generate Candidates[/]\n"
        f"Area: [yellow]{cfg.area_name}, {cfg.area_city}[/]\n"
        f"Mode: {'[magenta]Grid[/]' if args.grid else '[green]Test Points (hand-curated)[/]'}\n"
        f"Max points: [yellow]{max_points}[/]\n"
    )

    boundary = get_ganga_dham_boundary()

    candidates = generate_candidates(
        boundary=boundary,
        spacing_m=args.spacing,
        max_points=max_points,
        use_test_points=not args.grid,
        area_name=cfg.area_name,
    )

    if not candidates:
        console.print("[red]No candidates generated — check boundary configuration.[/]")
        sys.exit(1)

    # Display table
    table = Table(
        title=f"Candidate Points ({len(candidates)} total)",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("ID", style="dim", width=10)
    table.add_column("Latitude", justify="right")
    table.add_column("Longitude", justify="right")
    table.add_column("Area")
    table.add_column("In Boundary?", justify="center")

    for c in candidates:
        in_bnd = "YES" if boundary.contains(c.latitude, c.longitude) else "NO"
        table.add_row(c.id, f"{c.latitude:.6f}", f"{c.longitude:.6f}", c.area, in_bnd)

    console.print(table)

    # Save
    output_path = cfg.processed_dir / "candidate_points.csv"
    save_candidates(candidates, output_path)
    console.print(f"\n[green]Saved {len(candidates)} candidates to:[/] {output_path}")
    console.print(
        "\n[bold]Next step:[/] Run [cyan]python scripts/02_check_streetview.py[/] "
        "to check Street View availability.\n"
        "[dim](Requires GOOGLE_MAPS_API_KEY in .env)[/]"
    )



if __name__ == "__main__":
    main()
