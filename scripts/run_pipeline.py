"""
run_pipeline.py
===============
Master pipeline runner for Pune Convex Mirror Atlas.

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --auto-confirm
    python scripts/run_pipeline.py --grid --spacing 30
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel

from src.config import get_config

console = Console()


def run_step(cmd: list[str], step_name: str) -> None:
    console.print(f"\n[bold cyan]>>> Running {step_name}...[/]")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        console.print(f"[bold red][FAILED] {step_name} failed with code {result.returncode}.[/]")
        sys.exit(result.returncode)
    console.print(f"[bold green][DONE] {step_name} completed successfully.[/]")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run the full Pune Convex Mirror Atlas pipeline.")
    parser.add_argument("--source", choices=["google", "mapillary"], default=None, help="Imagery source (google or mapillary).")
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Keep candidates unverified instead of claiming human confirmation.",
    )
    parser.add_argument("--grid", action="store_true", help="Use grid sampling for candidate points.")
    parser.add_argument("--spacing", type=int, default=40, help="Grid spacing in meters if using --grid.")
    args = parser.parse_args()

    cfg = get_config()

    source = args.source
    if source is None:
        if cfg.mapillary_client_token:
            source = "mapillary"
        else:
            source = "google"

    console.print(Panel(
        "[bold green]Pune Convex Mirror Atlas Pipeline[/]\n\n"
        f"Area: [yellow]{cfg.area_name}, {cfg.area_city}[/]\n"
        f"Source: [magenta]{source.upper()}[/]\n"
        f"Google API Key: {'[green]YES[/]' if cfg.has_api_key() else '[dim]NO[/]'}\n"
        f"Mapillary Token: {'[green]YES[/]' if bool(cfg.mapillary_client_token) else '[dim]NO[/]'}",
        title="Pipeline Runner",
        border_style="cyan",
    ))

    py = sys.executable

    if source == "mapillary":
        if not cfg.mapillary_client_token:
            console.print(
                "[bold red]Error: MAPILLARY_CLIENT_TOKEN is not set in .env[/]\n"
                "Get a free token from https://www.mapillary.com/dashboard/developers and add it to .env"
            )
            sys.exit(1)

        # Step 1: Candidates
        step1_cmd = [py, "scripts/01_generate_candidates.py"]
        if args.grid:
            step1_cmd.extend(["--grid", "--spacing", str(args.spacing)])
        run_step(step1_cmd, "Step 1: Generate Candidates")

        # Step 2 & 3: Download Mapillary Imagery
        run_step([py, "scripts/download_mapillary.py", "--max", str(cfg.max_images)], "Step 2/3: Download Mapillary Imagery")

    else:
        if not cfg.has_api_key():
            console.print(
                "[bold red]Error: GOOGLE_MAPS_API_KEY is not set in .env[/]\n"
                "Please configure your Google Maps API key in .env or use --source mapillary."
            )
            sys.exit(1)

        # Step 1
        step1_cmd = [py, "scripts/01_generate_candidates.py"]
        if args.grid:
            step1_cmd.extend(["--grid", "--spacing", str(args.spacing)])
        run_step(step1_cmd, "Step 1: Generate Candidates")

        # Step 2
        run_step([py, "scripts/02_check_streetview.py", "-y"], "Step 2: Check Street View Availability")

        # Step 3
        run_step([py, "scripts/03_download_imagery.py", "-y"], "Step 3: Download Street View Imagery")

    # Step 4
    run_step([py, "scripts/04_detect_mirrors.py"], "Step 4: Detect Convex Mirrors")

    # Step 5
    step5_cmd = [py, "scripts/05_review.py"]
    if args.auto_confirm:
        step5_cmd.append("--auto-confirm")
    run_step(step5_cmd, "Step 5: Review Candidates")

    # Step 6
    run_step([py, "scripts/06_build_map.py"], "Step 6: Build Map & Gallery")

    # Step 7
    run_step([py, "scripts/07_generate_report.py"], "Step 7: Generate Report")

    console.print(Panel(
        "[bold green]All pipeline steps completed successfully![/]\n\n"
        f"Interactive Map: {cfg.results_dir / 'ganga_dham_convex_mirror_map.html'}\n"
        f"Image Gallery:   {cfg.results_dir / 'mirror_gallery.html'}\n"
        f"Presentation:    {cfg.results_dir / 'presentation.html'}\n"
        f"Summary Report:  {cfg.results_dir / 'summary.json'}",
        title="Atlas Ready",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
