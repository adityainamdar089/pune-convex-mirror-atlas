"""
gallery.py
==========
Generates a beautiful HTML mirror gallery.

Each mirror card shows:
- Mirror number (#001, #002, ...)
- Location
- Status badge
- Rating
- Image thumbnail (if available)
- Notes and description

Output: data/results/mirror_gallery.html
"""

from __future__ import annotations

from pathlib import Path

from src.review.cli_review import MirrorRecord
from src.logging_config import get_logger

log = get_logger(__name__)

_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', sans-serif;
    background: #0f1117;
    color: #e8eaf0;
    min-height: 100vh;
    padding: 2rem;
  }

  header {
    text-align: center;
    margin-bottom: 3rem;
  }

  header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.03em;
  }

  header p {
    color: #6b7280;
    margin-top: 0.5rem;
    font-size: 1rem;
  }

  .stats-bar {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
  }

  .stat {
    text-align: center;
    background: #1e2130;
    border: 1px solid #2a2f45;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    min-width: 100px;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #60a5fa;
  }

  .stat-label {
    font-size: 0.75rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
  }

  .gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .card {
    background: #1e2130;
    border: 1px solid #2a2f45;
    border-radius: 16px;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(96, 165, 250, 0.15);
  }

  .card-image {
    width: 100%;
    height: 200px;
    object-fit: cover;
    background: #111827;
    display: block;
  }

  .card-image-placeholder {
    width: 100%;
    height: 200px;
    background: linear-gradient(135deg, #1a1f2e, #252b3d);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3rem;
    color: #374151;
  }

  .card-body {
    padding: 1.25rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
  }

  .card-number {
    font-size: 1.25rem;
    font-weight: 700;
    color: #e8eaf0;
  }

  .badge {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.25rem 0.6rem;
    border-radius: 9999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badge-confirmed { background: #064e3b; color: #34d399; }
  .badge-uncertain { background: #451a03; color: #fb923c; }
  .badge-rejected  { background: #1f1f1f; color: #6b7280; }
  .badge-candidate { background: #1e3a5f; color: #60a5fa; }

  .card-location {
    font-size: 0.85rem;
    color: #9ca3af;
    margin-bottom: 0.5rem;
  }

  .card-rating {
    font-size: 1.5rem;
    font-weight: 700;
    color: #fbbf24;
    margin-bottom: 0.5rem;
  }

  .card-description {
    font-size: 0.875rem;
    color: #d1d5db;
    font-style: italic;
    margin-bottom: 0.5rem;
    line-height: 1.5;
  }

  .card-notes {
    font-size: 0.8rem;
    color: #6b7280;
    border-top: 1px solid #2a2f45;
    padding-top: 0.5rem;
    margin-top: 0.5rem;
  }

  .card-meta {
    font-size: 0.75rem;
    color: #4b5563;
    margin-top: 0.5rem;
  }

  footer {
    text-align: center;
    color: #374151;
    font-size: 0.8rem;
    margin-top: 4rem;
    padding-top: 2rem;
    border-top: 1px solid #1e2130;
  }
</style>
"""


def build_gallery(
    mirrors: list[MirrorRecord],
    output_path: Path,
    title: str = "Convex Mirror Gallery — Ganga Dham, Pune",
    show_only_confirmed: bool = False,
    processed_dir: Path | None = None,
) -> Path:
    """
    Generate the HTML gallery.

    Parameters
    ----------
    mirrors:             All mirror records (or filtered list).
    output_path:         Output HTML path.
    title:               Page title.
    show_only_confirmed: If True, only show confirmed mirrors.
    processed_dir:       Directory containing thumbnails.
    """
    if show_only_confirmed:
        display = [m for m in mirrors if m.status == "confirmed"]
    else:
        display = mirrors

    display.sort(key=lambda m: (m.status != "confirmed", m.sequence_number or 999))

    confirmed = sum(1 for m in mirrors if m.status == "confirmed")
    uncertain = sum(1 for m in mirrors if m.status == "uncertain")
    rejected = sum(1 for m in mirrors if m.status == "rejected")

    cards_html = "\n".join(_make_card(m, processed_dir) for m in display)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  {_CSS}
</head>
<body>
  <header>
    <h1>🪞 {title}</h1>
    <p>A collection of convex mirrors discovered in Ganga Dham, Bibwewadi, Pune.</p>
  </header>

  <div class="stats-bar">
    <div class="stat">
      <div class="stat-value">{confirmed}</div>
      <div class="stat-label">Confirmed</div>
    </div>
    <div class="stat">
      <div class="stat-value">{uncertain}</div>
      <div class="stat-label">Uncertain</div>
    </div>
    <div class="stat">
      <div class="stat-value">{rejected}</div>
      <div class="stat-label">Rejected</div>
    </div>
    <div class="stat">
      <div class="stat-value">{len(mirrors)}</div>
      <div class="stat-label">Total</div>
    </div>
  </div>

  <div class="gallery">
    {cards_html}
  </div>

  <footer>
    <p>Imagery © Google. Pune Convex Mirror Atlas — personal project.</p>
    <p>All detections are candidates until manually verified.</p>
  </footer>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    log.info("Gallery saved to %s (%d mirrors displayed)", output_path, len(display))
    return output_path


import base64

def _find_image_file(image_ref: str, processed_dir: Path | None) -> Path | None:
    if not image_ref:
        return None
    candidates = []
    if processed_dir:
        candidates.append(processed_dir / "thumbnails" / f"{image_ref}_thumb.jpg")
        raw_dir = processed_dir.parent / "raw"
        candidates.append(raw_dir / "mapillary" / f"{image_ref}.jpg")
        candidates.append(raw_dir / f"{image_ref}.jpg")
        # Search all subdirs of raw
        if raw_dir.exists():
            candidates.extend(list(raw_dir.glob(f"**/{image_ref}.jpg")))
            candidates.extend(list(raw_dir.glob(f"**/{image_ref}*.jpg")))

    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _make_card(mirror: MirrorRecord, processed_dir: Path | None) -> str:
    # Image resolution
    img_file = _find_image_file(mirror.image_reference, processed_dir)
    if img_file:
        try:
            with open(img_file, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            img_html = f'<img class="card-image" src="data:image/jpeg;base64,{b64}" alt="Mirror {mirror.mirror_id}">'
        except Exception:
            img_html = '<div class="card-image-placeholder">🪞</div>'
    else:
        img_html = '<div class="card-image-placeholder">🪞</div>'

    # Badge
    badge_class = f"badge-{mirror.status}"
    badge = f'<span class="badge {badge_class}">{mirror.status}</span>'

    # Number
    num = f"Mirror #{mirror.sequence_number:03d}" if mirror.sequence_number else f"Candidate {mirror.mirror_id[:8]}"

    # Rating
    rating_html = ""
    if mirror.rating:
        stars = "★" * int(round(mirror.rating / 2))
        rating_html = f'<div class="card-rating">{mirror.rating}/10 {stars}</div>'

    # Description / notes
    desc_html = f'<div class="card-description">"{mirror.description}"</div>' if mirror.description else ""
    notes_html = f'<div class="card-notes">📝 {mirror.notes}</div>' if mirror.notes else ""
    photo_html = ""
    if mirror.panorama_id:
        photo_url = f"https://www.mapillary.com/app/?pKey={mirror.panorama_id}"
        photo_html = (
            f'<a href="{photo_url}" target="_blank" rel="noopener" '
            'class="card-photo-link">View source photo on Mapillary</a>'
        )

    return f"""
    <div class="card">
      {img_html}
      <div class="card-body">
        <div class="card-header">
          <div class="card-number">{num}</div>
          {badge}
        </div>
        <div class="card-location">📍 Ganga Dham, Pune · {mirror.latitude:.5f}, {mirror.longitude:.5f}</div>
        {rating_html}
        {desc_html}
        {notes_html}
        {photo_html}
        <div class="card-meta">Heading: {mirror.heading}° · Confidence: {mirror.confidence:.2f}</div>
      </div>
    </div>"""
