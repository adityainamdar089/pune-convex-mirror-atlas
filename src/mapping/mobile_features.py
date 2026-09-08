"""
mobile_features.py
==================
Injects mobile-friendly UI and geolocation-based nearest-mirror lookup
into a Folium-generated HTML map.

Requires HTTPS (GitHub Pages, Netlify, etc.) for browser geolocation on mobile.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.review.cli_review import MirrorRecord


def _mirror_payload(mirrors: list[MirrorRecord]) -> list[dict]:
    """Serialize confirmed/uncertain mirrors for client-side distance search."""
    payload = []
    for m in mirrors:
        if m.status == "rejected":
            continue
        seq = f"#{m.sequence_number:03d}" if m.sequence_number else m.mirror_id[:8]
        payload.append({
            "id": m.mirror_id,
            "seq": seq,
            "lat": m.latitude,
            "lon": m.longitude,
            "status": m.status,
            "confidence": round(m.confidence, 3),
            "heading": m.heading,
        })
    return payload


_MOBILE_CSS = """
<style id="pune-mirror-mobile-css">
  html, body { height: 100%; margin: 0; }
  .folium-map { width: 100% !important; height: 100vh !important; }

  #pm-nearest-btn {
    position: fixed;
    bottom: max(20px, env(safe-area-inset-bottom));
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    background: #2563eb;
    color: #fff;
    border: none;
    border-radius: 999px;
    padding: 14px 22px;
    font: 600 15px/1.2 system-ui, -apple-system, sans-serif;
    box-shadow: 0 4px 20px rgba(37,99,235,.45);
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
  #pm-nearest-btn:active { transform: translateX(-50%) scale(.97); }
  #pm-nearest-btn:disabled { opacity: .6; cursor: wait; }

  #pm-panel {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    z-index: 10000;
    background: #fff;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -4px 24px rgba(0,0,0,.15);
    padding: 16px 16px max(16px, env(safe-area-inset-bottom));
    transform: translateY(110%);
    transition: transform .3s ease;
    font: 14px/1.5 system-ui, -apple-system, sans-serif;
    max-height: 45vh;
    overflow-y: auto;
  }
  #pm-panel.open { transform: translateY(0); }

  #pm-panel h3 { margin: 0 0 8px; font-size: 17px; }
  #pm-panel .pm-dist {
    font-size: 28px; font-weight: 700; color: #2563eb; margin: 4px 0 10px;
  }
  #pm-panel .pm-meta { color: #555; font-size: 13px; margin-bottom: 12px; }
  #pm-panel .pm-actions { display: flex; gap: 8px; flex-wrap: wrap; }
  #pm-panel .pm-actions a, #pm-panel .pm-actions button {
    flex: 1; min-width: 120px; text-align: center;
    padding: 10px 14px; border-radius: 10px;
    font: 600 13px system-ui, sans-serif;
    text-decoration: none; border: none; cursor: pointer;
  }
  .pm-nav { background: #2563eb; color: #fff; }
  .pm-close { background: #f1f5f9; color: #334155; }

  #pm-toast {
    position: fixed; top: 12px; left: 12px; right: 12px;
    z-index: 10001; background: #fef2f2; color: #991b1b;
    padding: 12px 16px; border-radius: 10px;
    font: 14px system-ui, sans-serif;
    box-shadow: 0 2px 12px rgba(0,0,0,.12);
    display: none;
  }
</style>
"""

_MOBILE_JS_TEMPLATE = """
<script id="pune-mirror-mobile-js">
(function() {
  const MIRRORS = __MIRRORS_JSON__;

  function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const toRad = d => d * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat/2)**2 +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function formatDist(m) {
    if (m < 1000) return Math.round(m) + ' m';
    return (m / 1000).toFixed(2) + ' km';
  }

  function findNearest(lat, lon) {
    let best = null, bestD = Infinity;
    for (const m of MIRRORS) {
      const d = haversine(lat, lon, m.lat, m.lon);
      if (d < bestD) { bestD = d; best = m; }
    }
    return best ? { mirror: best, distance: bestD } : null;
  }

  function getMap() {
    for (const k of Object.keys(window)) {
      if (k.startsWith('map_') && window[k] && window[k].setView) return window[k];
    }
    return null;
  }

  let userMarker = null, routeLine = null, nearestMarker = null;

  function showToast(msg) {
    const t = document.getElementById('pm-toast');
    t.textContent = msg;
    t.style.display = 'block';
    setTimeout(() => { t.style.display = 'none'; }, 5000);
  }

  function clearOverlays(map) {
    if (userMarker) { map.removeLayer(userMarker); userMarker = null; }
    if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
    if (nearestMarker) { nearestMarker = null; }
  }

  function onNearestFound(map, lat, lon, result) {
    const { mirror, distance } = result;
    clearOverlays(map);

    userMarker = L.circleMarker([lat, lon], {
      radius: 10, color: '#2563eb', fillColor: '#3b82f6', fillOpacity: 1, weight: 3
    }).addTo(map).bindPopup('<b>You are here</b>');

    routeLine = L.polyline([[lat, lon], [mirror.lat, mirror.lon]], {
      color: '#2563eb', weight: 4, dashArray: '8 8', opacity: .8
    }).addTo(map);

    map.fitBounds(routeLine.getBounds(), { padding: [60, 60], maxZoom: 18 });

    const panel = document.getElementById('pm-panel');
    document.getElementById('pm-title').textContent = 'Nearest Mirror: ' + mirror.seq;
    document.getElementById('pm-dist').textContent = formatDist(distance);
    document.getElementById('pm-meta').innerHTML =
      'Status: <b>' + mirror.status + '</b> &middot; Confidence: ' + mirror.confidence +
      '<br>Heading: ' + mirror.heading + '&deg;';
    const navUrl = 'https://www.google.com/maps/dir/?api=1&origin=' +
      lat + ',' + lon + '&destination=' + mirror.lat + ',' + mirror.lon + '&travelmode=walking';
    document.getElementById('pm-nav').href = navUrl;
    panel.classList.add('open');

    map.eachLayer(function(layer) {
      if (layer instanceof L.Marker && layer.getLatLng) {
        const ll = layer.getLatLng();
        if (Math.abs(ll.lat - mirror.lat) < 1e-6 && Math.abs(ll.lng - mirror.lon) < 1e-6) {
          layer.openPopup();
        }
      }
    });
  }

  function locateNearest() {
    const btn = document.getElementById('pm-nearest-btn');
    const map = getMap();
    if (!map) { showToast('Map not ready. Please refresh.'); return; }
    if (!MIRRORS.length) { showToast('No mirrors on the map yet.'); return; }
    if (!navigator.geolocation) {
      showToast('Geolocation is not supported on this browser.');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Locating…';

    navigator.geolocation.getCurrentPosition(
      function(pos) {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const result = findNearest(lat, lon);
        btn.disabled = false;
        btn.textContent = '📍 Find Nearest Mirror';
        if (!result) { showToast('No mirrors found.'); return; }
        onNearestFound(map, lat, lon, result);
      },
      function(err) {
        btn.disabled = false;
        btn.textContent = '📍 Find Nearest Mirror';
        const msgs = {
          1: 'Location permission denied. Allow location access in your browser settings.',
          2: 'Location unavailable. Try again outdoors with GPS enabled.',
          3: 'Location request timed out. Please try again.'
        };
        showToast(msgs[err.code] || 'Could not get your location.');
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  }

  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.createElement('button');
    btn.id = 'pm-nearest-btn';
    btn.textContent = '📍 Find Nearest Mirror';
    btn.onclick = locateNearest;
    document.body.appendChild(btn);

    const toast = document.createElement('div');
    toast.id = 'pm-toast';
    document.body.appendChild(toast);

    const panel = document.createElement('div');
    panel.id = 'pm-panel';
    panel.innerHTML =
      '<h3 id="pm-title">Nearest Mirror</h3>' +
      '<div class="pm-dist" id="pm-dist">—</div>' +
      '<div class="pm-meta" id="pm-meta"></div>' +
      '<div class="pm-actions">' +
        '<a id="pm-nav" class="pm-nav" href="#" target="_blank" rel="noopener">Navigate</a>' +
        '<button class="pm-close" onclick="document.getElementById(\\'pm-panel\\').classList.remove(\\'open\\')">Close</button>' +
      '</div>';
    document.body.appendChild(panel);

    const vp = document.querySelector('meta[name="viewport"]');
    if (vp) {
      vp.setAttribute('content',
        'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
    }
  });
})();
</script>
"""


def inject_mobile_features(html_path: Path, mirrors: list[MirrorRecord]) -> None:
    """Post-process a Folium HTML file with mobile UI and geolocation."""
    content = html_path.read_text(encoding="utf-8")
    payload = json.dumps(_mirror_payload(mirrors))
    js = _MOBILE_JS_TEMPLATE.replace("__MIRRORS_JSON__", payload)

    if "pune-mirror-mobile-css" not in content:
        content = content.replace("</head>", _MOBILE_CSS + "\n</head>", 1)

    if "pune-mirror-mobile-js" not in content:
        content = content.replace("</body>", js + "\n</body>", 1)

    # Ensure viewport meta for mobile
    if 'name="viewport"' not in content:
        content = content.replace(
            "<head>",
            '<head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">',
            1,
        )

    html_path.write_text(content, encoding="utf-8")


def export_mirrors_json(mirrors: list[MirrorRecord], output_path: Path) -> Path:
    """Export mirror coordinates as JSON for static hosting / API-free clients."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_mirror_payload(mirrors), indent=2),
        encoding="utf-8",
    )
    return output_path
