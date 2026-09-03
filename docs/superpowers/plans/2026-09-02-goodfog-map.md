# Good Fog Likelihood Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tile-free SVG map above the viewpoint picker showing the eight viewpoints as dots colored by inversion likelihood for the selected tab, with tap-to-select.

**Architecture:** A build script derives land polygons for a fixed frame from US Census TIGERweb (counties minus areal hydrography) into a committed `data/coast.geojson`. The backend adds `lat`/`lon` to each snapshot viewpoint. The frontend gets a pure, tested `mapModel.js` (d3-geo Mercator fit to the frame, dot placement, overlap nudge, per-tab score) and a `Map.svelte` component wired into `App.svelte`.

**Tech Stack:** Python 3.12 + shapely 2.1.2 (dev) + httpx for the build script; Svelte 5 + `d3-geo@3.1.1` + vitest for the frontend.

**Spec:** `docs/superpowers/specs/2026-09-02-goodfog-map-design.md`

## Global Constraints

- Repo: `/Users/mike/claudeprojects/goodfog`, branch `map-likelihood` (already created from `main`). Never push to `main` directly; open a PR.
- Frame: lon −122.66…−122.40, lat 37.76…37.96. Simplify tolerance 0.0005°, coords rounded to 4 decimals, exterior rings clockwise (d3-geo winding).
- Version bumps to `0.2.0` in `frontend/package.json` (+ lockfile) and `backend/pyproject.toml` (a test enforces the match).
- npm: exact pins only (`"d3-geo": "3.1.1"`), `npm install --ignore-scripts` then `npm audit signatures`. Python: exact pins; `shapely==2.1.2` goes in the **dev** dependency group.
- No runtime third-party requests; the map is bundled data + SVG.
- The frontend computes no scores; `mapModel.scoreForTab` only reads `vp.results[*].score`.
- Colors reuse `scoreColor`; null score → `#8b949e` and the text `–`.
- TDD: failing test first for every code change. Commit each task with the trailers:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01Uucw9EqwctfzAmKYxTpBpK
  ```
- Backend tests: `cd backend && uv run pytest -q`. Frontend: `cd frontend && npm test && npm run build`.

---

## File structure

```
scripts/build_geo.py               fetch counties + water from TIGERweb, land = counties − water, simplify, write data/coast.geojson
data/coast.geojson                 generated, committed (FeatureCollection of land parts + bbox)
backend/goodfog/snapshot.py        + lat/lon on each viewpoint entry
backend/tests/test_snapshot.py     + lat/lon assertion
backend/tests/test_geo_data.py     guards winding, frame, viewpoints on land
backend/pyproject.toml             version 0.2.0; shapely dev dep
frontend/package.json              version 0.2.0; d3-geo
frontend/vite.config.js            @data alias; server.fs.allow repo root
frontend/Dockerfile                COPY data
frontend/src/lib/colors.js         + textColorFor(hex)
frontend/src/lib/mapModel.js       FRAME, DOT_R, frameAspect, makeProjection, landPaths, scoreForTab, nudgeApart, placeDots
frontend/src/components/Map.svelte SVG map
frontend/src/App.svelte            import coast, render <Map>
CLAUDE.md, README.md               mention data/ + build script
```

---

### Task 1: Snapshot lat/lon and version bump

**Files:**
- Modify: `backend/goodfog/snapshot.py` (`_viewpoint`), `backend/tests/test_snapshot.py`, `backend/pyproject.toml` (version), `frontend/package.json` (version), `frontend/package-lock.json` (version fields)

**Interfaces:**
- Produces: snapshot `viewpoints[i].lat: float`, `viewpoints[i].lon: float`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_snapshot.py`:
```python


def test_viewpoint_entry_carries_coordinates():
    s = _snap()
    for entry, vp in zip(s["viewpoints"], VIEWPOINTS, strict=True):
        assert entry["lat"] == vp.lat
        assert entry["lon"] == vp.lon
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_snapshot.py -q`
Expected: FAIL with `KeyError: 'lat'`

- [ ] **Step 3: Implement**

In `backend/goodfog/snapshot.py`, inside `_viewpoint`'s returned dict, add after `"name": vp.name,`:
```python
        "lat": vp.lat,
        "lon": vp.lon,
```

- [ ] **Step 4: Bump versions**

