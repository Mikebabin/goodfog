# Good Fog — Likelihood Map Design Spec

**Date:** 2026-09-02
**Status:** Approved for planning
**Issue:** https://github.com/Mikebabin/goodfog/issues/4
**Builds on:** `docs/superpowers/specs/2026-09-02-goodfog-design.md`

## 1. Purpose

Show the eight viewpoints on a small map, each dot colored by its inversion likelihood
for the selected window, so the best spot is visible at a glance instead of by clicking
through the picker. Tapping a dot selects that viewpoint.

**Success criteria**

- On load, a map appears between the header and the viewpoint picker showing land, water,
  and eight dots with their likelihood percentages, colored with the same bands the app
  already uses for scores.
- Switching tabs recolors the dots for that window; on the Plan tab each dot shows its
  best window's score.
- Tapping a dot selects the viewpoint (same effect as the picker); the selected dot is
  ringed and labeled with its name.
- No third-party requests at runtime; the map works offline like the rest of the PWA.
- Dots in the Headlands cluster (Hawk Hill, Conzelman Pullouts, Battery Spencer, 1.6 km
  apart) do not overlap at 360 px width.

## 2. Decisions

| Decision | Choice | Why |
|---|---|---|
| Basemap | Schematic SVG land/water from committed GeoJSON | Tile-free, offline, tiny, matches the dark theme; same pattern as Mrs. Toasty |
| Land source | US Census TIGERweb: Marin + San Francisco county polygons **minus** Areal Hydrography polygons, clipped to the frame | Free, no key, ~10 m detail. County legal boundaries include water (SF covers the Golden Gate channel), so subtracting TIGER water is required; verified 2026-09-02 that all eight viewpoints land on land and the Gate, Richardson Bay, and Rodeo Lagoon are water |
| Frame | Fixed bbox lon −122.66…−122.40, lat 37.76…37.96 | Contains all eight spots incl. Twin Peaks with margin; fixed so the layout never shifts |
| Projection | `d3-geo` Mercator fit to the frame | Proven in Mrs. Toasty; exact pin `d3-geo@3.1.1` |
| Placement | Above the picker, always visible | Picker stays as the accessible list |
| Labels | Score % inside every dot; name label only on the selected dot | Keeps the Headlands cluster readable |
| Overlap | Deterministic nudge in pixel space | Pure, tested; no force layout dependency |
| Version | 0.2.0 in both manifests | User-visible feature |

**Out of scope:** roads, terrain, tiles, user location, zoom/pan, more viewpoints.

## 3. Data

### 3.1 `scripts/build_geo.py` → `data/coast.geojson`

Run from repo root: `uv run --project backend python scripts/build_geo.py`. Never hand-edit
the output.

1. Fetch counties: `GET https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query`
   with `where=STATE='06' AND COUNTY IN ('041','075')`, `geometry=<frame>`,
   `geometryType=esriGeometryEnvelope`, `inSR=4326`, `outSR=4326`, `outFields=NAME,GEOID`, `f=geojson`.
   Expect exactly 2 features.
2. Fetch water: `GET .../TIGERweb/Hydro/MapServer/1/query` with `where=1=1`, same geometry
   params, `outFields=NAME,MTFCC`, `resultRecordCount=2000`, `f=geojson`. Fail if
   `exceededTransferLimit` is true.
3. `land = unary_union(counties) ∩ frame − unary_union(water) ∩ frame`, then
   `simplify(0.0005, preserve_topology=True)`, drop parts with area < 1e-7 deg², orient
   exterior rings clockwise (d3-geo winding, as in Mrs. Toasty), round coords to 4 decimals.
4. Write a `FeatureCollection` with one `Feature` per land part (`properties: {}`) and a
   top-level `"bbox": [-122.66, 37.76, -122.40, 37.96]`.

Expected output: ~7 parts, ~700 vertices, ~11 KB. Dependencies: `httpx` (already a backend
dep) and `shapely` (add as a backend **dev** dependency, exact pin `2.1.2`, since only the
script and its test use it).

### 3.2 Backend snapshot

Each entry in `viewpoints[]` gains `"lat"` and `"lon"` (floats from `viewpoints.py`).
Nothing else changes.

## 4. Frontend

### 4.1 `src/lib/mapModel.js` (pure, tested)

