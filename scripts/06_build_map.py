"""
06_build_map.py
===============
Step 6: Generate the interactive HTML map and gallery.

Usage
-----
    python scripts/06_build_map.py

Output
------
    data/results/ganga_dham_convex_mirror_map.html
    data/results/mirror_gallery.html
    data/results/presentation.html
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from src.config import get_config
from src.logging_config import setup_logging
from src.geo.boundary import get_ganga_dham_boundary
from src.review.cli_review import load_mirrors
from src.mapping.map_builder import build_map
from src.mapping.gallery import build_gallery
from src.mapping.presentation import build_presentation

console = Console()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    cfg = get_config()
    setup_logging(cfg.log_level)

    mirrors_path = cfg.results_dir / "mirrors.csv"
    if not mirrors_path.exists():
        console.print(
            f"[red]mirrors.csv not found at {mirrors_path}.[/]\n"
            f"Run [cyan]python scripts/05_review.py[/] first."
        )
        sys.exit(1)

    mirrors = load_mirrors(mirrors_path)
    boundary = get_ganga_dham_boundary()

    console.print(
        f"\n[bold cyan]Pune Convex Mirror Atlas — Step 6: Build Map & Gallery[/]\n"
        f"Total mirrors: [yellow]{len(mirrors)}[/]\n"
        f"Confirmed: [green]{sum(1 for m in mirrors if m.status == 'confirmed')}[/]\n"
    )

    # Interactive map
    map_path = cfg.results_dir / "ganga_dham_convex_mirror_map.html"
    build_map(mirrors, map_path, boundary=boundary, show_uncertain=True, show_rejected=False)
    console.print(f"[green][OK] Map:[/] {map_path}")

    # Gallery
    gallery_path = cfg.results_dir / "mirror_gallery.html"
    build_gallery(mirrors, gallery_path, processed_dir=cfg.processed_dir)
    console.print(f"[green][OK] Gallery:[/] {gallery_path}")

    # Presentation
    pres_path = cfg.results_dir / "presentation.html"
    build_presentation(mirrors, pres_path, map_path=map_path)
    console.print(f"[green][OK] Presentation:[/] {pres_path}")

    console.print(
        f"\n[bold]Next step:[/] Run [cyan]python scripts/07_generate_report.py[/] "
        f"for full statistics."
    )


if __name__ == "__main__":
    main()
