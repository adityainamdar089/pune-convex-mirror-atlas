"""
presentation.py
===============
Birthday gift presentation layer.

Title: THE CONVEX MIRRORS OF GANGA DHAM
Subtitle: "A little map of the mirrors you somehow love."

Design: personal, playful, minimalist, warm, handmade.
NOT a corporate GIS dashboard.

Output: data/results/presentation.html
"""

from __future__ import annotations

from pathlib import Path

from src.review.cli_review import MirrorRecord
from src.logging_config import get_logger

log = get_logger(__name__)

_PLAYFUL_LABELS = [
    "suspiciously good one",
    "found guarding a parking entrance",
    "quietly watching the crossroads",
    "on duty since before anyone noticed",
    "the shy one, tucked by the wall",
    "very professional, excellent curve",
    "reflects the whole world, beautifully",
    "the tallest one on the block",
    "small but determined",
    "the one nearest the banyan tree",
]


def build_presentation(
    mirrors: list[MirrorRecord],
    output_path: Path,
    map_path: Path | None = None,
) -> Path:
    """
    Generate the gift presentation HTML page.
    """
    confirmed = [m for m in mirrors if m.status == "confirmed"]
    confirmed.sort(key=lambda m: m.sequence_number or 999)

    mirror_cards = "\n".join(
        _make_mirror_card(m, idx)
        for idx, m in enumerate(confirmed)
    )

    map_section = ""
    if map_path and map_path.exists():
        map_section = f"""
        <section class="section">
          <h2 class="section-title">The Map</h2>
          <p class="section-sub">Every pin is a mirror that passed the test.</p>
          <div class="map-embed">
            <iframe src="{map_path.name}" width="100%" height="500"
                    style="border:0; border-radius:12px; opacity:0.95;"
                    loading="lazy"></iframe>
          </div>
        </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Convex Mirrors of Ganga Dham</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Inter:wght@300;400;500&display=swap');

    :root {{
      --cream: #fdf6e3;
      --warm-brown: #7c5c3a;
      --soft-gold: #c9a84c;
      --light-olive: #8a9a5b;
      --mirror-grey: #9ca3af;
      --dark-text: #2d2d2d;
      --card-bg: #fffbf2;
      --card-border: #e8dcc8;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter', sans-serif;
      background: var(--cream);
      color: var(--dark-text);
      min-height: 100vh;
    }}

    .hero {{
      text-align: center;
      padding: 5rem 2rem 3rem;
      background: linear-gradient(180deg, #fff8ee 0%, var(--cream) 100%);
      border-bottom: 1px solid var(--card-border);
    }}

    .hero-eyebrow {{
      font-family: 'Inter', sans-serif;
      font-size: 0.75rem;
      font-weight: 500;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--soft-gold);
      margin-bottom: 1rem;
    }}

    .hero h1 {{
      font-family: 'Crimson Pro', serif;
      font-size: clamp(2.5rem, 6vw, 4.5rem);
      font-weight: 600;
      color: var(--warm-brown);
      line-height: 1.1;
      letter-spacing: -0.01em;
      margin-bottom: 1rem;
    }}

    .hero-subtitle {{
      font-family: 'Crimson Pro', serif;
      font-size: 1.4rem;
      font-style: italic;
      color: #8a7355;
      max-width: 500px;
      margin: 0 auto 2rem;
      line-height: 1.5;
    }}

    .mirror-count {{
      display: inline-block;
      background: var(--warm-brown);
      color: var(--cream);
      font-family: 'Crimson Pro', serif;
      font-size: 1.1rem;
      padding: 0.5rem 1.5rem;
      border-radius: 9999px;
      margin-top: 0.5rem;
    }}

    .section {{
      max-width: 900px;
      margin: 4rem auto;
      padding: 0 2rem;
    }}

    .section-title {{
      font-family: 'Crimson Pro', serif;
      font-size: 2rem;
      font-weight: 600;
      color: var(--warm-brown);
      margin-bottom: 0.25rem;
    }}

    .section-sub {{
      font-size: 0.9rem;
      color: #9ca3af;
      margin-bottom: 2rem;
      font-style: italic;
    }}

    .mirror-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 1.5rem;
    }}

    .mirror-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.5rem;
      position: relative;
      transition: box-shadow 0.2s ease;
    }}

    .mirror-card:hover {{
      box-shadow: 0 8px 30px rgba(124, 92, 58, 0.1);
    }}

    .mirror-card-number {{
      font-family: 'Crimson Pro', serif;
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--warm-brown);
      margin-bottom: 0.25rem;
    }}

    .mirror-card-label {{
      font-size: 0.8rem;
      color: var(--soft-gold);
      font-style: italic;
      margin-bottom: 1rem;
    }}

    .mirror-card-coords {{
      font-size: 0.75rem;
      color: #9ca3af;
      font-family: monospace;
      margin-bottom: 0.75rem;
    }}

    .mirror-card-desc {{
      font-family: 'Crimson Pro', serif;
      font-size: 0.95rem;
      color: #5a4a35;
      font-style: italic;
      line-height: 1.5;
      margin-bottom: 0.75rem;
    }}

    .mirror-card-rating {{
      font-size: 1.1rem;
      color: var(--soft-gold);
      font-weight: 500;
    }}

    .mirror-card-notes {{
      font-size: 0.8rem;
      color: #9ca3af;
      margin-top: 0.5rem;
      border-top: 1px dashed var(--card-border);
      padding-top: 0.5rem;
    }}

    .map-embed {{
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }}

    .footer {{
      text-align: center;
      padding: 3rem 2rem;
      color: #c9a88a;
      font-family: 'Crimson Pro', serif;
      font-size: 1rem;
      font-style: italic;
      border-top: 1px solid var(--card-border);
      margin-top: 4rem;
    }}

    .footer strong {{
      display: block;
      font-size: 1.3rem;
      color: var(--warm-brown);
      margin-bottom: 0.5rem;
    }}

    .no-mirrors {{
      text-align: center;
      color: #9ca3af;
      font-style: italic;
      padding: 3rem;
    }}
  </style>
</head>
<body>
  <div class="hero">
    <div class="hero-eyebrow">A personal project · Ganga Dham, Pune</div>
    <h1>The Convex Mirrors<br>of Ganga Dham</h1>
    <p class="hero-subtitle">"A little map of the mirrors you somehow love."</p>
    <div class="mirror-count">🪞 {len(confirmed)} confirmed mirror{"s" if len(confirmed) != 1 else ""} found</div>
  </div>

  {map_section}

  <section class="section">
    <h2 class="section-title">The Mirrors</h2>
    <p class="section-sub">Each one found, photographed, and confirmed by hand.</p>
    <div class="mirror-grid">
      {"".join([mirror_cards]) if confirmed else '<div class="no-mirrors">No confirmed mirrors yet. Run the pipeline and review candidates first.</div>'}
    </div>
  </section>

  <footer class="footer">
    <strong>Made with care.</strong>
    For the person who notices the mirrors on every corner.<br>
    <small style="font-size:0.75rem; color:#c9a88a; font-style:normal; margin-top:0.5rem; display:block;">
      Imagery © Google. All detections manually verified.
    </small>
  </footer>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    log.info("Presentation saved to %s", output_path)
    return output_path


def _make_mirror_card(mirror: MirrorRecord, index: int) -> str:
    label = _PLAYFUL_LABELS[index % len(_PLAYFUL_LABELS)]
    rating_str = f"⭐ {mirror.rating}/10" if mirror.rating else ""
    desc = mirror.description or "—"
    notes_html = f'<div class="mirror-card-notes">📝 {mirror.notes}</div>' if mirror.notes else ""

    return f"""
    <div class="mirror-card">
      <div class="mirror-card-number">Mirror #{mirror.sequence_number:03d}</div>
      <div class="mirror-card-label">— {label}</div>
      <div class="mirror-card-coords">{mirror.latitude:.5f}, {mirror.longitude:.5f}</div>
      <div class="mirror-card-desc">"{desc}"</div>
      <div class="mirror-card-rating">{rating_str}</div>
      {notes_html}
    </div>"""