- `backend/pyproject.toml`: `version = "0.2.0"`
- `frontend/package.json`: `"version": "0.2.0"`
- `frontend/package-lock.json`: change both `"version": "0.1.0"` occurrences at the top (root and `packages[""]`) to `"0.2.0"`. Verify with `grep -n '"version": "0.2.0"' frontend/package-lock.json | head -2` (expect 2 lines, both near the top).

- [ ] **Step 5: Run all backend tests**

Run: `cd backend && uv run pytest -q`
Expected: all pass (the version-match test confirms both manifests read 0.2.0)

- [ ] **Step 6: Commit**

```bash
git add backend frontend/package.json frontend/package-lock.json
git commit -m "feat(backend): expose viewpoint lat/lon in snapshot; bump to 0.2.0"
```

---

### Task 2: Geo build script and committed coastline data

**Files:**
- Create: `scripts/build_geo.py`, `data/coast.geojson` (generated), `backend/tests/test_geo_data.py`
- Modify: `backend/pyproject.toml` (dev deps), `backend/uv.lock` (regenerated)

**Interfaces:**
- Produces: `data/coast.geojson` — `{"type":"FeatureCollection","bbox":[-122.66,37.76,-122.4,37.96],"features":[{"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[...]}}, ...]}`; every feature a `Polygon` with clockwise exterior ring, coords rounded to 4 decimals.

- [ ] **Step 1: Add shapely as a dev dependency**

In `backend/pyproject.toml`, `[dependency-groups] dev` list, add `"shapely==2.1.2",`. Then:
```bash
cd backend && uv sync && uv run python -c "import shapely; print(shapely.__version__)"
```
Expected: `2.1.2`

- [ ] **Step 2: Write the failing data test**

