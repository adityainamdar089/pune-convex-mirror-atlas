"""
build_site.py
=============
Build the interactive map and copy outputs to docs/ for GitHub Pages hosting.

Usage:
    python scripts/build_site.py

Output:
    docs/index.html          — mobile-friendly map with nearest-mirror lookup
    docs/gallery.html        — mirror gallery
    docs/mirrors.json        — mirror coordinates (for external apps)
    data/results/            — same files kept locally
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from src.config import get_config
from src.geo.boundary import get_ganga_dham_boundary
from src.logging_config import setup_logging
from src.mapping.gallery import build_gallery
from src.mapping.map_builder import build_map
from src.mapping.mobile_features import export_mirrors_json
from src.review.cli_review import load_mirrors

console = Console()
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = get_config()
    setup_logging(cfg.log_level)

    mirrors_path = cfg.results_dir / "mirrors.csv"
    if not mirrors_path.exists():
        console.print(
            f"[red]mirrors.csv not found at {mirrors_path}.[/]\n"
            f"Run [cyan]python scripts/run_demo.py[/] or the full pipeline first."
        )
        sys.exit(1)

    mirrors = load_mirrors(mirrors_path)
    boundary = get_ganga_dham_boundary()

    # Build locally
    map_path = cfg.results_dir / "ganga_dham_convex_mirror_map.html"
    build_map(mirrors, map_path, boundary=boundary)

    gallery_path = cfg.results_dir / "mirror_gallery.html"
    build_gallery(mirrors, gallery_path, processed_dir=cfg.processed_dir)

    json_path = cfg.results_dir / "mirrors.json"
    export_mirrors_json(mirrors, json_path)

    # Copy to docs/ for GitHub Pages
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(map_path, DOCS_DIR / "index.html")
    shutil.copy2(gallery_path, DOCS_DIR / "gallery.html")
    shutil.copy2(json_path, DOCS_DIR / "mirrors.json")
    (DOCS_DIR / ".nojekyll").touch()

    console.print(f"\n[bold green]Site built successfully![/]")
    console.print(f"  Local map:  {map_path}")
    console.print(f"  GitHub Pages: docs/index.html")
    console.print(f"  Mirrors:  {len(mirrors)} ({sum(1 for m in mirrors if m.status == 'confirmed')} confirmed)")
    console.print(
        f"\n[bold]To host free on GitHub Pages:[/]\n"
        f"  1. Push this repo to GitHub\n"
        f"  2. Settings → Pages → Source: [cyan]Deploy from branch[/]\n"
        f"  3. Branch: [cyan]main[/], folder: [cyan]/docs[/]\n"
        f"  4. Your map will be at: [cyan]https://YOUR_USERNAME.github.io/REPO_NAME/[/]"
    )


if __name__ == "__main__":
    main()
