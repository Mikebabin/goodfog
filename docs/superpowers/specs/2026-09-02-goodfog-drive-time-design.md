# Good Fog — Drive Time Design Spec

**Date:** 2026-09-02
**Status:** Approved for planning
**Issue:** https://github.com/Mikebabin/goodfog/issues/7
**Builds on:** `docs/superpowers/specs/2026-09-02-goodfog-design.md`,
`docs/superpowers/specs/2026-09-02-goodfog-map-design.md`

## 1. Purpose

Let a user say where they are (typed address or browser geolocation) and see how long the
drive is to each of the eight viewpoints, plus a "Leave by" time for the selected window,
so they can pick the spot they can actually reach before the light.

**Success criteria**

- An origin box sits above the viewpoint picker. Entering an address and pressing Go, or
  tapping the 📍 button, resolves an origin and shows its label with a ✕ to clear it.
- Within a couple of seconds each viewpoint card shows "~32 min drive" (or "—" if that
  destination is unroutable); the Timing card shows "Drive" and "Leave by" rows; the Plan
  tab's compare columns show the drive time once under the card title.
- The origin persists across visits (localStorage). Clearing it removes every drive label.
- With no `ORS_API_KEY` configured the origin box is not rendered and nothing else changes.
- The OpenRouteService key never reaches the browser; the browser talks only to `/api/*`.
- A full re-run of the eight-destination drive lookup costs exactly one upstream request.

## 2. Decisions

| Decision | Choice | Why |
|---|---|---|
| Provider | OpenRouteService (ORS), free plan | One key covers directions/matrix and Pelias geocoding; no card; quotas (matrix ≈500/day, geocode ≈1000/day) are ample for a hobby app |
| Where the call happens | Backend proxy | Keeps the key server-side (project rule: secrets only via env vars); lets us cache and throttle |
| Routing call | One `matrix` request, origin → all eight viewpoints | 1 request instead of 8; matrix returns durations and distances together |
| Traffic | Free-flow only, labelled "no traffic" in the UI | ORS free tier has no live traffic; honest labelling beats false precision |
| Origin input | Address field + Go, 📍 geolocation, remembered in localStorage `goodfog.origin` | Planning from work or home both matter; persistence removes the biggest friction |
| Address matching | Geocode on submit, `size=1`, `focus.point` on the Golden Gate, `boundary.country=US` | No autocomplete → far fewer quota hits; focus makes "24th St" resolve to SF not NYC |
| Cache | In-memory TTL cache keyed on origin rounded to 3 decimals (~100 m), 1 h, 500 entries | Repeat visits and map re-renders don't burn quota; small enough to ignore memory |
| Placement | Picker cards + Timing card "Leave by" + Plan tab columns | Answers "which spot can I reach" and "when do I leave" without a new view |
| Leave-by math | Pure string/UTC arithmetic on the local ISO string, drive rounded **up** to the minute | Matches `fmtTime`'s no-tz approach; rounding up never tells the user to leave too late |
| Privacy | Origins are never logged or persisted server-side; cache holds rounded coordinates only | Location is sensitive; the server has no business remembering it |
| Version | 0.3.0 in both manifests | User-visible feature |

**Out of scope:** turn-by-turn directions, route polylines on the map, live traffic,
autocomplete, multiple saved origins, walking/transit modes, rate limiting per client IP.

## 3. Backend

### 3.1 Config (`config.py`)

`Settings` gains `ors_api_key: str | None` read from env `ORS_API_KEY` (stripped; empty →
`None`). Nothing else changes. `docker-compose.yml` passes `ORS_API_KEY: ${ORS_API_KEY:-}`
to the `api` service. README, GETTING-STARTED and CLAUDE.md list the new variable and
state that drive time is optional and disabled without it.

### 3.2 Provider (`providers/ors.py`)

```python
BASE = "https://api.openrouteservice.org"

@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float

class RoutingError(ProviderError): ...

class OrsProvider:
    def __init__(self, client: httpx.AsyncClient, api_key: str): ...
    async def geocode(self, text: str) -> Place | None: ...
    async def matrix(self, origin: tuple[float, float], dests: list[tuple[float, float]]) -> list[Leg | None]: ...
```

