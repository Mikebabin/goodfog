# Good Fog — Design Spec

**Date:** 2026-09-02
**Status:** Approved for planning

## 1. Purpose

Good Fog tells a Bay Area photographer whether a marine-layer *inversion* is worth
shooting from one of eight Marin Headlands / Mt. Tamalpais viewpoints, and whether they
will stand **above** the fog or be **socked inside** it, for three upcoming windows:
tonight's sunset, tomorrow's sunrise, tomorrow's sunset.

This is a faithful port of the existing single-file `index.html` (Marin Inversion
Checker) into the same architecture as Mrs. Toasty: a FastAPI backend that polls the
forecast and does all the math, a Svelte 5 PWA that only renders, deployed with Docker
Compose on Coolify at https://goodfog.babins.net.

**Success criteria for v1**

- Opening the site on a phone shows results for the default viewpoint (East Peak,
  Tonight) within 2 seconds, with no button press.
- For every viewpoint × window, the score, verdict, fog-base status, factors, and
  explanation text match what the current `index.html` produces for the same
  Open-Meteo response (verified by fixture tests ported from the JS).
- The four tabs (Tonight, Tom. AM, Tom. PM, Plan) and all cards (verdict, elevation
  banner, LCL bar, timing, conditions, shot notes, why, verify links) are present.
- Deploys to Coolify from `docker-compose.yml` with zero secrets.

## 2. Decisions already made

| Decision | Choice | Why |
|---|---|---|
| Stack | FastAPI backend + Svelte 5/Vite PWA + nginx, Docker Compose | Same as Mrs. Toasty; user preference |
| Where scoring lives | Backend, pure Python with `now` passed in | Testable, one upstream fetch for all viewpoints, ready for history/sensors later |
| Forecast source | Open-Meteo hourly + daily, one multi-coordinate call | Free, no key; already what the app uses |
| Feature scope | Faithful port of current behavior | Rewrite first, redesign later |
| UX deviation | No "Check Conditions" button; results load automatically | Snapshot is precomputed server-side |
| Branding | "Good Fog" | Repo name; replaces "Marin Inversion Checker" |
| Units | Feet, °F, mph, as in the current app | v1 scope |

**Out of v1 scope:** new viewpoints, new data sources (soundings, satellite, cameras),
history charts, notifications, layout redesign, °C/metres toggle.

## 3. Architecture

```
goodfog/
  backend/
    pyproject.toml, uv.lock, Dockerfile
    goodfog/
      app.py          FastAPI app, lifespan starts poller, /api/health, /api/snapshot
      settings.py     env: POLL_MINUTES, OPEN_METEO_MODELS, BUILD_COMMIT, app_version
      viewpoints.py   VIEWPOINTS tuple (data ported verbatim from index.html)
      fog.py          pure math: lcl_ft, lcl_status, score, verdict, elevation_verdict, windows
      providers/open_meteo.py   fetch + parse → Forecast per viewpoint
      poller.py       schedule, builds immutable Snapshot
      snapshot.py     dataclasses + to_dict()
    tests/
  frontend/
    package.json, package-lock.json, vite.config.js, index.html, nginx.conf, Dockerfile
    src/
      App.svelte, main.js
      lib/            pure helpers (tested): barScale.js, time.js, plan.js, colors.js
      components/     LocationPicker, Tabs, VerdictBanner, ElevationBanner, ElevationBar,
                      TimingCard, ConditionsCard, ShotNotesCard, WhyCard, PlanView,
                      VerifyLinks, Footer
  docs/superpowers/specs/, docs/GETTING-STARTED.md
  docker-compose.yml, docker-compose.override.yml, .env.example, CLAUDE.md, README.md
```

The current `index.html` is removed in the port PR once fixture tests confirm parity.

**Runtime data flow**

1. Backend starts; poller runs immediately, then every `POLL_MINUTES` (default 15).
2. Poller makes one Open-Meteo request with all eight lat/lon pairs
   (`latitude=a,b,c&longitude=...`), `hourly=cloudcover_low,cloudcover_mid,cloudcover_high,
   windspeed_10m,precipitation_probability,temperature_2m,dewpoint_2m`,
   `daily=sunrise,sunset`, `timezone=America/Los_Angeles`, `forecast_days=3`.
3. For each viewpoint and each of the three windows it picks the forecast hour nearest
   the sun event, computes LCL, status, score, factors, explanation, and elevation
   verdict, and swaps in a new immutable `Snapshot`.
4. Frontend fetches `GET /api/snapshot` on load and every 5 minutes while visible, and
   renders the selected viewpoint and tab. Plan tab compares the three windows client-side.
5. On upstream failure the poller keeps the previous snapshot and records `error`;
   `/api/health` reports `stale: true` when the snapshot is older than 3 poll intervals.

## 4. Backend