```js
export const FRAME = { west: -122.66, south: 37.76, east: -122.40, north: 37.96 };
export const DOT_R = 12;                       // px
export function makeProjection(width, height)   // geoMercator().fitExtent to the FRAME polygon
export function landPaths(coast, projection)    // string[] of SVG path d for each feature
export function scoreForTab(vp, tab)            // number|null: vp.results[tab]?.score, or on 'plan' the max over windows (null if all null)
export function placeDots(viewpoints, tab, projection) // [{id, name, x, y, score, color}], color = scoreColor(score) or '#8b949e'
export function nudgeApart(dots, minDist = 2*DOT_R + 2, iterations = 10) // pushes overlapping pairs apart along their axis, symmetric, deterministic; returns new array
```

`placeDots` calls `nudgeApart` before returning. Height is derived from the frame's aspect
in Mercator space so the map is never letterboxed: `height = round(width * frameAspect)`,
where `frameAspect` is computed once from the projected frame corners (≈ 1.0 here).

### 4.2 `src/components/Map.svelte`

Props: `coast` (FeatureCollection), `viewpoints`, `selectedId`, `tab`, `onselect`.
Renders `<svg viewBox="0 0 {w} {h}">` with `bind:clientWidth`:

- water: full-bleed rect `#0b1a2b`; land: paths filled `var(--panel)` stroked `var(--border)`;
- one `<g role="button" tabindex="0">` per dot: circle `r=DOT_R` filled `color`, stroke
  `var(--bg)` 2 px; text = `score` (or `–` when null), 0.7rem bold, fill chosen for contrast
  (white on red/orange/green, dark on amber) via a `textColorFor(hex)` helper in `colors.js`;
- selected dot: extra ring `r=DOT_R+4` stroke `var(--blue)` and a name label below
  (`0.7rem`, `var(--text-strong)`, with a dark text-shadow); label is clamped inside the SVG;
- click / Enter / Space → `onselect(id)`; `aria-label="{name}, {score}% likelihood"`.

`App.svelte` imports `coast` from `@data/coast.geojson?raw` (Vite alias, as Mrs. Toasty does)
and places `<Map>` between `<Header/>` and `<LocationPicker/>` inside the `{#if snapshot && vp}`
block, passing `viewpoints={viewpoints} {selectedId} {tab} onselect={select}`.

### 4.3 Build

- `frontend/vite.config.js`: add `resolve.alias['@data'] = ../data` and `server.fs.allow` for
  the repo root (copy from Mrs. Toasty).
- `frontend/Dockerfile`: `COPY data /src/data` before the build (context is repo root already).
- `frontend/package.json`: add `"d3-geo": "3.1.1"`; bump version to `0.2.0`; `backend/pyproject.toml`
  to `0.2.0`.

## 5. Testing

**Backend**
- `tests/test_geo_data.py`: `data/coast.geojson` parses; every ring is within the frame bbox;
  every exterior ring is clockwise (shoelace sign), holes counter-clockwise; every viewpoint
  in `VIEWPOINTS` is inside some land polygon (point-in-polygon with shapely, dev dep);
  a point in the Golden Gate (−122.478, 37.818) is not.
- `tests/test_snapshot.py`: viewpoint entries carry `lat`/`lon` matching `VIEWPOINTS`.
- `tests/test_config.py`: version match still holds at 0.2.0.

**Frontend (vitest)**
- `mapModel.test.js`: `makeProjection` maps the frame's NW corner to (0,0) and SE to (w,h)
  within 0.5 px; `scoreForTab` for a window tab, for `plan` (max, ignores nulls), and all-null;
  `placeDots` returns 8 dots inside the viewBox with colors from `scoreColor`; `nudgeApart`
  separates two dots 4 px apart to ≥ minDist while keeping their midpoint, and leaves
  non-overlapping dots untouched; the real Hawk Hill / Conzelman / Battery Spencer coordinates
  at width 360 end ≥ minDist apart.
- `colors.test.js`: `textColorFor` returns dark text for amber (`#d29922`), light for the rest.

**Manual**: load the app, confirm land shapes look right (Gate open, Richardson Bay, Tam
peninsula), click each dot selects the viewpoint, Plan tab shows best scores.

## 6. Error handling

- Build script fails loudly on unexpected feature counts or transfer limits; nothing is
  written on failure.
- Missing/null results render a grey dot with `–`.
- If `coast.geojson` fails to import the build fails (it is bundled), so there is no runtime
  fallback path.