- `geocode`: `GET {BASE}/geocode/search` with query `api_key`, `text`, `size=1`,
  `focus.point.lat=37.83`, `focus.point.lon=-122.48`, `boundary.country=US`. Returns the
  first feature as `Place(label=properties.label, lat=coords[1], lon=coords[0])`, or `None`
  when `features` is empty. Non-2xx, network error or malformed JSON → `RoutingError`.
- `matrix`: `POST {BASE}/v2/matrix/driving-car`, header `Authorization: <key>`, body
  `{"locations": [[lon, lat] for origin, *dests], "sources": [0], "destinations": [1..n],
  "metrics": ["duration", "distance"]}`. Returns one `Leg(seconds: int, meters: int)` per
  destination in order, taking `durations[0][i]` / `distances[0][i]`; a `null` cell becomes
  `None`. Seconds and meters are rounded to integers. Non-2xx / network / shape errors →
  `RoutingError`.
- All coordinates are (lat, lon) tuples on our side; the provider flips to ORS's
  `[lon, lat]` at the boundary and nowhere else.
- Timeout 10 s per request.

### 3.3 Pure helpers (`drive.py`)

```python
def round_origin(lat: float, lon: float) -> tuple[float, float]  # round(x, 3) each
def validate_origin(lat, lon) -> tuple[float, float]              # raises ValueError unless -90..90 / -180..180 and finite
def build_drive_response(viewpoints, legs, origin) -> dict
```

`build_drive_response` returns

```json
{
  "origin": {"lat": 37.7749, "lon": -122.4194},
  "drives": {
    "hawk-hill": {"seconds": 1540, "meters": 14830},
    "east-peak": null
  }
}
```

with one key per viewpoint id, `null` where the leg is `None`.

### 3.4 Cache (`drive.py`)

`DriveCache(ttl_seconds=3600, max_entries=500)` with `get(key, now) -> dict | None` and
`put(key, value, now)`. Pure: `now` is passed in (a float, seconds). Expired entries are
dropped on `get`; when full, `put` evicts the oldest inserted entry. Key is the rounded
origin tuple.

### 3.5 Endpoints (`app.py`)

`create_app(settings, poller, ors: OrsProvider | None = None, drive_cache=None)`. When
`settings.ors_api_key` is set, `main` builds an `OrsProvider` on the shared httpx client.

- `GET /api/geocode?q=<text>` → `200 {"label", "lat", "lon"}`; `404 {"detail": "no_match"}`
  when Pelias returns nothing; `422` when `q` is blank or > 200 chars; `503
  {"detail": "routing_unavailable"}` when no provider is configured or `RoutingError`.
- `POST /api/drive` body `{"lat": float, "lon": float}` → `200` drive response (§3.3);
  `422` on out-of-range coordinates; `503 routing_unavailable` when no provider or
  `RoutingError`. Cache is consulted with the rounded origin before calling ORS; the
  response's `origin` echoes the *rounded* coordinates.
- Neither endpoint logs the query or coordinates. Upstream failures log the status code
  only.
- `/api/health` gains `"drive": true|false` (provider configured).

### 3.6 Snapshot flag

`build_snapshot` gains keyword `features: dict` and emits it verbatim; the poller passes
`{"drive": settings.ors_api_key is not None}`. The frontend reads `snapshot.features.drive`
to decide whether to render the origin box.

## 4. Frontend

### 4.1 API (`lib/api.js`)

```js
export async function geocode(q, fetchImpl = fetch)     // → {status:'ok', place} | {status:'no_match'} | {status:'unavailable'} | {status:'error', error}
export async function fetchDrive(lat, lon, fetchImpl = fetch) // → {status:'ok', data} | {status:'unavailable'} | {status:'error', error}
```

Never throw; tagged results like `fetchSnapshot`.

### 4.2 Pure helpers (`lib/drive.js`, tested)

```js
export function fmtDrive(seconds)                // null → '—'; < 60 min → '32 min'; else '1 h 05 min' (round up to whole minutes)
export function leaveBy(arriveByIso, seconds)    // 'YYYY-MM-DDTHH:MM' minus ceil(seconds/60) minutes, day rollover handled, no tz
export function driveMinutes(seconds)            // Math.ceil(seconds / 60); null → null
```