### 4.1 Viewpoint data (`viewpoints.py`)

A frozen dataclass per viewpoint with the exact fields and values from `index.html`:
`id, name, lat, lon, elev_ft, desc, green_ft (lo, hi), yellow_ft (lo, hi), dawn_gated,
too_low, too_high, composition, access, cam_tip`. Order preserved (Hawk Hill first,
East Peak last). Default selection is East Peak.

### 4.2 Fog math (`fog.py`) — pure functions, no I/O, no clock

Ported 1:1 from the JS. Names and thresholds:

- `lcl_ft(temp_c, dew_c) -> int | None`: `max(0, round(125 * (t - td) * 3.281))`; `None` if
  either input is `None`. Python `round` is banker's rounding; use `math.floor(x + 0.5)`
  to match JS `Math.round`.
- `Hour` dataclass from one forecast index: `low_cloud, mid_cloud, high_cloud` (default 0
  when null), `wind_mph = jsround(kmh * 0.621371)`, `rain_pct`, `temp_f`, `dewpoint_f`
  (nullable), `lcl_ft`.
- `lcl_status(vp, hour) -> Status(kind, reason)`: `none` if `low_cloud < 20` or `lcl is None`;
  `red/low` if `lcl < green_lo`; `green` if `lcl <= green_hi`; `yellow` if `lcl <= yellow_hi`;
  else `red/high`.
- `score(vp, hour) -> Result(score, factors, explanation, lcl_ft, status)`: the five-part
  rubric (low cloud 40, wind 20, clear-above 20, rain 20, fog-base gate: green +10 cap 100,
  red cap 35, none cap 15) with the exact factor labels and explanation strings.
- `verdict(score) -> Verdict(label, emoji, cls)`: ≥70 Go for it!, ≥50 Worth a try,
  ≥30 Maybe next time, else Stay home.
- `elevation_verdict(vp, hour) -> ElevationVerdict(cls, icon, title, detail)`.
- `build_windows(sunrise, sunset) -> list[Window]`: `tonight` = `sunset[0]` (label Sunset,
  arrive 45 min before), `tomorrow_am` = `sunrise[1]` (Sunrise, 30), `tomorrow_pm` =
  `sunset[1]` (Sunset, 45). `hour` is the ISO hour string truncated to `:00` in the forecast
  timezone.
  *Superseded by `2026-09-02-three-day-outlook-design.md`: seven windows, day fields, days × halves Plan grid.*

### 4.3 Provider (`providers/open_meteo.py`)

`async fetch(viewpoints, models) -> dict[str, Forecast]` using `httpx` with a 15 s timeout.
Open-Meteo returns a list when given multiple coordinates; map back by index. Parse into
`Forecast(hourly_time: list[str], hourly: dict[str, list], daily_sunrise, daily_sunset)`.
Any exception propagates to the poller, which logs and keeps the old snapshot.

### 4.4 Snapshot and API

`GET /api/snapshot`:

```json
{
  "app_version": "0.1.0",
  "commit": "abc1234",
  "generated_at": "2026-09-02T23:15:04-07:00",
  "windows": [
    {"id": "tonight", "title": "Tonight Sunset", "tab": "Tonight", "sun_label": "Sunset",
     "sun_event": "2026-09-02T19:32", "arrive_by": "2026-09-02T18:47", "hour": "2026-09-02T19:00"},
    {"id": "tomorrow_am", ...}, {"id": "tomorrow_pm", ...}
  ],
  "viewpoints": [
    {"id": "east-peak", "name": "East Peak", "elev_ft": 2571, "desc": "...", "green_ft": [200, 2400],
     "yellow_ft": [2400, 2571], "dawn_gated": true, "composition": "...", "access": "...", "cam_tip": "...",
     "windows": [...],
     "results": {
       "tonight": {
         "score": 72, "verdict": {"label": "Go for it!", "emoji": "🚀", "cls": "go"},
         "status": {"kind": "green", "reason": null},
         "factors": [{"label": "Low cloud 80%", "rating": "good"}, ...],
         "explanation": "...",
         "lcl_ft": 1394,
         "elevation": {"cls": "above", "icon": "🏔️", "title": "Above the fog layer", "detail": "..."},
         "wx": {"low_cloud": 80, "mid_cloud": 5, "high_cloud": 0, "wind_mph": 4, "rain_pct": 0,
                "temp_f": 61, "dewpoint_f": 55, "lcl_ft": 1394}
       }, "tomorrow_am": null, "tomorrow_pm": {...}
     }}
  ]
}
```
  *Superseded by `2026-09-02-three-day-outlook-design.md`: seven windows, day fields, days × halves Plan grid.*

