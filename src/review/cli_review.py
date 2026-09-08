"""
cli_review.py
=============
Terminal-based human verification interface.

For each candidate mirror, displays:
- Mirror ID and sequence number
- Image path and bounding box
- Coordinates, heading, panorama ID
- Confidence score
- Capture date

Reviewer choices:
    [C] CONFIRMED   — This is a convex mirror.
    [R] REJECTED    — This is not a convex mirror.
    [U] UNCERTAIN   — Cannot determine from this image.
    [S] SKIP        — Skip for now (remains candidate).
    [Q] QUIT        — Save progress and exit.

Results saved to: data/results/mirrors.csv

Usage
-----
    from src.review.cli_review import run_review_session
    from src.detection.deduplication import DeduplicatedMirror
    run_review_session(candidates, output_path)
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from src.detection.deduplication import DeduplicatedMirror
from src.logging_config import get_logger

log = get_logger(__name__)
console = Console()

# ── Mirror record (final output schema) ───────────────────────────────────────

@dataclass
class MirrorRecord:
    """
    A verified (or reviewed) mirror record.
    This is the final output written to mirrors.csv.
    """
    mirror_id: str
    latitude: float
    longitude: float
    area: str
    status: str                # confirmed | rejected | uncertain | candidate
    confidence: float
    image_reference: str       # path to best image
    panorama_id: str
    heading: int
    capture_date: str
    notes: str = ""
    description: str = ""
    rating: Optional[float] = None
    reviewed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sequence_number: int = 0   # Mirror #001, #002, etc.

    def as_dict(self) -> dict:
        return asdict(self)


_MIRROR_CSV_FIELDS = [
    "mirror_id", "latitude", "longitude", "area", "status",
    "confidence", "image_reference", "panorama_id", "heading",
    "capture_date", "notes", "description", "rating",
    "reviewed_at", "sequence_number",
]


# ── Review session ────────────────────────────────────────────────────────────

def run_review_session(
    candidates: list[DeduplicatedMirror],
    output_path: Path,
    area_name: str = "Ganga Dham",
    resume: bool = True,
) -> list[MirrorRecord]:
    """
    Run an interactive terminal review session.

    Parameters
    ----------
    candidates:   List of deduplicated candidates to review.
    output_path:  Path to write mirrors.csv.
    area_name:    Area name for the record.
    resume:       If True and output_path exists, load existing reviews
                  and skip already-reviewed candidates.

    Returns
    -------
    List of all MirrorRecord objects (including pre-existing if resumed).
    """
    existing = _load_existing(output_path) if resume else {}
    results: dict[str, MirrorRecord] = dict(existing)

    pending = [c for c in candidates if c.mirror_id not in results]

    console.print(Panel(
        f"[bold cyan]Pune Convex Mirror Atlas — Human Review[/]\n\n"
        f"Total candidates: [yellow]{len(candidates)}[/]\n"
        f"Already reviewed: [green]{len(existing)}[/]\n"
        f"Pending review:   [yellow]{len(pending)}[/]\n\n"
        f"[dim]Commands: C=Confirmed, R=Rejected, U=Uncertain, S=Skip, Q=Quit[/]",
        title="Review Session",
        border_style="cyan",
    ))

    confirmed_count = sum(1 for r in results.values() if r.status == "confirmed")

    for idx, candidate in enumerate(pending, start=len(existing) + 1):
        console.print()

        det = candidate.best_detection
        if det is None:
            log.warning("Candidate %s has no best_detection — skipping.", candidate.mirror_id)
            continue

        # Display candidate info
        _display_candidate(candidate, idx, len(candidates))

        # Prompt for decision
        choice = _prompt_decision()

        if choice == "q":
            console.print("[yellow]Saving progress and exiting review...[/]")
            break

        if choice == "s":
            console.print("[dim]Skipped.[/]")
            continue

        status_map = {"c": "confirmed", "r": "rejected", "u": "uncertain"}
        status = status_map.get(choice, "candidate")

        # Optional notes and description
        notes = ""
        description = ""
        rating = None

        if status == "confirmed":
            confirmed_count += 1
            console.print(f"[green]✓ Confirmed as Mirror #{confirmed_count:03d}[/]")
            description = Prompt.ask(
                "  Brief description (e.g. 'near parking entrance')",
                default="",
            )
            rating_str = Prompt.ask(
                "  Rating out of 10 (or press Enter to skip)",
                default="",
            )
            if rating_str:
                try:
                    rating = float(rating_str)
                except ValueError:
                    pass

        notes = Prompt.ask("  Notes (press Enter to skip)", default="")

        image_ref = det.image_id if det else ""
        rec = MirrorRecord(
            mirror_id=candidate.mirror_id,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            area=area_name,
            status=status,
            confidence=candidate.best_confidence,
            image_reference=image_ref,
            panorama_id=det.panorama_id if det else "",
            heading=det.heading if det else 0,
            capture_date="",
            notes=notes,
            description=description,
            rating=rating,
            sequence_number=confirmed_count if status == "confirmed" else 0,
        )
        results[candidate.mirror_id] = rec
        _save_results(list(results.values()), output_path)

    # Summary
    total = len(results)
    confirmed = sum(1 for r in results.values() if r.status == "confirmed")
    rejected = sum(1 for r in results.values() if r.status == "rejected")
    uncertain = sum(1 for r in results.values() if r.status == "uncertain")

    console.print()
    console.print(Panel(
        f"[bold]Review Complete[/]\n\n"
        f"Confirmed:  [green]{confirmed}[/]\n"
        f"Rejected:   [red]{rejected}[/]\n"
        f"Uncertain:  [yellow]{uncertain}[/]\n"
        f"Total reviewed: {total}\n\n"
        f"Results saved to: [cyan]{output_path}[/]",
        border_style="green",
    ))

    return list(results.values())


def _display_candidate(
    candidate: DeduplicatedMirror,
    index: int,
    total: int,
) -> None:
    det = candidate.best_detection

    table = Table(box=box.ROUNDED, show_header=False, border_style="blue")
    table.add_column("Field", style="bold cyan", width=20)
    table.add_column("Value")

    table.add_row("Candidate", f"{index}/{total}")
    table.add_row("Mirror ID", candidate.mirror_id)
    table.add_row("Latitude", f"{candidate.latitude:.6f}")
    table.add_row("Longitude", f"{candidate.longitude:.6f}")
    table.add_row("Confidence", f"{candidate.best_confidence:.2f}")
    table.add_row("Detection count", str(candidate.detection_count))

    if det:
        table.add_row("Heading", f"{det.heading}°")
        table.add_row("Panorama ID", det.panorama_id or "[dim]N/A[/]")
        table.add_row("Image ID", det.image_id or "[dim]N/A[/]")
        table.add_row(
            "Bounding box",
            f"x={det.bbox_x}, y={det.bbox_y}, w={det.bbox_w}, h={det.bbox_h}",
        )
        table.add_row("Detector", det.detector_type)

    console.print(table)


def _prompt_decision() -> str:
    """Prompt for reviewer decision, return lowercase single character."""
    while True:
        choice = Prompt.ask(
            "[bold]Decision[/] [[green]C[/]onfirmed / [red]R[/]ejected / "
            "[yellow]U[/]ncertain / [dim]S[/]kip / [dim]Q[/]uit]",
            default="S",
        ).strip().lower()
        if choice in ("c", "r", "u", "s", "q"):
            return choice
        console.print("[red]Invalid choice. Enter C, R, U, S, or Q.[/]")


def _load_existing(path: Path) -> dict[str, MirrorRecord]:
    if not path.exists():
        return {}
    records = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                r = MirrorRecord(
                    mirror_id=row["mirror_id"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    area=row["area"],
                    status=row["status"],
                    confidence=float(row["confidence"]),
                    image_reference=row["image_reference"],
                    panorama_id=row["panorama_id"],
                    heading=int(row["heading"]),
                    capture_date=row["capture_date"],
                    notes=row.get("notes", ""),
                    description=row.get("description", ""),
                    rating=float(row["rating"]) if row.get("rating") else None,
                    reviewed_at=row.get("reviewed_at", ""),
                    sequence_number=int(row.get("sequence_number", 0)),
                )
                records[r.mirror_id] = r
    except Exception as e:
        log.warning("Could not load existing reviews from %s: %s", path, e)
    return records


def _save_results(records: list[MirrorRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_MIRROR_CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.as_dict())
    log.debug("Saved %d mirror records to %s", len(records), path)


def load_mirrors(path: Path) -> list[MirrorRecord]:
    """Load mirror records from CSV."""
    return list(_load_existing(path).values())
