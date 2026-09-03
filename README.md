# Good Fog

**Good Fog** tells you whether a Bay Area fog *inversion* is worth photographing from a
given Marin Headlands or Mt. Tamalpais viewpoint, and whether you'll be standing **above**
the marine layer or lost **inside** it — for tonight's sunset and every sunrise and sunset through three days out. Day 2 and 3 are labelled as a lower-confidence outlook.

Live: https://goodfog.babins.net

## How it works

1. **Forecast** — the backend polls hourly cloud cover, wind, temperature, dewpoint, and
   sunrise/sunset for all eight viewpoints from the free [Open-Meteo](https://open-meteo.com)
   API in one request. No API key.
2. **Fog base (LCL)** — computes the lifted condensation level from temperature and dewpoint
   using the Espy/Bolton approximation (~125 m of lift per °C of temp–dewpoint spread).
3. **Per-viewpoint thresholds** — every viewpoint has a calibrated "sweet spot" range for the
   fog base: **above the layer**, **right at the edge**, or **inside the fog / socked in**.
4. **Likelihood score** — combines low-cloud coverage, wind, clear sky above, and rain into
   an inversion-likelihood %. The fog-base position gates the score.
5. **Map** — the eight viewpoints on a tile-free SVG map (US Census land/water polygons, bundled), each dot colored by its likelihood for the selected window. Tap a dot to select it.

The numbers are a **heuristic guide, not a measurement** — always confirm against the live
cameras and Windy before setting the 4:30am alarm.

## Viewpoints

| Spot | Elevation | Notes |
|------|-----------|-------|
| Point Bonita Lighthouse | 100 ft | Coastal; only works with a very low fog base |
| Twin Peaks (from Arguello & Jackson) | 370 ft vantage | Shoot *toward* the 922 ft peaks emerging above the fog |
| Conzelman Pullouts | ~600 ft | Flexible stops when the fog base is low |
| Battery Spencer | 790 ft | Golden Gate Bridge framed in fog |
| Hawk Hill | 923 ft | Classic Marin valley inversion |
| Trojan Point | ~1,750 ft | Mid-mountain sea of clouds (summit gate opens 7am) |
| West Peak | 2,560 ft | Faces the coast (gate opens 7am) |
| East Peak | 2,571 ft | Highest vantage — above nearly all layers (gate opens 7am) |

## Stack

- `backend/` — Python 3.12 + FastAPI. Polls Open-Meteo, does all the fog math, serves `/api/snapshot`.
- `frontend/` — Svelte 5 + Vite PWA served by nginx. Renders the snapshot; no scoring in the browser.
- `data/` — coastline GeoJSON built by `scripts/build_geo.py` from Census TIGERweb; committed.
- Deployed with Docker Compose on Coolify; merging `main` deploys.

## Running it

```sh
# backend
cd backend && uv sync && uv run uvicorn goodfog.app:app --port 8000
# frontend (separate terminal)
cd frontend && npm ci --ignore-scripts && npm run dev
# or the whole stack
docker compose up --build   # http://localhost:8080
```

Tests: `cd backend && uv run pytest` · `cd frontend && npm test`.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `POLL_MINUTES` | `15` | Forecast refresh interval |
| `OPEN_METEO_MODELS` | `best_match` | Open-Meteo model selection |
| `ORS_API_KEY` | _(unset)_ | Optional [OpenRouteService](https://openrouteservice.org) key. Enables "drive time from your location"; the feature is hidden without it. Free plan is plenty. |

Put secrets in a local `.env` (git-ignored; `docker compose` reads it automatically). The bare `uv run uvicorn` command does not read `.env` — export the variable in your shell instead. In production set them in the Coolify app.

## Verify before you go

The app links out to Windy (cloud/fog/wind layers), [fog.today](https://fog.today)
(NOAA GOES satellite), yr.no, and ALERTCalifornia live cameras on Mt. Tam and at
Muir Beach so you can ground-truth the forecast with your own eyes.
