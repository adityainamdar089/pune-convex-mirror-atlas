# Pune Convex Mirror Atlas

Interactive map of convex traffic mirrors in **Ganga Dham, Bibwewadi, Pune** — built from street-level imagery and OpenCV detection.

## Quick start (no API keys)

```bash
pip install -r requirements.txt
python scripts/run_demo.py          # synthetic data, zero API calls
python scripts/build_site.py        # build mobile map → docs/index.html
```

Open `docs/index.html` in a browser, or serve locally:

```bash
python -m http.server 8080 --directory docs
# Visit http://localhost:8080 on your phone (same Wi‑Fi)
```

## Full pipeline (real imagery)

1. Copy `.env.example` to `.env`
2. Add a **Mapillary** token (free): https://www.mapillary.com/dashboard/developers  
   — or a **Google Maps** API key with Street View Static API enabled
3. Run:

```bash
python scripts/run_pipeline.py --source mapillary --auto-confirm
python scripts/build_site.py
```

## Mobile: find nearest mirror

The hosted map includes a **“Find Nearest Mirror”** button:

1. Open the map on your phone (HTTPS required — GitHub Pages works)
2. Tap the button and allow location access
3. See distance to the closest mirror and tap **Navigate** for Google Maps directions

## Free hosting (GitHub Pages)

### Option A — `/docs` folder (simplest)

1. Push this repo to GitHub
2. **Settings → Pages → Build and deployment**
3. Source: **Deploy from a branch**
4. Branch: **main**, folder: **/docs**
5. Your map: `https://YOUR_USERNAME.github.io/pune-convex-mirror-atlas/`

After updating mirrors, rebuild:

```bash
python scripts/build_site.py
git add docs/
git commit -m "Update site"
git push
```

### Option B — GitHub Actions (auto-deploy on push)

1. Push to GitHub
2. **Settings → Pages → Build and deployment → Source: GitHub Actions**
3. The workflow in `.github/workflows/pages.yml` builds and deploys on every push to `main`

## Project structure

| Path | Purpose |
|------|---------|
| `scripts/run_pipeline.py` | Full 7-step pipeline |
| `scripts/run_demo.py` | Demo with synthetic images |
| `scripts/build_site.py` | Build map + copy to `docs/` |
| `docs/index.html` | Mobile-friendly hosted map |
| `docs/mirrors.json` | Mirror coordinates (JSON API) |
| `data/results/mirrors.csv` | Verified mirror records |

## Pipeline steps

1. Generate candidate road points  
2. Fetch street imagery (Google or Mapillary)  
3. Detect mirrors (OpenCV)  
4. Human review  
5. Build map & gallery  
6. Generate report  

## Tests

```bash
python -m pytest tests/ -q
```

## License

Street imagery © Google / Mapillary contributors. OpenStreetMap tiles © OSM contributors.
