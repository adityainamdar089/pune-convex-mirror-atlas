"""
map_builder.py
==============
Builds an interactive Leaflet.js map using Folium.

Output: data/results/ganga_dham_convex_mirror_map.html

Map features
------------
- Confirmed mirrors: green pins (main layer)
- Uncertain candidates: orange pins (optional toggle)
- Rejected candidates: grey pins (optional toggle)
- Clicking a marker opens a popup with mirror details
- Map centred on Ganga Dham
- Google attribution displayed

Usage
-----
    from src.mapping.map_builder import build_map
    build_map(mirrors, output_path, boundary)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import folium
from folium.plugins import MarkerCluster

from src.review.cli_review import MirrorRecord
from src.geo.boundary import AreaBoundary
from src.logging_config import get_logger

log = get_logger(__name__)

# Marker colours by status
_COLOUR_MAP = {
    "confirmed": "green",
    "uncertain": "orange",
    "rejected": "gray",
    "candidate": "blue",
}


def build_map(
    mirrors: list[MirrorRecord],
    output_path: Path,
    boundary: Optional[AreaBoundary] = None,
    show_uncertain: bool = True,
    show_rejected: bool = False,
    zoom_start: int = 17,
) -> Path:
    """
    Build and save the interactive Folium map.

    Parameters
    ----------
    mirrors:        List of MirrorRecord objects.
    output_path:    Where to save the HTML file.
    boundary:       If provided, draws the scan boundary polygon.
    show_uncertain: Include uncertain candidates on the map.
    show_rejected:  Include rejected candidates on the map.
    zoom_start:     Initial zoom level.

    Returns
    -------
    Path to the generated HTML file.
    """
    # Determine centre
    if boundary:
        center_lat, center_lon = boundary.center
    else:
        center_lat, center_lon = 18.4739, 73.8601

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
    )

    # Draw boundary polygon if available
    if boundary:
        coords = [(lat, lon) for lat, lon in
                  boundary.polygon.exterior.coords]
        folium.Polygon(
            locations=coords,
            color="blue",
            fill=True,
            fill_opacity=0.05,
            weight=2,
            tooltip="Ganga Dham scan boundary",
        ).add_to(m)

    # Separate layers
    confirmed_layer = folium.FeatureGroup(name="✅ Confirmed Mirrors", show=True)
    uncertain_layer = folium.FeatureGroup(name="🟡 Uncertain Candidates", show=show_uncertain)
    rejected_layer = folium.FeatureGroup(name="❌ Rejected Candidates", show=show_rejected)

    confirmed_count = 0

    for mirror in mirrors:
        if mirror.status == "rejected" and not show_rejected:
            continue
        if mirror.status == "uncertain" and not show_uncertain:
            continue

        colour = _COLOUR_MAP.get(mirror.status, "blue")
        seq = f"#{mirror.sequence_number:03d}" if mirror.sequence_number else ""

        popup_html = _make_popup(mirror, seq)

        marker = folium.Marker(
            location=[mirror.latitude, mirror.longitude],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"Mirror {seq or mirror.mirror_id[:8]} ({mirror.status})",
            icon=folium.Icon(color=colour, icon="eye", prefix="fa"),
        )

        if mirror.status == "confirmed":
            marker.add_to(confirmed_layer)
            confirmed_count += 1
        elif mirror.status == "uncertain":
            marker.add_to(uncertain_layer)
        else:
            marker.add_to(rejected_layer)

    confirmed_layer.add_to(m)
    uncertain_layer.add_to(m)
    rejected_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Attribution
    folium.map.Marker(
        [center_lat, center_lon],
        icon=folium.DivIcon(
            html="""<div style="font-size:10px; color:grey;">
                    Imagery © Google. Project: Pune Convex Mirror Atlas.
                    </div>""",
            icon_size=(300, 20),
        )
    ).add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))

    log.info(
        "Map saved to %s — %d confirmed mirrors, %d total records.",
        output_path, confirmed_count, len(mirrors),
    )
    return output_path


def _make_popup(mirror: MirrorRecord, seq: str) -> str:
    """Generate HTML for a marker popup."""
    status_emoji = {
        "confirmed": "✅",
        "uncertain": "🟡",
        "rejected": "❌",
        "candidate": "🔵",
    }.get(mirror.status, "❔")

    rating_str = f"{mirror.rating}/10" if mirror.rating else "—"
    desc = mirror.description or "—"
    notes = mirror.notes or "—"

    return f"""
    <div style="font-family: sans-serif; font-size: 13px;">
        <b>Mirror {seq or mirror.mirror_id[:8]}</b><br>
        <span>{status_emoji} {mirror.status.title()}</span><br>
        <hr style="margin:4px 0">
        <b>Lat:</b> {mirror.latitude:.6f}<br>
        <b>Lon:</b> {mirror.longitude:.6f}<br>
        <b>Heading:</b> {mirror.heading}°<br>
        <b>Confidence:</b> {mirror.confidence:.2f}<br>
        <b>Rating:</b> {rating_str}<br>
        <b>Description:</b> {desc}<br>
        <b>Notes:</b> {notes}<br>
        <hr style="margin:4px 0">
        <small style="color:grey;">
            Pano: {mirror.panorama_id or 'N/A'}<br>
            Captured: {mirror.capture_date or 'N/A'}
        </small>
    </div>
    """