`backend/tests/test_geo_data.py`:
```python
"""Guards for the generated data/coast.geojson (see scripts/build_geo.py)."""
import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.geometry.polygon import LinearRing
from shapely.ops import unary_union

from goodfog.viewpoints import VIEWPOINTS

ROOT = Path(__file__).resolve().parents[2]
COAST = ROOT / "data" / "coast.geojson"
FRAME = (-122.66, 37.76, -122.40, 37.96)


def _fc():
    return json.loads(COAST.read_text())


def test_file_shape_and_bbox():
    fc = _fc()
    assert fc["type"] == "FeatureCollection"
    assert fc["bbox"] == [-122.66, 37.76, -122.4, 37.96]
    assert 1 <= len(fc["features"]) <= 20
    for f in fc["features"]:
        assert f["geometry"]["type"] == "Polygon"
        assert f["properties"] == {}


def test_rings_are_within_frame_and_rounded():
    west, south, east, north = FRAME
    for f in _fc()["features"]:
        for ring in f["geometry"]["coordinates"]:
            for lon, lat in ring:
                assert west - 1e-9 <= lon <= east + 1e-9 and south - 1e-9 <= lat <= north + 1e-9
                assert round(lon, 4) == lon and round(lat, 4) == lat


def test_exterior_clockwise_holes_counterclockwise():
    # d3-geo uses spherical winding: a counter-clockwise exterior is read as the whole
    # sphere minus the polygon and paints the entire map.
    for f in _fc()["features"]:
        exterior, *holes = f["geometry"]["coordinates"]
        assert not LinearRing(exterior).is_ccw
        for h in holes:
            assert LinearRing(h).is_ccw


def test_viewpoints_on_land_and_golden_gate_is_water():
    land = unary_union([shape(f["geometry"]) for f in _fc()["features"]])
    for vp in VIEWPOINTS:
        assert land.contains(Point(vp.lon, vp.lat)), vp.id
    assert not land.contains(Point(-122.478, 37.818))  # mid Golden Gate channel
    assert not land.contains(Point(-122.47, 37.85))    # Richardson Bay
    assert not land.contains(Point(-122.535, 37.831))  # Rodeo Lagoon
```

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_geo_data.py -q`
Expected: FAIL with `FileNotFoundError` for `data/coast.geojson`

- [ ] **Step 4: Write the build script**

`scripts/build_geo.py`:
```python
"""Build data/coast.geojson: land polygons for the Good Fog map frame.

Land = (Marin + San Francisco county polygons) − (Census areal hydrography), clipped to
FRAME, simplified, exterior rings clockwise (d3-geo winding). County legal boundaries
include water (SF covers the Golden Gate channel), hence the subtraction.

Run from repo root:  uv run --project backend python scripts/build_geo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from shapely.geometry import box, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

FRAME = (-122.66, 37.76, -122.40, 37.96)  # west, south, east, north
TOLERANCE_DEG = 0.0005
MIN_AREA_DEG2 = 1e-7
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
COUNTIES_URL = f"{TIGER}/State_County/MapServer/1/query"
WATER_URL = f"{TIGER}/Hydro/MapServer/1/query"
OUT = Path(__file__).resolve().parent.parent / "data" / "coast.geojson"


def _geo_params(where: str, out_fields: str) -> dict:
    west, south, east, north = FRAME
    return {
        "where": where,
        "outFields": out_fields,
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "outSR": "4326",
        "resultRecordCount": "2000",
        "f": "geojson",
    }


def fetch(url: str, params: dict) -> list[dict]:
    r = httpx.get(url, params=params, timeout=120)
    r.raise_for_status()
    data = r.json()
    if data.get("exceededTransferLimit"):
        raise SystemExit(f"{url}: exceededTransferLimit; narrow the query")
    return data["features"]


def round_coords(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, (list, tuple)):
        return [round_coords(x) for x in obj]
    return obj


def build() -> dict:
    counties = fetch(COUNTIES_URL, _geo_params("STATE='06' AND COUNTY IN ('041','075')", "NAME,GEOID"))
    if len(counties) != 2:
        raise SystemExit(f"expected 2 counties, got {len(counties)}")
    water = fetch(WATER_URL, _geo_params("1=1", "NAME,MTFCC"))
    if not water:
        raise SystemExit("no water features returned")

    frame = box(*FRAME)
    land = unary_union([shape(f["geometry"]) for f in counties]).intersection(frame)
    land = land.difference(unary_union([shape(f["geometry"]) for f in water]).intersection(frame))
    land = land.simplify(TOLERANCE_DEG, preserve_topology=True)

    parts = [p for p in getattr(land, "geoms", [land]) if p.area > MIN_AREA_DEG2]
    features = [
        {"type": "Feature", "properties": {}, "geometry": round_coords(mapping(orient(p, sign=-1.0)))}
        for p in parts
    ]
    return {"type": "FeatureCollection", "bbox": list(FRAME), "features": features}


def main() -> int:
    fc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fc, separators=(",", ":")) + "\n")
    n = sum(len(r) for f in fc["features"] for r in f["geometry"]["coordinates"])
    print(f"wrote {OUT} ({len(fc['features'])} parts, {n} vertices, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Note: `mapping()` returns tuples; `round_coords` converts them to lists so `json.dumps` output is plain arrays.

- [ ] **Step 5: Run the script**

```bash
cd /Users/mike/claudeprojects/goodfog && uv run --project backend python scripts/build_geo.py
```
Expected: `wrote .../data/coast.geojson (~7 parts, ~700 vertices, ~11 KB)`. Feature count may differ slightly (5–10) with the live data; that is fine.

- [ ] **Step 6: Run the data tests and full suite**

Run: `cd backend && uv run pytest -q`
Expected: all pass. If `test_viewpoints_on_land_and_golden_gate_is_water` fails for a viewpoint, print which one and stop (report DONE_WITH_CONCERNS); do not loosen the test.

- [ ] **Step 7: Commit**

```bash
git add scripts/build_geo.py data/coast.geojson backend/pyproject.toml backend/uv.lock backend/tests/test_geo_data.py
git commit -m "feat(data): build script and committed coastline GeoJSON for the map frame"
```

---

### Task 3: Frontend deps, config, and pure map model

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.js`, `frontend/Dockerfile`, `frontend/src/lib/colors.js`, `frontend/src/lib/colors.test.js`
- Create: `frontend/src/lib/mapModel.js`, `frontend/src/lib/mapModel.test.js`

**Interfaces:**
- Produces: `textColorFor(hex) -> '#0d1117' | '#ffffff'`; `FRAME`, `DOT_R = 12`, `frameAspect() -> number`, `makeProjection(width, height)`, `landPaths(coast, projection) -> string[]`, `scoreForTab(vp, tab) -> number|null`, `nudgeApart(dots, minDist = 2*DOT_R+2, iterations = 10) -> dots`, `placeDots(viewpoints, tab, projection) -> [{id,name,x,y,score,color}]`.

- [ ] **Step 1: Install d3-geo and wire config**

`frontend/package.json` dependencies: add `"d3-geo": "3.1.1"` (keep `svelte`). Then:
```bash
cd frontend && npm install --ignore-scripts && npm audit signatures
```

`frontend/vite.config.js`: add to the exported config object, next to `server`:
```js
  resolve: { alias: { '@data': path.resolve(here, '../data') } },
  server: {
    fs: { allow: [path.resolve(here, '..')] },
    proxy: { '/api': 'http://localhost:8000' },
  },
```
(replace the existing one-line `server:` entry).

`frontend/Dockerfile`: after `RUN npm ci --ignore-scripts`, add `COPY data /src/data` before `COPY frontend .`.

- [ ] **Step 2: Write failing color test**

Append to `frontend/src/lib/colors.test.js`:
```js
import { textColorFor } from './colors.js';

it('picks dark text only on the bright amber band', () => {
  expect(textColorFor('#d29922')).toBe('#0d1117'); // amber
  expect(textColorFor('#3fb950')).toBe('#ffffff'); // green
  expect(textColorFor('#e3812c')).toBe('#ffffff'); // orange
  expect(textColorFor('#f85149')).toBe('#ffffff'); // red
  expect(textColorFor('#8b949e')).toBe('#ffffff'); // grey (no data)
});
```

- [ ] **Step 3: Write failing mapModel tests**

`frontend/src/lib/mapModel.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { DOT_R, FRAME, frameAspect, landPaths, makeProjection, nudgeApart, placeDots, scoreForTab } from './mapModel.js';

const W = 360;
const H = Math.round(W * frameAspect());
const proj = makeProjection(W, H);

const coast = {
  type: 'FeatureCollection',
  features: [{ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[-122.6, 37.9], [-122.5, 37.9], [-122.5, 37.8], [-122.6, 37.8], [-122.6, 37.9]]] } }],
};

const vp = (id, lon, lat, results) => ({ id, name: id, lon, lat, results });
const r = (score) => (score == null ? null : { score });

describe('projection', () => {
  it('fits the frame exactly', () => {
    const [x0, y0] = proj([FRAME.west, FRAME.north]);
    const [x1, y1] = proj([FRAME.east, FRAME.south]);
    expect(Math.abs(x0)).toBeLessThan(0.5);
    expect(Math.abs(y0)).toBeLessThan(0.5);
    expect(Math.abs(x1 - W)).toBeLessThan(0.5);
    expect(Math.abs(y1 - H)).toBeLessThan(0.5);
  });
  it('frameAspect is near square for this frame', () => {
    expect(frameAspect()).toBeGreaterThan(0.9);
    expect(frameAspect()).toBeLessThan(1.1);
  });
  it('landPaths returns one path string per feature', () => {
    const paths = landPaths(coast, proj);
    expect(paths).toHaveLength(1);
    expect(paths[0]).toMatch(/^M/);
  });
});

describe('scoreForTab', () => {
  const v = vp('a', -122.5, 37.85, { tonight: r(15), tomorrow_am: r(35), tomorrow_pm: null });
  it('reads the window score', () => {
    expect(scoreForTab(v, 'tonight')).toBe(15);
    expect(scoreForTab(v, 'tomorrow_pm')).toBeNull();
  });
  it('plan uses the best window and ignores nulls', () => {
    expect(scoreForTab(v, 'plan')).toBe(35);
    expect(scoreForTab(vp('b', 0, 0, { tonight: null }), 'plan')).toBeNull();
  });
});

describe('nudgeApart', () => {
  it('separates overlapping dots symmetrically and keeps the midpoint', () => {
    const out = nudgeApart([{ id: 'a', x: 100, y: 100 }, { id: 'b', x: 104, y: 100 }]);
    const d = Math.hypot(out[1].x - out[0].x, out[1].y - out[0].y);
    expect(d).toBeGreaterThanOrEqual(2 * DOT_R + 2 - 1e-6);
    expect((out[0].x + out[1].x) / 2).toBeCloseTo(102, 6);
    expect(out[0].y).toBeCloseTo(100, 6);
  });
  it('leaves non-overlapping dots untouched and does not mutate input', () => {
    const input = [{ id: 'a', x: 0, y: 0 }, { id: 'b', x: 100, y: 0 }];
    const out = nudgeApart(input);
    expect(out).toEqual(input);
    expect(out).not.toBe(input);
  });
  it('handles coincident dots deterministically', () => {
    const out = nudgeApart([{ id: 'a', x: 50, y: 50 }, { id: 'b', x: 50, y: 50 }]);
    expect(Math.abs(out[1].x - out[0].x)).toBeGreaterThanOrEqual(2 * DOT_R + 2 - 1e-6);
  });
});

describe('placeDots', () => {
  const vps = [
    vp('hawk-hill', -122.4997, 37.8283, { tonight: r(80) }),
    vp('conzelman-pullouts', -122.49, 37.827, { tonight: r(55) }),
    vp('battery-spencer', -122.4818, 37.8278, { tonight: r(20) }),
    vp('twin-peaks-vantage', -122.4581, 37.7874, { tonight: null }),
  ];
  const dots = placeDots(vps, 'tonight', proj);
  it('returns one dot per viewpoint inside the viewBox with band colors', () => {
    expect(dots.map((d) => d.id)).toEqual(vps.map((v) => v.id));
    for (const d of dots) {
      expect(d.x).toBeGreaterThan(0); expect(d.x).toBeLessThan(W);
      expect(d.y).toBeGreaterThan(0); expect(d.y).toBeLessThan(H);
    }
    expect(dots[0].color).toBe('#3fb950');
    expect(dots[1].color).toBe('#d29922');
    expect(dots[2].color).toBe('#f85149');
    expect(dots[3]).toMatchObject({ score: null, color: '#8b949e' });
  });
  it('keeps the Headlands cluster from overlapping at 360px', () => {
    const min = 2 * DOT_R + 2;
    for (let i = 0; i < 3; i++) for (let j = i + 1; j < 3; j++) {
      expect(Math.hypot(dots[i].x - dots[j].x, dots[i].y - dots[j].y)).toBeGreaterThanOrEqual(min - 1e-6);
    }
  });
});
```

- [ ] **Step 4: Run to verify failure**

Run: `cd frontend && npm test`
Expected: FAIL — `mapModel.js` not found; `textColorFor` not exported.

- [ ] **Step 5: Implement colors and mapModel**

Append to `frontend/src/lib/colors.js`:
```js

/** Text color that reads on a dot of the given fill: dark only on the bright amber band. */
export function textColorFor(hex) {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  const brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return brightness >= 0.6 ? '#0d1117' : '#ffffff';
}
```

`frontend/src/lib/mapModel.js`:
```js
import { geoMercator, geoPath } from 'd3-geo';
import { scoreColor } from './colors.js';

/** Fixed map frame around the eight viewpoints (lon/lat). The layout never shifts with data. */
export const FRAME = { west: -122.66, south: 37.76, east: -122.4, north: 37.96 };
export const DOT_R = 12; // px
const NO_DATA = '#8b949e';

// Clockwise ring (d3-geo spherical winding): a counter-clockwise ring means "everything but".
const framePolygon = {
  type: 'Polygon',
  coordinates: [[
    [FRAME.west, FRAME.north], [FRAME.east, FRAME.north], [FRAME.east, FRAME.south], [FRAME.west, FRAME.south], [FRAME.west, FRAME.north],
  ]],
};

/** height / width of the frame in Mercator space, so the SVG is never letterboxed. */
export function frameAspect() {
  const p = geoMercator();
  const [x0, y0] = p([FRAME.west, FRAME.north]);
  const [x1, y1] = p([FRAME.east, FRAME.south]);
  return (y1 - y0) / (x1 - x0);
}

export function makeProjection(width, height) {
  return geoMercator().fitExtent([[0, 0], [width, height]], framePolygon);
}

export function landPaths(coast, projection) {
  const path = geoPath(projection);
  return coast.features.map((f) => path(f));
}

/** Score to color a dot by: the tab's window, or on the Plan tab the best window (null if none). */
export function scoreForTab(vp, tab) {
  if (tab === 'plan') {
    const scores = Object.values(vp.results).filter((r) => r != null).map((r) => r.score);
    return scores.length ? Math.max(...scores) : null;
  }
  return vp.results[tab]?.score ?? null;
}

/** Push overlapping dots apart along their connecting axis. Pure, deterministic, symmetric. */
export function nudgeApart(dots, minDist = 2 * DOT_R + 2, iterations = 10) {
  const out = dots.map((d) => ({ ...d }));
  for (let it = 0; it < iterations; it++) {
    let moved = false;
    for (let i = 0; i < out.length; i++) {
      for (let j = i + 1; j < out.length; j++) {
        let dx = out[j].x - out[i].x;
        let dy = out[j].y - out[i].y;
        let d = Math.hypot(dx, dy);
        if (d >= minDist) continue;
        if (d === 0) { dx = 1; dy = 0; d = 1; }
        const push = (minDist - d) / 2;
        const ux = dx / d, uy = dy / d;
        out[i].x -= ux * push; out[i].y -= uy * push;
        out[j].x += ux * push; out[j].y += uy * push;
        moved = true;
      }
    }
    if (!moved) break;
  }
  return out;
}

export function placeDots(viewpoints, tab, projection) {
  const dots = viewpoints.map((vp) => {
    const [x, y] = projection([vp.lon, vp.lat]);
    const score = scoreForTab(vp, tab);
    return { id: vp.id, name: vp.name, x, y, score, color: score == null ? NO_DATA : scoreColor(score) };
  });
  return nudgeApart(dots);
}
```

- [ ] **Step 6: Run tests and build**

Run: `cd frontend && npm test && npm run build`
Expected: all pass (previous 16 + new), build clean. If the "fits the frame exactly" test is off by more than 0.5 px, the frame ring winding is wrong; check the ring order above rather than loosening the tolerance.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js frontend/Dockerfile frontend/src/lib
git commit -m "feat(frontend): d3-geo map model with tested projection, dot placement, and overlap nudge"
```

---

### Task 4: Map component wired into the app

**Files:**
- Create: `frontend/src/components/Map.svelte`
- Modify: `frontend/src/App.svelte`

**Interfaces:**
- Consumes: `coast` FeatureCollection (from `@data/coast.geojson?raw`), snapshot `viewpoints[]` with `lat`, `lon`, `results`; `select(id)`; `tab`; `placeDots`, `landPaths`, `makeProjection`, `frameAspect`, `DOT_R`, `textColorFor`.

- [ ] **Step 1: Write the component**

`frontend/src/components/Map.svelte`:
```svelte
<script>
  import { DOT_R, frameAspect, landPaths, makeProjection, placeDots } from '../lib/mapModel.js';
  import { textColorFor } from '../lib/colors.js';

  let { coast, viewpoints, selectedId, tab, onselect } = $props();

  let width = $state(360);
  const height = $derived(Math.round(width * frameAspect()));
  const projection = $derived(makeProjection(width, height));
  const land = $derived(landPaths(coast, projection));
  const dots = $derived(placeDots(viewpoints, tab, projection));
  const selected = $derived(dots.find((d) => d.id === selectedId) ?? null);
  const labelX = $derived(selected ? Math.min(Math.max(selected.x, 60), width - 60) : 0);

  function keyselect(e, id) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onselect(id); }
  }
</script>

<div class="wrap" bind:clientWidth={width}>
  <svg viewBox="0 0 {width} {height}" {width} {height} role="img" aria-label="Map of viewpoints colored by inversion likelihood">
    <rect x="0" y="0" {width} {height} class="water" />
    {#each land as d, i (i)}
      <path {d} class="land" />
    {/each}
    {#each dots as dot (dot.id)}
      <g
        class="dot"
        role="button"
        tabindex="0"
        aria-label="{dot.name}, {dot.score == null ? 'no data' : `${dot.score}% likelihood`}"
        onclick={() => onselect(dot.id)}
        onkeydown={(e) => keyselect(e, dot.id)}
      >
        {#if dot.id === selectedId}
          <circle cx={dot.x} cy={dot.y} r={DOT_R + 4} class="ring" />
        {/if}
        <circle cx={dot.x} cy={dot.y} r={DOT_R} fill={dot.color} class="disc" />
        <text x={dot.x} y={dot.y} dy="0.35em" text-anchor="middle" fill={textColorFor(dot.color)} class="score">{dot.score ?? '–'}</text>
      </g>
    {/each}
    {#if selected}
      <text x={labelX} y={selected.y + DOT_R + 14} text-anchor="middle" class="name">{selected.name}</text>
    {/if}
  </svg>
</div>

<style>
  .wrap { margin-bottom: 16px; border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
  svg { display: block; width: 100%; height: auto; }
  .water { fill: #0b1a2b; }
  .land { fill: var(--panel); stroke: var(--border); stroke-width: 1; }
  .dot { cursor: pointer; outline: none; }
  .dot:focus-visible .disc { stroke: var(--blue); stroke-width: 3; }
  .disc { stroke: var(--bg); stroke-width: 2; }
  .ring { fill: none; stroke: var(--blue); stroke-width: 2; }
  .score { font-size: 0.7rem; font-weight: 700; pointer-events: none; user-select: none; }
  .name { font-size: 0.7rem; font-weight: 600; fill: var(--text-strong); paint-order: stroke; stroke: var(--bg); stroke-width: 3px; pointer-events: none; }
</style>
```

- [ ] **Step 2: Wire into App.svelte**

In `frontend/src/App.svelte`:
- Add imports after the `onMount` import:
  ```js
  import coastRaw from '@data/coast.geojson?raw';
  import Map from './components/Map.svelte';
  ```
  and after the imports block: `const coast = JSON.parse(coastRaw); // Vite only auto-parses .json, so load .geojson as text`
- Inside `{#if snapshot && vp}`, insert as the first child, before `<LocationPicker ...>`:
  ```svelte
    <Map {coast} {viewpoints} {selectedId} {tab} onselect={select} />
  ```

- [ ] **Step 3: Test and build**

Run: `cd frontend && npm test && npm run build`
Expected: pass; build clean with no Svelte warnings (a11y warnings about `role="button"` on `<g>` must not appear; if one does, report it verbatim rather than suppressing).

- [ ] **Step 4: Run locally and check in a browser**

```bash
cd /Users/mike/claudeprojects/goodfog/backend && (uv run uvicorn goodfog.app:app --port 8000 &) && cd ../frontend && (npm run dev -- --port 5173 &) && sleep 8 && curl -s -o /dev/null -w "%{http_code}\n" localhost:5173/
```
The controller checks in Chrome: land shapes look right (Golden Gate open, Richardson Bay, Tam peninsula, Point Bonita headland), eight dots with numbers, Headlands trio not overlapping at narrow widths, clicking a dot selects it in the picker and cards, Plan tab shows best-window scores. Then stop both servers.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): likelihood map above the viewpoint picker (#4)"
```

---

### Task 5: Docs and PR

**Files:**
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 1: Docs**

`CLAUDE.md` Layout section: add a line
```
- `data/` — generated coastline GeoJSON for the map; regenerate with `uv run --project backend python scripts/build_geo.py`, never hand-edit (a test guards winding and the frame).
```
`README.md` "How it works": add item 5:
```
5. **Map** — the eight viewpoints on a tile-free SVG map (US Census land/water polygons, bundled), each dot colored by its likelihood for the selected window. Tap a dot to select it.
```
and in "Stack" add `- `data/` — coastline GeoJSON built by `scripts/build_geo.py` from Census TIGERweb; committed.`

- [ ] **Step 2: Full verification**

```bash
cd /Users/mike/claudeprojects/goodfog/backend && uv run pytest -q && cd ../frontend && npm test && npm run build
```
Expected: all green.

- [ ] **Step 3: Commit, push, PR**

```bash
cd /Users/mike/claudeprojects/goodfog && git add CLAUDE.md README.md && git commit -m "docs: map data and build script" && git push -u origin map-likelihood && gh pr create --title "Likelihood map above the viewpoint picker (0.2.0)" --body "$(cat <<'EOF'
Closes #4

## Summary
- Tile-free SVG map (Census land minus water for a fixed Marin/SF frame, committed as `data/coast.geojson`) with the eight viewpoints as dots colored by likelihood for the selected tab; Plan tab shows each spot's best window
- Tap a dot to select; selected dot ringed and labeled; Headlands cluster kept apart by a deterministic nudge
- Snapshot viewpoints gain `lat`/`lon`; version 0.2.0

Spec: docs/superpowers/specs/2026-09-02-goodfog-map-design.md
Plan: docs/superpowers/plans/2026-09-02-goodfog-map.md

## Test plan
- [ ] `cd backend && uv run pytest`
- [ ] `cd frontend && npm test && npm run build`
- [ ] Browser: map renders, dots select viewpoints, colors follow the tab

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01Uucw9EqwctfzAmKYxTpBpK
EOF
)"
```