Each viewpoint carries its own `windows` (built from its own sun times, which differ by up
to a minute between points) — the top-level `windows` is used by the frontend only for tab
ids/labels. A window result is `null` when the forecast hour is missing. Times are local
(America/Los_Angeles) ISO strings without offset, exactly as Open-Meteo returns them, so
the frontend formats them with no timezone math.

`GET /api/health` → `{status, app_version, commit, generated_at, stale, last_error}`.

### 4.5 Settings

| Env var | Default | Purpose |
|---|---|---|
| `POLL_MINUTES` | 15 | Poll interval |
| `OPEN_METEO_MODELS` | `best_match` | Passed as `models=` |
| `BUILD_COMMIT` | `dev` | Baked at build from `SOURCE_COMMIT` arg (see Mrs. Toasty note) |

No secrets. `.env.example` lists these.

## 5. Frontend

Svelte 5 (runes) + Vite + `vite-plugin-pwa`, exact-pinned deps, `npm ci --ignore-scripts`.
Dark theme and card layout copied from the current CSS, max width 520 px.

- **State**: `snapshot`, `selectedId` (default `east-peak`, persisted in `localStorage`),
  `tab` (default `tonight`). Refetch every 5 min while `document.visibilityState === 'visible'`.
- **Components** render straight from the snapshot; no scoring in the browser.
- **Pure helpers in `src/lib/`** (vitest):
  - `barScale.js`: `niceMax`, `barModel(vp, lclFt)` → `{maxFt, locPct, lclPct, bandL, bandW, bandCenter}` ported from `renderElevationBar`.
  - `time.js`: `fmtTime(iso)` → `h:mm AM/PM`.
  - `plan.js`: `bestWindow(results)` picks the highest score (ties → earliest), and the
    "Best bet" / "No great windows" sentence logic (threshold 40).
  - `colors.js`: `scoreColor(score)`.
- **Plan tab**: three-column comparison with the best window outlined, then a per-window
  conditions card, as today.
  *Superseded by `2026-09-02-three-day-outlook-design.md`: seven windows, day fields, days × halves Plan grid.*
- **Verify links**: Windy (clouds, fog, wind), fog.today, yr.no, ALERTCalifornia Tam East /
  Tam West / Muir Beach — same URLs.
- **Footer**: `v{version} · {commit}` from `/api/health`, same as Mrs. Toasty.
- **Error state**: if the snapshot fetch fails and nothing is cached, show the error box
  text from the original app.

## 6. Ops

- `docker-compose.yml` with `api` and `web` services, `SOURCE_COMMIT` build arg on both,
  no host ports; `docker-compose.override.yml` publishes `8080:80` locally.
- Backend Dockerfile mirrors Mrs. Toasty (python:3.12-slim, uv 0.10.12, non-root, HEALTHCHECK).
  Frontend Dockerfile: node:22-alpine build → nginx:1.27-alpine with the same `nginx.conf`
  (proxy `/api/` to `api:8000`).
- Coolify: new app from `Mikebabin/goodfog`, domain `goodfog.babins.net`, "Source commit
  availability" = build time. Merging `main` deploys.
- Version `0.1.0` in `frontend/package.json` (+ lockfile) and `backend/pyproject.toml`;
  a backend test asserts they match.
- `CLAUDE.md` and `docs/GETTING-STARTED.md` adapted from Mrs. Toasty.

## 7. Testing

**Backend (pytest)**

- `test_fog.py`: LCL formula (incl. `None`, negative spread → 0, JS-style rounding);
  `lcl_status` at every boundary for a representative viewpoint and for Twin Peaks
  (whose green band starts above its elevation); score rubric edges and each gate
  (green +10 capped at 100, red capped at 35, none capped at 15); verdict thresholds;
  elevation verdict text for all four statuses.
- `test_windows.py`: window construction from a daily block, arrive-by offsets, hour
  truncation.
- `test_open_meteo.py`: parse a saved multi-coordinate response fixture (`tests/fixtures/`),
  map by index, handle nulls in `dewpoint_2m`.
- `test_score.py`: a small table of `(viewpoint, hour inputs) → expected score/status/
  verdict` computed by running the original JS once during the port (values pasted in).
- `test_snapshot.py`: `to_dict()` shape; null result when hour missing.
- `test_app.py`: `/api/health` and `/api/snapshot` via `httpx.AsyncClient` with a stubbed
  provider; version match test.

**Frontend (vitest)**: `barScale`, `time`, `plan`, `colors`. Component rendering is
verified manually against the original `index.html` side by side before deleting it.

## 8. Error handling

- Provider failure: log, keep previous snapshot, set `last_error`; health shows `stale`
  after 3 missed polls. Frontend shows the last good data with a subtle "updated Xm ago"
  line in the footer.
- Missing hour in the forecast: that window's result is `null`; the UI shows "No data for
  this window."
- Frontend fetch failure with no cache: error box, retry on the next timer tick.