`leaveBy` parses the components, does the arithmetic with `Date.UTC` so DST and the
viewer's zone cannot leak in, and formats back to the same 16-char local ISO shape
`fmtTime` expects.

### 4.3 Origin state (`lib/origin.js`, tested)

```js
export const ORIGIN_KEY = 'goodfog.origin';
export function loadOrigin(storage)                  // parses {label, lat, lon}; anything malformed → null
export function saveOrigin(storage, origin)          // origin null → removeItem
```

### 4.4 Components

- **`OriginPicker.svelte`** — props `origin`, `busy`, `error`, `onsubmit(text)`,
  `onlocate()`, `onclear()`. Idle: text input (placeholder "Your address or neighborhood"),
  Go button, 📍 button. Resolved: "From **{label}** · drive times, no traffic" with ✕.
  Errors render inline in muted red: "Address not found", "Location blocked or unavailable",
  "Drive times unavailable right now". Geolocation uses `navigator.geolocation
  .getCurrentPosition` with a 10 s timeout and label "My location".
- **`LocationPicker.svelte`** — new optional prop `drives` (`{[id]: {seconds}} | null`).
  When present, each card shows a third line `~32 min drive` (or `—`).
- **`TimingCard.svelte`** — new optional prop `drive` (`{seconds} | null | undefined`).
  When a drive exists, adds rows `Drive  32 min` and `Leave by  6:58 PM`; the Leave-by
  row is emphasised (same style as Arrive by). Gate warning row stays last.
- **`PlanView.svelte`** — new optional prop `drive`; when present shows
  `🚗 32 min drive · no traffic` under the card title.
- **`App.svelte`** — state `origin` (from `loadOrigin`), `drives` (`null` until fetched),
  `driveBusy`, `driveError`. Effects: when `origin` changes, save it and call `fetchDrive`
  (clearing `drives` on null). On `unavailable` set `driveError` and clear `drives`.
  Renders `OriginPicker` between the map and the picker only when
  `snapshot.features?.drive` is true; passes `drives`/`drive` down.

## 5. Error handling

| Situation | Behaviour |
|---|---|
| No key configured | Snapshot `features.drive=false`; origin box hidden; endpoints 503 |
| ORS down / 5xx / timeout | Endpoint 503 `routing_unavailable`; UI shows "Drive times unavailable right now", keeps origin |
| Address not found | 404 `no_match`; UI "Address not found", input keeps its text |
| Geolocation denied | UI "Location blocked or unavailable"; nothing sent to server |
| One unroutable destination | That leg is `null`; card shows "—"; others unaffected |
| Bad coordinates | 422; UI treats as `error` and shows the generic unavailable message |

## 6. Testing

Backend (`pytest`, `respx`):
- `test_ors.py`: geocode happy path (fixture `fixtures/ors_geocode.json`), empty features →
  `None`, 401 → `RoutingError`; matrix happy path (`fixtures/ors_matrix.json`) returns legs
  in order with `None` for null cells; asserts request body uses `[lon, lat]`, `sources=[0]`,
  and the `Authorization` header.
- `test_drive.py`: `round_origin`, `validate_origin` bounds, `build_drive_response` shape,
  `DriveCache` hit/miss/expiry/eviction with injected `now`.
- `test_app.py` additions: 503 when no provider; `/api/drive` 200 + cached second call makes
  one upstream request; 422 on bad coords; `/api/geocode` 200/404/422; health `drive` flag.
- `test_config.py`: `ORS_API_KEY` unset/blank → `None`, set → stripped value.
- `test_snapshot.py`: `features` echoed.

Frontend (`vitest`): `drive.test.js` (`fmtDrive` rounding and hour formatting, `leaveBy`
including midnight rollover and 0 s), `origin.test.js` (malformed storage → null,
round-trip, remove on null), `api.test.js` additions (tagged results for 404/503/throw).

## 7. Deployment

Add `ORS_API_KEY` to the Coolify app's environment (Mike pastes it in the Coolify UI so
the value never passes through this session). Without it the feature stays hidden, so the
deploy is safe to ship before the key exists.
